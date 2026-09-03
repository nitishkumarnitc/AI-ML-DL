# 01 · Requirements — Customer Support Agent

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#2-ai-powered-customer-support-agent`](../00_requirements_all_systems.md#2-ai-powered-customer-support-agent) fixes the headline scope and NFRs. This file adds the reasoning behind each number.

---

## 1.1 Problem & users

### What breaks today

A SaaS company receives ~20k support conversations/day. Roughly **60% are repetitive** — password
resets, "where is my invoice," plan questions, refund requests for a known billing bug. Consequences,
in the order the business feels them:

1. **Cost scales linearly with growth.** Every new cohort of customers needs proportionally more
   agents, and support headcount becomes a tax on revenue growth.
2. **Queue times push the hard cases to the back.** A genuinely complex problem waits behind fifty
   password resets, so the customers with the most serious issues get the worst service.
3. **Agents burn out on repetition** and attrite, which raises hiring and training cost and lowers
   quality — a self-reinforcing loop.

### Users and their jobs

| User | Job | What "working" means to them |
|---|---|---|
| **Customer (primary)** | Get the problem *resolved* | Resolution or a clean handoff — **not a chat transcript** |
| **Support agent (secondary)** | Inherit escalations with context | A handoff packet they can act on, not 40 turns to re-read |
| Support lead | Hit SLAs within budget | Deflection rate up, CSAT flat or better |
| Finance | No unauthorized refunds | Every side-effecting action attributable and policy-compliant |
| Compliance | Auditable decisions | Full trace of what the agent did and why |

### The defining constraint

**This agent acts.** It issues refunds, changes plans, resets credentials. That produces an
**asymmetry in error cost** that shapes every subsequent decision:

| Failure class | Who notices | Cost | Recoverable? |
|---|---|---|---|
| Wrong answer | The customer, immediately | Annoyance; they re-ask | Yes — trivially |
| **Missed escalation** | **Nobody tells us** | Silent churn | No — the customer is gone |
| **Wrong side-effecting action** | Finance, later | Money + trust | Partially, and expensively |

Three consequences that would otherwise look like over-engineering:

- **Approval gating lives outside the agent** ([FR-4](#safety--observability)), because a prompt rule
  is a suggestion, not a control.
- **Escalation recall gets a harder target than any answer-quality metric**
  ([§1.3](#quality)) — 0.98 vs 0.92, because the cost of a miss is unbounded and invisible.
- **The handoff packet is a P0 deliverable** ([FR-5](#core-conversation)), not a nice-to-have. A
  handoff that dumps a transcript on a human has moved the work, not reduced it.

> **Mental model:** the agent is a **capable junior agent with a spending limit and a supervisor**,
> not an autonomous operator.
>
> *Where the analogy breaks:* a human junior develops judgement about *when* they're out of their
> depth. An LLM's confidence is uncorrelated with correctness, so "knowing when to escalate" is a
> separately-trained classifier ([FR-1](#core-conversation)) rather than an emergent property.

---

## 1.2 Functional requirements

### Core conversation

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Classify **intent + urgency + escalation-need** per turn | ≥ 0.92 macro-F1 intent; **≥ 0.98 recall on escalation-required** |
| **FR-2** | P0 | Answer from the help-centre KB via RAG | Groundedness ≥ 0.95 (mechanics per [01](../01_production_rag_system/README.md)) |
| **FR-5** | P0 | Escalate to a human with a **structured context packet** | Packet carries intent, steps taken, tool calls + results, sentiment trend, and the open question |
| **FR-6** | P0 | Session memory across the conversation | Resolves references correctly across ≥ 10 turns |
| FR-9 | P1 | Degrade gracefully when confidence is low | Asks a clarifying question rather than guessing |

**Why escalation recall is separated from intent F1.** A single macro-F1 number averages away the
class that matters. A model can score 0.94 macro-F1 while missing a third of escalation cases,
because escalations are rare and averaging hides rare-class failure. **The rare class is the expensive
one**, so it gets its own metric and its own threshold.

### Tools & actions

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-3** | P0 | Call tools: order lookup, invoice fetch, plan change, refund, credential reset | Correct tool + arguments ≥ 0.95 on the tool-eval set |
| **FR-4** | P0 | **Platform-enforced approval gate** for side-effecting actions above a value threshold | 100% of refunds > $50 require human approval; **enforced outside the agent** |
| FR-10 | P1 | Idempotent tool execution | A retried refund never double-pays |

**FR-4's phrasing is deliberate.** "The agent asks for approval" is prompt-level and defeatable.
"The platform will not execute the action without an approval record" is a control. The distinction is
the whole design ([§2.2](02_hld.md#22-component-choices)).

### Memory & channels

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-8 | P1 | Cross-session memory — recognize a returning customer | Retrieves prior tickets for the same account, subject to [Q2](#open-questions) |
| FR-11 | P1 | Multi-channel: web chat, email, WhatsApp | Shared session state; channel-appropriate formatting |

**Channels are not cosmetic.** Web chat is synchronous with a ~2 s expectation; email is asynchronous
with a ~minutes expectation and no streaming. The **latency SLO is per-channel**
([§1.3](#latency)) — applying the chat budget to email would be over-engineering, and applying the
email budget to chat would ship something that feels broken.

### Safety & observability

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-7** | P0 | Guardrails: PII redaction, abuse, **prompt injection**, off-topic | Zero PII in third-party provider payloads |
| FR-12 | P1 | Full trace: prompts, tool calls, policy decisions, tokens, cost | Conversation replayable for audit |
| FR-13 | P1 | Deflection + CSAT metrics per intent | Dashboard, segmented by intent |

---

## 1.3 Non-functional requirements

### Latency

| NFR | Target | Why this number |
|---|---|---|
| **First response TTFT (chat)** | p95 < 2 s | Chat convention; beyond ~2 s users repeat themselves or leave |
| First response (email) | p95 < 60 s | Async channel — no streaming, different expectation entirely |
| **Tool round trip** | p95 < 3 s *added* | Beyond this, the agent must emit an interim "checking that for you" message |
| Handoff packet build | p95 < 2 s | The human is already waiting |
| Approval decision | No SLO — human-bound | Customer is told a human is reviewing |

**Why the tool budget is stated as "added" rather than absolute.** A tool turn is
`LLM decides → tool executes → LLM interprets`, i.e. **two** LLM calls plus the tool. Budgeting it as
a single number hides that the LLM cost is paid twice, which matters for both latency and spend.

### Quality

| NFR | Target | Why this number |
|---|---|---|
| **Escalation recall** | **≥ 0.98** | A missed escalation is silent and unrecoverable. 0.98 accepts ~2% misses as the practical floor while forcing a bias toward over-escalation |
| Escalation precision | ≥ 0.70 | Deliberately loose — over-escalating costs agent time; under-escalating costs a customer. **The asymmetry is intentional** |
| Intent macro-F1 | ≥ 0.92 | Routing quality; errors here are recoverable in-conversation |
| Tool selection accuracy | ≥ 0.95 | A wrong read-only tool wastes a turn; a wrong write tool is [FR-4](#tools--actions)'s problem |
| **Wrong-action rate** | < 0.1% of side-effecting calls | Each one is a financial incident requiring manual remediation |
| Deflection rate | ≥ 50% | The business case for the project |
| CSAT on deflected | ≥ CSAT on human-handled − 5 pts | Guardrail: **deflection that tanks satisfaction is not a win** |

**On escalation precision at 0.70.** Setting both recall and precision high is the instinct, and it's
wrong here. Pushing precision up necessarily pushes recall down, and the costs aren't symmetric:
over-escalation costs a few minutes of agent time, under-escalation costs a customer. **Explicitly
accepting ~30% false-positive escalations is the correct trade**, and being able to defend that
number is the point.

### Capacity, availability, cost

| NFR | Target | Why |
|---|---|---|
| Concurrency | 500 concurrent conversations | 20k/day at ~8-min average duration, peaked |
| Availability | 99.95% (~22 min/month) | Customer-facing; **a support outage during a product incident compounds** |
| Cost | ≤ $0.15/conversation | vs ~$4.00 fully-loaded human handling |
| Retention | Transcripts 90 d · audit log 1 yr | Policy |
| PII | Redacted before third-party egress | Policy |

**Why 99.95% rather than 99.9%.** Support demand **correlates with product incidents** — the moment
the main product breaks, support volume spikes. A support system that fails under the same conditions
that cause its load is worse than useless. This drives the fallback and degraded-mode work in
[§2.5](02_hld.md#25-failure-modes--blast-radius).

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Voice support** | Text channels only; voice is a fundamentally tighter latency problem | See [`../00_requirements_all_systems.md#8-real-time-ai-voice-assistant`](../00_requirements_all_systems.md#8-real-time-ai-voice-assistant) — 800 ms for a four-stage pipeline |
| **Autonomous refunds above threshold** | Deliberate, permanent product constraint | Never — this is a policy boundary, not a roadmap item |
| Replacing the support team | Deflection, not elimination; humans handle the hard 50% | — |
| Custom intent model in v1 | Start with an LLM classifier; revisit if cost or latency demands | Classifier cost becomes material, or latency budget tightens |
| **Multi-agent decomposition** | A single agent with good tools is simpler and cheaper here | Subtasks become genuinely parallel or need different privileges — see [§2.2](02_hld.md#22-component-choices) |
| Proactive outbound contact | Inbound only | Separate product with its own consent requirements |

---

## 1.5 Latency budget

SLO: p95 first-response TTFT < 2 s (web chat).

### First response, no tool call

| # | Stage | Budget (p95) | Notes |
|---|---|---:|---|
| 1 | Channel adapter + session load | 40 ms | Redis session fetch |
| 2 | **Input guardrail** | 120 ms | Injection + PII + abuse classifiers, run in parallel |
| 3 | Intent + urgency + escalation classifier | 300 ms | Small-tier model, single call producing all three labels |
| 4 | Memory retrieval (session + cross-session) | 100 ms | Overlapped with 5 |
| 5 | KB retrieval + rerank | 300 ms | Per [01](../01_production_rag_system/README.md); overlapped with 4 |
| 6 | Prompt assembly | 20 ms | |
| 7 | **LLM TTFT** | **900 ms** | ~45% of the budget |
| 8 | Output guardrail | *0 ms* | **Overlapped** with streaming |
| | **Total** | **≈ 1,760 ms** | vs 2,000 ms SLO → **~240 ms headroom** ✅ |

**Stages 4 and 5 run concurrently** — independent lookups, ~100 ms and ~300 ms, so the pair costs 300
not 400 ms. **Stage 3 cannot be parallelized with 5**, because intent determines whether KB retrieval
is even the right action (an escalation-bound turn skips retrieval entirely).

### Turn with a tool call

| Stage | Budget |
|---|---:|
| Stages 1–7 above (LLM decides to call a tool) | 1,760 ms |
| Policy engine decision | 30 ms |
| Tool execution (internal API) | 1,000 ms |
| **Second LLM call** to interpret the result | 900 ms |
| **Total** | **≈ 3,690 ms** |

**Two LLM calls per tool turn**, which is why [FR-3](#tools--actions)'s budget is stated separately.
Above ~3 s the UI emits an interim message — masking latency is cheaper than eliminating it, and the
perceived improvement is larger.

### Where the budget is fragile

| Risk | Impact | Mitigation |
|---|---|---|
| Tool API slower than 1 s p95 | Blows the tool-turn budget | Interim message; per-tool timeout; assumption [A2](#assumptions) |
| Guardrails serialized instead of parallel | +240 ms | Run the three classifiers concurrently; they're independent |
| Cross-session memory retrieval unbounded | Grows with customer history | Cap at the most recent N tickets, not "all history" |
| LLM TTFT provider variance | 45% of budget | Fallback provider via [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform) |

---

## 1.6 Capacity & cost estimation

Rates are the **assumed** figures from [`../00_requirements_all_systems.md#shared-conventions`](../00_requirements_all_systems.md#shared-conventions).

### Volume

```
20,000 conversations/day
Assume 8 LLM turns per conversation (assumption A1)
  ⇒ 160,000 LLM calls/day  ≈  4.8M/month

Concurrency check:
  500 concurrent × 1 LLM call per ~60 s of conversation  ≈  8–10 QPS to the provider
  ⇒ MODEST. The binding constraint is provider rate limits and tool-API capacity,
    NOT model throughput or cost.
```

**That last line inverts the optimization priority relative to [01](../01_production_rag_system/01_requirements.md#16-capacity--cost-estimation).**
There, cost was 185× over budget and dominated every decision. Here, cost is comfortable and
**capacity and correctness dominate**. Recognizing which constraint actually binds is the first job in
any design.

### Token cost

```
Tokens per turn (assumption A1):
  input   2,500  = system prompt + KB context + conversation history + memory
  output    250

Routing assumption (A3): 60% small tier / 40% frontier

  small:    (2500/1e6 × $0.15) + (250/1e6 × $0.60)  = $0.000375 + $0.00015 = $0.000525
  frontier: (2500/1e6 × $3.00) + (250/1e6 × $15.00) = $0.0075   + $0.00375 = $0.01125

  blended = 0.6(0.000525) + 0.4(0.01125)            = $0.00482/turn
  per conversation (8 turns)                        ≈ $0.0386      ✅ vs $0.15 ceiling

Monthly: 20,000 × 30 × $0.0386 ≈ $23,160/month
```

**Add the components the naive estimate forgets:**

```
Guardrails:  3 classifiers × 8 turns × small tier ≈ $0.0004/conv    →  ~$240/month
Intent:      8 turns × small tier                ≈ $0.0006/conv    →  ~$360/month
KB retrieval (embed + rerank)                    ≈ $0.0002/conv    →  ~$120/month
Tool turns:  assume 30% of conversations, +1 LLM call each         →  ~$1,100/month
                                                                     ───────────
Realistic total                                                    ≈  $25,000/month
Per conversation                                                   ≈  $0.042   ✅ still well under
```

**ROI:**

```
Human baseline:   20k/day × 30 × $4.00     = $2.4M/month if fully human-handled
At 50% deflection: 10k/day deflected       ≈ $1.2M/month avoided
Platform cost:                             ≈ $25k/month
                                             ─────────
Net                                        ≈ $1.175M/month  ⇒ ~48× return
```

> **The honest caveat:** the $4.00 human-handling figure is fully-loaded cost per conversation, and
> deflection savings only materialize if headcount actually changes or growth is absorbed without
> hiring. If neither happens, the "saving" is capacity, not cash — and that's a different business
> case. **Say which one you're claiming.**

### Tool-API capacity — the real constraint

```
30% of 20k conversations involve a tool call, assume 1.5 calls each
  ⇒ 9,000 tool calls/day ≈ 0.1 QPS average, but PEAKED with conversation volume
  Peak: assume 4× diurnal ⇒ ~0.4 QPS

Modest in absolute terms — but these hit INTERNAL billing/order/auth APIs that were
sized for human-agent traffic (a human makes maybe 20 lookups/hour).
  ⇒ VERIFY headroom with each API owner before launch. This is an integration
    dependency, not a capacity calculation we can do unilaterally.
```

**This is the kind of constraint that sinks launches.** The model scales trivially; the 15-year-old
billing API behind three layers of middleware may not. It's assumption [A2](#assumptions) and
open question [Q4](#open-questions).

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | 8 LLM turns/conversation; 2,500 in / 250 out | Medium | Cost scales ~linearly; still under ceiling at 16 turns |
| **A2** | Internal tool APIs respond < 1 s p95 and have headroom | **Low** | Blows the tool-turn budget **and** may require API work outside this project's scope. **Highest-risk assumption** |
| **A3** | 60/40 small/frontier routing split | Medium | At 100% frontier, cost ≈ $0.09/conv — still under ceiling, so this is a comfort not a dependency |
| A4 | 60% of conversations are repetitive/deflectable | Medium | Directly sets the deflection ceiling and therefore the entire ROI case |
| A5 | Escalation recall ≥ 0.98 is achievable with an LLM classifier | Medium | May need a fine-tuned model or a rules-plus-model ensemble |
| A6 | $4.00 fully-loaded cost per human conversation | Medium | ROI scales linearly; the direction of the conclusion is robust |

**Ranked by risk: A2 > A4 > A5.** A2 is the one that can block launch and isn't in our control — it
needs a conversation with API owners in week one, not week ten.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | What is the refund approval threshold, and who sets it? | Directly sets human-review volume and therefore the staffing model | Finance |
| **Q2** | Is cross-session memory permitted under the privacy policy? | May forbid [FR-8](#memory--channels) outright | Legal / Privacy |
| **Q3** | Who owns the escalation taxonomy? | Blocks [FR-1](#core-conversation)'s label set — you cannot train a classifier without agreed labels | Support leadership |
| **Q4** | Do internal tool APIs have capacity headroom, and who owns them? | Assumption [A2](#assumptions); potentially a hard blocker | Platform teams |
| **Q5** | What happens to an in-flight conversation during a deploy? | Session migration vs. drain-and-finish | Us — decide in [§3.5](03_lld.md#35-state-machines) |
| **Q6** | Is the agent permitted to state policy, or only quote it? | Changes the prompt and the groundedness bar materially | Legal |

**Q3 is the sleeper.** Teams routinely start building an escalation classifier before anyone has
agreed what the categories *are*, then discover that "urgent" means different things to billing and
to technical support. **No labels, no classifier, no [FR-1](#core-conversation).**

---

**Next:** [02_hld.md →](02_hld.md) — architecture, why the policy engine sits outside the agent, why this is deliberately single-agent, failure modes, and the scale plan.
