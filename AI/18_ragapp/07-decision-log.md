# Decision Log (ADRs) — Why the Models & Design

> **Modular Knowledge Assistant** · design set → [README](README.md) · **you are here: Decision Log**
>
> Architecture Decision Records: the **why** behind each significant model and design choice. Format per entry: **Context → Decision → Rationale → Alternatives considered → Trade-offs / revisit-if.** These are the questions a reviewer (or interviewer) will ask; each answer is here.

---

## Index

| # | Decision | Area |
|---|----------|------|
| [ADR-1](#adr-1--azure-openai-as-the-single-model-provider) | Azure OpenAI as the single model provider | Models |
| [ADR-2](#adr-2--embedding-model-text-embedding-3-small-at-1536-dims) | Embedding model: `text-embedding-3-small` @ 1536 | Models |
| [ADR-3](#adr-3--vlm--the-same-multimodal-chat-deployment) | VLM = the same multimodal chat deployment | Models |
| [ADR-4](#adr-4--langgraph--postgres-checkpointer-for-the-agent) | LangGraph + Postgres checkpointer | Design |
| [ADR-5](#adr-5--forced-retrieval-middleware) | Forced-retrieval middleware | Design |
| [ADR-6](#adr-6--dual-vector-backend-behind-one-interface) | Dual vector backend (Chroma / Azure AI Search) | Design |
| [ADR-7](#adr-7--event-driven-ingestion-via-sqs) | Event-driven ingestion via SQS | Design |
| [ADR-8](#adr-8--strict-service-separation-no-cross-imports) | Strict service separation | Design |
| [ADR-9](#adr-9--pdfplumber-for-text--tables) | pdfplumber for text + tables | Models/Libs |
| [ADR-10](#adr-10--libreoffice-for-docx--pdf) | LibreOffice for DOCX → PDF | Libs |
| [ADR-11](#adr-11--recursive-chunking-1000150-with-atomic-types) | Recursive chunking 1000/150; atomic types | Design |
| [ADR-12](#adr-12--agent-reads-assets-via-ingestion-api-not-s3) | Agent reads assets via ingestion API, not S3 | Design/Security |
| [ADR-13](#adr-13--store-image--vlm-text-embed-text-only) | Store image + VLM text; embed text only | Design |
| [ADR-14](#adr-14--file_id-vs-job_id-identity-model) | `file_id` vs `job_id` identity model | Design |
| [ADR-15](#adr-15--three-logical-postgres-databases) | Three logical Postgres databases | Design |
| [ADR-16](#adr-16--cleanup-order-vectors--objects--state) | Cleanup order + `FAILED_DELETE` | Reliability |
| [ADR-17](#adr-17--doc_summary-attached-to-every-chunk) | `doc_summary` on every chunk | Design |
| [ADR-18](#adr-18--excel-rows-fetched-live-not-embedded) | Excel rows fetched live, not embedded | Design |

---

## ADR-1 — Azure OpenAI as the single model provider

- **Context:** the system needs chat synthesis, embeddings, a VLM, transcription, and TTS.
- **Decision:** source **all** inference from **Azure OpenAI** (chat, embedding, vision, transcription deployments), integrated via `langchain-openai`.
- **Rationale:** one provider = one auth/config surface, one billing/quota model, and **enterprise/compliance posture** (data-residency, private networking, tenant isolation) that raw OpenAI or a mix of vendors doesn't give out of the box. Multimodal chat also covers the VLM need (ADR-3), avoiding a second vision vendor.
- **Alternatives:** OpenAI direct (weaker enterprise controls); a best-of-breed mix (embeddings from X, VLM from Y — more integrations, more failure surface); self-hosted open models (ops burden, no immediate need).
- **Trade-offs / revisit if:** provider lock-in and Azure-region model availability. The `langchain-openai` boundary keeps the surface swappable; revisit if cost at scale or a capability gap justifies self-hosting a specific model.

## ADR-2 — Embedding model `text-embedding-3-small` at 1536 dims

- **Context:** every chunk (text and VLM description) must be embedded into one shared vector space.
- **Decision:** default to **`text-embedding-3-small`** at **1536 dimensions**.
- **Rationale:** best **cost/latency-to-quality** ratio for enterprise RAG; 1536 dims keep index size and similarity-search cost modest while retrieving well. The value is a **template default**, not a hard-code.
- **Alternatives:** `text-embedding-3-large` (higher quality, ~3× dims → more storage/latency/cost — reach for it only if recall is provably insufficient); older `ada-002` (worse quality/price).
- **Trade-offs / revisit if:** the embedding model and dimensions are a **hard cross-service contract** (ADR-6) — changing them requires a **controlled re-index**, never an in-place flip (see [04 §7](04-api-contracts-and-data-flows.md), [05 §6](05-technology-stack-and-operations.md)). Revisit if retrieval recall on the golden set plateaus below target.

## ADR-3 — VLM = the same multimodal chat deployment

- **Context:** image-dense/scanned pages need a model to "read" them (see [06](06-visual-extraction-and-vlm.md)).
- **Decision:** use the **same Azure OpenAI multimodal chat deployment** as the VLM, gated by `INGESTION_ENABLE_VLM`.
- **Rationale:** reuse an existing deployment — no new vendor, credential, or client. The visual track is **optional and off by default**, so image-light corpora pay nothing.
- **Alternatives:** a dedicated OCR engine (e.g., Tesseract — good for clean scans, poor on charts/diagrams and semantics); a specialized document-AI service (more capable, another vendor + cost). A VLM captures **both** transcription *and* semantic description ("what the chart means") in one call.
- **Trade-offs / revisit if:** VLM calls are the most expensive per-page step → mitigated by cheap **visual detection** (only image-dense pages) and DPI tuning. Revisit if a corpus is dominated by clean scanned text (OCR could be cheaper) or needs specialized layout parsing.

## ADR-4 — LangGraph + Postgres checkpointer for the agent

- **Context:** the assistant is multi-turn, streams, must survive refreshes/restarts, and be auditable.
- **Decision:** build the agent as a **LangGraph** graph with a **PostgreSQL checkpointer**; expose it to the browser via AG-UI/SSE.
- **Rationale:** explicit, inspectable state machine with **durable checkpoints** → conversation **resume/hydration**, and a clean place for middleware (ADR-5). Postgres persistence means process restarts don't lose in-flight state.
- **Alternatives:** a bespoke orchestration loop (reinvents checkpointing/streaming); a purely conversational framework (weaker durability/auditability).
- **Trade-offs / revisit if:** framework coupling and checkpoint-table growth (mitigated by the tombstone sweeper, [03 §4](03-lld-agent-and-ui.md)).

## ADR-5 — Forced-retrieval middleware

- **Context:** with persisted checkpoints, a *prior* tool message in history can let a *new* user question skip retrieval and answer from stale context.
- **Decision:** a `wrap_model_call` middleware sets `tool_choice="any"` until a tool message exists **after the latest user turn** (see [03 §2](03-lld-agent-and-ui.md)).
- **Rationale:** guarantees **every new question is grounded in a fresh search**, not leftover context — the single most important correctness guard for a checkpointed RAG agent.
- **Alternatives:** trust the model to retrieve (unreliable); clear history each turn (loses conversational context).
- **Trade-offs / revisit if:** forces at least one retrieval per turn (minor extra latency/cost) — an intentional correctness-over-cost choice.

## ADR-6 — Dual vector backend behind one interface

- **Context:** local dev must be cheap/offline; production must be managed and scalable.
- **Decision:** a **provider-neutral vector interface** with **Chroma** (local/dev) and **Azure AI Search** (managed/prod) adapters; the same interface on write (ingestion) and read (agent).
- **Rationale:** frictionless local development (Chroma in a Docker volume) with a **production-grade managed** option, without changing application code. Enforced invariants (same provider/index/embedding/dims) prevent write-here-read-there bugs ([05 §3](05-technology-stack-and-operations.md)).
- **Alternatives:** single backend everywhere (either costly locally or weak in prod); a third vector DB (no need).
- **Trade-offs / revisit if:** two adapters to maintain and keep at feature parity. Adding a provider means implementing **both** read and write adapters + schema/dimension validation ([02 §10](02-lld-ingest-service.md)).

## ADR-7 — Event-driven ingestion via SQS

- **Context:** document processing is slow, spiky, and must accept **non-UI** sources; failures must be recoverable.
- **Decision:** decouple submission from processing with **SQS** — API/producer publishes a message; a consumer runs `process_job`; transient errors return to the queue; a DLQ catches poison messages.
- **Rationale:** **resilience** (retry/redelivery/DLQ), **backpressure** (pull at a sustainable rate), and **multi-source** ingestion (external systems publish the same message contract). Slow VLM/embedding work never blocks the request path.
- **Alternatives:** synchronous processing in the request (times out on big docs); a heavyweight task queue like Celery (more infra than needed given AWS-native SQS).
- **Trade-offs / revisit if:** the consumer currently runs **inside** the ingestion API process — fine for now, but high volume needs **independent worker scaling** (noted in [01 §9](01-hld.md), [05 §7](05-technology-stack-and-operations.md)).

## ADR-8 — Strict service separation (no cross-imports)

- **Context:** UI, agent (read), and ingestion (write) evolve independently.
- **Decision:** **no direct imports** between the three services; they communicate only via **HTTP, SQS, and a shared vector schema**.
- **Rationale:** independent deploy/scale, clear security boundaries (only ingestion holds S3/vector-write creds), and **replaceability** of any one service.
- **Alternatives:** a monolith (simpler locally, couples scaling and blast radius); a shared library of models (couples release cycles).
- **Trade-offs / revisit if:** cross-service contracts (metadata, queue message, embedding dims) must be versioned and changed **together** — the main coordination cost.

## ADR-9 — `pdfplumber` for text + tables

- **Context:** PDFs are the primary format and carry both prose and tables, and the pipeline needs page-level inspection for visual detection.
- **Decision:** use **`pdfplumber`** for per-page text, table extraction, and object inspection (`images`, `rects`, `lines`).
- **Rationale:** pure-Python (no system deps), solid **table** extraction, and the **page-object introspection** that powers visual detection (ADR-3 / [06 §2](06-visual-extraction-and-vlm.md)).
- **Alternatives:** PyMuPDF/fitz (faster, but AGPL licensing concerns); `pypdf` (weak tables); Unstructured/LlamaParse (heavier, external).
- **Trade-offs / revisit if:** `pdfplumber` is slower on very large PDFs — acceptable in an async worker; revisit for extreme-scale ingestion.

## ADR-10 — LibreOffice for DOCX → PDF

- **Context:** Word documents must be indexed with the same fidelity (incl. embedded images/figures) as PDFs.
- **Decision:** convert DOC/DOCX to **PDF via LibreOffice**, then **re-enter the PDF branch** (text + tables + visual/VLM), rather than parsing `.docx` directly.
- **Rationale:** **one high-fidelity path** — layout, tables, and embedded figures are preserved and get the same visual treatment ([02 §5](02-lld-ingest-service.md) DOCX→PDF edge). Avoids a second, lower-fidelity extraction code path.
- **Alternatives:** `python-docx` (loses layout/figures, no page images); a cloud converter (another dependency).
- **Trade-offs / revisit if:** LibreOffice is a heavy container binary that must be on `PATH` (covered by a DOCX smoke test, [05 §5](05-technology-stack-and-operations.md)).

## ADR-11 — Recursive chunking 1000/150, with atomic types

- **Context:** text must be split for embedding without shredding meaning; some units must never be split.
- **Decision:** **recursive character chunking** at `CHUNK_SIZE=1000` / `OVERLAP=150`; **`visual_insight`, `page_image`, and `excel_summary` are atomic** (not chunked).
- **Rationale:** 1000/150 balances **retrieval precision vs context continuity** for prose; overlap preserves cross-boundary meaning. Splitting a figure's description, an image reference, or a sheet summary would be nonsensical.
- **Alternatives:** semantic/structure-aware chunking (higher quality, more complex — a future upgrade); fixed no-overlap (loses boundary context).
- **Trade-offs / revisit if:** overlap must stay `< size`. Revisit toward structure-aware chunking if retrieval error analysis shows boundary losses.

## ADR-12 — Agent reads assets via ingestion API, not S3

- **Context:** the agent needs source files, page images, and Excel rows at answer time.
- **Decision:** the agent fetches every asset through **ingestion HTTP APIs** (`/documents/{job_id}/…`), never with its own S3 credentials.
- **Rationale:** **security** — storage credentials live in exactly one service (ingestion); the agent can't mutate the index or read raw buckets. Also a single owner of storage-path logic (`image_uri` stays internal, resolved server-side — see the [04 identifier fix](04-api-contracts-and-data-flows.md)).
- **Alternatives:** presigned URLs (extra surface, expiry handling); direct S3 in the agent (spreads credentials, breaks the boundary of ADR-8).
- **Trade-offs / revisit if:** an extra network hop per asset — acceptable for the security/ownership win; the agent's `AGENT_INGESTION_BASE_URL` must be reachable.

## ADR-13 — Store image + VLM text; embed text only

- **Context:** image-dense pages must be both **findable** and **groundable**.
- **Decision:** store the **rendered PNG** and its **VLM text description**; **embed only the text**; fetch the image lazily by `job_id`+`page` ([06 §5](06-visual-extraction-and-vlm.md)).
- **Rationale:** text retrieval over a **rich VLM description** is cheaper, simpler, and more controllable than image embeddings, and the actual image is still available for multimodal grounding + citation. Avoids maintaining a second (image) vector space.
- **Alternatives:** CLIP-style image embeddings + cross-modal search (more infra, harder to tune, weaker on text-in-image); no image storage (loses visual citation and grounding).
- **Trade-offs / revisit if:** retrieval quality depends on VLM description quality (prompt-tunable). Revisit if pure visual-similarity search becomes a requirement.

## ADR-14 — `file_id` vs `job_id` identity model

- **Context:** the same logical document is re-ingested (updated) over time, and must be deletable.
- **Decision:** **`file_id`** = stable logical identity (producer-supplied); **`job_id`** = one ingestion version; asset `document_id` resolves to the active `job_id` (see the [04 identifier model](04-api-contracts-and-data-flows.md)).
- **Rationale:** idempotent **dedup / update / delete** keyed on `file_id`, while vectors/images are versioned by `job_id` so a re-ingest never collides with or corrupts the prior version.
- **Alternatives:** a single ID (can't distinguish "new version" from "new document" → duplicates or lost updates).
- **Trade-offs / revisit if:** producers **must** keep `file_id` stable across versions — an unstable `file_id` creates duplicates instead of updates ([01 §9](01-hld.md)).

## ADR-15 — Three logical Postgres databases

- **Context:** three distinct state concerns: ingestion jobs, agent app data, and LangGraph checkpoints.
- **Decision:** separate logical databases — `docs_db`, `convo_db`, `graph_checkpoints_db`.
- **Rationale:** **separation of concerns** and independent ownership/backup; framework-managed graph state stays isolated from product data.
- **Alternatives:** one shared DB (couples migrations and blast radius); three separate servers (over-provisioned for now).
- **Trade-offs / revisit if:** backups must cover all three **plus** object storage and the vector index together ([05 §4](05-technology-stack-and-operations.md)).

## ADR-16 — Cleanup order: vectors → objects → state

- **Context:** a partial delete could leave **searchable vectors** for a "deleted" document — a correctness/privacy hazard.
- **Decision:** always delete **vectors first, then objects, then mutate job state**; if vector deletion fails, record **`FAILED_DELETE`** and retain source (don't report a false success).
- **Rationale:** guarantees no **orphaned searchable vectors**; the retained source + job enables a safe retry ([02 §9](02-lld-ingest-service.md)).
- **Alternatives:** delete source first (risks orphan vectors pointing at missing assets); best-effort delete (hides failures).
- **Trade-offs / revisit if:** a stuck `FAILED_DELETE` needs an operator retry — an intentional, visible state rather than silent data loss.

## ADR-17 — `doc_summary` attached to every chunk

- **Context:** an isolated chunk can lack document-level orientation ("what is this from?").
- **Decision:** generate a short **document summary** (chat model) and attach it to **every chunk's** metadata.
- **Rationale:** gives the model **orientation context** at answer time without a second retrieval, improving coherence on narrow chunks.
- **Alternatives:** no summary (weaker grounding on stray chunks); a separate summary retrieval (extra latency).
- **Trade-offs / revisit if:** minor metadata duplication across chunks and one extra summarization call per document at ingest — cheap relative to the grounding benefit.

## ADR-18 — Excel rows fetched live, not embedded

- **Context:** spreadsheets can have huge row counts; embedding every row is wasteful and stale-prone.
- **Decision:** embed an **`excel_summary`** per sheet; **fetch actual rows on demand** via the sheet API at answer time, capped by `AGENT_EXCEL_SHEET_CONTEXT_MAX_ROWS` (default 200).
- **Rationale:** keeps the index small, avoids embedding volatile tabular data, and controls prompt size/cost with a **row cap**; the summary makes the sheet findable, the live fetch makes it accurate.
- **Alternatives:** embed every row (index bloat, cost, staleness); embed nothing (sheet becomes unfindable).
- **Trade-offs / revisit if:** the row cap can truncate very large sheets — surface that in the answer/citation; revisit the cap per use case.

---

## How to add a new ADR
1. Append the next `ADR-N` with the five-part format (Context → Decision → Rationale → Alternatives → Trade-offs/revisit-if).
2. Add a row to the **Index**.
3. Link it from the relevant design doc where the decision is enacted.
