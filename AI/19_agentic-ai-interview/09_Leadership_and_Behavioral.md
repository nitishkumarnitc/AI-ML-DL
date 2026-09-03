# 09 — Leadership & Behavioral

> At Principal level this is **half the decision**. The CTO chat and behavioral round test: vision, influence without authority, judgment, the "technical multiplier" claim, and whether you'll raise the bar for the org. Prepare stories as rigorously as system design.

---

## ⭐ STAR stories to prepare (write each out, ~2–3 min spoken)

Use **STAR**: Situation → Task → Action → **Result (with numbers)**. Map each to a theme they'll probe. Aim for **8–10 stories** that you can flex to many questions.

| Theme (from JD) | Story you need | Numbers to include |
|---|---|---|
| **Built production agentic AI** | A multi-agent/RAG system you shipped end-to-end | users, accuracy, adoption, uptime |
| **Reliability / eval** | A time you made an AI system trustworthy (caught hallucinations / built eval) | error rate ↓, incidents prevented |
| **Latency / cost win** | The AWS/latency optimization | latency ↓ %, $ saved, throughput ↑ |
| **Distributed systems at scale** | Kafka/Redis event-driven design | QPS, lag handled, scale |
| **Technical multiplier / mentoring** | Leveled up engineers / set a standard others adopted | # people, adoption across teams |
| **Architecture review / influence** | Led an HLD/LLD review; changed a direction | decision impact |
| **Build vs buy** | A framework/tool/model decision you made | cost/time saved, why |
| **Conflict / disagreement** | Disagreed with a senior/exec, navigated it | outcome, relationship intact |
| **Failure / mistake** | Something that went wrong + what you learned | honest, growth-oriented |
| **Ambiguity / 0→1** | Started something with no clear spec | shipped, learned, iterated |

> For each, note the **decision and trade-off** you owned — Principals are hired for judgment. "I chose X over Y knowing Z" beats "I implemented X."

---

## 🔑 The "technical multiplier" narrative (they used this exact phrase twice)

They want someone whose impact is **N engineers**, not 1. Prepare concrete evidence:
- **Standards you set** that others adopted (a pattern, a template, an eval harness, a review checklist).
- **Abstractions/SDKs/platforms** that made others faster (ties to [02](02_Agentic_AI_and_Orchestration.md), [07](07_System_Design_HLD_LLD.md)).
- **Mentoring** with outcomes (someone you grew, a review culture you built).
- **Docs / knowledge-sharing** that scaled your expertise.
- **Unblocking** — how you make the hard architectural calls that free up teams.

Frame: *"My job as a Principal isn't to write the most code — it's to make the org's AI engineering better than it would be without me. Here's how I've done that..."*

---

## 🧭 Build vs Buy (JD names this as a core responsibility)

Have a crisp framework:
- **Buy/adopt** when it's **not your differentiation**, a mature ecosystem exists, and speed-to-value matters (e.g., managed vector DB, hosted models, observability tooling, base orchestration frameworks).
- **Build** when it's **core differentiation**, no good fit exists, or control/cost/compliance/data-residency demands it (e.g., your domain eval harness, the fintech guardrail policy layer, the internal agent SDK).
- **Decision factors:** TCO (not just license — ops burden), lock-in, time-to-value, control/customization, security/compliance, team capacity, reversibility.
- **Principal stance:** *"I'm biased toward buying commodity infrastructure and building only what's our moat. Resume-driven development is a liability at scale. But I re-evaluate — 'buy' today can become 'build' when volume changes the economics."*
- **Concrete example:** buy the base orchestration + observability + vector store; build the domain eval framework, guardrail/compliance policy layer, and the agent SDK that encodes the org's standards.

---

## 🗣️ Influence without authority (Principal core skill)

Stories/answers should show you drive change through **credibility, data, and persuasion**, not title:
- Prototype to prove a point; let data settle debates.
- Write the design doc that aligns people; run the review that surfaces the trade-off.
- Disagree respectfully, commit once decided ("disagree and commit").
- Bring people along vs. mandating — especially since their core is Java/Spring and you'll be introducing AI patterns.

---

## 🎙️ Likely behavioral questions + how to attack

- **"Why this company / why this role?"** → genuine: scale of impact (millions of financial transactions), 0→1 platform ownership, CTO partnership, hard problems (regulated + high-stakes AI). Tie to your trajectory. Avoid generic flattery.
- **"Why leave your current role?"** → forward-looking (bigger scope, platform ownership, Principal impact), never trash-talk current employer.
- **"Tell me about the most complex system you've built."** → your best agentic/distributed story, heavy on trade-offs + your specific decisions + results.
- **"Describe a technical decision you got wrong."** → real, specific, what you learned, how you now decide differently. Shows growth + humility.
- **"How do you set technical direction across teams that don't report to you?"** → influence-without-authority story: design docs, prototypes, reviews, data, coalition-building.
- **"How would you set the AI engineering bar here in your first 90 days?"** → listen/audit first (understand current stack, pain points, Java core), find a high-leverage win, establish eval + guardrail standards, build one exemplar agent + SDK others copy, mentor. Show humility (learn before mandating) + vision.
- **"How do you handle an engineer/senior who disagrees with your architecture?"** → seek to understand, surface the real trade-off, use data/prototype, decide transparently, disagree-and-commit, revisit if evidence changes.
- **"You have limited GPU budget and three teams want models. Prioritize."** → tie to business value/risk, shared infra (multi-LoRA, gateway, caching), cost transparency, say no with rationale. Leadership + [06](06_Distributed_Systems_Backend.md).
- **"How do you stay current?"** → concrete: papers/newsletters you read, things you've prototyped recently, your AI-ML learning repo. Show genuine curiosity.

---

## 🧠 First-90-days plan (have this ready — Principals get asked)

- **Days 0–30 (Learn):** map the current AI + Java/Spring backend landscape, talk to CTO + team leads + product, understand the debt-market domain + compliance constraints, find the pain and the quick wins. Resist the urge to mandate.
- **Days 30–60 (Prove):** ship one high-leverage exemplar (a well-built agent/RAG feature + the eval harness around it) that demonstrates the standard. Draft the platform/SDK vision.
- **Days 60–90 (Scale):** codify standards (eval, guardrails, observability), start the agent SDK, establish the architecture-review cadence, begin mentoring. Publish a 6–12 month AI platform roadmap with the CTO.

---

## 🚫 Anti-patterns to avoid in this round

- Being all-tech, no-people at Principal level → they want a multiplier, show the human side.
- Vague results ("improved performance") → **always quantify**.
- Overclaiming (esp. fine-tuning at scale, or Java depth) → be precise; Principals are trusted for honesty. → [05](05_FineTuning_and_Alignment.md).
- Trashing past employers/colleagues.
- Not having questions for them → [10](10_Questions_to_Ask_and_Redflags.md).
