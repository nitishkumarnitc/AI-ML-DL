# 10 · Fixing the Latency: FAISS Index Persistence

> ← [`09-one-trace-not-two.md`](09-one-trace-not-two.md) · **Next:** [`11-tracing-react-agents.md`](11-tracing-react-agents.md) →

---

Problem 2 from lesson 07: every query re-loaded, re-chunked and re-embedded 441 pages — **~202 seconds per query**. This lesson fixes it, and the fix is the single most important production practice in RAG.

The author is candid in the video that this code is more involved than the rest and that the point of the lesson is LangSmith, not writing the world's best RAG. Fair. But the *invalidation logic* is where the real content is, so that's what this lesson concentrates on.

---

## The idea

Embeddings are a **pure function** of three things:

```
embeddings = f(document content, chunking parameters, embedding model)
```

Pure function of unchanged inputs → **cacheable**. FAISS can serialise an index to disk. So:

```
first run ever   :  load → chunk → embed → SAVE index to disk → answer
every run after  :  LOAD index from disk → answer
```

---

## The code

`03_rag_v4.py`:

```python
# 03_rag_v4.py
import os, json, hashlib
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGSMITH_PROJECT"] = "RAG Chatbot"

from langsmith import traceable
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

PDF_PATH        = "islr.pdf"
INDEX_DIR       = Path("faiss_index")
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 150
EMBEDDING_MODEL = "text-embedding-3-small"


# ---------------------------------------------------------------- fingerprint
def index_fingerprint(path: str) -> dict:
    """Everything that, if changed, invalidates the index."""
    st = os.stat(path)
    return {
        "pdf_path":        path,
        "pdf_size":        st.st_size,
        "pdf_mtime":       int(st.st_mtime),
        "chunk_size":      CHUNK_SIZE,
        "chunk_overlap":   CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
    }


def fingerprint_matches(fp: dict) -> bool:
    meta_file = INDEX_DIR / "fingerprint.json"
    if not INDEX_DIR.exists() or not meta_file.exists():
        return False
    return json.loads(meta_file.read_text()) == fp


# ---------------------------------------------------------------- build / load
@traceable(name="load_pdf", tags=["pdf", "loader"],
           metadata={"loader": "PyPDFLoader"})
def load_pdf(path):
    return PyPDFLoader(path).load()


@traceable(name="split_documents")
def split_documents(documents):
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).split_documents(documents)


@traceable(name="build_vector_store", tags=["embeddings", "vector_store"],
           metadata={"embedding_model": EMBEDDING_MODEL})
def build_vector_store(chunks):
    return FAISS.from_documents(chunks, OpenAIEmbeddings(model=EMBEDDING_MODEL))


@traceable(name="build_index", tags=["lifecycle", "index_build"])
def build_index(path, fp):
    docs   = load_pdf(path)
    chunks = split_documents(docs)
    store  = build_vector_store(chunks)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    store.save_local(str(INDEX_DIR))
    (INDEX_DIR / "fingerprint.json").write_text(json.dumps(fp))
    return store


@traceable(name="load_index", tags=["lifecycle", "index_load"])
def load_index():
    return FAISS.load_local(
        str(INDEX_DIR),
        OpenAIEmbeddings(model=EMBEDDING_MODEL),
        allow_dangerous_deserialization=True,   # see the warning below
    )


@traceable(name="get_retriever", tags=["lifecycle"])
def get_retriever():
    fp = index_fingerprint(PDF_PATH)
    if fingerprint_matches(fp):
        store = load_index()                    # fast path
    else:
        store = build_index(PDF_PATH, fp)       # slow path
    return store.as_retriever(search_kwargs={"k": 4})


retriever = get_retriever()
chain     = build_chain(retriever)

while True:
    q = input("\nAsk: ")
    if not q:
        break
    print(chain.invoke(q, config={"run_name": "pdf_rag_query"}))
```

> **⚠️ `allow_dangerous_deserialization=True`.** FAISS's LangChain wrapper stores the docstore via **pickle**, and unpickling arbitrary data executes arbitrary code. LangChain requires this flag as a deliberate speed bump. It is safe for an index **your own process wrote to your own disk**. It is *not* safe for an index downloaded from anywhere, restored from an untrusted bucket, or shipped by a third party. For a multi-tenant or user-uploadable corpus, use a store that doesn't pickle (pgvector, Qdrant, Chroma, Weaviate) rather than reaching for the flag. The video does not raise this; it matters.

---

## The numbers

| Run | Path taken | Latency |
|---|---|---|
| First ever (no index) | `build_index` → load, split, embed, save | **~30 s** |
| Second, new question | `load_index` | **1.65 s** |
| Third, broader question | `load_index` + more docs retrieved | **4.42 s** |

From **~202 s** to **1.65 s**. Two orders of magnitude, from caching a pure function.

The third row is instructive too: 4.42 s rather than 1.65 s, because that question retrieved more context, so the LLM had more input tokens to process. **Not a regression — a longer prompt.** Being able to tell those two apart at a glance is exactly what per-run token counts are for.

---

## Reading the two paths in LangSmith

The trace shape *tells you which path ran*, which makes this self-documenting:

### Cold (first run, ~30 s)

```
build_index                                     ~30 s
├── load_pdf              → 441 Documents        15 s
├── split_documents       → N chunks             fast
└── build_vector_store    → FAISS store          slow ★
```

### Warm (subsequent, ~1.65 s)

```
load_index                                       fast
└── output: the deserialised FAISS store
```

One glance at the run name — `build_index` vs `load_index` — and you know whether you paid for embedding. If you ever see `build_index` in production traces after the first deploy, **something is invalidating your index and you have a bug**. That is a monitoring rule you can write (lesson 13): alert if any trace tagged `index_build` appears outside a deploy window.

---

## When does the index rebuild?

The five conditions from the video, and what each one is guarding against:

| # | Condition | Why it must invalidate |
|---|---|---|
| 1 | **No index exists** — first run ever | Nothing to load |
| 2 | **PDF content changed** | The embeddings describe the old text |
| 3 | **PDF metadata changed** — file size or last-modified time | Cheap proxy for "content changed" without reading the file |
| 4 | **Chunking parameters changed** — `chunk_size` or `chunk_overlap` | Different boundaries → entirely different chunks → different vectors |
| 5 | **Embedding model changed** | **Vectors from different models are not comparable at all.** Different geometry, often different dimensionality. Querying a `3-small` index with `3-large` embeddings returns nonsense — or crashes on a dimension mismatch |

Condition 5 is the one that causes silent quality collapse if you get it wrong: if dimensionality happens to match, nothing errors, and retrieval quality just quietly becomes garbage. **Always put the embedding model in the fingerprint.**

### ⭐ Content hash vs mtime

*Added.* Conditions 2 and 3 in the video are handled by size + mtime. That's fast and usually right, but it fails in both directions:

| Failure | Cause | Consequence |
|---|---|---|
| **False rebuild** | `git checkout` or a file copy resets mtime without changing content | You pay 30 s and an embedding bill for nothing |
| **False reuse** | Content edited to the same byte length with mtime preserved (rsync, some build tools, artefact restores) | **You serve answers from a stale index and never find out** |

The false-reuse case is the dangerous one. Hash the content instead:

```python
def content_hash(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()
```

Then use `{"pdf_sha256": content_hash(path), "chunk_size": ..., "embedding_model": ...}` as the fingerprint. Cost: a few hundred milliseconds of disk read for a large PDF. Benefit: correctness you don't have to think about again. For a multi-document corpus, hash the sorted list of per-file hashes so a single changed file invalidates deterministically.

---

## ⭐ Beyond the video — what this looks like at production scale

*Added.*

The fingerprint pattern is the right *idea* at any scale, but the mechanics change:

| Scale | Approach |
|---|---|
| One PDF, one process | Exactly the above — local FAISS + fingerprint file |
| One corpus, several replicas | Build the index in **CI**, publish it as a versioned artefact, have replicas download the pinned version at boot. Never let request-serving replicas build indexes — you'd pay N times and get N slightly different indexes |
| Corpus changes continuously | Move to a **real vector database** (pgvector, Qdrant, Weaviate, Pinecone). Incremental upsert per document, no monolithic rebuild |
| Multiple tenants | One namespace/collection per tenant. The fingerprint pattern doesn't survive here; the database's own consistency does |

Two rules that survive every scale change:

1. **Never embed on the request path.** Embedding the *query* is fine and unavoidable — it's one short call. Embedding the *corpus* on a request path is the bug this lesson is about.
2. **Version the index and record the version in trace metadata.** `metadata={"index_version": "2026-08-31-a3f9c1"}` costs nothing and lets you answer "did quality drop when we re-indexed?" — which is otherwise unanswerable, because you cannot get the old index back to compare.

---

## Recap

- Embeddings are a **pure function** of (content, chunking parameters, embedding model) → cacheable.
- Persist with `store.save_local(...)`, restore with `FAISS.load_local(...)`, gate on a **fingerprint**.
- **~202 s → 1.65 s.** The remaining variation across warm queries is prompt length, not regression — token counts distinguish them.
- The **run name tells you which path ran**. `build_index` in steady-state production is an alertable bug.
- Rebuild on: no index · content change · metadata change · chunking-parameter change · **embedding-model change**. The last is non-negotiable — cross-model vectors are incomparable.
- Prefer a **content hash** over size+mtime; the false-reuse failure is silent and serves stale answers.
- `allow_dangerous_deserialization=True` is pickle. Fine for indexes you wrote; never for indexes you received.
- At scale: build in CI, publish a versioned artefact, or use a real vector DB. **Never embed the corpus on a request path.** Record `index_version` in metadata.

---

## Exercise

1. Run cold, then warm. Confirm `build_index` vs `load_index` in the trace and note both latencies.
2. Change `chunk_size` from 1000 to 800. Predict which path runs, then verify.
3. `touch islr.pdf` without editing it. Does the mtime fingerprint rebuild? Should it? Swap in the content hash and re-test.
4. Add `index_version` to the chain's `config` metadata and confirm it appears on the query trace.
5. Ask a narrow question and a broad one. Compare latency *and* input-token count. Explain the difference without using the word "slow".

---

**Next:** [`11-tracing-react-agents.md`](11-tracing-react-agents.md) →
