# 00 — Requirements for All 10 Systems

> **Purpose:** the **Phase 1** artifact for every design in this folder — scope, functional
> requirements, quantified NFRs, non-goals, latency budgets, and capacity arithmetic.
> **Read this before any HLD.** An unscoped design is unfalsifiable, and jumping straight to boxes is
> the single most common failure in a design interview.

Each system's HLD and LLD live in its own file (`01_…` through `10_…`). This file is the shared
front-matter: it fixes the numbers those designs must satisfy.

---

## Table of contents

- [Shared conventions](#shared-conventions)
- [How to read a requirements block](#how-to-read-a-requirements-block)
- [1. Production-grade RAG system](#1-production-grade-rag-system)
- [2. AI-powered customer support agent](#2-ai-powered-customer-support-agent)
- [3. Multi-agent AI system](#3-multi-agent-ai-system)
- [4. LLM inference platform](#4-llm-inference-platform)
- [5. Large-scale document intelligence system](#5-large-scale-document-intelligence-system)
- [6. AI recommendation system](#6-ai-recommendation-system)
- [7. LLM evaluation platform](#7-llm-evaluation-platform)
- [8. Real-time AI voice assistant](#8-real-time-ai-voice-assistant)
- [9. Multi-provider LLM platform](#9-multi-provider-llm-platform)
- [10. Enterprise AI agent platform](#10-enterprise-ai-agent-platform)
- [Cross-system requirement matrix](#cross-system-requirement-matrix)
- [Shared assumptions register](#shared-assumptions-register)

---

## Shared conventions

Applied to every system below so the individual blocks stay readable.

### Priority scheme

| Tag | Meaning |
|---|---|
| **P0** | Must exist for v1 to be usable at all. Cutting it cancels the project. |
| **P1** | Needed for production launch. Can ship a private beta without it. |
| **P2** | Wanted; explicitly deferrable. |

### Latency vocabulary

| Term | Meaning | Why it matters |
|---|---|---|
| **p50 / p95 / p99** | Median / 95th / 99th percentile | **A latency target without a percentile is not a target.** p99 is where users churn |
| **TTFT** | Time To First Token | For streaming UIs this *is* perceived latency; total time matters far less |
| **TTFB** | Time To First Byte | Non-streaming equivalent |
| **E2E** | End-to-end, request in → last token out | Governs cost and concurrency, not perceived speed |

### Cost baseline used throughout

Rates below are the **assumed** per-million-token prices used for all arithmetic in this file. They
are illustrative mid-2025-era figures for a "small" and "frontier" hosted model; **verify against
current provider pricing before quoting any of these numbers.**

| Tier | Input / 1M | Output / 1M | Used for |
|---|---|---|---|
| **Small** (e.g. mini/flash class) | $0.15 | $0.60 | Routing, classification, simple queries |
| **Frontier** (e.g. large class) | $3.00 | $15.00 | Hard reasoning, final answers |
| **Embedding** | $0.02 | — | Ingestion + query embedding |
| **Rerank** | ~$1.00 / 1k queries | — | Cross-encoder reranking |

> **⚠️ These are assumptions, not facts.** Labelling them as such is the point — a design that cites
> precise-sounding prices without flagging them as inputs is quietly fragile. Every capacity estimate
> below states which tier it assumes.

### Availability arithmetic

| Target | Downtime/month | Typical cost driver |
|---|---|---|
| 99.0% | ~7.3 h | Single AZ, best-effort |
| 99.9% | ~43 min | Multi-AZ, stateless services, health checks |
| 99.95% | ~22 min | + provider fallback, active-active regions for reads |
| 99.99% | ~4.4 min | Multi-region active-active, hard to reach when you depend on third-party LLM APIs |

> **A hard constraint worth internalizing:** if your system's answer path depends on one external LLM
> provider, **your availability ceiling is that provider's SLA** — typically 99.9%. Promising 99.99%
> is only credible with a fallback provider *and* a degraded non-LLM path (§9).

---

## How to read a requirements block

Each of the ten follows the same skeleton:

1. **Problem & users** — what breaks today, who feels it
2. **Functional requirements** — numbered, testable, prioritized
3. **NFRs** — quantified, with the reason for each number
4. **Non-goals** — scoping, stated as a skill not an omission
5. **Latency budget** — decomposed, and it must *sum* to the SLO
6. **Capacity & cost** — arithmetic shown, assumptions labelled
7. **Assumptions & open questions** — what would change the design if false

---

# 1. Production-grade RAG system

> **Prompt:** Design a production-grade RAG system — document ingestion, chunking, embeddings, vector
> DB, retrieval, reranking, LLM, citations, evaluation, caching, scaling.

## 1.1 Problem & users

An enterprise has ~10M internal documents (policies, wikis, tickets, PDFs) spread across
SharePoint, Confluence, and S3. Employees can't find answers; search returns keyword matches, not
answers. **Primary user:** an employee asking a natural-language question. **Primary job:** get a
correct, *attributable* answer in seconds. Attribution is not a nice-to-have — an answer nobody can
verify is worse than no answer, because it gets trusted and repeated.

## 1.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Answer a natural-language question from the corpus | Groundedness ≥ 0.95 on the golden set |
| FR-2 | P0 | **Inline citations** to source passages | ≥ 90% of factual claims carry a resolvable citation |
| FR-3 | P0 | Ingest PDF, DOCX, HTML, Markdown, plain text | Parse success ≥ 99% on the corpus sample |
| FR-4 | P0 | Enforce per-user document ACLs at query time | Zero cross-permission leaks in the ACL test suite |
| FR-5 | P0 | Refuse when retrieval is insufficient | Says "not found in the documents" rather than guessing |
| FR-6 | P1 | Incremental re-ingest on source change | New/changed doc searchable < 5 min |
| FR-7 | P1 | Stream the answer | TTFT within budget (§1.5) |
| FR-8 | P1 | Offline eval suite + CI regression gate | Blocks deploy on > 3-point drop in any tier-1 metric |
| FR-9 | P1 | Hard delete a document from index + caches | Purged within 15 min (GDPR right-to-erasure) |
| FR-10 | P2 | Multi-turn follow-ups with query rewriting | Resolves pronouns against conversation history |
| FR-11 | P2 | Feedback capture (thumbs) feeding the golden set | — |

## 1.3 Non-functional requirements

| NFR | Target | Why this number |
|---|---|---|
| TTFT | p95 < 1.5 s | Users tolerate ~2 s of silence before perceiving a hang |
| E2E answer | p95 < 6 s | Long enough for a ~400-token grounded answer at streaming speed |
| Throughput | 50 QPS sustained, 200 QPS peak | 5k daily actives × ~8 queries/day, 4× diurnal peak |
| Availability | 99.9% | Internal tool; ceilinged by the LLM provider's own SLA anyway |
| Groundedness | ≥ 0.95 | Below this, citation trust collapses and users stop using it |
| Citation accuracy | ≥ 0.90 | A wrong citation is worse than none — it manufactures false confidence |
| Retrieval recall@20 | ≥ 0.90 | Retrieval is the ceiling on the whole system; the generator cannot recover what was never fetched |
| Cost | ≤ $0.02/query, ≤ $8k/month | Unit-economics ceiling from the business |
| Freshness | Searchable < 5 min after source change | Promised to content owners |
| Scale | 10M docs, ~80M chunks, 5k tenants | Sizing driver for the retrieval tier |
| Isolation | Tenant + ACL filter pushed **into** the ANN query | Post-filtering leaks and silently wrecks recall |

## 1.4 Non-goals

- Model training or fine-tuning — we consume hosted models.
- Multi-modal input (images, audio) — text only in v1.
- Writing back to source systems — read-only.
- Real-time collaborative editing of documents.
- Cross-lingual retrieval — English only in v1.

## 1.5 Latency budget (TTFT, p95)

| Stage | Budget | Note |
|---|---|---|
| Auth + validation | 20 ms | JWT verify, no DB hit |
| Semantic cache lookup | 30 ms | Short-circuits everything below on hit |
| Query embedding | 60 ms | Small embedding model, batched |
| Vector search (top-50, ACL-filtered) | 120 ms | HNSW with tenant + ACL predicate |
| Rerank 50 → 8 (cross-encoder) | 180 ms | The single biggest optional cost |
| Prompt assembly | 20 ms | Template + context packing |
| **LLM TTFT** | **900 ms** | Frontier tier, ~1.8k-token prompt |
| Guardrail (output, streaming) | 100 ms | **Overlapped** with generation, not additive |
| **Total** | **≈ 1.33 s** | vs 1.5 s SLO → **~170 ms headroom** ✅ |

**Cache-hit path:** 20 + 30 = **50 ms** — two orders of magnitude better, which is why the semantic
cache sits first and why its hit rate dominates the cost model.

## 1.6 Capacity & cost

```
Traffic
  50 QPS avg → 50 × 86,400 ≈ 4.3M requests/day ≈ 130M/month

Tokens per request  (assumption: measured from a prototype)
  input  1,800  (1,200 system prompt + 8 chunks × ~75 tokens)
  output   400

Naive cost, frontier tier
  in:  1800/1e6 × $3.00  = $0.0054
  out:  400/1e6 × $15.00 = $0.0060
  total ≈ $0.0114/query  →  130M × $0.0114 ≈ $1.48M/month   ← 185× over the $8k ceiling ⇒ REDESIGN
```

**This is the point of doing the arithmetic.** The naive design is off by more than two orders of
magnitude. Levers, cheapest-to-implement first:

| Lever | Mechanism | Est. effect | Residual |
|---|---|---|---|
| Prompt caching | 1,200 of 1,800 input tokens are a static system prompt | input −~55% | ~$1.1M |
| Semantic cache | Assume 30% of queries are near-duplicates | total −30% | ~$780k |
| **Model routing** | Route ~70% of queries to the small tier | blended −~80% | ~$160k |
| Context trimming | 8 chunks → 5 via better reranking | input −~25% | ~$130k |
| Shorter answers | Cap output at 250 tokens | output −~38% | ~$95k |

Still ~12× over. **The honest conclusion: $8k/month at 130M queries/month is not achievable with a
hosted frontier model.** Options to put to the business:

1. **Raise the ceiling** to ~$100k/month (≈ $0.0008/query — defensible for an internal tool).
2. **Cut traffic assumptions** — 130M/month is 8 queries/day/user for 5k users *every day*; realistic
   engagement is likely 5–10× lower, which alone lands near budget.
3. **Self-host** a small open-weight model for the 70% simple tier — trades API cost for GPU cost and
   operational burden (see §4).

> **Interview signal:** discovering the requirements are mutually unsatisfiable, and saying so with
> numbers and options, is a *stronger* answer than a design that silently pretends otherwise.

**Storage**

```
10M docs × 8 chunks = 80M chunks
Embeddings @ 1024 dims:
  float32:  80M × 1024 × 4 B = 327 GB       ← wrong default at this scale
  int8:     80M × 1024 × 1 B =  82 GB       ← quantize; ~1-2% recall loss, typically acceptable
  + HNSW graph overhead ~40%  ≈ 115 GB      ⇒ budget ~128 GB RAM, or disk-backed IVF
Raw text: 80M × 300 B ≈ 24 GB (object store, cheap)
```

## 1.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | 30% semantic-cache hit rate | Cost model degrades ~linearly; re-measure on real traffic |
| A2 | 70% of queries answerable by the small tier | Routing savings shrink; may need a mid tier |
| A3 | ACLs are resolvable to a filter expression at query time | If ACLs need a per-doc service call, retrieval latency blows the budget → need a denormalized ACL cache |
| A4 | Documents are mostly text-extractable | Scanned PDFs push work into the OCR pipeline (§5) |
| **Q1** | Are stale answers acceptable during reindex? | Determines dual-write vs. cutover complexity |
| **Q2** | Is the 5-min freshness SLA per-document or per-source? | Changes ingestion batching strategy |

---

# 2. AI-powered customer support agent

> **Prompt:** Intent detection, tool calling, conversation memory, RAG, human handoff, guardrails,
> observability.

## 2.1 Problem & users

A SaaS company receives ~20k support conversations/day. ~60% are repetitive (password resets, billing
questions, "where is my invoice"). **Primary user:** a customer wanting a resolution, not a chat.
**Secondary user:** the support agent who inherits the conversation on handoff — and who needs full
context, not a transcript to re-read. **Primary job:** resolve or cleanly escalate.

**The defining constraint:** this agent *acts* — it issues refunds, changes plans, resets
credentials. A wrong sentence is embarrassing; a wrong **action** is a financial and trust incident.
That distinction drives the whole design.

## 2.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Classify intent + urgency | ≥ 0.92 macro-F1 on the labelled set |
| FR-2 | P0 | Answer from help-centre KB via RAG | Groundedness ≥ 0.95 |
| FR-3 | P0 | Call tools (order lookup, invoice fetch, plan change, refund) | Correct tool + args ≥ 0.95 on the tool-eval set |
| FR-4 | P0 | **Human approval gate for side-effecting actions** above a value threshold | 100% of refunds > $50 require approval |
| FR-5 | P0 | Escalate to human with full context summary | Handoff packet includes intent, steps taken, tool calls, sentiment |
| FR-6 | P0 | Conversation memory within a session | Resolves references across ≥ 10 turns |
| FR-7 | P0 | Guardrails: PII redaction, abuse, injection, off-topic | Zero PII in third-party provider payloads |
| FR-8 | P1 | Cross-session memory (recognize a returning customer) | Retrieves prior tickets for the same account |
| FR-9 | P1 | Multi-channel (web chat, email, WhatsApp) | Shared session state across channels |
| FR-10 | P1 | Full trace per conversation: prompts, tools, tokens, cost | Replayable for audit |
| FR-11 | P1 | Deflection + CSAT metrics per intent | Dashboard |
| FR-12 | P2 | Proactive suggestions to the human agent post-handoff | — |

## 2.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| First response TTFT | p95 < 2 s | Chat expectation; slower reads as broken |
| Tool-call round trip | p95 < 3 s added | Internal APIs; anything slower needs a "working on it" message |
| Availability | 99.95% | Customer-facing; a support outage during an incident is compounding |
| Deflection rate | ≥ 50% resolved without human | The business case for the project |
| **Escalation recall** | ≥ 0.98 | **Missing a required escalation is the worst failure mode** — worse than over-escalating |
| Wrong-action rate | < 0.1% of side-effecting calls | Each one is a financial incident |
| Cost | ≤ $0.15/conversation | vs. ~$4 human handling cost |
| Concurrency | 500 concurrent conversations | 20k/day, ~8-min average duration, peaked |
| Data retention | Transcripts 90 d; audit log 1 yr | Policy |

## 2.4 Non-goals

- Voice support — text channels only (voice is §8).
- Autonomous refunds above the threshold — always human-approved.
- Replacing the human team — deflection, not elimination.
- Training a custom intent model in v1 — start with an LLM classifier, revisit if cost demands.

## 2.5 Latency budget (first response, p95)

| Stage | Budget |
|---|---|
| Session load + auth | 40 ms |
| Guardrail: input (injection, PII, abuse) | 120 ms |
| Intent classification (small tier) | 300 ms |
| Memory retrieval (session + cross-session) | 100 ms |
| KB retrieval + rerank | 300 ms |
| **LLM TTFT** | **900 ms** |
| Output guardrail | 100 ms (overlapped) |
| **Total** | **≈ 1.76 s** vs 2 s SLO → ~240 ms headroom ✅ |

Tool-calling turns add a full round trip (tool latency + a second LLM call to interpret the result),
which is why FR-3's budget is stated separately and why any tool over ~2 s needs an interim message.

## 2.6 Capacity & cost

```
20k conversations/day; assume 8 LLM turns each = 160k LLM calls/day
Assume tokens/turn: 2,500 in (system + memory + KB context + history) / 250 out

Blended routing assumption: 60% small tier, 40% frontier
  small:    (2500/1e6 × $0.15) + (250/1e6 × $0.60) = $0.000525
  frontier: (2500/1e6 × $3.00) + (250/1e6 × $15.00) = $0.01125
  blended ≈ 0.6(0.000525) + 0.4(0.01125) = $0.00482/turn
  per conversation: × 8 ≈ $0.039     ✅ under the $0.15 ceiling

Monthly: 20k × 30 × $0.039 ≈ $23.4k/month
Human baseline avoided: 50% deflection × 600k conv/yr × $4 ≈ $1.2M/yr  ⇒ clearly positive ROI
```

Concurrency: `500 concurrent × ~1 LLM call per 60 s of conversation ≈ 8-10 QPS` to the provider —
modest; **the binding constraint is provider rate limits and tool-API capacity, not model cost.**

## 2.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | 8 turns/conversation average | Cost scales linearly |
| A2 | Internal tool APIs respond < 1 s p95 | Need async "I'm working on it" UX |
| A3 | 60/40 routing split holds | Cost moves toward $0.09/conv — still under ceiling |
| **Q1** | What is the refund approval threshold? | Sets the human-in-the-loop volume |
| **Q2** | Is cross-session memory permitted under the privacy policy? | May forbid FR-8 outright |
| **Q3** | Who owns the escalation taxonomy? | Blocks FR-1 label set |

---

# 3. Multi-agent AI system

> **Prompt:** Agent orchestration, planner/executor, communication, shared state, tool management,
> failure handling, cost control.

## 3.1 Problem & users

Tasks that a single agent handles poorly because they need **decomposition and specialization** —
e.g. "research these 5 competitors and produce a comparison memo." **Primary user:** a knowledge
worker delegating a multi-step task. **Primary job:** get a correct compiled result without
babysitting.

> **⚠️ The requirement to challenge first.** Multi-agent architectures are frequently chosen for
> fashion rather than need. **A single agent with good tools beats a multi-agent system for most
> tasks**, and costs far less. Multi-agent earns its complexity only when: (a) subtasks are genuinely
> **parallelizable**, (b) subtasks need **different tools or privileges**, or (c) you want
> **independent verification** of a result. Saying this out loud is a senior signal; designing a
> 6-agent system for a task one agent could do is the opposite.

## 3.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Decompose a goal into a DAG of subtasks | Valid, acyclic, dependency-correct plan |
| FR-2 | P0 | Execute independent subtasks **in parallel** | Wall-clock < sum of subtask times |
| FR-3 | P0 | Per-agent tool allow-lists | An agent cannot invoke a tool outside its list |
| FR-4 | P0 | Shared state / blackboard readable by all agents | Consistent reads; no lost updates |
| FR-5 | P0 | **Hard budget caps** — tokens, wall-clock, step count, $ | Run aborts at cap with partial results, never runs away |
| FR-6 | P0 | Synthesize subtask outputs into one deliverable | — |
| FR-7 | P1 | Retry a failed subtask without restarting the run | Idempotent subtask execution |
| FR-8 | P1 | Verifier/critic agent reviews the result before return | Catches ≥ 50% of injected errors in the eval set |
| FR-9 | P1 | Full run trace: plan,每 agent step, tool calls, cost | Replayable |
| FR-10 | P1 | Human checkpoint before side-effecting actions | — |
| FR-11 | P2 | Dynamic replanning when a subtask reveals new information | — |

## 3.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| E2E task time | p95 < 5 min for a 10-subtask run | Async UX; user does something else |
| Parallel speedup | ≥ 3× vs sequential on parallelizable DAGs | The justification for the architecture |
| Cost per run | ≤ $2.00, hard cap $5.00 | Above this, a human doing it is cheaper |
| Step cap | ≤ 50 agent steps/run | Runaway-loop backstop |
| Task success | ≥ 0.80 on the eval suite | — |
| Determinism | Same input + same versions → same **plan** | Debuggability; execution may still vary |
| Availability | 99.9% | Async; retries absorb blips |
| Isolation | One agent's failure must not corrupt shared state | Transactional blackboard writes |

## 3.4 Non-goals

- Open-ended autonomy — every run is bounded and goal-scoped.
- Agents writing production code unreviewed.
- Emergent agent-to-agent negotiation — communication is via the structured blackboard, not free-form
  chat (free-form inter-agent chat burns tokens and degrades into loops).
- Self-modifying agents.

## 3.5 Cost & budget control (the section that matters most)

Multi-agent cost is **multiplicative**, and this is where naive designs explode:

```
Naive: 10 subtasks × 5 turns each × frontier tier
  per turn: (3000/1e6 × $3.00) + (500/1e6 × $15.00) = $0.009 + $0.0075 = $0.0165
  run: 10 × 5 × $0.0165 = $0.825
  + planner (3 calls) + synthesizer (2 calls) + critic (2 calls) ≈ 7 × $0.0165 = $0.116
  ⇒ ≈ $0.94/run   ✅ under the $2 ceiling

But add ONE retry loop per subtask and it doubles to ~$1.9 — at the ceiling.
And an unbounded replanning loop is UNBOUNDED cost. Hence FR-5 is P0, not P1.
```

**Enforcement mechanisms (all required):**

| Control | Mechanism |
|---|---|
| Token budget | Decremented atomically per call; run aborts at 0 |
| Step cap | Hard counter, 50 steps |
| Wall-clock cap | 10 min, then abort with partials |
| $ cap | Pre-flight estimate + running total; abort at $5 |
| Per-agent model tier | Workers on small tier; planner/critic on frontier |
| Loop detection | Abort if the same (agent, tool, args-hash) repeats 3× |

## 3.6 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | Tasks decompose into ≤ 10 subtasks | Deeper DAGs need hierarchical planning and blow the step cap |
| A2 | Subtasks are mostly independent | Serial dependencies erase the parallel speedup — and remove the justification for multi-agent |
| A3 | A critic catches ≥ 50% of errors | If lower, human review becomes mandatory |
| **Q1** | Is partial output acceptable on abort? | Determines the synthesizer's contract |
| **Q2** | Can two agents hold conflicting conclusions? | Needs a resolution policy in the synthesizer |

---

# 4. LLM inference platform

> **Prompt:** Model routing, GPU management, batching, streaming, autoscaling, latency, rate
> limiting, fallback models, observability.

## 4.1 Problem & users

Serve **self-hosted open-weight models** to internal product teams — the build-vs-buy inverse of §9.
**Primary user:** an application engineer who wants an OpenAI-compatible endpoint and doesn't want to
know about GPUs. **Primary job:** low-latency inference at predictable cost.

**Why self-host at all** (the question to answer before designing): data residency/privacy that
forbids third-party APIs; cost at sustained high volume; latency floors; model customization; or
avoiding provider deprecation cycles. **If none apply, don't build this — use §9.**

## 4.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | OpenAI-compatible `/v1/chat/completions`, streaming + non-streaming | Drop-in for existing SDKs |
| FR-2 | P0 | Serve ≥ 3 model sizes concurrently | 8B, 24B, 70B class |
| FR-3 | P0 | **Continuous batching** | ≥ 5× throughput vs static batching |
| FR-4 | P0 | Per-tenant rate limits + quotas (RPM and TPM) | 429 with `Retry-After` |
| FR-5 | P0 | Autoscale on **queue depth**, not CPU | Scale-up latency < 3 min |
| FR-6 | P0 | Route by requested model + fallback on capacity loss | — |
| FR-7 | P1 | Prefix/KV cache reuse across requests | ≥ 30% TTFT reduction on shared system prompts |
| FR-8 | P1 | Per-request metrics: tokens, TTFT, TPOT, queue time, GPU | Prometheus |
| FR-9 | P1 | Rolling model updates with zero dropped requests | Drain + blue/green |
| FR-10 | P1 | Speculative decoding for the large tier | — |
| FR-11 | P2 | LoRA adapter hot-swap on a shared base | Multi-tenant fine-tunes without extra GPUs |

## 4.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| TTFT | p95 < 400 ms (8B), < 900 ms (70B) | Self-hosting's main win is beating API latency |
| **TPOT** (time per output token) | < 25 ms → ≥ 40 tok/s | Below ~20 tok/s reads as slow to a human reader |
| Throughput | ≥ 2,500 output tok/s per 8×H100 node (8B, batched) | Utilization target driving unit cost |
| GPU utilization | ≥ 60% average | Below this, self-hosting loses to APIs on cost |
| Availability | 99.9% | Multi-AZ; GPU capacity is the constraint |
| Queue wait | p95 < 200 ms | Above this, add capacity |
| Cost | ≤ $0.30 per 1M output tokens (8B) | Must beat the API alternative to justify existing |
| Max context | 32k tokens | KV-cache memory driver |

## 4.4 Non-goals

- Training or fine-tuning (serving only; adapters are consumed, not produced).
- Non-text modalities in v1.
- Serving third-party APIs — that's §9. **This platform serves weights we host.**
- Per-request GPU isolation — batching is the whole point.

## 4.5 The memory arithmetic that sizes everything

This is the calculation that determines the entire design:

```
Model weights (70B class)
  fp16:  70B × 2 B = 140 GB     → needs 2× H100-80GB minimum, tensor-parallel
  int8:  70B × 1 B =  70 GB     → fits 1× H100-80GB, but leaves ~10 GB for KV cache ⇒ tiny batch
  int4:  70B × 0.5 B = 35 GB    → 1× H100, ~45 GB for KV cache ⇒ real batching possible

KV cache per token (70B: 80 layers, 64 heads, 128 head_dim, GQA 8 kv-heads)
  2 (K+V) × 80 layers × 8 kv_heads × 128 dim × 2 B (fp16) ≈ 327 KB/token
  A 32k-context request: 32,000 × 327 KB ≈ 10.5 GB for ONE request

⇒ On 1× H100-80GB with int4 weights (35 GB), ~45 GB usable KV:
     45 GB / 10.5 GB ≈ 4 concurrent full-context requests
   With realistic 4k-context requests (1.3 GB each): ~34 concurrent
```

> **The design consequence:** **KV cache, not model weights, is the binding constraint on
> concurrency.** This is why continuous batching + PagedAttention matter so much, and why GQA
> (grouped-query attention) is load-bearing in modern models — it cuts KV cache ~8× versus full
> multi-head attention. A design that discusses GPU memory only in terms of weights has missed the
> actual bottleneck.

## 4.6 Capacity & cost

```
Assume: 8×H100 node ≈ $32/hr (cloud, on-demand) ≈ $23k/month
8B model, int8, continuous batching → assume ~2,500 output tok/s/node sustained

Monthly output capacity: 2,500 × 2.6M s ≈ 6.5B output tokens
Cost per 1M output tokens: $23,000 / 6,500 ≈ $3.54       ← at 100% utilization

At the 60% utilization target: ≈ $5.90 per 1M output tokens
Compare: small-tier hosted API at $0.60 per 1M output   ⇒ SELF-HOSTING IS ~10× MORE EXPENSIVE HERE
```

> **⚠️ The uncomfortable conclusion, and the point of running the numbers.** At this scale and with a
> small model, **self-hosting loses badly to a hosted API.** Self-hosting wins when:
> - Volume is high enough to keep utilization > 80% *and* reserved/spot pricing applies (can cut GPU
>   cost 60-70%).
> - The comparison is against a **frontier-tier** API ($15/1M out), not a small tier — then
>   $5.90 vs $15 is a real win.
> - **Non-cost drivers dominate:** data residency, privacy, latency floor, no per-token billing.
>
> **Do not justify this platform on cost alone unless the arithmetic actually supports it.** State
> the real driver.

## 4.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | ~2,500 output tok/s per node for 8B batched | Benchmark before committing; varies hugely with context length |
| A2 | On-demand GPU pricing | Reserved/spot changes the conclusion materially |
| A3 | Average context ~4k, not 32k | Long contexts collapse concurrency (§4.5) |
| **Q1** | What is the actual non-cost driver? | If none, cancel and use §9 |
| **Q2** | Is GPU capacity procurable at the needed scale? | Supply, not budget, is often the real constraint |

---

# 5. Large-scale document intelligence system

> **Prompt:** PDF/image ingestion, OCR, document parsing, extraction, validation, asynchronous
> processing, retries, storage.

> **Overlaps** [`21_ai-system-design-deep-dives/02_document_intelligence_agent.md`](../21_ai-system-design-deep-dives/02_document_intelligence_agent.md),
> which covers loan/bond term extraction in a fintech domain. **This one is the generic,
> high-throughput pipeline**: any document type, OCR-first, batch-scale. Read both; the fintech file
> goes deeper on domain validation, this one on throughput and failure handling.

## 5.1 Problem & users

Process ~500k documents/day — invoices, contracts, forms, scanned images — into validated structured
data. **Primary user:** a downstream business system consuming structured records. **Primary job:**
turn a page into trustworthy fields, with confidence scores and a human queue for the uncertain ones.

**The defining property:** this is a **throughput-bound async pipeline**, not a latency-bound request
path. That single fact changes almost every design decision versus §1 and §2.

## 5.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Ingest PDF (native + scanned), TIFF, JPEG, PNG, DOCX | ≥ 99.5% accepted without crash |
| FR-2 | P0 | OCR scanned pages | Character error rate < 2% on the benchmark set |
| FR-3 | P0 | Layout parsing: tables, columns, headers, key-value regions | Table structure F1 ≥ 0.85 |
| FR-4 | P0 | Extract a typed schema per document class | Field-level accuracy ≥ 0.95 on P0 fields |
| FR-5 | P0 | **Per-field confidence score** | Calibrated: low-confidence fields correlate with actual errors |
| FR-6 | P0 | Validation rules (totals sum, dates plausible, IDs match format) | Violations flagged, never silently corrected |
| FR-7 | P0 | Human review queue for low-confidence / failed validation | Prioritized by value × uncertainty |
| FR-8 | P0 | Async processing with **idempotent retries** | Re-submitting a document never double-writes |
| FR-9 | P1 | Classify document type before extraction | ≥ 0.97 accuracy |
| FR-10 | P1 | Handle 500-page documents without timeout | Page-level parallelism |
| FR-11 | P1 | Dead-letter queue + replay | No silent drops |
| FR-12 | P1 | Full lineage: page → region → field → value | Auditable |
| FR-13 | P2 | Active learning from human corrections | — |

## 5.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| Throughput | 500k docs/day ≈ 6 docs/s avg, 25 docs/s peak | Business volume, 4× peak |
| E2E latency | p95 < 5 min/doc; p99 < 30 min | Async SLA to downstream |
| Availability | 99.9% ingestion accept | Queue absorbs processing outages; **rejecting an upload is the unacceptable failure** |
| Durability | 99.999999999% (11 nines) | Object store; source documents must never be lost |
| Field accuracy | ≥ 0.95 P0 fields, ≥ 0.85 P1 | Below this, human review volume kills the ROI |
| Auto-approval rate | ≥ 70% straight-through | The business case |
| Cost | ≤ $0.05/document | vs ~$1.50 manual entry |
| Retention | Source 7 yr; extractions 7 yr | Compliance |

## 5.4 Non-goals

- Real-time/synchronous extraction — async only (a sync API is a separate, latency-bound design).
- Handwriting recognition in v1 — print only.
- Document *generation*.
- Languages beyond English/Spanish in v1.

## 5.5 Capacity & cost

```
500k docs/day, assume 8 pages/doc average = 4M pages/day

OCR:  cloud OCR assume ~$1.50/1000 pages → 4M/1000 × $1.50 = $6,000/day  ← DOMINATES
      self-hosted OCR on GPU: assume 40 pages/s/GPU → 4M/40 = 100k GPU-s/day ≈ 28 GPU-hr/day
      at $2/GPU-hr ≈ $56/day  ⇒ ~100× cheaper; strong case to self-host OCR

LLM extraction (only on parsed text, not every page):
  assume 3,000 in / 400 out per doc, small tier
  (3000/1e6 × $0.15) + (400/1e6 × $0.60) = $0.00045 + $0.00024 = $0.00069/doc
  500k × $0.00069 ≈ $345/day

Storage: 500k × 8 pages × ~200 KB ≈ 800 GB/day ≈ 24 TB/month
  at ~$0.023/GB/month ≈ $550/month, growing; lifecycle to cold storage after 90 d

Daily total (self-hosted OCR): ~$56 + $345 + storage ≈ $420/day ≈ $0.0008/doc
  ✅ far under the $0.05 ceiling — the ceiling is set by HUMAN REVIEW, not compute
```

**The real cost driver:** at 70% auto-approval, 150k docs/day go to human review. At ~30 s/doc and a
$15/hr reviewer, that is `150k × 30/3600 × $15 ≈ $18,750/day` — **45× the compute cost.** Every
percentage point of auto-approval rate is worth ~$270/day. **This is where the design effort belongs**,
and it reframes confidence calibration (FR-5) from a nicety into the highest-leverage requirement in
the system.

## 5.6 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | 8 pages/doc average | Linear scaling of OCR cost |
| A2 | 70% auto-approval achievable | Review cost dominates further; may need per-class thresholds |
| A3 | Self-hosted OCR reaches ~40 pages/s/GPU | Benchmark; falls back to cloud OCR at 100× cost |
| **Q1** | How many document classes, and are they known upfront? | Determines classifier vs. open-set extraction |
| **Q2** | Is a wrong auto-approved field recoverable downstream? | Sets the confidence threshold policy |

---

# 6. AI recommendation system

> **Prompt:** Candidate generation, ranking, embeddings, feature store, online/offline inference,
> feedback loops, personalization.

## 6.1 Problem & users

Recommend items (products/content) to ~10M monthly actives across a 5M-item catalogue. **Primary
user:** an end user browsing a home feed. **Primary job:** surface something they'll engage with.

> **⚠️ Note on why this is in an AI-platform set:** this is **classical ML system design**, not LLM
> design, and that's deliberate — knowing *when not to reach for an LLM* is itself signal. An LLM in
> the ranking hot path at 5k QPS would be both too slow and ~1000× too expensive. LLMs belong here
> only in offline roles: generating item embeddings from descriptions, or cold-start feature
> enrichment.

## 6.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Return top-N personalized recommendations | p95 < 150 ms |
| FR-2 | P0 | Multi-source candidate generation (collaborative, content, trending, recent) | Recall@500 ≥ 0.80 vs. engaged set |
| FR-3 | P0 | ML ranking over candidates | +≥ 10% CTR vs. popularity baseline |
| FR-4 | P0 | Feature store with **train/serve consistency** | Zero training-serving skew on shared features |
| FR-5 | P0 | Log impressions + engagements for training | No loss; exactly-once semantics into the warehouse |
| FR-6 | P0 | Cold-start for new users and new items | Content-based fallback |
| FR-7 | P1 | Business rules: dedup, diversity, blocklists, freshness | Post-ranking layer |
| FR-8 | P1 | Near-real-time features (last-N interactions) | < 30 s to reflect |
| FR-9 | P1 | A/B framework with guardrail metrics | — |
| FR-10 | P1 | Daily model retrain + shadow eval before promotion | — |
| FR-11 | P2 | Explanations ("because you viewed X") | — |

## 6.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| Serving latency | p95 < 150 ms, p99 < 250 ms | Feed render budget; blocks page paint |
| Throughput | 5k QPS sustained, 20k peak | 10M MAU, session patterns |
| Availability | 99.95% | A blank feed is a broken product |
| Freshness (behaviour) | New interaction reflected < 30 s | Session relevance |
| Freshness (model) | Retrain daily | Catalogue and taste drift |
| Offline/online metric parity | Offline AUC lift ⇒ online CTR lift, sign-consistent | Otherwise offline eval is useless |
| Cost | ≤ $0.30 per 1k recommendation requests | Unit economics |
| Fallback | Popularity list always available | Degraded mode is never a blank feed |

## 6.4 Non-goals

- LLM in the ranking hot path (see §6.1).
- Real-time model training — daily batch + NRT features.
- Cross-device identity resolution in v1.
- Full causal uplift modelling — correlational ranking in v1.

## 6.5 Latency budget (p95, 150 ms)

| Stage | Budget |
|---|---|
| Request + auth | 10 ms |
| Fetch user features (feature store, cached) | 20 ms |
| Candidate generation — 4 sources **in parallel** | 40 ms (max, not sum) |
| Dedup + merge to ~500 | 10 ms |
| Feature hydration for 500 candidates | 25 ms |
| Ranking model inference (batch of 500) | 30 ms |
| Business rules + diversity | 10 ms |
| **Total** | **≈ 145 ms** ✅ (5 ms headroom — tight; parallelism in candidate gen is load-bearing) |

## 6.6 Capacity & cost

```
5k QPS × 86,400 ≈ 432M requests/day

Ranking inference: 500 candidates × 432M = 216B scorings/day
  ⇒ MUST be a small model (GBDT or a shallow DNN), batched, CPU-servable
  A transformer at 1 ms/candidate would need 216B ms = 2.5M CPU-hours/day — absurd
  ⇒ target ~0.06 ms/candidate: 216B × 0.06 ms = 3.6M s ≈ 1,000 CPU-hr/day ≈ $50/day

Embeddings: 5M items × 256 dims × 4 B = 5 GB  → fits in memory on every serving node
Users: 10M × 256 × 4 B = 10 GB → feature store (Redis), not per-node

Cost: ~$50/day inference + ~$200/day feature store + ~$100/day logging ≈ $350/day
  per 1k requests: $350 / 432k ≈ $0.0008   ✅ far under the $0.30 ceiling
```

> The arithmetic makes the architecture inevitable: **216B scorings/day forces a cheap model**. This
> is why recsys uses two stages — cheap recall over millions, expensive ranking over hundreds. A
> single-stage design is not merely suboptimal, it's arithmetically impossible.

## 6.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | ~500 candidates suffice for recall@500 ≥ 0.80 | More candidates → ranking cost scales linearly |
| A2 | GBDT-class model meets the CTR target | A DNN needs GPU serving and re-budgeting |
| A3 | Offline AUC predicts online CTR directionally | If not, only A/B tests can gate releases — slows iteration hard |
| **Q1** | What is the true objective — CTR, watch time, revenue, retention? | Changes labels, loss, and guardrails entirely |
| **Q2** | Any fairness/exposure constraints for sellers/creators? | Adds constraints to the ranking layer |

---

# 7. LLM evaluation platform

> **Prompt:** Dataset management, offline evaluation, LLM-as-a-judge, human evaluation, metrics,
> regression detection, experiment tracking.

> **Overlaps** [`21_ai-system-design-deep-dives/04_agent_eval_guardrail_platform.md`](../21_ai-system-design-deep-dives/04_agent_eval_guardrail_platform.md)
> (eval + guardrails combined, fintech agent context) and builds directly on the concepts in
> [`16_evals/`](../16_evals/README.md). **This file is the platform**: multi-team, multi-app, the
> system other teams' CI calls.

## 7.1 Problem & users

20 product teams ship LLM features with no shared way to answer *"is this change better?"*
**Primary user:** an engineer who changed a prompt and needs a verdict before merging. **Secondary:**
a PM tracking quality over time; a compliance reviewer needing evidence.

**The defining constraint:** the platform is itself in the release path. **If it's slow or flaky,
teams route around it** — so CI latency and determinism are product requirements, not nice-to-haves.

## 7.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Versioned datasets (golden sets) with lineage | Immutable; every run pinned to a dataset version |
| FR-2 | P0 | Run an eval suite against a target app/prompt/model version | — |
| FR-3 | P0 | Built-in metrics: groundedness, answer relevance, correctness, contextual precision/recall | Match published reference implementations within tolerance |
| FR-4 | P0 | **LLM-as-a-judge with G-Eval-style stabilization** | Same input → score variance < 0.05 across reruns |
| FR-5 | P0 | Custom metrics via user-supplied criteria/rubric | — |
| FR-6 | P0 | **Regression detection vs. a pinned baseline** | Blocks CI on > threshold drop |
| FR-7 | P0 | Experiment tracking: config + metric history | Comparable across runs |
| FR-8 | P1 | Human evaluation workflow with inter-rater agreement | Reports Cohen's κ; flags ambiguous rubrics |
| FR-9 | P1 | Online eval on sampled production traffic | Configurable sample rate |
| FR-10 | P1 | Judge calibration against human labels (MAE) | Reported per metric |
| FR-11 | P1 | CI integration (GitHub Actions) with pass/fail gate | — |
| FR-12 | P2 | Auto dataset synthesis from production failures | — |
| FR-13 | P2 | Cost/latency captured alongside quality (operational evals) | — |

## 7.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| Suite runtime | p95 < 10 min for 200 test cases | **Must fit in a CI gate** or teams bypass it |
| Parallelism | ≥ 32 concurrent judge calls | How the 10-min target is met |
| Judge determinism | score σ < 0.05 across reruns | Otherwise regression detection is noise |
| Judge-human agreement | MAE ≤ 1.0 on a 0–10 scale | Below this, the judge isn't trustworthy as a gate |
| Availability | 99.5% | Internal; a retry is acceptable |
| Throughput | 500 suite runs/day across 20 teams | 25 runs/team/day |
| Cost | ≤ $2.00 per 200-case suite run | Cheap enough to run on every PR |
| Retention | Runs + traces 1 yr | Trend analysis, audit |
| Isolation | Team A cannot read team B's datasets | Multi-tenant |

## 7.4 Non-goals

- Being the guardrail/runtime-blocking layer (that's a serving concern, §10).
- Training reward models.
- Replacing human review for high-stakes launches — gating, not deciding.
- Evaluating non-LLM models (classical ML metrics are out of scope).

## 7.5 Capacity & cost

```
200 test cases × ~3 metrics = 600 judge calls per suite run
Assume judge = frontier tier (quality matters), 1,500 in / 200 out per judge call
  (1500/1e6 × $3.00) + (200/1e6 × $15.00) = $0.0045 + $0.0030 = $0.0075/judge call
  per run: 600 × $0.0075 = $4.50      ← EXCEEDS the $2.00 ceiling

Plus the target app's own calls: 200 cases × $0.0114 (from §1) = $2.28
  ⇒ true total ≈ $6.78/run
  500 runs/day × $6.78 ≈ $3,390/day ≈ $102k/month   ← untenable
```

**Levers:**

| Lever | Effect | New cost/run |
|---|---|---|
| Judge on small tier for cheap metrics, frontier only for correctness/groundedness | −60% judge cost | ~$4.00 |
| Cache judge verdicts keyed by (prompt-hash, output-hash, metric, judge-version) — reruns of unchanged cases are free | Assume 50% hit on iterative PRs | ~$2.30 |
| Tiered suites: 50-case **smoke** on every PR, 200-case **full** nightly | −75% on PR-path volume | ~$0.90 PR / $2.30 nightly |
| Cap concurrency to avoid burst rate-limit retries | Avoids wasted spend | — |

⇒ **Tiered suites are the key structural decision**, not a micro-optimization: it decouples "fast
enough for CI" from "thorough enough to trust," which are genuinely different requirements.

## 7.6 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | G-Eval-style log-prob weighting available from the judge provider | Without log-probs, determinism (NFR) is unachievable — must switch judge provider or accept higher variance |
| A2 | 50% judge-cache hit rate on iterative PRs | Cost rises toward $4/run |
| A3 | Teams will adopt a shared platform | If not, the multi-tenant complexity is wasted — validate first |
| **Q1** | Who owns golden-dataset quality? | Datasets rot; ownership is the real failure mode |
| **Q2** | Is a judge permitted to see production data (PII)? | May force a self-hosted judge |

---

# 8. Real-time AI voice assistant

> **Prompt:** Audio streaming, ASR, interruption handling, LLM streaming, TTS, latency optimization,
> session management.

## 8.1 Problem & users

A phone/app voice assistant. **Primary user:** a caller speaking naturally. **Primary job:** be
answered fast enough to feel like a conversation.

**The defining constraint, and it dominates everything:** humans perceive conversational lag above
**~500 ms** and start talking over the system above ~800 ms. The entire pipeline — ASR → LLM → TTS —
must fit inside a budget that a *single* LLM call in §1 already exceeds. **This is the tightest
latency problem in the set, and it forces architectural choices no other system here needs.**

## 8.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Stream audio in, stream audio out | Bidirectional, full-duplex |
| FR-2 | P0 | Streaming ASR with partial hypotheses | Partials < 200 ms behind speech |
| FR-3 | P0 | **Endpointing** — detect end of user turn | p95 detection < 300 ms after speech stops |
| FR-4 | P0 | **Barge-in** — user interrupts, system stops speaking immediately | TTS halts < 150 ms after speech detected |
| FR-5 | P0 | Streaming LLM response | First sentence out before full response generated |
| FR-6 | P0 | Streaming TTS, sentence-chunked | First audio < 250 ms after first LLM sentence |
| FR-7 | P0 | Session state across turns | — |
| FR-8 | P1 | Tool calling mid-conversation with filler audio ("let me check…") | Masks tool latency |
| FR-9 | P1 | Graceful degradation on ASR low confidence | Asks for clarification, never guesses |
| FR-10 | P1 | Per-session transcript + trace | Audit, QA |
| FR-11 | P2 | Speaker diarization for multi-party calls | — |
| FR-12 | P2 | Emotion/sentiment signal to adjust responses | — |

## 8.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| **Response latency** (user stops → first audio) | **p95 < 800 ms**, target p50 < 500 ms | Above ~800 ms callers talk over the system |
| Barge-in stop | < 150 ms | Beyond this the system feels like it's ignoring you |
| ASR WER | < 8% on telephony audio | Above this, downstream intent accuracy collapses |
| Availability | 99.95% | Phone calls fail loudly and immediately |
| Concurrency | 1,000 concurrent calls | Contact-centre sizing |
| Audio quality | 8 kHz telephony / 16 kHz app | Codec constraint |
| Cost | ≤ $0.08/minute | vs ~$0.60/min human agent |
| Session duration | Up to 30 min | Memory/context management driver |

## 8.4 Non-goals

- Music or non-speech audio understanding.
- Voice cloning of specific individuals.
- On-device inference in v1 — cloud pipeline.
- Languages beyond English in v1.

## 8.5 The latency budget — the hardest in this document

| Stage | Budget (p95) | Notes |
|---|---|---|
| Audio in (network + jitter buffer) | 60 ms | WebRTC/SIP |
| Streaming ASR finalization after endpoint | 150 ms | Partials already computed during speech |
| **Endpointing decision** | **250 ms** | VAD + silence threshold. **Aggressive = cuts users off; conservative = feels slow.** The single most-tuned parameter in the system |
| LLM TTFT | 250 ms | **Requires a small/fast model — a frontier model's 900 ms alone blows the budget** |
| First TTS chunk | 120 ms | Streaming TTS, sentence-level |
| Audio out (network) | 40 ms | |
| **Total** | **≈ 870 ms** | vs 800 ms SLO → **⚠️ OVER by 70 ms** |

**The budget doesn't close.** This is the correct and interesting finding. Options:

| Option | Saving | Cost |
|---|---|---|
| **Speculative endpointing** — start LLM on high-confidence partials before endpoint confirmed | ~150 ms | Wasted LLM calls on false endpoints (~10-15%); cheap on a small model |
| Cut endpointing to 180 ms | 70 ms | More false cuts — worse UX for slow speakers |
| Co-locate ASR/LLM/TTS in one region/VPC | ~40 ms | Reduced provider flexibility |
| Pre-warm/pin the LLM (no cold start) | variable | Reserved capacity cost |
| Filler audio ("mm-hm", "let me see") to mask | perceptual only | Feels natural if done sparingly; grating if overused |

⇒ **Speculative endpointing + co-location** brings p95 to ~680 ms. **This is the design's central
trade-off and belongs in the opening answer, not buried.**

## 8.6 Capacity & cost

```
1,000 concurrent calls, assume 6-min average → 10,000 calls/day, 60,000 call-minutes/day

Per minute of call, assume ~4 turns:
  ASR:  streaming, assume $0.006/min                        = $0.0060
  LLM:  4 turns × (800 in / 100 out), small tier
        4 × [(800/1e6 × $0.15) + (100/1e6 × $0.60)]         = $0.00072
  TTS:  assume ~600 characters/min at $15/1M chars          = $0.0090
  ⇒ ≈ $0.0157/min      ✅ well under the $0.08 ceiling

Monthly: 60,000 × 30 × $0.0157 ≈ $28.3k/month
Human baseline avoided at 40% containment: 720k min/mo × 0.4 × $0.60 ≈ $173k/mo ⇒ strong ROI

⇒ ASR and TTS dominate cost (~96%), NOT the LLM. Optimization effort belongs there —
  the opposite of every other system in this document.
```

## 8.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | A small-tier LLM at 250 ms TTFT gives acceptable answer quality | If quality is insufficient, the latency SLO is unreachable — renegotiate the SLO, not the model |
| A2 | ~4 turns per call-minute | Cost scales linearly |
| A3 | Telephony audio yields < 8% WER | Noisy lines may need a domain-adapted ASR model |
| **Q1** | Is 800 ms p95 negotiable? | If yes, a frontier model becomes viable and quality rises materially |
| **Q2** | Regulatory recording/consent requirements per region? | Affects storage and session design |

---

# 9. Multi-provider LLM platform

> **Prompt:** OpenAI/Anthropic/Gemini/Bedrock, unified API, model routing, fallback, prompt
> management, rate limits, cost optimization.

## 9.1 Problem & users

30 internal applications each integrate LLM providers directly. Result: duplicated retry logic, no
central cost visibility, no fallback when a provider degrades, prompt changes shipped without review,
and a migration cost per app whenever a model is deprecated. **Primary user:** an application
engineer who wants one endpoint and one SDK. **Secondary:** finance (cost attribution) and security
(egress control).

This is the **gateway** pattern — the buy-side counterpart to §4's build-side.

## 9.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | Unified API across OpenAI, Anthropic, Gemini, Bedrock | One request shape; provider-specific features degrade gracefully |
| FR-2 | P0 | Streaming passthrough | No added buffering latency |
| FR-3 | P0 | **Fallback chain on provider failure** | Automatic failover < 500 ms added; configurable order |
| FR-4 | P0 | Per-tenant rate limits + budget caps | Hard stop at budget; 429 with `Retry-After` |
| FR-5 | P0 | **Per-request cost attribution** by team/app/feature | Reconciles with provider invoices within 2% |
| FR-6 | P0 | Central API-key custody; apps never hold provider keys | Keys in a vault, rotated |
| FR-7 | P0 | Full request/response logging with configurable PII redaction | Zero raw PII in third-party payloads where policy forbids |
| FR-8 | P1 | Model routing policy (cost/latency/quality-aware) | ≥ 30% cost reduction vs. all-frontier |
| FR-9 | P1 | Versioned prompt registry with canary + rollback | Prompt change auditable and revertible |
| FR-10 | P1 | Semantic + exact response cache | ≥ 25% hit rate on eligible traffic |
| FR-11 | P1 | Circuit breaker per provider with health probes | Opens on error-rate threshold |
| FR-12 | P1 | Model alias pinning (`prod-fast` → a specific version) | Insulates apps from deprecations |
| FR-13 | P2 | Shadow traffic to a candidate model for comparison | — |

## 9.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| **Added latency (gateway overhead)** | **p95 < 30 ms** | A gateway that adds real latency gets bypassed |
| Availability | 99.99% | **Higher than any single provider** — this is the entire value proposition, achieved *by* multi-provider fallback |
| Throughput | 2k RPS aggregate | 30 apps |
| Streaming overhead | < 10 ms per chunk | |
| Cost attribution accuracy | within 2% of invoices | Finance requirement |
| Config propagation | < 60 s | Routing/prompt changes without redeploy |
| Availability of logs | 99.9%, async write | **Logging must never block the request path** |

## 9.4 Non-goals

- Hosting/serving models — that's §4.
- Being an agent framework (no orchestration logic; it's a transport + policy layer).
- Fine-tuning management in v1.
- Guaranteeing semantic equivalence across providers — a prompt tuned for one model may behave
  differently on another, and the gateway cannot fix that. **Say this explicitly**; it's the most
  common false expectation of a unified API.

## 9.5 Latency budget (gateway overhead only, p95 < 30 ms)

| Stage | Budget |
|---|---|
| TLS + auth (JWT verify, cached JWKS) | 5 ms |
| Rate-limit + budget check (Redis) | 6 ms |
| Routing policy evaluation | 3 ms |
| Cache lookup | 8 ms |
| Request translation to provider schema | 3 ms |
| Response translation + async log enqueue | 5 ms |
| **Total** | **30 ms** ✅ (at budget — every element is tight by design) |

**Cache hit** short-circuits the provider entirely: ~19 ms total vs. ~900 ms+ — which is why the
cache sits before routing.

## 9.6 Capacity & cost

```
2k RPS × 86,400 ≈ 173M requests/day

Gateway compute: assume ~2 ms CPU/request → 173M × 2 ms = 346k CPU-s/day ≈ 96 CPU-hr/day
  at ~$0.04/CPU-hr ≈ $4/day  ⇒ gateway compute is NOISE vs. token spend

Logging: 173M × ~4 KB = 692 GB/day  ← THE REAL INFRASTRUCTURE COST
  hot 7 d: 4.8 TB;  warm 30 d compressed ~4:1: ~5 TB;  then cold/expire
  assume ~$1,500/month storage + ingest  ⇒ sample verbose bodies; keep metadata for 100%

Value delivered (the actual justification):
  assume $500k/month org-wide token spend
  routing (−30%) + caching (−25% of eligible) ⇒ conservatively −40% ≈ $200k/month saved
  ⇒ the platform pays for itself many times over on cost control ALONE,
    before counting the availability and migration-insulation benefits
```

> **The design insight the arithmetic surfaces:** a gateway's own compute is negligible; its costs are
> **logging volume** and **engineering time**, and its value is **cost control + availability +
> insulation from provider churn**. Justify it on those, not on compute efficiency.

## 9.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | ~$500k/month org token spend | Below ~$50k/month the platform likely isn't worth the engineering |
| A2 | 25% cache-hit rate on eligible traffic | Savings shrink; routing becomes the main lever |
| A3 | Apps tolerate a unified (lowest-common-denominator) API | Heavy users of provider-specific features need an escape hatch (passthrough mode) |
| **Q1** | Is cross-provider fallback acceptable given output differences? | Some apps may need to fail rather than silently switch models |
| **Q2** | Data-residency constraints per provider/region? | Constrains the routing table |

---

# 10. Enterprise AI agent platform

> **Prompt:** Authentication/authorization, MCP/tools, RAG, agent memory, workflows, multi-tenancy,
> guardrails, audit logs, observability, security.

> **Overlaps** [`21_ai-system-design-deep-dives/01_agentic_ai_platform.md`](../21_ai-system-design-deep-dives/01_agentic_ai_platform.md).
> That file is fintech-domain-scoped; **this one is the generic multi-tenant enterprise platform**,
> and is deliberately the **capstone** — it composes §1 (RAG), §2 (agent), §3 (orchestration),
> §7 (evals), and §9 (gateway) into one system. Read it last.

## 10.1 Problem & users

A platform on which **any** internal team can build, deploy, and operate an agent — without each
team re-solving auth, tools, RAG, memory, guardrails, audit, and observability. **Primary users:**
(a) an agent *builder* on a product team, (b) an *end user* consuming an agent, (c) a *platform
admin* enforcing policy, (d) a *compliance auditor* reconstructing what happened.

Four distinct users with conflicting needs — builders want freedom, admins want control — and
**resolving that conflict is the actual design problem.**

## 10.2 Functional requirements

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-1 | P0 | SSO (OIDC/SAML) + RBAC | Roles: builder, operator, end-user, admin, auditor |
| FR-2 | P0 | **Agent acts with the end user's permissions, not the platform's** | Zero privilege escalation in the pen-test suite |
| FR-3 | P0 | Tool registry (MCP-compatible) with per-agent allow-lists | An agent cannot call an unregistered/unlisted tool |
| FR-4 | P0 | Managed RAG per tenant with ACL-aware retrieval | Zero cross-tenant/cross-ACL leakage |
| FR-5 | P0 | Agent memory: session + long-term, tenant-scoped | — |
| FR-6 | P0 | **Immutable audit log** of every prompt, tool call, decision, and actor | Tamper-evident; 7-yr retention |
| FR-7 | P0 | Guardrails: input (injection, PII) + output (PII, toxicity, schema) | Configurable fail-open/fail-closed per agent |
| FR-8 | P0 | **Human approval gates for side-effecting tools** | Enforced platform-side, not per-agent |
| FR-9 | P0 | Multi-tenancy with data + compute isolation | Noisy-neighbour isolation verified under load |
| FR-10 | P1 | Deterministic workflows alongside autonomous agents | Builders pick per use case |
| FR-11 | P1 | Eval integration gating agent promotion (§7) | Cannot promote to prod on a failed suite |
| FR-12 | P1 | Per-tenant/agent cost budgets + attribution | Hard caps |
| FR-13 | P1 | Full observability: traces, tokens, latency, tool outcomes | — |
| FR-14 | P1 | Versioning + instant rollback of agent definitions | — |
| FR-15 | P2 | Agent marketplace / templates across teams | — |
| FR-16 | P2 | Agent-to-agent delegation with privilege narrowing | Never widening |

## 10.3 Non-functional requirements

| NFR | Target | Why |
|---|---|---|
| Agent response TTFT | p95 < 2.5 s | Slightly looser than §2 — platform layers add overhead |
| Platform overhead | < 150 ms added vs. direct calls | Otherwise teams bypass the platform |
| Availability | 99.95% | Many internal apps depend on it |
| Tenants | 200 tenants, 2k agents, 50k end users | Sizing |
| Concurrency | 2k concurrent agent sessions | |
| **Audit completeness** | **100%, no sampling** | Compliance: a sampled audit log is not an audit log |
| Audit durability | 11 nines, immutable, 7 yr | WORM storage |
| Isolation | No cross-tenant data access, ever | The requirement that ends the platform if violated |
| Guardrail latency | < 150 ms input, output overlapped | Must not dominate the budget |
| Cost | ≤ $0.10/agent interaction + attributable | Chargeback model |
| Onboarding | New agent live in < 1 day | The platform's adoption promise |

## 10.4 Non-goals

- Model hosting (§4) or provider abstraction (§9) — **consumed as dependencies**, not rebuilt.
- Being an eval platform (§7) — integrated, not reimplemented.
- No-code agent building in v1 — config-as-code (YAML + prompts in git).
- Cross-tenant agent collaboration.

## 10.5 The security model (the section that defines this system)

Everything else is assembly; **this is the design.**

| Threat | Control |
|---|---|
| **Prompt injection via retrieved docs or tool output** | Retrieved/tool content is **untrusted data, never instructions**: structural separation in the prompt, tool allow-lists, and **no tool invocation derived solely from retrieved text** |
| **Privilege escalation** | Agent executes under the **end user's** token (on-behalf-of), never a platform service account. Tools re-check authorization server-side — never trust the agent's claim |
| **Cross-tenant leakage** | `tenant_id` from the auth token only, **never** from the request body; pushed into every query as a mandatory predicate; enforced at the data layer, not the app layer |
| **Data exfiltration via tool args** | Egress allow-list; outbound payload scanning; block tools that can post arbitrary content externally without approval |
| **Runaway cost/actions** | Step, token, wall-clock, and $ caps (§3.5); human approval for side-effecting tools |
| **Audit tampering** | Append-only WORM store; hash-chained entries; separate credentials from the application plane |
| **Model/prompt supply chain** | Pinned model versions; prompts reviewed in git; canary before promotion |

> **The single most important control:** *the agent's identity is the user's identity.* An agent that
> runs as a service account with union-of-all-permissions is the enterprise-agent equivalent of
> `sudo` — and it is the default that most naive designs land on.

## 10.6 Capacity & cost

```
50k users × ~4 agent interactions/day = 200k interactions/day
Assume 6 LLM turns each = 1.2M LLM calls/day

Blended (assume 60% small / 40% frontier), 3,000 in / 350 out per turn:
  small:    (3000/1e6 × $0.15) + (350/1e6 × $0.60) = $0.00066
  frontier: (3000/1e6 × $3.00) + (350/1e6 × $15.00) = $0.01425
  blended ≈ 0.6(0.00066) + 0.4(0.01425) = $0.0061/turn
  per interaction (6 turns) ≈ $0.0366     ✅ under the $0.10 ceiling

Monthly LLM: 200k × 30 × $0.0366 ≈ $220k/month  ⇒ per-tenant chargeback is mandatory, not optional

Audit log: 1.2M calls/day × ~8 KB = 9.6 GB/day = 288 GB/month = 3.5 TB/yr
  × 7 yr with compression ≈ 8-10 TB in WORM ≈ manageable (~$250/month cold storage)
  ⇒ 100% audit retention is CHEAP. There is no cost argument for sampling it.
```

## 10.7 Assumptions & open questions

| # | Assumption | If false |
|---|---|---|
| A1 | Tools support on-behalf-of / delegated auth | If tools only accept service accounts, FR-2 is unachievable — a **blocking** platform prerequisite, not an implementation detail |
| A2 | 60/40 routing split | Cost moves toward $0.085/interaction — still under ceiling |
| A3 | Teams accept config-as-code | If no-code is required, add a builder UI (significant scope) |
| A4 | 4 interactions/user/day | Linear cost scaling |
| **Q1** | Who approves a new tool's registration? | Governance gate; unowned = shadow tools |
| **Q2** | Is fail-open or fail-closed correct when guardrails are unavailable? | Differs per agent; needs an explicit per-agent policy, and a platform default |
| **Q3** | Chargeback or central budget? | Changes the quota enforcement design |

---

# Cross-system requirement matrix

Where the ten systems share concerns — and where they genuinely diverge. **The divergences are the
interesting part**: they show the same-sounding requirement resolving differently under different
constraints.

| Concern | 1 RAG | 2 Support | 3 Multi-agent | 4 Inference | 5 DocIntel | 6 RecSys | 7 Eval | 8 Voice | 9 Gateway | 10 Platform |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Latency-critical** | ✅ | ✅ | ➖ async | ✅ | ➖ async | ✅✅ | ➖ | ✅✅✅ | ✅✅ | ✅ |
| **Throughput-critical** | ➖ | ➖ | ➖ | ✅✅ | ✅✅✅ | ✅✅✅ | ➖ | ✅ | ✅✅ | ✅ |
| Retrieval / RAG | ✅✅✅ | ✅ | ✅ | ✖ | ➖ | ✖ | ➖ | ➖ | ✖ | ✅✅ |
| Tool calling | ✖ | ✅✅ | ✅✅✅ | ✖ | ✖ | ✖ | ✖ | ✅ | ✖ | ✅✅✅ |
| Human-in-the-loop | ➖ | ✅✅ | ✅ | ✖ | ✅✅✅ | ✖ | ✅ | ➖ | ✖ | ✅✅ |
| Multi-tenancy | ✅ | ➖ | ➖ | ✅ | ➖ | ✖ | ✅✅ | ➖ | ✅✅ | ✅✅✅ |
| Eval / regression gate | ✅✅ | ✅ | ✅ | ➖ | ✅ | ✅✅ | ✅✅✅ | ✅ | ➖ | ✅✅ |
| Prompt injection | ✅✅ | ✅✅ | ✅✅ | ✖ | ✅ | ✖ | ➖ | ➖ | ➖ | ✅✅✅ |
| Cost is the binding constraint | ✅✅✅ | ➖ | ✅✅ | ✅✅✅ | ➖ (human is) | ➖ | ✅✅ | ➖ | ✅✅✅ | ✅✅ |
| GPU / hardware | ✖ | ✖ | ✖ | ✅✅✅ | ✅ | ➖ | ✖ | ✅ | ✖ | ✖ |
| Streaming | ✅ | ✅ | ✖ | ✅✅ | ✖ | ✖ | ✖ | ✅✅✅ | ✅✅ | ✅ |
| Classical ML (not LLM) | ➖ rerank | ➖ intent | ✖ | ✖ | ✅ OCR | ✅✅✅ | ✖ | ✅ ASR/TTS | ✖ | ➖ |

Legend: ✅✅✅ defining constraint · ✅✅ major · ✅ present · ➖ minor/optional · ✖ out of scope

**Four patterns worth noticing:**

1. **"Latency-critical" means wildly different budgets.** §6 needs 150 ms *total*; §8 needs 800 ms
   for a four-stage pipeline; §1 gets 1.5 s for TTFT alone. Same word, three different architectures.
2. **The binding constraint is rarely the LLM.** §5 is bound by human review cost, §6 by scoring
   volume, §8 by ASR/TTS cost, §9 by logging volume. **Only §1, §4, and §9 are genuinely
   token-cost-bound.** Identifying the true constraint is the first job in every design.
3. **The capacity arithmetic invalidated the stated requirements in three systems** (§1 cost, §4
   self-hosting rationale, §7 CI cost). That is the arithmetic doing its job — and reporting it is a
   stronger answer than a design that quietly ignores it.
4. **§10 composes the others.** Build it last; treat §1, §4, §7, and §9 as its dependencies rather
   than reimplementing them.

---

# Shared assumptions register

Assumptions used across multiple systems, collected so a change propagates predictably.

| # | Assumption | Used in | Impact if wrong |
|---|---|---|---|
| SA-1 | Token prices per the §"Cost baseline" table | 1, 2, 3, 7, 8, 9, 10 | **All cost arithmetic scales proportionally.** Re-run before quoting |
| SA-2 | Small-tier models handle 60-70% of traffic acceptably | 1, 2, 9, 10 | Routing savings shrink; costs rise 2-3× |
| SA-3 | Semantic caching achieves 25-30% hit rate | 1, 9 | Direct proportional cost increase |
| SA-4 | Hosted provider SLA ≈ 99.9% | 1, 2, 9, 10 | **Caps single-provider availability**; 99.99% requires multi-provider |
| SA-5 | Prompt caching cuts repeated-prefix input cost materially | 1, 2, 10 | Input costs rise ~2× where system prompts dominate |
| SA-6 | Cross-encoder reranking adds ~180 ms for 50 docs | 1, 2, 10 | Latency budgets need rework; may drop reranking |
| SA-7 | GPU on-demand ≈ $4/GPU-hr (H100 class) | 4, 5 | Reserved/spot cuts 60-70% and changes build-vs-buy conclusions |
| SA-8 | Engineering cost is out of scope for all TCO figures | all | Every "cheap" self-hosted option is understated; a hosted API's premium buys back headcount |

> **How to use this register:** when an interviewer challenges a number, point at the assumption
> rather than defending the number. *"That figure rests on SA-2 — 65% small-tier routing. If your
> traffic is harder than I've assumed, cost roughly triples and the model-routing lever mostly
> disappears."* That is a materially stronger answer than restating the original estimate.

---

## Next: the designs

Each system's HLD and LLD live in its own file. Requirements above are the contract those designs must
satisfy.

| # | File | Status |
|---|---|---|
| 01 | `01_production_rag_system.md` | ⏳ |
| 02 | `02_customer_support_agent.md` | ⏳ |
| 03 | `03_multi_agent_system.md` | ⏳ |
| 04 | `04_llm_inference_platform.md` | ⏳ |
| 05 | `05_document_intelligence.md` | ⏳ |
| 06 | `06_recommendation_system.md` | ⏳ |
| 07 | `07_llm_evaluation_platform.md` | ⏳ |
| 08 | `08_realtime_voice_assistant.md` | ⏳ |
| 09 | `09_multi_provider_llm_platform.md` | ⏳ |
| 10 | `10_enterprise_agent_platform.md` | ⏳ |
