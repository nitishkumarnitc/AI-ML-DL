# 01 — Company & Role Strategy

## 🏢 The company — what to know

- **What they do:** A tech-led debt marketplace / infrastructure company connecting **borrowers, lenders, and investors** — "freeing the flow of finance" across the debt lifecycle. A well-funded fintech operating at large scale (thousands of enterprise clients, very high debt volumes).
- **Platform surface:** Multiple products across debt origination, co-lending, bond/securitization marketplaces, collections, and data/analytics. Think: **loan lifecycle, credit underwriting, risk, collections, compliance**.
- **Enterprise stack:** Heavily **Java / Spring Boot** on the core; AI services expected in **Python/Node/TS**.

> ⚠️ Research the specific company (products, recent news, funding, scale, leadership) the week of the interview, and verify current figures. Don't quote stale stats confidently; say "as I understand it."

### Why this matters for AI

Debt markets = **high-stakes, regulated, document-heavy, audit-critical**. That shapes every AI answer:
- **Correctness > cleverness.** A hallucinated repayment schedule or misread covenant is a real financial/legal risk.
- **Explainability & auditability** are non-negotiable — every LLM output feeding a decision needs traceability.
- **Data sensitivity** — PII, financial records, RBI/regulatory constraints, data residency (India).
- **Latency + throughput** — millions of transactions; agents can't be 30-second black boxes in a transaction path.

**Use these framings in every answer.** When asked "how would you design X," always add the fintech constraint lens: *"Because this is regulated debt data, I'd add audit logging / human-in-the-loop / guardrails here."* That's the signal that separates a generic AI engineer from a Principal for a regulated-finance company.

---

## 🎯 What a Principal Engineer is actually judged on

At Principal/Staff level, the loop tests **judgment and leverage**, not just knowledge:

| Dimension | What they're checking | How you show it |
|-----------|----------------------|-----------------|
| **Technical depth** | Can you go 3 layers deeper than a senior on agents/RAG/infra? | Specific trade-offs, failure modes, "here's what breaks at scale" |
| **Architectural judgment** | Do you make sound trade-offs under ambiguity? | Name the trade-off explicitly, pick, justify, state what you'd measure |
| **Blast radius / leverage** | Do your decisions make *other* engineers faster? | SDKs, platform abstractions, reviews, standards you set |
| **Business/domain sense** | Do you connect tech to $ and risk? | Cost, latency, regulatory, revenue framing |
| **Communication** | Can you explain to CTO *and* to a junior? | Structured, layered answers; whiteboard clarity |
| **Build vs buy** | Pragmatism over resume-driven dev | "I'd buy X because our differentiation is Y, not Z" |

### The Principal mindset shift (rehearse this)
- Senior answer: *"I'd use LangGraph with a supervisor node and tool calls."*
- Principal answer: *"First, what decision does this agent influence and what's the cost of it being wrong? For a repayment-restructuring agent, wrong = regulatory + financial exposure, so I'd bias toward a constrained tool-augmented workflow with deterministic guardrails and human sign-off, not open-ended autonomy. Architecture-wise LangGraph gives us the explicit state machine we need for auditability; here's how I'd structure state, checkpointing, and the eval harness, and here's the platform SDK so product teams don't each reinvent this..."*

The second answer wins the loop.

---

## 🧩 Your positioning narrative (memorize the spine)

**One-paragraph pitch:**
> "I build production-grade agentic AI on top of solid distributed-systems foundations. I've shipped multi-agent LangGraph workflows and RAG pipelines, but I obsess over the un-sexy parts that make them survive production — evaluation harnesses, hallucination detection, telemetry, and the Kafka/Redis event-driven plumbing that keeps latency and cost in check. I've cut AWS spend and latency by treating inference like any other high-throughput service. And I've done it as a multiplier — leading architecture reviews and mentoring so the whole team levels up, not just my own output."

**Three proof pillars** (attach a concrete story to each — see [09](09_Leadership_and_Behavioral.md)):
1. **"I ship agents that work in prod"** — a multi-agent/RAG system with real users + how you made it reliable.
2. **"I scale the infra under AI"** — the Kafka/Redis/AWS latency-or-cost win, with numbers.
3. **"I multiply the team"** — architecture review / mentoring / standard you set that others adopted.

---

## 🗺️ Likely interview loop (Principal AI, fintech)

1. **Recruiter / HM screen** — story, motivation, fit, comp expectations.
2. **Agentic AI deep-dive** — LangGraph/AutoGen, multi-agent design, tool use, planning. → [02](02_Agentic_AI_and_Orchestration.md)
3. **RAG / retrieval deep-dive** — hybrid search, KGs, eval. → [03](03_RAG_and_Retrieval.md)
4. **LLMOps / responsible AI** — eval, guardrails, monitoring, fine-tuning. → [04](04_LLMOps_Eval_Guardrails.md), [05](05_FineTuning_and_Alignment.md)
5. **System design (HLD)** — design an end-to-end agentic AI platform / a specific fintech AI feature. → [07](07_System_Design_HLD_LLD.md)
6. **Coding / LLD** — practical Python, maybe async, maybe a small algorithmic problem. → [08](08_Coding_and_DSA.md)
7. **Distributed systems** — Kafka/Redis/K8s/AWS depth. → [06](06_Distributed_Systems_Backend.md)
8. **Leadership / behavioral / CTO chat** — vision, influence, build-vs-buy, mentoring. → [09](09_Leadership_and_Behavioral.md)

> Not all loops have all rounds; some merge. But prep every bucket — Principal loops are broad.

---

## 🎤 The outreach flattery — decode it

The recruiter email pre-mapped your resume to the role. **That's your cheat sheet for what they'll probe.** Every claim they made about you, they'll test:
- "multi-agent workflows" → expect a "walk me through one you built" deep-dive.
- "hallucination detection, telemetry" → expect "how do you catch hallucinations in prod?"
- "reduced latency, optimized AWS" → expect "give me the numbers and the how."
- "mentored teams, led architecture reviews" → expect a leadership STAR question.

**Action:** For each bullet in that email, have a 2–3 minute concrete story ready.
