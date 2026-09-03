# 04 — LLMOps, Evaluation, Guardrails & Responsible AI

> This is where you have a real edge (dataset generation, hallucination detection, telemetry). It's also the most Principal-differentiating round — juniors build agents, Principals make them *trustworthy at scale in a regulated domain*.

---

## 🎯 The core thesis to lead with

> "In a regulated debt-markets context, the model is the easy part. The hard part — and the Principal's job — is proving the system is correct, safe, and auditable *continuously*, not once. So I treat evaluation, guardrails, and observability as first-class platform components, not afterthoughts."

---

## 📏 Evaluation framework (own this — the JD says "own the agent evaluation framework")

### Layers of eval
1. **Offline / pre-deployment**
   - **Golden datasets** — curated input→expected pairs per task, maintained with SMEs.
   - **Regression suites** — every prompt/model/retrieval change runs against goldens; block deploy on regression.
   - **Metrics:** task-specific (exact match, F1, groundedness, tool-call correctness), plus latency/cost.
2. **LLM-as-judge**
   - Use a strong model to score outputs (correctness, groundedness, helpfulness, safety) with rubrics.
   - **Guard the judge:** calibrate against human labels, watch for position/verbosity/self-preference bias, use pairwise comparison over absolute scores where possible, pin judge model+prompt versions.
   - Cheaper + faster than humans at scale, but *validate it against humans periodically*.
3. **Human-in-the-loop eval** — SME review for high-risk tasks; sample production traffic.
4. **Online / production**
   - **A/B and shadow deployment** — run new version in shadow, compare before switching.
   - **Live metrics:** groundedness/hallucination rate, refusal rate, user feedback (thumbs), escalation rate, tool-error rate, latency/cost per request.
   - **Guardrail hit rates** as a signal.

### Agent-specific eval (harder than single-turn)
- **Trajectory eval** — was the *path* right, not just the final answer? (tool selection, step order, unnecessary steps).
- **Component + end-to-end** — eval each node (router accuracy, retrieval recall, tool-call validity) *and* the whole flow.
- **Simulated users / scenarios** — replay realistic multi-turn tasks.
- **Cost/step efficiency** — did it solve it in 3 steps or 15?

---

## 🚨 Hallucination control (your named strength — go deep)

Defense in depth:
1. **Ground it** — RAG with citations; the model answers *only* from retrieved context.
2. **Force attribution** — every claim cites a source span; post-check that citations actually support claims (NLI / LLM verifier).
3. **Abstain** — "I don't have enough information" is a valid, *rewarded* output in fintech. Calibrate to refuse rather than guess.
4. **Structured outputs** — schema-constrain anything that becomes a number/decision; validate; never let free text become a transaction value.
5. **Verifier pass** — a second model/step checks the answer against context (self-consistency, NLI entailment, or a dedicated fact-check agent).
6. **Deterministic guards** — arithmetic, dates, totals computed in code, not by the LLM.
7. **Confidence + human gate** — low confidence or high-stakes → route to human.

> **Say the honest part:** "You can't drive hallucination to zero. So the design question is: what's the *cost of a wrong answer here*, and does the architecture make wrong answers cheap to catch and impossible to act on unchecked?"

---

## 🛡️ Guardrails (JD: "establish standard guardrail policies")

**Input guardrails:** prompt-injection detection, PII detection/redaction, jailbreak filtering, topic/scope restriction, input validation.

**Output guardrails:** toxicity/PII leak checks, groundedness/citation enforcement, schema validation, policy compliance (e.g., no financial *advice* if not permitted), sensitive-data masking.

**Action guardrails (agents):** allow-list tools, require human approval before writes to systems of record, spend/rate limits, sandbox code execution.

**Implementation:** guardrails as **middleware** wrapping every LLM/agent call (not per-prompt strings). Options: NeMo Guardrails, Guardrails AI, Llama Guard / Prompt Guard, or custom. Centralize as a **platform policy layer** so all product teams inherit the same standards — that's the Principal move.

**Prompt injection (must volunteer for a doc-heavy fintech):** treat all retrieved/user/tool content as untrusted; instruction/data separation; don't let retrieved docs issue tool calls without validation; sandbox and least-privilege tools; detection + monitoring. Especially critical when agents read borrower-submitted documents.

---

## 🔍 Explainability (JD: "explainability frameworks for all LLM outputs")

For a lending/debt decision, "the AI said so" is unacceptable. Provide:
- **Traceability** — full lineage: prompt version, model version, retrieved sources, tool calls, intermediate reasoning, final output. Immutable + replayable.
- **Citations** — every factual claim linked to source.
- **Decision rationale** — structured explanation artifact per decision (which factors, which sources, confidence).
- **Reproducibility** — pin versions; deterministic replay of a decision for audit/dispute.
- **Human override trail** — log where humans intervened and why.

This doubles as your **audit story** for regulators.

---

## 📡 Observability / telemetry (your named strength)

- **Tracing:** every request → full span tree (retrieval, each tool call, each LLM call, tokens, latency, cost). Tools: **LangSmith, Langfuse, Arize Phoenix, OpenTelemetry-based** (OTel now has GenAI semantic conventions — mention it).
- **Metrics to dashboard:** latency (p50/p95/p99), cost/request + cost/user + cost/feature, token usage, error/timeout rates, hallucination/groundedness rate, refusal rate, guardrail hits, tool-error rate, cache hit rate, user feedback.
- **Alerting:** drift in quality metrics, cost spikes, latency regressions, guardrail-hit surges (possible attack).
- **Feedback loop:** capture prod failures → into golden/regression set → close the loop. Dataset generation from production traffic is the flywheel.
- **Data/quality drift:** monitor input distribution + output-quality metrics over time; models don't drift but *inputs and the world do*.

---

## ♻️ LLMOps lifecycle / CI-CD for LLM systems

- **Version everything:** prompts, models, retrieval configs, tools, guardrail policies, eval sets. Treat prompts like code (PR, review, versioned).
- **Eval gates in CI** — regression suite must pass to deploy.
- **Progressive rollout** — shadow → canary → A/B → full, with automatic rollback on metric regression.
- **Model gateway** — central routing (model choice, fallback, rate limit, cost cap, caching). Decouples product teams from provider specifics; enables instant model swap.
- **Reproducibility & rollback** — pin versions, one-click revert.

---

## 🎙️ Likely questions + scaffolds

- **"How do you evaluate an agent that has no single right answer?"** → rubric-based LLM-as-judge (calibrated to humans) + trajectory eval + task-outcome metrics + human sample; pairwise comparisons; golden set as regression anchor.
- **"How do you catch hallucinations in production?"** → groundedness scoring on sampled traffic (LLM/NLI verifier), citation-support checks, user-feedback + escalation signals, abstention-rate monitoring, drift alerts; failures feed the eval set.
- **"Design guardrails for an agent that reads borrower docs and drafts terms."** → untrusted-input handling + injection detection, PII redaction, groundedness + schema validation on output, tool allow-list, human approval before any write, full audit trace. Layer them as middleware.
- **"How do you build trust with compliance/regulators?"** → traceability + reproducibility + explanation artifacts + human-in-loop gates + documented eval results + guardrail policies. "I can replay any decision and show exactly what informed it."
- **"Your eval passes but prod quality drops — why?"** → distribution shift (prod inputs ≠ eval set), stale golden set, judge miscalibration, retrieval degraded (index drift), silent provider model update. Fix: prod-sampled eval, drift monitoring, pinned models, continuously refreshed goldens.
- **"LLM-as-judge — what could go wrong?"** → bias (position/verbosity/self-preference), miscalibration, cost, non-determinism. Mitigate: rubrics, pairwise, human calibration, version pinning, use for *relative* not absolute truth.
