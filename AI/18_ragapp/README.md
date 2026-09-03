# Modular Knowledge Assistant — System Design

> **Status:** ✅ Reviewed against source, Docker Compose, and env templates on 2026-07-28 · **Design set index**

This folder is the implementation-aligned technical design for the reusable agent stack. It was reviewed against the current source tree, Docker Compose configuration, and environment templates on 2026-07-28. It complements the existing operational and decision-log material in `docs/`; it does not replace service READMEs or deployment runbooks.

## Document map

| Document | Purpose | Primary audience |
| --- | --- | --- |
| [01-hld.md](01-hld.md) | System context, component architecture, deployment topology, non-functional design, and risks | Architects, technical leads, platform engineers |
| [02-lld-ingest-service.md](02-lld-ingest-service.md) | Ingestion service modules, queue contract, job lifecycle, processing pipeline, and data model | Backend engineers |
| [03-lld-agent-and-ui.md](03-lld-agent-and-ui.md) | Agent graph, retrieval and citation flow, API/UI design, conversation state, and voice capabilities | Backend and frontend engineers |
| [04-api-contracts-and-data-flows.md](04-api-contracts-and-data-flows.md) | HTTP/SSE interfaces, message and metadata contracts, and end-to-end sequences | Integrators and QA engineers |
| [05-technology-stack-and-operations.md](05-technology-stack-and-operations.md) | Runtime stack, provider options, local deployment, configuration invariants, testing, and observability | Developers and DevOps engineers |
| [06-visual-extraction-and-vlm.md](06-visual-extraction-and-vlm.md) | How image-dense/scanned PDFs are handled separately via VLM — detection, render, `visual_insight`/`page_image` chunks, examples | Backend engineers, AI engineers |
| [07-decision-log.md](07-decision-log.md) | ADRs — why each model and design choice was made (rationale, alternatives, trade-offs) | Architects, reviewers, new joiners |
| [eval.md](eval.md) | AI evaluation framework — Phase-1 design note and implementation plan | QA, backend, and platform engineers |
| [eval-proposal.md](eval-proposal.md) | Evaluation proposal — full offline + online program, metrics, rollout | Tech leads, eval/platform engineers |
| [observability-proposal.md](observability-proposal.md) | Observability proposal — traces, metrics, logs, LLM/agent telemetry, SLOs, alerting | On-call, backend, SRE, platform engineers |

## System at a glance

The stack implements enterprise document RAG with separate write and read paths:

- `ingest-service` owns document intake, S3-compatible object storage, SQS consumption, document extraction, chunking, embedding, vector writes, and ingestion job state.
- `chat-service` owns conversational APIs, LangGraph checkpoints, retrieval, multimodal context assembly, citations, prompt configuration, transcription, and text-to-speech.
- `web-ui` owns the browser experience for chat, document management, prompt configuration, feedback, and voice interaction.

The services do not import each other. Their runtime contracts are HTTP, SQS, shared provider configuration, vector-store schema, and Postgres-backed state.

## Skills & concepts demonstrated

This design set doubles as a map of the skills and tools it exercises, grouped by area. Each row links to the document(s) where that area is worked out in detail.

| Area | Concepts & skills practiced | Concrete tools/libraries | Where it's covered |
| --- | --- | --- | --- |
| Agent orchestration | Stateful multi-turn agents, forced-tool middleware, graph-based control flow, checkpoint/resume design | LangChain `create_agent`, LangGraph, PostgreSQL checkpointer | [03 §2](03-lld-agent-and-ui.md) |
| Retrieval / RAG | Multi-query expansion, dense vector retrieval, deduplication, citation grounding, multimodal context assembly | LangChain `Document` model, vector search (Chroma / Azure AI Search) | [03 §3](03-lld-agent-and-ui.md) |
| Document processing | File-type-aware extraction, layout-preserving conversion, recursive vs. atomic chunking strategy | `pdfplumber`, `python-pptx`, `openpyxl`, LibreOffice, LangChain text splitters | [02 §5](02-lld-ingest-service.md) |
| Vision / multimodal | Cheap heuristic-based visual detection, VLM prompting, dual-track (searchable text + groundable image) chunk design | Azure OpenAI multimodal chat, Pillow (page rasterization) | [06](06-visual-extraction-and-vlm.md) |
| Event-driven backend | Async task processing, retry/redelivery semantics, DLQ handling, idempotent upserts, cleanup ordering | Amazon SQS/LocalStack, `boto3`, async SQLAlchemy | [02 §2, §9](02-lld-ingest-service.md) |
| API design | Streaming APIs (SSE), REST contract design, cross-service metadata contracts, auth middleware | FastAPI, AG-UI protocol, OIDC/SSO | [04](04-api-contracts-and-data-flows.md) |
| Frontend | Component-driven SPA, real-time streaming UI state, auth-aware routing, voice I/O | React, TypeScript, Vite, React Router, `@ag-ui/client` | [03 §6-7](03-lld-agent-and-ui.md) |
| Evaluation & quality | LLM-judge metrics, golden-dataset design, offline/online eval loops, tiered CI gates | DeepEval, Ragas, Playwright | [eval.md](eval.md), [eval-proposal.md](eval-proposal.md) |
| Observability | Distributed tracing across async/queue boundaries, GenAI semantic conventions, SLO/alert design | OpenTelemetry, structured logging | [observability-proposal.md](observability-proposal.md) |
| Architecture & reliability | Service-boundary design, provider abstraction, ADR-driven decision-making, failure-mode-first design | Docker Compose, dual vector-backend adapters | [01](01-hld.md), [07](07-decision-log.md) |

## Architectural invariants

1. Ingestion is the only service that reads or writes document object storage and the vector index write path.
2. Agent service only reads the vector store and fetches source assets through the ingestion HTTP API.
3. Both services must target the same vector space: provider, backing collection/index, embedding deployment, and embedding dimensions must agree.
4. Runtime state is externalized: Postgres for application/checkpoint/job state, S3-compatible storage for source artifacts, SQS for ingestion work, and Chroma or Azure AI Search for vectors.
5. Configuration is service-scoped: each service loads its own `.env.local`; secrets are never committed or included in these design documents.

## Scope and terminology

| Term | Meaning |
| --- | --- |
| Job | An ingest-service record that tracks one submitted document version from queueing through deletion. |
| `file_id` | Optional stable external identity used for deduplication and update/delete operations. |
| `job_id` | Generated identifier for an individual ingestion attempt/version and the primary foreign key for vector metadata. |
| Chunk | A LangChain `Document` persisted as one searchable vector plus metadata. |
| AG-UI | Event protocol used by the LangGraph agent endpoint to stream a chat run to the browser. |
| Visual chunk | A chunk associated with a page/slide image, typically `visual_insight` or `page_image`. |

## Reading order

Start with the HLD, then choose the LLD for the service you will change. Review the API/data-flow document before integrating another system or changing a contract. Use the technology/operations document for local setup, provider choices, and guardrails.
