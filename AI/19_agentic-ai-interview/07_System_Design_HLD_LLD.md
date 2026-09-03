# 07 — System Design (HLD / LLD)

> The round most likely to decide the Principal offer. They'll ask you to design an AI system end-to-end, then drill. Practice **out loud with a whiteboard.**

---

## 🧭 A framework for AI system design (use this every time)

1. **Clarify & scope (2–4 min)** — don't design yet. Ask:
   - Users, scale (QPS, docs, users, transactions/day), latency SLA, budget.
   - What decision does this influence? **Cost of being wrong?** (Sets the whole safety posture — crucial for fintech.)
   - Real-time vs batch? Human-in-the-loop allowed? Regulatory constraints? Data sensitivity/residency?
2. **Define requirements** — functional + **non-functional** (latency, throughput, availability, cost, **auditability, compliance, explainability**). Call out NFRs explicitly — Principal signal.
3. **High-level architecture** — draw boxes: ingress/API → orchestration → model/agent layer → retrieval → tools/data → guardrails → observability. Data flow arrows.
4. **Deep-dive components** — go where they push, or pick the interesting part (retrieval strategy, agent state, eval).
5. **Address the cross-cutting concerns** — scale, failure modes, cost, security/tenancy, eval/monitoring, rollout.
6. **Trade-offs & alternatives** — name what you rejected and why. **Build vs buy.**
7. **Summarize** — recap, call out risks and what you'd measure/iterate on.

**Always overlay the fintech lens:** audit trail, human gate on high-stakes actions, PII handling, explainability, graceful degradation.

---

## 🧱 Reference architecture: Agentic AI Platform (memorize this skeleton)

```
                    ┌─────────────── Observability / Tracing / Eval ───────────────┐
                    │  (LangSmith/Langfuse/OTel, cost+latency+quality dashboards)   │
 Clients / Products │                                                               │
   │                ▼                                                               │
 [ API Gateway ] → [ Model Gateway ] → routing, fallback, rate-limit, cost cap, cache
   │                     │
   │              [ Agent Runtime (LangGraph) ] ── checkpointing (state store)
   │                     │  ├─ Planner / Supervisor
   │                     │  ├─ Specialist agents (extract, risk, compliance, ...)
   │                     │  └─ Tool layer (registry + governance, MCP)
   │                     │
 [ Kafka ] ⇄ async work, events, re-indexing, long-horizon steps, audit log
   │
 [ Retrieval ]: OpenSearch (BM25+vector) + reranker + KG (Neptune)   [ Redis ]: cache/rate-limit/session
   │
 [ Data ]: S3 (docs) · RDS/Postgres (metadata, state) · Vector index · KG
   │
 [ Guardrails middleware ] wraps every LLM/tool call (input/output/action)
   │
 [ Human-in-the-loop console ] for approvals on high-stakes actions
```

Everything is: **versioned** (prompts/models/configs), **traced** (every span), **evaluated** (regression gates + prod sampling), **tenant-isolated**, **auditable** (immutable decision lineage).

---

## 📚 Worked case studies (rehearse 2–3 fully)

### Case 1 — "Design a document intelligence agent for loan agreements"
*(extract terms, flag risky covenants, answer questions, draft summaries)*
- **Scope Qs:** volume of docs, languages, table-heavy?, real-time vs batch, does output feed an automated decision or a human?
- **Ingestion:** layout-aware parsing (tables/clauses preserved), structure-aware chunking, metadata (entity, doc type, date, clause), PII handling. Event-driven via Kafka on new doc.
- **Retrieval:** hybrid (BM25 for clause refs/identifiers + vector for semantics) + rerank. KG for cross-document entity relationships (guarantors, cross-defaults).
- **Agent:** supervisor → extraction agent (schema-constrained structured output), covenant-risk agent, QA/RAG agent. Deterministic validation of extracted numbers/dates.
- **Guardrails/eval:** groundedness + citations on every extracted term, human sign-off before anything writes to system of record, golden set of SME-labeled docs for regression, hallucination monitoring.
- **Auditability:** full trace + source citations per extracted field → replayable for disputes.
- **Scale/cost:** cache repeated doc queries (Redis), route simple extractions to a small/cheap model, batch overnight bulk processing.

### Case 2 — "Design a collections / customer-support agent" (borrower interaction)
- Emphasize: **compliance in messaging** (regulated communication rules), tone/policy guardrails, PII, human escalation, no unauthorized financial advice, full transcript audit, refusal calibration.
- Real-time latency (streaming, TTFT), multi-turn memory (Redis), tool use (fetch account state — read-only vs write gated).

### Case 3 — "Design the agent evaluation platform" (very likely, since JD says you own eval)
- Golden dataset store + versioning, LLM-as-judge service (calibrated), regression runner in CI, trajectory eval, prod-traffic sampling → labeling → feedback into goldens, dashboards, A/B + shadow infra, drift alerts. → [04](04_LLMOps_Eval_Guardrails.md).

### Case 4 — "Design a low-latency RAG API at 10k QPS"
- Focus: hybrid retrieval at scale (sharded OpenSearch), aggressive semantic caching (Redis), model routing, continuous batching (vLLM), autoscale on queue depth, p99 budget breakdown across stages, graceful degradation (cached/smaller-model fallback under load). → [03](03_RAG_and_Retrieval.md), [06](06_Distributed_Systems_Backend.md).

---

## 🧨 Failure modes to always address (unprompted)

- **Model/provider outage** → fallback model via gateway, cached responses, degrade gracefully.
- **Latency spike / rate limit** → backpressure (Kafka), timeouts, circuit breakers, queue + async.
- **Hallucination / wrong output** → groundedness checks, human gate, abstention. → [04](04_LLMOps_Eval_Guardrails.md).
- **Cost blowup** → budgets, routing, caching, monitoring + alerts.
- **Bad deploy** → shadow/canary + auto-rollback on eval regression.
- **Security** → prompt injection (untrusted docs!), tenant data leakage, tool least-privilege.
- **Data drift** → prod eval sampling + alerts.

---

## 🎯 LLD (low-level design) prompts you might get

- Design the **tool registry / SDK interface** (how product teams register tools with schemas, auth, governance).
- Design the **agent state schema + checkpointing** (what's persisted, resume semantics, idempotency).
- Design the **model gateway** (routing policy, fallback chain, rate-limit + cost tracking, cache keys).
- Design **idempotent event processing** for inference (dedupe keys, exactly-once side-effects on a ledger).
- Class/interface design for a **guardrail middleware** pipeline (composable input/output/action checks).

For LLD: talk interfaces/contracts, data models, idempotency, error handling, extensibility, testing. Clean abstractions = Principal signal.

---

## 💡 Meta-tips for the design round

- **Drive the conversation.** Principals lead; don't wait to be spoon-fed constraints.
- **State assumptions out loud**, then proceed. Adjust when corrected.
- **Numbers:** do rough capacity math (QPS × avg tokens × cost/token; storage = docs × chunks × vector dim × bytes).
- **Trade-offs, always.** "I'd choose X over Y because Z, accepting trade-off W."
- **Name what you'd measure** to validate the design in prod.
- **Don't over-engineer.** Start simple, scale when justified. "I'd ship the single-agent RAG version first, add multi-agent + KG when the data shows we need it."
