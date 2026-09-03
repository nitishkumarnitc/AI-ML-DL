# 03 — RAG & Retrieval

> They explicitly want: advanced retrieval, **hybrid search (BM25 + vector)**, and **knowledge graph integrations**. Debt markets = massive document corpora (loan agreements, covenants, term sheets, credit reports, regulatory filings).

---

## 🧱 RAG pipeline anatomy (draw this)

```
Ingest → Parse/Clean → Chunk → Embed → Index (vector + keyword + KG)
                                              │
Query → (rewrite/expand) → Retrieve (hybrid) → Rerank → Assemble context → LLM → (cite/verify) → Answer
```

Every stage has failure modes and levers. Principal signal = you know **where quality is actually lost** (usually retrieval + chunking, not the LLM).

---

## 🔍 Hybrid search: BM25 + Vector (they named it)

- **BM25 / keyword (sparse):** exact terms, rare tokens, IDs, names, numbers, legal clauses. Great for "clause 4.2", account numbers, exact entity names.
- **Vector / dense (semantic):** paraphrase, concept, synonym matching. Great for "what are the prepayment penalties" matching differently-worded text.
- **Why hybrid:** dense misses exact identifiers; sparse misses semantics. Fintech docs have **both** precise identifiers AND natural-language clauses → hybrid is close to mandatory.
- **Fusion:** **Reciprocal Rank Fusion (RRF)** is the pragmatic default (rank-based, no score normalization needed). Or weighted score combination (requires normalization). Mention **learned fusion** as the advanced option.
- **Implementations:** Elasticsearch/OpenSearch (BM25 + kNN in one), Weaviate/Qdrant/pgvector + separate BM25, or Vespa. Given AWS: **OpenSearch** (managed, does both) is a natural pick.

**Say this:** *"I'd run BM25 and vector in parallel, fuse with RRF, then rerank the top-k with a cross-encoder. For debt docs the sparse leg is what saves us on exact clause and identifier lookups that pure embeddings fumble."*

---

## 🎯 Reranking

- Retrieve broad (top 50–100), **rerank** to top 5–10 with a **cross-encoder** (e.g., Cohere Rerank, bge-reranker, or a hosted reranker). Cross-encoders score query+doc jointly → far more precise than bi-encoder similarity.
- Trade-off: latency/cost per candidate → rerank a bounded candidate set, not the whole corpus.
- Big quality lever, often bigger than swapping the LLM.

---

## ✂️ Chunking (where most RAG quality dies)

- **Fixed-size w/ overlap** — simple baseline.
- **Semantic / structure-aware** — split on document structure (sections, clauses, tables). **Critical for legal/financial docs** — a covenant split mid-clause is useless.
- **Parent-document / hierarchical** — retrieve small chunks for precision, feed the parent section for context.
- **Table & layout handling** — financial docs are table-heavy; naive text extraction destroys tables. Use layout-aware parsing (e.g., structured PDF extraction) and keep tables intact or convert to markdown/structured form.
- **Metadata on every chunk** — doc id, section, date, entity, source, version → enables **filtering** (e.g., "only 2025 filings for entity X") and **citations**.

**Principal point:** *"Retrieval quality is set at ingestion. I invest in structure-aware chunking and rich metadata before touching the model — most RAG failures are retrieval failures dressed up as hallucinations."*

---

## 🕸️ Knowledge Graphs / GraphRAG (they named this)

- **Why KG in debt markets:** entities (borrowers, lenders, guarantors, instruments, covenants) have **relationships** (owns, guarantees, subordinated-to, cross-defaults-with). Pure vector RAG can't do **multi-hop** reasoning ("which loans are exposed if entity X defaults?").
- **GraphRAG pattern:** extract entities+relations into a graph (Neo4j / Amazon Neptune), retrieve subgraphs relevant to the query, feed structured context to the LLM. Great for **multi-hop, aggregation, and "connect the dots" questions**.
- **Hybrid: vector + KG** — vector for unstructured passage retrieval, KG for structured relationship/traversal. Combine for questions needing both narrative and relationship reasoning.
- **Cost/complexity caveat:** KG extraction + maintenance is expensive and can drift. *"I'd add a KG where multi-hop relationship queries are core to the product value, not as a default — it's a real ops investment."*

---

## 🔧 Advanced retrieval techniques (name-drop with judgment)

- **Query rewriting / expansion** — decontextualize follow-ups, expand acronyms, multi-query.
- **HyDE** (hypothetical document embeddings) — embed a hypothetical answer to improve recall.
- **Multi-query / fusion retrieval** — generate query variants, union + rerank.
- **Metadata filtering + self-query** — LLM extracts filters (date/entity) from the question.
- **Contextual retrieval** (Anthropic technique) — prepend chunk-situating context before embedding; big recall win.
- **Small-to-big / sentence-window** — retrieve precise, expand for context.
- **Agentic RAG** — agent decides *what/whether* to retrieve, iterates, verifies → ties to [02](02_Agentic_AI_and_Orchestration.md).

Don't list all — pick 2–3 relevant to the scenario and justify.

---

## 📏 RAG evaluation (they'll ask "how do you know it's good?")

Two halves — **retrieval** and **generation**:

- **Retrieval:** recall@k, precision@k, MRR, NDCG. Need a labeled query→relevant-doc set (build via SMEs + synthetic query generation).
- **Generation:** **faithfulness/groundedness** (is the answer supported by retrieved context?), **answer relevance**, **context relevance/utilization**. Frameworks: **RAGAS**, TruLens, or custom **LLM-as-judge**.
- **Hallucination = groundedness failure.** Enforce **citations**; verify each claim maps to a retrieved span; refuse/abstain when context is insufficient. → deep dive in [04](04_LLMOps_Eval_Guardrails.md).
- **Golden dataset + regression suite** — every change (chunking, embedder, reranker, prompt) runs against it. No shipping on vibes.

---

## 🎙️ Likely questions + scaffolds

- **"Design RAG over 10M loan documents."** → ingestion (layout-aware parse, structure chunking, metadata) → hybrid index (OpenSearch BM25+kNN) → query rewrite → hybrid retrieve → cross-encoder rerank → grounded generation w/ citations → eval harness (RAGAS + golden set) → freshness (re-index on doc updates via Kafka events) → access control (row/doc-level, PII). Add: KG for cross-entity exposure queries.
- **"Vector search returns garbage — debug it."** → Isolate stage: is it retrieval or generation? Check recall on a labeled set first. Common culprits: bad chunking, wrong embedding model/domain mismatch, no reranker, missing metadata filters, query/doc distribution mismatch. Fix retrieval before blaming the LLM.
- **"When is fine-tuning better than RAG?"** → RAG for knowledge/freshness/citations; fine-tune for format/style/behavior/latency. Often both. → [05](05_FineTuning_and_Alignment.md).
- **"How do you keep the index fresh with millions of changing docs?"** → event-driven re-indexing: doc-change events on **Kafka** → dedupe/debounce → re-embed changed chunks only → atomic index update / versioned aliases. Ties to [06](06_Distributed_Systems_Backend.md).
- **"How do you prevent leaking one client's docs to another?"** → doc-level ACLs enforced at retrieval (filter by tenant/entitlement *before* the LLM sees anything), tenant isolation in the index, never rely on the prompt for security.
