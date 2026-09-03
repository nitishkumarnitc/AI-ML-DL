# 15 — Your 3 Projects as Interview Evidence

> Everything here is **grounded in your actual code** (as of 2026‑07‑29). This is the file that fills the `____` blanks in [13_STAR_and_Metrics_Worksheet.md](13_STAR_and_Metrics_Worksheet.md) with real material, so you can speak with specifics instead of generalities.
>
> **Honesty rules baked in (so you never get caught out):**
> - Numbers **from code/config** are marked ✅ *(grounded)* — safe to state.
> - Numbers you must supply from real dashboards/PRs are marked 🟡 `[your real figure]` — **do not invent these on the spot**; fill them before the loop or say "from memory, roughly…".
> - Claims that are **design/proposal/marketing, not shipped-and-measured** are marked ⚠️ — present as *roadmap* or *design intent*, never as measured production outcomes.

---

## 🎬 Your portfolio in one line (the arc that makes you a Principal)

> "I've built the **same production agent platform pattern three times, each pushing a different frontier**: a config‑driven **10‑agent Sales BDC system** (LLM‑routed, concurrency‑safe, hybrid memory), a **Service appointment system migrated to MCP** (Model Context Protocol) with a dual‑transport shared contract, and a fully **documented enterprise RAG platform** where every design choice has a recorded trade‑off. Across all three I converged on the same spine — config‑driven agent registries, a gateway‑mediated LLM layer with fallback/tiering, MCP for dynamic tools, a shared error taxonomy, and async event‑driven execution with distributed tracing."

That sentence is your answer to "tell me about your work" **and** proof of the JD's "platform‑level abstractions and SDKs that accelerate AI agent development across multiple product teams."

**The shared platform spine (repeat this — it's the Principal signal):**
| Concern | How you solved it (consistently, across repos) |
|---|---|
| Add an agent without touching routing | **Config‑driven registry** → prompt + toolset regenerate from `AgentConfig` |
| Swap model / survive provider blips | **Gateway‑mediated LLM factory** with `service_tier`, `fallback_model`, `reasoning_effort` |
| Dynamic, discoverable tools | **MCP** (JSON‑RPC 2.0 over SSE) with schema validation + pooled, self‑healing sessions |
| Uniform failure handling | **SAE error taxonomy** with `retryable`/`external_reporting` + per‑transport classifiers |
| Agent gateway fit | **Async accept‑then‑callback** execution with B3 trace continuity |
| Debuggability | **MLflow + OpenTelemetry** typed spans, one trace per conversation |

---

# 🅰️ Project A — **Sales AI Agents** (your flagship; lead with this)

`<my current company>/sales-ai-agents`

**What it is:** A production multi‑agent **BDC (Business Development Center)** system for automotive dealerships — **1 supervisor + 9 specialist agents**, deployed as **3 services** (inbound/outbound/greetings), handling **text / email / voice** across a multi‑tenant, Kafka‑backed platform. Specialists: vehicle discovery, dealer info, inventory expert, appointment booking, finance/trade‑in/credit self‑service, and human handoff.

**Architecture headline (say this first):**
> "A single long‑lived **LangGraph ReAct supervisor** does 100% LLM‑driven routing off a **config registry**, wrapping each specialist as a tool. It's made concurrency‑safe with **ContextVar request isolation**, backed by **hybrid memory** (LangGraph checkpointer for STM + AWS Bedrock AgentCore for LTM), and every customer‑facing string passes a single **Responder exit gate**."

### 💰 Money talking points (each cites real code)
1. **100% LLM‑driven routing off a config registry** — `src/agents/_registry/register_agents.py` + `bdc_supervisor/agent.py`. Adding an agent = registering an `AgentConfig`; the ReAct system prompt and toolset regenerate at startup. *Zero hardcoded routing.* → This is your **"platform abstractions for N teams"** story.
2. **Dual‑input tool contract to stop state pollution** — `_build_agent_input`/`_create_agent_tool`. Sub‑agents receive `customer_message` (verbatim) **separately from** `supervisor_context` (facts only, no directives), so the LLM can't paraphrase the customer's intent into a sub‑agent. *This is a subtle multi‑agent failure mode most people never hit — huge depth signal.*
3. **Concurrency‑safe single ReAct graph via ContextVar isolation** — `bdc_supervisor/request_context.py` (`_supervisor_context_var`) + immutable `RunConfig`. One compiled graph serves concurrent requests with no prompt/state bleed. → Perfect for **Bhanu's** "how does this survive concurrency?" probe.
4. **Hybrid memory with an LLM insight extractor** — STM = LangGraph checkpointer (AgentCore/Redis‑backed, `cached_checkpointer.py`); LTM = **AWS Bedrock AgentCore Memory** (`memory/ltm.py`). Insights extracted via **structured output** into 6 memory types (SEMANTIC/EPISODIC/DERIVED/ENTITY/CONTEXTUAL, `insight_extractor.py`), protected by a **circuit breaker** (`circuit_breaker.py`) + **token‑bucket rate limiter** (✅ 100 req/s, `rate_limiter.py`).
5. **Tiered routing to cut cost + latency** — `_tiered_route/_nano_route`: keyword → **`gpt‑5.4‑nano`** mini‑router (✅ 150‑token cap, 5s timeout) → full ReAct fallback, switchable via `ROUTING_STRATEGY`. → Your **cost/latency** story for **Dinesh**.
6. **MCP tools discovered + wrapped dynamically, pooled & self‑healing** — `src/tools/15_mcp/auto_register.py` discovers remote tools, builds **Pydantic schemas dynamically**, wraps them as LangChain `StructuredTool`s and injects `dealer_id/tenant_id/user_id`; `mcp_client_factory.py` pools clients (✅ `MCP_POOL_MAX_CLIENTS=50`, TTL) with **session self‑healing** (`_reset_session`, generation counter to dedupe concurrent resets) + retry/backoff.
7. **Defense‑in‑depth safety** — LLM guardrails on `nova‑2‑lite` with a **prompt built only from enabled guards** (`guardrails/runner.py`: injection, indirect‑injection, toxicity, history‑tampering) + **deterministic fact injection** (`_ensure_context_facts` prevents date/identity hallucination) + **single Responder exit gate** + **price‑disclaimer enforcement** (`utils/price_disclaimer.py`). → Your **regulated‑domain guardrails** story.
8. **RAG‑Fusion intent classifier** — `src/intent_classifier/`: a `MultiEmbeddingRetriever` (as‑is + with‑context + spaCy sub‑queries), MMR + intent‑level fusion, then an LLM router producing `nlu_hints`. Uses **Elasticsearch 7.17** + **`all‑MiniLM‑L6‑v2`** embeddings. → Your **retrieval depth** story even though the main flow isn't classic doc‑RAG.
9. **Async event‑driven execution with full tracing** — `agent_core/executor.py` returns `"working"` immediately, processes in a tracked background task, POSTs to the callback gateway with **B3 trace continuity**; MLflow/OTel spans throughout; `InstrumentedChatOpenAI` emits token/latency counters.
10. **Outbound = explicit LangGraph state machine + LLM validator** — `outbound_module/graph.py` (department router → classifier → category agents → responder → `response_validator`); `response_validator.py` does structured‑output checks (CTA/length/tone/no‑promises). → Your closest thing to **LLM‑as‑judge** on this repo.

### 🎯 Ready STAR stories (drop straight into doc 13)
- **Story 1 — Production multi‑agent system:** *S:* dealership BDC needed to handle text/email/voice with specialist behavior across a multi‑tenant platform. *T:* own the agent orchestration architecture. *A (decisions):* single LLM‑routed ReAct supervisor over a **config registry** (so product teams add agents without routing changes); **dual‑input contract** to stop intent pollution; **ContextVar isolation** for concurrency; **tiered routing** to control cost. *R:* 🟡 `[N dealerships / conversations/day / % auto‑handled]` — fill from real data.
- **Story 3 — Latency/cost win:** *A (levers):* nano‑router tier before full ReAct, message‑history windowing (✅ supervisor 10 / sub‑agent 5 turns) to cap prompt growth, a cheap dedicated **Responder** model (✅ target p50 200ms / p95 500ms in `env_config`), gateway `service_tier`. *R:* 🟡 `[cost/token ↓, p95 ↓]`.
- **Story 5 — Technical multiplier:** the **registry + AgentConfig pattern** is the thing other engineers reuse — "adding a specialist is a config change, not a routing rewrite." *R:* 🟡 `[N agents added by others / onboarding time ↓]`.
- **Story 8 — Decision you'd revisit:** the ~3,000‑line `bdc_supervisor/agent.py` monolith — "it centralized routing correctly but became a change‑risk hotspot; I'd extract the tool‑wrapper and routing‑strategy layers into the platform SDK." *(Shows self‑critique — Principal maturity.)*

### 🟡 Metrics to fill before the loop
`conversations/day`, `# active dealerships/tenants`, `% conversations fully automated vs handed off`, `p95 end‑to‑end latency`, `cost/conversation`, `LTM read‑after‑write latency` (do **NOT** use the README's ⚠️ "60,000x faster" claim — it's unverified marketing, not in code).

### ⚠️ Gaps to pre‑empt (honest answers ready)
- **No inbound LLM‑as‑judge in this repo** — evaluation lives in a **separate sibling repo `sales-ai-sessions-eval`**; the only in‑repo judge is the outbound `ResponseValidatorAgent`. Say exactly that.
- **Output guardrail is log‑only** (there's a literal `TODO: add retry loop if failure rate > 5%`) — enforcement is roadmap.
- **Fail‑open vs fail‑closed inconsistency** — `runner.py` fails closed; `supervisor_service` treats guard errors as neutral (fail‑open). Have a crisp justification (availability vs safety trade‑off by guard type).
- **Single‑gateway dependency** (Bifrost/GPT‑5 + Nova) — the fallback is another gateway model, so provider diversity is limited. Know the mitigation (add a second provider behind the factory seam).
- **Hallucination handling is preventive, not detective** — fact injection + disclaimers, no post‑hoc groundedness check on inbound. That's your "what I'd add next" answer.

---

# 🅱️ Project B — **Service AI Agents** (your MCP showcase — the cutting‑edge story)

`<my current company>/service-ai-agents` (current branch `feat/AIPL-1719_MCP`)

**What it is:** My current company's **Service department** AI agents (service BDC). `inbound_module/` handles real‑time SMS/TEXT service conversations via a **supervisor → specialist** design for scheduling/rescheduling/cancelling appointments, maintenance Q&A, and human handoff. `outbound_module/` runs PySpark/Delta audience jobs + a LangGraph targeting agent. **This branch's headline = migrating appointment tools to MCP.**

**Architecture headline (say this first):**
> "It's **nested LangGraph orchestration** — a supervisor `StateGraph` routes through a **ReAct agent** to specialist sub‑agents that are **themselves LangGraph graphs**. On this branch I moved appointment execution onto our internal **MCP Gateway** (JSON‑RPC 2.0 over SSE) with a **dual‑transport, single‑contract** design so the agents are transport‑agnostic."

### 💰 Money talking points (each cites real code)
1. **MCP migration with a shared‑contract dual transport** — `tools/mcp_tools.py` (`MCPTools`) and `tools/appointment_tool_client.py` (HTTP) **share the same payload builders (`build_*_payload`) and normalizers (`normalize_*`) from `booking_appointments.py`**. Because `MCPTools` mirrors the HTTP class's method names, it's a **drop‑in via duck typing** — booking sub‑agents never change. → This is a *beautiful* Principal‑level abstraction story.
2. **MCP as a real capability protocol, not hardcoded calls** — `tools/mcp_client.py` does `list_tools()` discovery, caches `inputSchema`, **validates required params before dispatch** (`validate_tool_arguments`), and retries transient errors with backoff. `_MCP_TOOL_NAMES` centralizes the MCP↔HTTP **namespace divergence** (e.g. transport is `list` over MCP but `get` over HTTP).
3. **Deliberate abstraction iteration** — git history shows you first built an **Adapter Pattern with HTTP fallback** (`3078bf2`) then **removed it** (`7c6361c` "use MCP directly with SAE error codes"). → Textbook **"don't over‑abstract; standardize once the pattern is clear"** story for an architecture‑review question.
4. **Nested LangGraph graphs** — supervisor `StateGraph` (`process_turn → respond → END`) → `create_react_agent` router → sub‑agent graphs like `schedule_appointment_fast` (`load_defaults → detect_scope → resolve_booking_state → unified_plan → {fetch_slots→slot_presenter | execute_booking | clarification_drafter} → finish`). Multi‑turn `active_agent`/`paused_agent` persisted via checkpoint.
5. **Concurrent per‑turn fan‑out** — the supervisor runs summarization + entity extraction + intent classification + input guardrail **concurrently via `asyncio.gather`** each turn. → latency‑aware design.
6. **DynamoDB LangGraph checkpointer** — `state/stm.py` (`DynamoDBMemorySaver`, ✅ 30‑day TTL, S3 offload for large state, 3 retries). Externalized state = stateless, horizontally scalable workers.
7. **Production SAE error taxonomy** — `shared/errors/sae_errors.py`: `SAE001–SAE014`, each with `(retryable, external_reporting, category)`; three classifiers (`ClassifyLLMException`, `ClassifyHTTPException`, `ClassifyMCPException`). Every MCP failure is normalized before it reaches the agent. → **Bhanu's** reliability question, answered.
8. **Security: identity from trusted context, never the model** — `MCPTools._mcp_context` / `appointment_headers` build tenant/dealer/user headers from `request_identity`/`run_config`. → explicit **prompt‑injection mitigation** (great regulated‑domain point).
9. **Async accept‑then‑callback executor** — `agent_core/executor.py` returns `working`, processes in background, POSTs `SEND_TEXT`/`ADD_INTERNAL_NOTE`/`ROUTED` to the gateway callback.
10. **Hard‑won domain correctness** — `booking_appointments.py`: timezone‑safe epoch math with `ZoneInfo`, slot‑window filtering (7 AM–8 PM), transport IDs must be **real UUIDs** (a label like `"SELF"` makes the backend silently return `{data: null}`), mixed‑intent "remainder" re‑routing. → shows you sweat production edge cases.

### 🎯 Ready STAR stories
- **Story 1 — Agentic system / MCP:** *A (decisions):* dual‑transport shared contract so agents are transport‑agnostic; MCP discovery + schema validation; removed the adapter once MCP was the clear standard. *R:* 🟡 `[appointments booked/day, tool‑call success rate]`.
- **Story 6 — Architecture review / influence:** the adapter‑then‑removal decision + the `_MCP_TOOL_NAMES` namespace‑mapping call are perfect "I changed a design based on evidence" material.
- **Story 4 — Distributed systems:** DynamoDB checkpointer + `asyncio.gather` fan‑out + MCP backoff/retry + Gunicorn (✅ 4 uvicorn workers, 120s timeout).

### ⚠️ Gaps to pre‑empt (be honest — this branch is fresh, unmerged)
- **`mcp_agent` is a stub** — `agents/mcp_agent/agent.py` has a `TODO: use LLM to determine tool…`; it only lists tools. The **real** MCP usage is booking sub‑agents calling `MCPTools`. **Do not oversell "an autonomous MCP planner agent."**
- **Shared single MCP session across tenants** — one `MCPTools`/SSE transport initialized with the first request's headers; per‑call headers are merged into args but the session isn't re‑scoped per tenant. **Acknowledge this as a known multi‑tenant concurrency risk + your fix** (per‑tenant session pool, like the sales repo already does).
- **Guardrails log‑only (fail‑open v1)**, **`cancel_appointment` unimplemented** (raises until spec provided), **config duplication** (`config.py` module vs `config/` package), **no RAG/vector** (structured CRM data, not embeddings — don't claim semantic retrieval).

---

# 🅲 Project C — **RagApp** (your judgment / design‑maturity showcase)

`/Users/nitishkumar/Documents/AI-ML/RagApp`

> ⚠️ **Critical honesty note:** this folder is **11 design documents** (HLD, 2 LLDs, API contracts, tech‑stack/ops, a VLM deep‑dive, an **18‑entry ADR decision log**, plus eval & observability *proposals*) — **not running source code**. Treat it as a **design/architecture artifact**. If an interviewer says "show me the code," point to the *actual* service repo (elsewhere) — never imply this folder is the running system. As **design evidence it's gold**: every choice has Context → Decision → Rationale → Alternatives → Trade‑off.

**What it describes:** an enterprise **agentic RAG platform** ("Reusable Agent Stack") that ingests business docs (PDF/PPTX/XLSX/DOCX), extracts **text + visual** knowledge, indexes to a shared vector space, and serves a browser assistant with **page‑level citations** and multimodal grounding. Clean **write path (ingestion)** vs **read path (agent)** split; local mode (LocalStack + Chroma) and prod mode (AWS S3/SQS, Azure OpenAI, Azure AI Search, Postgres, Entra ID). Stack: **LangChain 1.2 + LangGraph 1.1**, FastAPI, AG‑UI SSE streaming, `text‑embedding‑3‑small` @ 1536 dims.

### 💰 Money talking points (each cites a doc/ADR)
1. **Forced‑retrieval middleware (ADR‑5)** — with a **Postgres‑checkpointed** agent, a prior tool message could let a *new* question answer from stale context. A `wrap_model_call` middleware forces `tool_choice="any"` until a tool message exists **after the latest user turn**. Framed as "the single most important correctness guard for a checkpointed RAG agent." → *elite* depth signal; most people miss this.
2. **Two‑track visual extraction / VLM (ADR‑13)** — cheap local `pdfplumber` signals (text length, coverage ratio, image‑area ratio) decide which pages get rasterized (300 DPI) and VLM‑described. Each yields a searchable `visual_insight` **and** a lazily‑fetched `page_image`. **Only text is embedded; images fetched by `job_id+page`** — deliberately **no CLIP embeddings**. → strong multimodal‑RAG reasoning.
3. **Two‑tier identity: `file_id` (logical doc) vs `job_id` (version) (ADR‑14)** — enables idempotent update/delete and version‑scoped image keys, so re‑ingest never collides.
4. **Delete correctness as a privacy property (ADR‑16)** — always delete **vectors → objects → job state**; if vector deletion fails, record `FAILED_DELETE` and retain source rather than report false success → no "orphaned searchable vectors" for a deleted doc. → *great* regulated‑data answer.
5. **Prompt‑config versioning as the rollout/experiment surface** — immutable versions pinned per conversation → reproducibility; activate/shadow/canary/rollback with **no deploy**.
6. **Strict write/read separation, one contract (ADR‑6/8)** — no cross‑imports; the vector metadata schema + embedding dims are the hard contract; changing the embedding model forces a **controlled re‑index**, never an in‑place flip.
7. **Eval designed as two loops (⚠️ proposal)** — offline component scoring (retrieval recall@k/MRR/nDCG → faithfulness → correctness → citation‑support → safety, with mandatory **unanswerable/abstention** rows) + online sampled groundedness; DeepEval + Ragas. → your **LLMOps** framework answer.
8. **Observability on OTel GenAI semantic conventions (⚠️ proposal)** — `traceparent` propagated across the SQS boundary so one trace spans upload→worker→upsert; PII redaction at the collector.

### 🎯 How to use it in the loop
- It's your **"how I think about architecture"** exhibit — when asked "design an enterprise RAG system," you narrate ADRs you've actually written.
- It fills your **RAG/retrieval** and **LLMOps/eval** answers ([03], [04]) with concrete, opinionated positions.

### ⚠️ Gaps to pre‑empt
- **Design docs, not shipped code** (say so). **Eval & observability are proposals**, not measured. **Retrieval is dense‑only** — no BM25/hybrid fusion, **no reranker** at the app layer (multi‑query expansion + dedup + `top_k=8`; Azure AI Search *could* add hybrid later). **Single‑provider (Azure OpenAI)**. **Fixed 1000/150 chunking** (not semantic). Have the "how I'd productionize / add hybrid + cross‑encoder rerank" answer ready — it's a classic Principal probe.

---

## 🧭 JD bullet → which project proves it (your coverage map)

| JD requirement | Your proof | Where |
|---|---|---|
| Multi‑agent orchestration, planning loops, tool‑augmented reasoning | Sales 10‑agent ReAct supervisor; Service nested graphs | A, B |
| LangGraph / AutoGen expertise | LangGraph everywhere (StateGraph + ReAct + checkpointers) | A, B, C |
| RAG, hybrid search, retrieval | RagApp RAG platform; Sales RAG‑Fusion intent classifier + Elasticsearch | C, A |
| Low‑latency LLM inference layers | Tiered nano‑routing, Responder gate, gateway `service_tier`, async fan‑out | A, B |
| Async, event‑driven AI services (Kafka/Redis) | Async callback executors; Redis STM/LTM cache; SQS pipeline; Kafka platform layer | A, B, C |
| Platform abstractions / SDKs for many teams | Config‑driven agent **registry** pattern (reused across both prod repos) | A, B |
| Agent evaluation / LLM‑as‑judge | Outbound `ResponseValidatorAgent`; RagApp two‑loop eval design; sibling eval repo | A, C |
| Guardrails & Responsible AI | LLM guardrails (nova), fact injection, Responder gate, price disclaimers, SAE taxonomy | A, B |
| Explainability / auditability | Page‑level **citations**; MLflow/OTel per‑conversation traces; SAE codes | C, A, B |
| Fault‑tolerant, cost‑efficient at scale | Circuit breaker, rate limiter, checkpointer TTL/offload, tiered models, fallback | A, B |
| Technical multiplier / mentoring | Registry/SDK pattern others build on; ADR discipline | A, B, C |
| MCP / emerging frameworks (build‑vs‑buy) | Full MCP migration + adapter‑then‑removal decision | B, A |

> If they hit a JD bullet you can't back with one of these three, say so plainly and pivot to the closest real evidence. Honesty + a strong adjacent example beats a fabricated one every time.
