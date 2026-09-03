# Technology Stack and Operations

> **Modular Knowledge Assistant** · design set → [README](README.md) · **you are here: Technology Stack & Operations**

## 1. Technology stack

Version numbers below are indicative (major.minor) rather than exact pins. Treat each service's manifest, lock file, and built image as the source of truth for the precise version in use and for upgrade work.

### Why this stack, layer by layer

Each layer below pairs a concrete tool choice with the skill or concept it exists to exercise — read this alongside the [decision log](07-decision-log.md), which carries the full context/alternatives/trade-offs for the starred (★) decisions.

- **Frontend** — a component-driven SPA (React + TypeScript) consuming a streaming agent protocol (`@ag-ui/client`) instead of polling: the skill here is building UI state machines around an event stream (tokens, thinking steps, citations arriving out of order) rather than a single request/response payload.
- **Agent service** — LangChain/LangGraph★ turn a chat loop into an explicit, checkpointed state machine (PostgreSQL-backed), which is what makes multi-turn conversations resumable across restarts and auditable after the fact. The forced-retrieval middleware (ADR-5) is a concrete pattern for a common stateful-agent bug class: stale tool output leaking into a new turn.
- **Ingestion service** — an async, queue-driven pipeline (SQS★) decouples slow, spiky document processing from the request path; per-file-type extractors (`pdfplumber`, `python-pptx`, `openpyxl`, LibreOffice) are a survey of how differently structured documents have to be normalized into one chunk model before they can be embedded.
- **Vision/VLM** — rather than a dedicated OCR/vision vendor, the same multimodal chat deployment doubles as a VLM (ADR-3), gated behind a cheap local heuristic (§2 of [06](06-visual-extraction-and-vlm.md)) so the expensive path only runs when text extraction would actually fail.
- **Vector/data layer** — a provider-neutral vector interface with two adapters (Chroma for local/dev, Azure AI Search for managed/prod) is the pattern for keeping application code portable across a swappable backend (ADR-6), enforced by explicit cross-service configuration invariants (§3 below).
- **Platform/infra** — Docker Compose profiles, LocalStack, and three logical Postgres databases are the local-dev-parity skill: running a close approximation of the production topology (queue, object storage, multiple stateful stores) entirely on a laptop.

### Frontend

| Technology | Indicative version | Role |
| --- | --- | --- |
| React / React DOM | `18.2.x` | Browser UI framework. |
| TypeScript | `5.4.x` | Typed frontend implementation. |
| Vite | `5.4.x` | Development server and production build. |
| React Router | `6.24.x` | Chat/documents/configuration routes. |
| Tailwind CSS | `3.5.x` | Styling system. |
| `@ag-ui/client` | `0.0.x` | AG-UI HTTP agent and streaming state. |
| OIDC/SSO browser library | Per chosen provider | Browser-side SSO authentication. |
| React Markdown + remark-gfm | `10.1.x` / `4.0.x` | Markdown response rendering. |
| Lucide React | `0.469.x` | Icon library. |
| Nginx | Container base/config | Static delivery and reverse proxy. |

### Agent service

| Technology | Indicative version | Role |
| --- | --- | --- |
| Python | `>=3.11`; Docker image uses Python 3.11 slim | Service runtime. |
| FastAPI | `0.128.x` | HTTP and streaming API framework. |
| Uvicorn | `0.38.x` | ASGI server. |
| LangChain | `1.1.x` | Agent/model abstractions. |
| LangGraph | `1.1.x` | Stateful agent graph/checkpoint orchestration. |
| AG-UI LangGraph / protocol | `0.0.x` / `0.1.x` | LangGraph-to-browser event bridge. |
| LangChain OpenAI | `1.1.x` | Azure OpenAI chat and embedding integration. |
| OpenAI SDK | `2.35.x` | Provider/client support. |
| PostgreSQL + psycopg | `3.2.x` | Application and checkpoint persistence. |
| SQLAlchemy | `2.0.x` | Persistence model/repository layer. |
| Chroma | `1.3.x` | Local/development vector read backend. |
| Azure Search Documents | `11.3.x` | Azure AI Search vector read backend. |

### Ingestion service

| Technology | Indicative version | Role |
| --- | --- | --- |
| Python | `>=3.11`; Docker image uses Python 3.11 slim | Service runtime. |
| FastAPI / Uvicorn | `0.129.x` / `0.40.x` | Upload and job APIs. |
| Boto3 | `>=1.34` | S3 and SQS integration. |
| LangChain core/community/text splitters | `1.1.x` / `0.4.x` / `1.0.x` | Document model and recursive chunking. |
| LangChain OpenAI | `1.1.x` | Azure OpenAI embeddings/chat/VLM integration. |
| Chroma | `1.3.x` | Local/development vector write backend. |
| Azure Search Documents | `11.3.x` | Azure AI Search vector write backend. |
| `pdfplumber` | `0.11.x` | PDF text, table, and page inspection. |
| Pillow | `11.1.x` | Image handling. |
| `python-pptx` | `1.0.x` | Presentation processing. |
| `openpyxl` | `3.1.x` | Spreadsheet processing and sheet retrieval. |
| LibreOffice | Docker-installed binary | DOC/DOCX to PDF conversion; must be on `PATH`. |
| PostgreSQL + psycopg/SQLAlchemy | `3.2.x` / `2.0.x` | Job persistence. |

### Platform services

| Service | Supported configurations | Role |
| --- | --- | --- |
| Azure OpenAI | Chat deployment, embedding deployment, optional transcription/vision deployment | All model inference and embeddings. |
| Chroma | Docker volume-backed persistent directory | Local/simple vector retrieval. |
| Azure AI Search | Shared configured index | Managed semantic/hybrid vector retrieval. |
| Amazon S3 | Real AWS or LocalStack endpoint | Source files and generated assets. |
| Amazon SQS | Real AWS or LocalStack endpoint | Ingestion queue and retry/DLQ mechanics. |
| PostgreSQL | Three logical databases | Ingestion jobs, agent application state, LangGraph state. |
| SSO / OIDC provider | Optional, controlled by `AUTH_ENABLED` | User authentication and bearer-token validation. |

## 2. Local deployment modes

| Mode | Components | Best use |
| --- | --- | --- |
| Full Compose | `docker compose --profile localstack --profile app up -d` | End-to-end local stack with local S3/SQS and shared Chroma Docker volume. |
| Host services + LocalStack | Start LocalStack profile, then run both Python services and Vite on host | Faster code/debug iteration. Use `http://localhost:4576` for host-side S3/SQS endpoints. |
| Cloud-backed | Services point to real S3/SQS, Azure OpenAI, Azure AI Search, Postgres | Integration/staging-like validation. |

Example Compose endpoint mappings (host ports are configurable per environment):

| Component | Host URL/port |
| --- | --- |
| UI | `http://localhost:6280` |
| Agent API | `http://localhost:6501` |
| Ingestion API | `http://localhost:6511` |
| LocalStack S3/SQS | `http://localhost:4576` |

## 3. Configuration model

Each service reads one local configuration file:

```text
ingest-service/.env.local
chat-service/.env.local
```

The templates define vector-provider, storage, Azure model, auth, Postgres, processing, and queue settings. They are deliberately gitignored; start from `.env.local.example` and never place real keys in source control or documentation.

### Required cross-service checks

| Invariant | Failure prevented |
| --- | --- |
| Same vector provider | Writing to one backend while searching another. |
| Same collection (Chroma) or index (Azure AI Search) | Empty search results after successful ingestion. |
| Same embedding deployment and dimensions | Invalid similarity search across incompatible vector spaces. |
| Compatible metadata schema | Missing page/sheet/image fields and broken citations. |
| Reachable `AGENT_INGESTION_BASE_URL` | Failed image/Excel context expansion on retrieval. |

### Important tunables

| Area | Settings | Default/template values |
| --- | --- | --- |
| Chunking | `INGESTION_CHUNK_SIZE`, `INGESTION_CHUNK_OVERLAP` | `1000` / `150`; overlap must be smaller than size. |
| Vector retrieval | `*_VECTOR_TOP_K`, score threshold, backend options | Top-K `8`; provider-specific options. |
| Vision | `INGESTION_ENABLE_VLM`, `INGESTION_VLM_DPI` | Disabled by default; DPI template value `300`. |
| Excel retrieval | `AGENT_EXCEL_SHEET_CONTEXT_MAX_ROWS` | `200`. |
| Queue | SQS wait time/visibility timeout | `20` seconds / `3600` seconds. |
| Voice | TTS provider/key/model/voice/timeout/max chars | Empty values select a mock provider. |

## 4. Observability and reliability

| Layer | Current behavior | Recommended production baseline |
| --- | --- | --- |
| Logs | Loguru in both backend services; job ID, status, vector count, and processing details logged. | Centralize structured logs with request/run/job correlation IDs and redaction. |
| Tracing | An optional OpenTelemetry-based observability integration; bootstrap tolerates its absence. | Enable OpenTelemetry-compatible traces for HTTP, model, SQS, and vector calls. |
| Health | `/health` endpoints on both backend services; Compose depends on agent health. | Add readiness checks for dependencies and dashboard alerts. |
| Retry | Transient ingestion errors return to SQS; queue has DLQ policy in local setup. | Monitor age of oldest message, DLQ depth, retry counts, and document-processing latency. |
| State recovery | Postgres job state; LangGraph checkpoints; conversation tombstone sweeper. | Back up Postgres, object storage, and vector index together; test restore/re-index. |

## 5. Testing and quality gates

The repository provides a focused fast gate and a broader verification ladder:

```bash
bash scripts/run_quality_gate.sh --targeted
bash scripts/run_quality_gate.sh
bash scripts/dev/probe.sh
bash scripts/dev/verify_all.sh --skip-vector-smoke
```

Service tests use `pytest`; agent tests cover authentication, configuration, conversations, citations/images, RAG timeouts, TTS, and transcription. Ingestion tests cover document APIs, job processing, PDF/slides/DOCX processors, vector schema, and auth. The DOCX smoke check can run inside the built ingestion image to verify LibreOffice filters.

For a real end-to-end document test, provide an actual sample document and configured provider credentials:

```bash
SAMPLE_PATH=/path/to/file.pdf bash scripts/dev/e2e_live.sh
```

## 6. Operational runbook highlights

1. Run the targeted quality gate first after a focused change; run the full gate before declaring a merge request ready.
2. If vectors appear empty, verify provider/index/collection, embedding deployment/dimensions, shared Chroma persistence directory, and job completion state before debugging retrieval prompts.
3. If a document is stuck, inspect job status and error details, then queue/DLQ state. Do not manually delete source data before vector deletion succeeds.
4. If visual citations are missing, verify VLM/image-rendering flags, object storage permissions, `image_uri` metadata, and the agent's ingestion base URL.
5. When changing embedding model or dimensionality, provision a new index/collection or explicitly re-index; old and new vectors must not coexist in the same similarity space.

## 7. Production hardening backlog

The codebase already has the main separation of concerns. Before a production workload carrying sensitive enterprise content, explicitly design and test:

- Internal service-to-service authentication for agent-to-ingestion calls.
- Authorization coverage for configuration management endpoints and role-based controls for prompt activation.
- Namespace/tenant-aware retrieval filters and audit records.
- Private endpoints, TLS, restricted CORS, WAF/rate limits, secret rotation, and storage encryption/key policy.
- Independent worker deployment/scaling, queue concurrency controls, back-pressure, and a documented replay strategy.
- Retention/deletion policy across S3, vectors, ingestion jobs, agent conversations, and LangGraph checkpoints.
- Model safety controls, content filtering, source/citation policy, cost budgets, and observability redaction.
