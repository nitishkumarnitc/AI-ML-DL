# 05 · Sample project — Applied AI / LLM Product Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- runs the real RAG pipeline over a 10-doc corpus, prints the eval results + latency/cost log, and demos multi-turn memory (a follow-up question gets rewritten using the prior one). `--ask`, `--interactive`, and `--json-out` are all real CLI options. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A small **RAG feature shipped end-to-end**: answer questions over a handful of docs, with structured output, a per-query latency/cost log, and a 5-question eval set — then a one-page tradeoff writeup on prompt-only vs RAG vs fine-tune for this use case.

## 🧠 Why this mirrors the real job
- "Design LLM features: prompting, RAG... structured output, guardrails" → all four appear below.
- "Ship and operate them: latency, cost, evals" → you log real numbers per call, not just "it works on my machine."
- "Pick the right pattern (fine-tune vs RAG vs prompt)" → the writeup forces you to justify the choice, which is the actual product-engineering judgment call.

## 🧰 Prerequisites
- Python, an LLM API (or local model), a small embedding model (`sentence-transformers` or an API embedding endpoint).
- 8–10 short markdown/text docs on one topic (your own notes work fine).
- ~4–5 hours.

## 🧰 Tools, libraries & skills used here
- **Information retrieval fundamentals**: term-frequency vectors, cosine similarity, stopword filtering, and light stemming — implemented from scratch here so you understand what an embedding-based retriever is actually approximating.
- **Structured output & guardrails**: a fixed response shape (`answer`/`confidence`/`source_chunk_ids`) and a similarity threshold that triggers an honest refusal instead of a guess.
- **Instrumentation**: per-query latency and token/cost logging — the exact metrics a product engineer reports to justify a design choice or catch a regression.
- **What a real RAG stack adds on top**: a real embedding model (`sentence-transformers`, OpenAI/Voyage embeddings), a vector database (**Chroma**, **Pinecone**, **Weaviate**, **pgvector**), an orchestration layer (**LangChain**, **LlamaIndex**), token counting (**tiktoken**), and an eval framework (**Ragas**, **TruLens**) to measure retrieval + generation quality continuously.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| math (stdlib) | built in | cosine similarity (sqrt/dot product) for retrieval |
| re (stdlib) | built in | tokenizing text into words |
| time (stdlib) | built in | measuring retrieval/generation latency per query |
| collections.Counter (stdlib) | built in | term-frequency vectors for bag-of-words retrieval |

## 🪜 Step-by-step

### 1. Chunk and embed your docs
```python
from sentence_transformers import SentenceTransformer
import numpy as np, glob

embedder = SentenceTransformer("all-MiniLM-L6-v2")
docs = [open(f).read() for f in glob.glob("docs/*.md")]
chunks = [c for d in docs for c in d.split("\n\n") if c.strip()]
chunk_vecs = embedder.encode(chunks, normalize_embeddings=True)
```

### 2. Retrieve + generate with structured output
```python
import time, json

class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter(); return self
    def __exit__(self, *a):
        self.elapsed = time.perf_counter() - self.t0

def retrieve(query, k=3):
    qv = embedder.encode([query], normalize_embeddings=True)[0]
    scores = chunk_vecs @ qv
    top_idx = np.argsort(-scores)[:k]
    return [chunks[i] for i in top_idx]

SCHEMA_PROMPT = """Answer using ONLY the context. Respond as JSON:
{"answer": "...", "confidence": "high|medium|low", "source_chunk_ids": [...]}"""

def answer(query):
    with Timer() as retrieval_t:
        context = retrieve(query)
    prompt = f"{SCHEMA_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}"
    with Timer() as gen_t:
        raw = call_llm(prompt)  # your LLM client call; count input/output tokens too
    return json.loads(raw), retrieval_t.elapsed, gen_t.elapsed
```

### 3. Log cost + latency per query
```python
LOG = []

def answer_and_log(query, price_per_1k_tokens=0.002):
    result, retrieval_s, gen_s = answer(query)
    tokens_used = estimate_tokens(query, result)  # rough word-count/4 estimate is fine
    LOG.append({
        "query": query, "retrieval_ms": retrieval_s * 1000, "gen_ms": gen_s * 1000,
        "total_ms": (retrieval_s + gen_s) * 1000,
        "est_cost_usd": tokens_used / 1000 * price_per_1k_tokens,
    })
    return result
```

### 4. Build a 5-question eval set
Write 5 questions with a known correct answer from your docs. Score exact/substring match, or fuzzy match if answers are free text:
```python
EVAL = [{"q": "...", "expected_substring": "..."} for _ in range(5)]

def run_eval():
    correct = 0
    for item in EVAL:
        result = answer_and_log(item["q"])
        if item["expected_substring"].lower() in result["answer"].lower():
            correct += 1
    return correct / len(EVAL)
```

### 5. Write the tradeoff memo
Answer explicitly:
- **Prompt-only** (no retrieval): would it work here? Why/why not — is the answer outside model knowledge?
- **RAG** (what you built): what's the failure mode — retrieval missing the right chunk, or generation ignoring context?
- **Fine-tune**: would it help *this* problem, or is it solving a different one (style vs facts)?
- **Cost/latency**: from your log — mean/median `total_ms` and `est_cost_usd` per query. Is this shippable at expected traffic?

## ✅ Deliverable
- Working RAG script + `LOG` (latency/cost per query) + eval pass rate.
- One-page tradeoff memo (prompt vs RAG vs fine-tune) with your recommendation and why.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`01_prompt-engineering`](../../01_prompt-engineering/README.md) · [`12_rag`](../../12_rag/README.md) · [`06_vector-databases`](../../06_vector-databases/README.md) · [`16_evals`](../../16_evals/README.md) · [`18_ragapp`](../../18_ragapp/README.md) — full system design.
