# 16 · Member of Technical Staff, Frontier AI (Research/Data Quality Lead)

- **Type:** Full-time, core team
- **In one line:** Own research and evaluation initiatives end-to-end — translate messy, real-world ops signal into structured eval frameworks, calibrate quality with domain experts, and act as the quality gate deciding when a result is strong enough to externalize.
- **Where (examples):** AI-data-lab core/research teams and frontier labs' internal research-ops functions — the same category of organization as [#08](../08_rl-environments-and-infra-engineer/README.md) and [#11](../11_agent-evaluation-and-data-pipeline-engineer/README.md), one level up in scope.

← back to [AI Jobs hub](../README.md)

🧪 **[Try the sample project for this role](project.md)**

---

## 🎯 What the work is
- Own research/eval initiatives end-to-end: problem framing, data design, quality calibration, signal validation.
- Design ML-oriented data systems — task definitions, annotation schemas, rubrics, incentives, pipelines optimized for downstream model performance.
- Analyze model/system failures for root cause; translate ambiguous real-world behavior into structured eval frameworks and new data categories.
- Act as a **quality gate**: block claims, pause work, or force scope changes when signal strength or data integrity is insufficient.
- Translate research progress into credible, evidence-grounded narratives for both technical and non-technical/client-facing stakeholders.

## 🧰 Core skills
- **Research signal judgment** — knowing when a result is trustworthy (sample size, annotator/judge agreement, contamination, reproducibility) versus when it's noise.
- **Ops-to-research translation** — turning vague, real-world complaints/failures into a falsifiable hypothesis and a structured, gradable eval category.
- ML-oriented data/rubric/incentive design; comfort operating in ambiguity with a bias toward decisive ownership.
- Clear written/verbal communication of trade-offs and confidence levels to mixed technical/non-technical audiences.

## 📈 Market note
This role sits **above** [#08 RL Environments & Infra](../08_rl-environments-and-infra-engineer/README.md) and [#11 Agent Evaluation & Data-Pipeline Engineer](../11_agent-evaluation-and-data-pipeline-engineer/README.md) in scope: those roles *build* the environments/pipelines that produce signal; this role *owns the program* — decides what's worth building, whether the signal it produces is defensible, and how to communicate it. It's also the natural full-time destination for someone who's been doing the contractor-side work in [#12](../12_rl-environment-task-author-contract/README.md), [#14](../14_domain-sme-ai-data-contributor-contract/README.md), or [#15](../15_agentic-coding-evaluator-contract/README.md) and wants to own the quality bar for that whole supply chain rather than execute one task at a time.

## 📚 Path in this repo
- [`10_rl-environments-and-infra` Lesson 10](../../10_rl-environments-and-infra/10-ops-to-research-translation-and-signal-judgment.md) 🆕 — built specifically for this role: the ops→research pipeline, the signal-trustworthiness checklist, being the quality gate, incentive design.
- [`10_rl-environments-and-infra` Lesson 6](../../10_rl-environments-and-infra/06-running-frontier-models-and-failure-analysis.md) — the same triage discipline at the single-task level; read before Lesson 10.
- [`10_rl-environments-and-infra` Lesson 4](../../10_rl-environments-and-infra/04-task-generation-and-data-pipelines.md) — task/data pipeline design underlying "ML-oriented data systems."
- [`16_evals`](../../16_evals/README.md) — contamination, offline/online evals, LLM-as-judge calibration — the general vocabulary Lesson 10 specializes.

## 🎒 How to stand out
- Bring an example where you **blocked or paused** a result that looked good on the surface, and show the specific check (sample size, agreement, contamination) that caught it — this role is judged on that instinct, not on volume of shipped evals.
- Show fluency translating the same finding two ways: the precise technical version for a researcher, and the plain-language decision-and-confidence version for a non-technical stakeholder.

## 🔁 Adjacent roles
- [RL Environments & Infra](../08_rl-environments-and-infra-engineer/README.md) · [Agent Evaluation & Data-Pipeline Engineer](../11_agent-evaluation-and-data-pipeline-engineer/README.md) · [Research Engineer — Model Training](../02_research-engineer-model-training/README.md) · [RL Env / Task Author (contract)](../12_rl-environment-task-author-contract/README.md)
