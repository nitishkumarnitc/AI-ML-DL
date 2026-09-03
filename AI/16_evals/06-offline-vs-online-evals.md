# Lesson 6 — Offline Evals vs Online Evals

> **Source:** CampusX · *Offline Evals Vs Online Evals* · 1:21:09 · [watch](https://www.youtube.com/watch?v=SahaDGzN-Bk&list=PLEneLIDJFpcA&index=6)
> **One-liner:** Offline eval is everything covered so far, given a name — pre-deployment testing against a golden dataset. This lecture's real payoff is *online* eval: monitoring live traffic with **no answer key at all**, using a LangSmith walkthrough to show the full pipeline (logging → captured vs. computed signals → dashboarding/alerting → stratified sampling → LLM-as-judge) — plus the crucial distinction that offline eval checks **correctness**, while online eval can usually only check **normalcy**.

---

## 🎯 TL;DR

**Offline eval** turns out to be a new name for everything already covered in Lessons 3–5 — any eval you run *before* deployment, against a golden dataset with a known answer, is offline eval by definition. It has three concrete benefits: pre-release gating (including full CI/CD automation), version comparison, and regression testing. But going to production introduces three risks offline eval structurally cannot see: unanticipated real-world inputs, emergent failures that only appear at scale (latency under concurrent load, hidden bias visible only across thousands of conversations), and **drift** (the real world moves on while your golden dataset stays frozen). **Online eval** monitors live traffic with no golden answer available — its core limitation, demonstrated with a worked UPSC-grader example, is that it usually can only tell you the system is behaving *normally* (consistent with its historical baseline), not that it's *correct*. The full online pipeline — logging → captured/computed signals → dashboards/alerts → stratified sampling → LLM-as-judge — is walked through live in LangSmith, closing with the **self-improving loop**: production failures get pulled back into the offline golden dataset, closing the circle.

---

## 1. Offline evaluation — a new name for what you already know

**The direct claim made at the start:** *"You won't learn anything new here — everything we've discussed in the last two-three sessions, where I showed you how to build an eval pipeline, is an example of offline eval."* The definition: any eval pipeline you run on your LLM application **before deploying it** is offline eval — including, explicitly, the UPSC Mains grading system from Lesson 5, which was tested step by step (golden dataset, LLM-as-judge) entirely before deployment.

### Three concrete benefits of offline eval

1. **Pre-release testing / gating.** Beyond just manually checking a score before shipping, this can be **fully automated as a CI/CD gate**: a code push triggers CI (e.g. GitHub Actions), which runs the eval script automatically; if the resulting score clears a defined threshold (e.g. above 95%), the deployment pipeline triggers automatically; if it falls below, the team gets a failure notification instead of a deploy. This ties directly into the LLM Ops material referenced from elsewhere in the CampusX catalog.
2. **Version comparison.** To decide between two options — Claude vs. OpenAI as the backend model, one reranker vs. another, one vector database vs. another, even two different software architectures — keep everything else identical and run the *same* eval, on the *same* golden dataset, against each version. Since the playing field is level, the resulting scores are directly comparable, and the decision follows from the numbers rather than a guess.
3. **Regression testing.** Worked example: a Campus X chatbot is observed responding coldly whenever refunds come up, so the system prompt is edited to be "kind and polite." The unintended side effect: the bot becomes *too* soft — e.g. rounding a real ₹19,500 price down when describing it, just to sound gentler, which is now a factual error introduced by a prompt change meant to fix tone. **This is regression**: fixing one thing quietly breaks another. The fix is to build a golden dataset that deliberately spans every question category (refunds, pricing, curriculum, etc.), so that after any change, you can check whether the category you were *not* trying to improve held steady — e.g. if refund-question accuracy was 90% before a prompt change, it should stay near 90% after, not drop to 80%, even if the change was aimed at pricing questions.

**The concise summary of offline eval's role, stated directly:** *"Offline eval's job is to check whether your application is working correctly."*

---

## 2. Three risks that only appear in production

Once deployed, three categories of risk exist that offline eval — by construction — cannot catch, because they don't exist inside a fixed golden dataset:

### Risk 1 — A far wider variety of unanticipated inputs
The golden dataset used for testing might contain 200–500 anticipated questions. Real production traffic is an open set: users may mix languages (e.g. Hindi-English code-switching, when the model was mostly trained/tuned on English), ask ambiguous half-questions, vent in anger with a real question buried inside, or deliberately attempt adversarial/prompt-injection attacks. Production exposes the system to a superset of scenarios no offline test set can fully anticipate.

### Risk 2 — Emergent and systematic failures that only appear at scale
Two named examples:
- **Concurrency-driven latency spikes** — a new course launch drives a sudden concurrent-user surge, and latency degrades in a way no offline test (which doesn't simulate thousands of simultaneous users) could have caught.
- **Bias visible only in aggregate** — a chatbot might, for example, answer non-technical-background users noticeably worse than technical-background users, a pattern that's statistically invisible in a handful of test conversations but becomes visible once thousands of real conversations accumulate.

### Risk 3 — Drift
Worked example: a Campus X RAG chatbot is built from today's course pages, pricing, curriculum, and transcripts. Over time, the business naturally changes — prices update, curricula shift, policies evolve. A year later, the live documents look meaningfully different from what they were when the golden dataset was built. **The eval pipeline itself becomes stale** — it may keep reporting good offline scores against its now-outdated golden dataset, even while real users are increasingly unhappy in production, because the golden dataset was never updated to reflect the world as it now is. This is **drift**, and it's presented as the most conceptually important of the three risks: an offline eval pipeline doesn't announce its own obsolescence — it just keeps confidently reporting scores against a reality that no longer matches.

**The conclusion drawn directly:** offline eval fundamentally works by comparing output against a pre-defined correct answer — and none of these three production risks come with a pre-defined correct answer attached. This is exactly the gap **online eval** exists to fill.

---

## 3. Online evaluation — and the crucial correctness-vs-normalcy distinction

**Definition given:** *"Online eval is evaluating your system on live production traffic after deployment, as real users interact with it."* Its single most defining feature: **it works without an answer key.**

### The worked example that makes the distinction concrete

Return to the UPSC Mains auto-grading platform from Lesson 5. Offline, the system's correctness was measured by comparing its scores to a human grader's scores on the same answers (Mean Absolute Error). **Can that same correctness check run in production?** No — once deployed, the platform is grading *new* student answers no human has ever also graded, so there is no ground-truth score to compare against. **Correctness, in the strict sense, becomes unmeasurable online.**

**What *can* be checked instead: normalcy**, via a distribution-based baseline comparison:
1. Every week, plot the distribution of scores the system assigned across all evaluated answers (e.g. most students clustering around 500/1000, some at 700, few at 200).
2. Compare each new week's distribution against the established baseline shape from prior weeks.
3. If a given week's distribution suddenly shifts dramatically (e.g. most students now clustering around 800–900), that's a signal something changed — not proof of an error, but a trigger to investigate (it *could* be a genuinely stronger cohort of students, or it could be the grading system malfunctioning).

**The precise conclusion, stated directly:** *"Offline eval tells you whether your application is working correctly. Online eval tells you whether your application is currently working normally."* These are explicitly **not competitors** — they're complementary, and a mature system runs both, always, together.

### Not every online metric is stuck with only "normalcy" — it depends on the metric

The lecture clarifies this isn't an absolute rule: some metrics **can** still be computed online without any answer key, because they're inherently reference-free. **Faithfulness** is the given example — checking whether an answer is grounded in its retrieved context requires only the context and the answer itself, no golden answer needed, so faithfulness genuinely *can* be computed live in production. Where a metric structurally requires a correct answer (like the UPSC grading correctness), you're stuck estimating normalcy instead — unless you find an alternative signal.

**A worked alternative signal for correctness-like feedback: user feedback itself.** For a general chatbot, you can't verify a live answer against a golden key — but if thumbs-down ratings spike over the last hour compared to the historical baseline, that's a legitimate (if indirect) proxy signal that something is going wrong with correctness, even without ever knowing the "right" answer to any specific question.

---

## 4. Two categories of signal to track online

| Type | Definition | Examples |
|---|---|---|
| **Captured signals** | Already present in the interaction — you just store them, no computation needed | Thumbs up/down, latency, token usage/cost (the provider already reports this) |
| **Computed signals** | Require running an evaluator to derive them | Faithfulness, answer relevance, correctness estimate, hallucination rate, toxicity, bias/fairness |

This distinction determines which of two different pipeline shapes a given metric follows (see below).

---

## 5. The online evaluation pipeline, step by step (with a live LangSmith walkthrough)

### Step 1 — Logging (the foundation everything else depends on)

**The core idea:** capture a structured, replayable record of every conversation turn — nothing can be evaluated later if it wasn't recorded. What gets logged per turn: conversation ID, turn ID, user ID, session ID, timestamp, the user's question, the retrieved context (for RAG), the generated output, and operational data (latency in ms, prompt/completion token counts, cost, error status codes) — plus behavioral signals (thumbs up/down, escalation to a human, repeated/rephrased questions signaling frustration). The tool demonstrated for this is **LangSmith** (previously covered on the channel), which stores every conversation with its full metadata in one place.

**Three engineering properties logging must have, named directly:**
1. **Non-blocking** — logging must not add latency to the user-facing conversation; both operations run independently.
2. **Durable and queryable** — stored in a proper data warehouse / observability tool so it can be reliably fetched later.
3. **Late-signal attachment** — some signals (e.g. a user emailing support a day *after* the conversation ended to complain) arrive later and must still be correctly attached back to the original conversation ID.
4. **PII handling** — sensitive data shared mid-conversation (phone numbers, card numbers, addresses) must be masked/redacted before storage, so no teammate can later extract someone's personal information from the logs.

### Step 2a — Captured-signal pipeline: logging → dashboard → alerting

For signals that need no computation (e.g. latency), the flow is simple: log the raw value → display it on a **dashboard** as a time-series (last hour / 24 hours / week / months) → set **alerting** thresholds (Slack, email, PagerDuty, etc.) so an engineer is notified automatically when, say, latency crosses 4 seconds, rather than needing to watch a graph all day. **Demonstrated live in LangSmith's Monitoring tab**: per-project dashboards already show trace latency, error rate, LLM call counts, and cost, aggregated over a selectable time window — and a single slow conversation doesn't matter in isolation; it's the *aggregate* trend (e.g. average latency climbing over the last hour) that signals a real system-level problem.

### Step 2b — Computed-signal pipeline: logging → sampling → evaluator → dashboard → alerting

For a metric like **hallucination rate**, which requires judgment, an extra evaluation step is inserted before the dashboard:

1. **Log** every conversation as before.
2. **Set up an evaluator** — since there's no golden dataset in production, this must be a **reference-free** evaluation, typically LLM-as-a-judge: feed the judge the retrieved context, the user's question, and the model's output, with a detailed rubric asking it to flag hallucination.
3. **Sample, don't evaluate everything.** Running an LLM-as-judge over every single production conversation would roughly double your inference cost (you're already paying to run the chatbot; now you'd pay again to judge every one of its answers) — so a representative sample is drawn instead, and the evaluator only runs on that sample.
4. **Aggregate and dashboard** the resulting metric (e.g. hallucination rate) over time, exactly like a captured signal from here on.
5. **Alert** when the aggregated metric crosses a threshold.

### The sampling strategy itself: stratified, not random

**The question posed directly:** is drawing a purely random sample of conversations the best strategy? **The answer given: no — use stratified sampling instead.** Rather than sampling uniformly, bucket conversations into categories first (e.g. those that got a thumbs-down, those that ended in escalation, those where the user repeatedly rephrased the same question, those discussing money/refunds/fees) and **oversample the problematic categories** while undersampling conversations that already got a thumbs-up (a reasonable, if imperfect, signal that hallucination is less likely there). This meaningfully raises the odds that your limited evaluation budget actually catches real hallucinations, rather than spending it uniformly across mostly-fine conversations.

### The LangSmith "Evaluators" walkthrough, and the tracing-vs-dataset toggle

LangSmith ships pre-built evaluator templates: PII leakage, prompt-injection detection, safety/toxicity, hallucination, correctness, and more, plus agent-specific and modality-specific (image/voice chatbot) variants — each backed by its own LLM-as-judge pipeline with its own rubric, judge model choice, and output format.

**The single most important configuration choice highlighted:** every evaluator you build can be pointed either at **tracing** (live logged conversations) or at a **dataset** (a fixed, pre-loaded set of examples). **Pointed at tracing → it becomes an online evaluator. Pointed at a dataset → it becomes an offline evaluator.** This is presented as the cleanest practical illustration that LangSmith is a genuinely unified platform for both — the same evaluator-building UI produces either kind, depending only on what you point it at.

---

## 6. Closing the loop: the self-improving cycle

LangSmith's UI includes a literal **"Add to dataset"** action on any logged conversation — when a team identifies a real production failure while reviewing traces, they can pull that exact conversation directly into an offline dataset (with the option to annotate what specifically went wrong), which then feeds the *next* offline evaluation run. **This is the same self-improving loop introduced conceptually in Lesson 3**, now shown as a concrete, one-click action inside a real tool: offline eval → deploy → online eval surfaces a failure → that failure becomes new offline eval data → re-run offline eval → redeploy — continuously, for as long as the system is live.

---

## 7. Key terms

| Term | Meaning |
|---|---|
| **Offline eval** | Any eval run before deployment against a golden dataset with a known answer — checks *correctness*. |
| **Online eval** | Monitoring live production traffic with no answer key — checks *normalcy* (or, for reference-free metrics like faithfulness, can still check quality directly). |
| **Drift** | The real world (documents, prices, policies) changing while the golden dataset stays frozen, silently making offline eval results stale. |
| **Captured signal** | An online metric that needs no computation — just storage (latency, thumbs up/down, token cost). |
| **Computed signal** | An online metric requiring an evaluator to derive (faithfulness, hallucination rate, toxicity). |
| **Stratified sampling** | Oversampling categories of conversation most likely to contain real problems (thumbs-down, escalations, money-related), rather than sampling production traffic uniformly at random. |
| **Self-improving loop** | Production failures pulled into the offline golden dataset, closing the cycle between online and offline eval. |

---

## ✍️ Notes / follow-ups
- This closes the application-eval overview arc. Next the series pivots to model-level evals — starting with *why an AI engineer specifically* needs them → [Lesson 7 — LLM Model Evals & Capabilities](07-model-evals-and-capabilities.md).
- Key habit: **before trusting any online metric, ask whether it's structurally reference-free (like faithfulness) or whether it's really only checking normalcy against a baseline (like the UPSC-grader distribution) — the two require very different confidence levels.**
