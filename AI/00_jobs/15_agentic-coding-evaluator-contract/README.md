# 15 · Agentic Coding Evaluator — Contract (hourly)

- **Type:** Remote contractor, hourly (commonly $70–$130/hr range depending on platform/experience)
- **In one line:** Use autonomous AI coding agents/assistants to actually do software-engineering work, then evaluate, compare, and document how well they did it — no prior AI experience required, your software-engineering judgment *is* the product.
- **Where (examples):** Expert networks & data labs — Mercor, Turing, Outlier (Scale), Handshake AI, Surge AI, Invisible (the same category of platforms as [#12](../12_rl-environment-task-author-contract/README.md) and [#14](../14_domain-sme-ai-data-contributor-contract/README.md); many overlap across postings).

← back to [AI Jobs hub](../README.md)

🧪 **[Try the sample project for this role](project.md)**

---

## 🎯 What the work is
- Delegate real software-engineering tasks (bug fixes, refactors, feature slices) to autonomous coding agents and coding assistants, then plan/implement/debug alongside them.
- Evaluate the AI-generated code itself: spot invented APIs, wrong signatures, subtly-wrong logic, and scope creep ([Lesson 2](../../23_ai-coding-agents-and-code-eval/02-evaluating-ai-generated-code.md)).
- Run the **same task** through multiple tools (terminal-native agents, IDE-embedded assistants) and compare reasoning quality, not just the final diff.
- Write up best practices and reproducible findings for agentic-coding workflows — documentation someone else can act on.

## 🧰 Core skills
- Solid software-engineering fundamentals (debugging, refactoring, reading unfamiliar code, writing tests) — this is the actual bar, not AI knowledge.
- Prompt engineering good enough to spec a task clearly and re-prompt when an agent is stuck.
- Rubric-based, auditable evaluation writing — precise about *why* something is wrong, not just *that* it is.
- Comfort operating several different coding-agent tools/environments in the same week.

## 📈 Market note
This is a **distinct role from #12 and #14**: #12 (RL Env/Task Author) delivers a formal gradable environment + automated grader; #14 (Domain SME) grades model *answers* in any domain. This role is specifically about **using and judging coding agents** as a daily practice — closer to a hands-on QA/pair-programmer for AI tools than a formal environment author. It's currently one of the most commonly posted "AI expert" contractor gigs for software engineers, paid hourly rather than per-deliverable, and explicitly states no prior AI experience is required.

## 📚 Path in this repo
- [`23_ai-coding-agents-and-code-eval`](../../23_ai-coding-agents-and-code-eval/README.md) — the core: the tool landscape, the code-hallucination rubric, and the review workflow. Built specifically to cover this role.
- [`01_prompt-engineering`](../../01_prompt-engineering/README.md) — spec'ing tasks and re-prompting a stuck agent.
- [`17_claude-code`](../../17_claude-code/README.md) — deep daily-workflow fluency with one representative terminal-native agent.
- [`16_evals`](../../16_evals/README.md) — the general eval vocabulary (LLM-as-judge, reference-based vs. free) this role specializes to code.

## 🎒 How to stand out
- Bring a **reusable rubric** (like [Lesson 2's](../../23_ai-coding-agents-and-code-eval/02-evaluating-ai-generated-code.md)) instead of ad hoc "looks fine/doesn't" judgments — auditable, consistent grading is what separates a paid contributor from a casual user.
- Show fluency across at least two different agent tools/environments, not just one — the role explicitly values comparison.

## 🔁 Adjacent roles
- [RL Env / Task Author (contract)](../12_rl-environment-task-author-contract/README.md) · [Domain SME / AI Data Contributor](../14_domain-sme-ai-data-contributor-contract/README.md) · [Agent Evaluation & Data-Pipeline Engineer](../11_agent-evaluation-and-data-pipeline-engineer/README.md)
