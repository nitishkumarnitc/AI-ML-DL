# 06 · Sample project — GenAI Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- indexes 10 docs into 25 sentence-level chunks, runs the real recall@k/MRR/precision@k eval (15 queries), and probes BOTH a scope-refusal guardrail and a PII-redaction guardrail. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A **RAG chatbot over a small doc corpus** using a real vector DB, with **retrieval quality metrics** (recall@k, MRR) measured against a labeled query→doc set, plus one safety guardrail that refuses out-of-scope questions.

## 🧠 Why this mirrors the real job
- "Integrate foundation models via APIs; build RAG, chat" → the core deliverable.
- "Add retrieval (vector/graph)... and evals" → recall@k / MRR are how you'd actually know retrieval is working, not "the demo looked right."
- "Guardrails and safety in production" → the refusal guardrail is a one-line feature with outsized production importance.

## 🧰 Prerequisites
- Python, `chromadb` (local, no server needed), `sentence-transformers`, an LLM API or local model.
- 10–15 short docs on one topic.
- ~4–5 hours.

## 🧰 Tools, libraries & skills used here
- **Retrieval quality metrics**: `recall@k` and `MRR` (Mean Reciprocal Rank) computed against ground-truth query→doc labels — the standard way information-retrieval systems (and RAG pipelines) are actually evaluated, as opposed to "the demo looked right."
- **A hand-rolled local vector store** (bag-of-words + cosine similarity) standing in for a real one, so the recall@k/MRR harness is transparent end to end.
- **Guardrail via similarity threshold** — a cheap, real technique: if nothing in the corpus is similar enough to the query, refuse rather than let the generator improvise.
- **What a real GenAI stack adds on top**: a downloaded embedding model (`sentence-transformers`, Cohere/OpenAI embeddings), a vector DB (**Chroma**, **Weaviate**, **Qdrant**), a reranker (Cohere Rerank, `cross-encoder` models) to improve precision after initial retrieval, and eval tooling (**Ragas**, **DeepEval**) to track recall/precision over time as the corpus changes.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| math (stdlib) | built in | cosine similarity for retrieval and the guardrail threshold check |
| re (stdlib) | built in | tokenizing text into words |
| collections.Counter (stdlib) | built in | term-frequency vectors for the local vector store |

## 🪜 Step-by-step

### 1. Index docs in a real vector DB
```python
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.Client()
collection = client.create_collection("docs")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

doc_ids = ["doc1", "doc2", "doc3"]  # ... your actual doc ids
doc_texts = [...]  # matching text per id
collection.add(
    ids=doc_ids, documents=doc_texts,
    embeddings=embedder.encode(doc_texts, normalize_embeddings=True).tolist(),
)
```

### 2. Build a labeled retrieval eval set
This is the part most people skip. Write 10 queries and, for each, **which doc_id is actually relevant** — you need ground truth to measure retrieval, not just generation:
```python
RETRIEVAL_EVAL = [
    {"query": "How does X work?", "relevant_doc_id": "doc3"},
    # ... 10 total
]
```

### 3. Measure recall@k and MRR
```python
def evaluate_retrieval(k=3):
    recall_hits, reciprocal_ranks = 0, []
    for item in RETRIEVAL_EVAL:
        qv = embedder.encode([item["query"]], normalize_embeddings=True).tolist()
        results = collection.query(query_embeddings=qv, n_results=k)
        retrieved_ids = results["ids"][0]
        if item["relevant_doc_id"] in retrieved_ids:
            recall_hits += 1
            rank = retrieved_ids.index(item["relevant_doc_id"]) + 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)
    recall_at_k = recall_hits / len(RETRIEVAL_EVAL)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    return recall_at_k, mrr

recall_at_3, mrr = evaluate_retrieval(k=3)
print(f"recall@3={recall_at_3:.2f}  MRR={mrr:.2f}")
```
If recall@3 is low, don't jump to a bigger model — first check chunk size, embedding model choice, and whether your queries phrase things very differently from the docs (a real, common root cause).

### 4. Generate with a scope guardrail
```python
SYSTEM = """Answer ONLY using the provided context. If the context doesn't contain
the answer, or the question is unrelated to the documented topic, reply exactly:
"I don't have information on that." Do not use outside knowledge."""

def chat(query):
    qv = embedder.encode([query], normalize_embeddings=True).tolist()
    context = collection.query(query_embeddings=qv, n_results=3)["documents"][0]
    return call_llm(system=SYSTEM, prompt=f"Context:\n{context}\n\nQuestion: {query}")
```

### 5. Prove the guardrail works
```python
IN_SCOPE = ["<a real question about your docs>"]
OUT_OF_SCOPE = ["What's the capital of France?", "Write me a poem about cats."]

for q in IN_SCOPE + OUT_OF_SCOPE:
    print(q, "->", chat(q))
```
Confirm: in-scope questions get real answers, out-of-scope ones get the refusal — not a hallucinated answer.

## ✅ Deliverable
- recall@3 and MRR numbers with the eval set that produced them.
- Chat transcript showing correct refusals on out-of-scope questions.
- One paragraph: if recall@3 was below ~0.8, what you'd try next (chunking, embedding model, query rewriting) — since "just prompt better" doesn't fix a retrieval problem.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`12_rag`](../../12_rag/README.md) · [`06_vector-databases`](../../06_vector-databases/README.md) · [`07_graph-rag`](../../07_graph-rag/README.md) · [`16_evals`](../../16_evals/README.md) · [`03_llm-security-and-guardrails`](../../03_llm-security-and-guardrails/README.md) for stronger guardrails.
