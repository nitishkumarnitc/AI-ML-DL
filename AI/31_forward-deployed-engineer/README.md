# 31 — Forward-Deployed / AI Solutions Engineer (FDE)

> The deep-dive tutorial for the role. The one-page job card lives at [`../00_jobs/10_forward-deployed-ai-solutions-engineer/`](../00_jobs/10_forward-deployed-ai-solutions-engineer/README.md); the 3-hour timed exercise lives in its [`project.md`](../00_jobs/10_forward-deployed-ai-solutions-engineer/project.md). **This folder is the craft.**

---

## The role in one page

An FDE is the engineer who sits inside the customer's reality and makes the product actually work there.

Not a sales engineer (they leave after the sale). Not a solutions architect (they draw the diagram, someone else writes the code). Not a consultant (their work doesn't have to flow back into the product). **An FDE writes the code, stays for the outcome, and is the product team's highest-bandwidth channel to the field.**

The thesis of this whole tutorial fits in one sentence:

> **The demo is 1% of the work and 90% of the perceived progress — and closing that gap is the entire job.**

Everything else here is a consequence of that sentence. Discovery exists to find out whether the gap is closeable. Evals exist to make the gap measurable. Unit economics exist to prove the gap is worth closing. Stakeholder management exists because the customer cannot see the gap and you can.

---

## What makes this role different from every other AI engineering role

| | A product AI engineer | **An FDE** |
|---|---|---|
| Optimises for | The general case, across all users | **Time-to-value in one customer's messy reality** |
| Gets a spec | Usually | **Never — you get a business problem and three conflicting opinions** |
| Data | Clean, yours, documented | **Theirs, messy, undocumented, and you need three approvals to see it** |
| Definition of "good" | Written down in a PRD | **Not written down anywhere, and two stakeholders disagree** |
| Ships when | Tests pass, review approved | **When someone's job is measurably different** |
| Hardest skill | System design | **Saying "that won't work, here's what will" to someone who outranks you and is paying** |
| Failure looks like | A bug | **A successful pilot that quietly never reaches production** |

That last row is the one to internalise. **The characteristic FDE failure is not a broken system — it's a working pilot that dies.** Most of this tutorial is about preventing it.

---

## The files

Read in order the first time. After that, 03/04/10 are the ones you'll come back to.

| # | File | What it gives you | Priority |
|---|---|---|:--:|
| 01 | [What the role actually is](01-what-the-role-actually-is.md) | Role variants by company, a real week, how you're measured, the adjacent-role map | ⭐⭐⭐ |
| 02 | [The demo-to-production gap](02-the-demo-to-production-gap.md) | **The core thesis, quantified** — four stages, what breaks at each, the 100× rule | ⭐⭐⭐ |
| 03 | [Discovery and scoping](03-discovery-and-scoping.md) | The 12 questions that matter, the red-flag table, how to qualify out and stay hired | ⭐⭐⭐ |
| 04 | [Evals are the deliverable](04-evals-are-the-deliverable.md) | **Measure human agreement before model accuracy.** Golden sets from their data, rubrics, the ceiling conversation | ⭐⭐⭐ |
| 05 | [Prompt and context engineering in the field](05-prompt-and-context-engineering-in-the-field.md) | What actually moves accuracy on someone else's data, in what order | ⭐⭐⭐ |
| 06 | [Agents, tools and integration](06-agents-tools-and-integration.md) | Their real APIs: auth, idempotency, partial failure, human-in-the-loop | ⭐⭐⭐ |
| 07 | [Unit economics](07-unit-economics.md) | **Cost per business outcome, not per token.** The arithmetic that gets signed | ⭐⭐⭐ |
| 08 | [Security and the enterprise blockers](08-security-and-enterprise-blockers.md) | What actually kills deals in month three, and how to front-load it | ⭐⭐ |
| 09 | [Pilot to production](09-pilot-to-production.md) | The trap, written exit criteria, the handover that makes you redeployable | ⭐⭐⭐ |
| 10 | [Stakeholder communication](10-stakeholder-communication.md) | **Five annotated role-play scripts** — the non-determinism talk, the accuracy talk, the escalation | ⭐⭐⭐ |
| 11 | [The FDE toolkit](11-the-fde-toolkit.md) | The six things you rebuild at every customer, with **runnable code** | ⭐⭐⭐ |
| 12 | [The interview loop](12-the-interview-loop.md) | Every round including the customer role-play, with real answers | ⭐⭐⭐ |
| 13 | [Exercises and the first 90 days](13-exercises-and-first-90-days.md) | Drills, a portfolio spine, a 30/60/90 that survives contact | ⭐⭐ |

---

## What this folder assumes you already have

FDE work is a *composition* of skills this repo already covers. This tutorial does not re-teach them — it teaches the field judgement layer on top.

| You need | It's here |
|---|---|
| RAG and retrieval | [`../12_rag/`](../12_rag/README.md) · [`../06_vector-databases/`](../06_vector-databases/README.md) · [`../20_data-engineering-for-rag/`](../20_data-engineering-for-rag/README.md) |
| **Eval methodology** (the single biggest input) | [`../16_evals/`](../16_evals/README.md) |
| Agents and orchestration | [`../05_multi-agent-frameworks/`](../05_multi-agent-frameworks/README.md) · [`../13_langgraph/`](../13_langgraph/README.md) · [`../15_mcp/`](../15_mcp/README.md) |
| Prompting | [`../01_prompt-engineering/`](../01_prompt-engineering/README.md) |
| Guardrails and injection defence | [`../03_llm-security-and-guardrails/`](../03_llm-security-and-guardrails/README.md) |
| **Applied system design under real constraints** | [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md) — 12 worked designs; the FDE design round is this, scoped to one customer |
| Deeper design drills | [`../21_ai-system-design-deep-dives/`](../21_ai-system-design-deep-dives/README.md) · [`../27_ai-platform-system-design/`](../27_ai-platform-system-design/README.md) |
| Running it after handover | [`../../Shared/03_llmops/`](../../Shared/03_llmops/README.md) · [`../../Shared/02_mlops/`](../../Shared/02_mlops/README.md) |
| Shipping fast with coding agents | [`../17_claude-code/`](../17_claude-code/README.md) · [`../23_ai-coding-agents-and-code-eval/`](../23_ai-coding-agents-and-code-eval/README.md) |

> **[`28_ai-system-design-by-industry`](../28_ai-system-design-by-industry/README.md) is your unfair advantage in this loop.** Twelve designs, each naming its rejected alternatives and its revisit-when thresholds, across e-commerce, banking, automotive, healthcare, logistics, manufacturing, insurance, media, real estate, travel, HR and dev-tools. An FDE design round is exactly one of those conversations, held with the customer in the room. Reread the one nearest your interviewer's industry the night before.

---

## Five ideas that carry the whole tutorial

If you remember nothing else:

1. **Measure human agreement before you measure model accuracy.** If three of the customer's experts agree on only 88 of 100 cases, your ceiling is ~88% and you need to say so in week one, not month three. This single move is the most valuable thing an FDE does early — see [04](04-evals-are-the-deliverable.md).

2. **The eval harness is the deliverable, not the prototype.** It forces the customer to define "good" while disagreement is still cheap, it converts "this feels wrong" into a number, and it's the artifact that survives your departure.

3. **Human review capacity — not model quality — sets the operating threshold.** This pattern recurs in five of the twelve designs in [`28_`](../28_ai-system-design-by-industry/README.md) (fraud analysts, quality engineers, claims handlers, recruiters, PR reviewers). In the field it means: ask how many outputs a person can check per shift *before* you pick a confidence threshold.

4. **Cost per successful business outcome, never cost per token.** $0.04 per attempt at a 60% success rate is $0.067 per success against a $9.00 human baseline. That's the number a CFO signs — and notice the story survives a mediocre model but not a bad workflow fit.

5. **A pilot with no written exit criteria will not become production.** Define the accuracy bar, the volume, the p95, the reviewer's capacity, the security review, and the named signatories in week one — see [09](09-pilot-to-production.md).

---

## Market note

One of the fastest-growing engineering roles at AI-native companies since 2024, and unusually well-paid for a role that doesn't require research credentials — it rewards senior generalists who ship and can hold a room.

Indicative total-comp bands (US, senior IC), **which you should verify on levels.fyi rather than trust here** — public ranges move fast and my knowledge has a cutoff:

| Company type | Indicative band | Notes |
|---|---|---|
| Frontier labs (Anthropic, OpenAI) | ~$300K–$450K | Heavy equity; the bar is high and the loop is long |
| AI-native scale-ups (Sierra, Harvey, Glean, Decagon) | ~$200K–$320K | More equity risk, more autonomy, faster |
| Palantir (FDSE — the role's origin) | ~$130K–$230K | The best training ground; the culture is the curriculum |
| Enterprise incumbents adding AI solutions teams | ~$180K–$260K | Slower, more process, often more interesting data |

Non-US bands differ substantially; India-based roles at these companies typically run ₹60L–₹1.2Cr for senior FDE-equivalents, with the frontier labs at the top.

---

## How to use this

1. **Read [02](02-the-demo-to-production-gap.md) first if you read only one file.** It's the thesis, and it reframes everything else.
2. **Do the drills in [13](13-exercises-and-first-90-days.md) out loud.** The FDE loop is won in the role-play round, and role-play is not a reading skill.
3. **Build the toolkit in [11](11-the-fde-toolkit.md) for real, once.** Then you carry it into interviews as evidence and into the job as leverage.
4. **Pair [12](12-the-interview-loop.md) with one design from [`28_`](../28_ai-system-design-by-industry/README.md)** in your target industry, and rehearse it as a customer conversation rather than a whiteboard exercise.
