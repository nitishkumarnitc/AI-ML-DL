# Lesson 14 — Evaluating RAG: Testing the Generator & Full Pipeline with the RAG Triad

> **Source:** CampusX · *Evaluating RAG: Testing the Generator & Full Pipeline with the RAG Triad* · [watch](https://www.youtube.com/watch?v=PATGn2XhmCY&list=PLEneLIDJFpcA&index=15)
> **One-liner:** Builds and evaluates the generator in isolation (Faithfulness, Answer Relevancy), improves it purely through prompt engineering, connects it to Lesson 13's retriever into a real pipeline, runs the full RAG Triad — and then hits a genuinely confusing result (great recall/precision, terrible contextual relevancy) that turns into the lesson's best diagnostic lesson.

---

## 🎯 TL;DR

Same project, next two components. First, the **generator** is built and tested alone (context is injected manually from the golden dataset, not from the retriever) on two metrics: **Faithfulness** (91% out of the box) and **Answer Relevancy** (73% out of the box — the harder metric, since a faithful answer can still miss the point of the question). Prompt engineering alone — no model swap — pushes Faithfulness to 96% and Answer Relevancy to 92%. Then the retriever and generator are wired into a real pipeline and evaluated with the **RAG Triad** (Context Relevance, Faithfulness, Answer Relevancy). The twist: Faithfulness and Answer Relevancy stay strong (92–93%, 86–87%), but **Contextual Relevancy comes back at just 42–43%** — despite the *same* retriever independently scoring 99% recall and 89% precision in Lesson 13. Working out why becomes the session's central lesson about what precision actually does and doesn't measure.

---

## 1. Building the generator (`src/generator.py`)

A deliberately simple component: an LLM (**GPT-4o-mini**, temperature 0 — "you'll almost always see temperature set to zero during evaluation," even though production generation might use something higher) wrapped in a LangChain prompt + output parser. The initial system prompt:

```text
You are a helpful teaching assistant for a course on LLM Evaluations.
Answer the students' questions only from the context provided below.
- Use only information present in the context; do not add outside knowledge.
- If the context does not contain enough information to answer, say
  "I don't have enough information in the course material to answer that."
- Keep the answer clear and concise.
```

`generate(query, context)` takes a question and a context string and returns an answer. A quick manual test — a hand-written dummy context and question, no retriever involved — confirms the wiring works before any formal evaluation.

---

## 2. The generator's two failure modes → two metrics

Exactly the same "find the failure modes first" method as the retriever lesson:

### Failure mode 1 — Unfaithful (hallucinated) response

**Worked example:** Question — *"Does the CampusX AI Engineering program include live classes?"* Context — *"The program includes recorded lessons, coding assignments, projects, and weekly doubt-solving sessions."* The context never mentions live classes either way. A bad generator still answers: *"The program includes two live classes every week..."* — invented information the context never supported. This is explicitly tied back to the earlier **Air Canada chatbot case study** from the course (where the bot invented a refund policy) as a real-world instance of exactly this failure mode, and flagged as genuinely dangerous in production.

**Critical clarification:** faithfulness is *not* the same as correctness. If the retrieved context itself is wrong, a "faithful" generator that builds its answer entirely from that wrong context is still faithful — it just produced a wrong-but-faithful answer. Faithfulness only measures whether the answer stayed within the bounds of what it was given.

**Metric: Faithfulness** — is the generated answer grounded entirely in the given context?

### Failure mode 2 — Faithful but irrelevant response

**Worked example:** Same question and context as above. This time the generator answers *"The program includes coding assignments, projects, recorded lessons, and weekly doubt-solving sessions"* — every word of this is faithfully pulled from the context, but it never actually answers whether live classes are included. A better answer would explicitly say the context doesn't confirm live classes are included. The user still didn't get their question answered, even though nothing was hallucinated.

**Metric: Answer Relevancy** — does the generated answer actually address the question that was asked?

(Citation accuracy, correctness, and completeness are explicitly deferred to the application-level eval stage, not covered here.)

---

## 3. How each metric is calculated

### Faithfulness — worked example

1. Send the question + a **golden context** (not yet the retriever's output — the generator is still being tested in isolation) to the generator; get an answer.
2. LLM-as-judge breaks that answer into claims.
3. For each claim, the judge checks: does this claim's information exist in the golden context?
4. Faithfulness = (claims supported by the context) / (total claims in the answer).

**Worked numbers from the video:** an answer broken into 3 claims where claim 1 and claim 2 are found in the golden context but claim 3 isn't → Faithfulness = 2/3 ≈ 67% for that question. Average this across every golden-dataset row for the final score.

### Answer Relevancy — worked example, and why no golden context is needed

1. Send question + context to the generator; get an answer.
2. LLM-as-judge breaks the answer into claims (same mechanism as faithfulness).
3. For each claim, ask: does this claim help answer the *question* (regardless of whether it's grounded in context)?
4. Answer Relevancy = (claims that help answer the question) / (total claims).

**Worked example:** an answer about benchmark saturation broken into 3 claims — two are directly on-topic, one drifts into an unrelated point about benchmark contamination → Answer Relevancy = 2/3 ≈ 67%.

**Why this is a reference-free eval, unlike Faithfulness:** Answer Relevancy never checks the answer against a golden context or golden answer — it only checks the answer against the *question*. The golden dataset is still used to *generate* the answers being tested, but not as a ground-truth reference for scoring.

---

## 4. Golden dataset for the generator

Two columns: `question` and **`golden_context`** (not an ideal answer this time — the generator needs to be handed context directly, since it's being tested in isolation from the retriever). Built by exporting the entire Chroma vector store's ~862 chunks to a single JSON file, feeding that to Claude with instructions to generate one (question, golden-context) pair at a time — reviewed manually against the instructor's own knowledge of what was actually taught — producing 15 verified entries saved to `goldens/faithfulness_dataset.json`.

The DeepEval code pattern (`evals/eval_generator.py`) follows the same three-part shape as the retriever eval:

```python
test_case = LLMTestCase(
    input=question,                                  # from golden dataset
    actual_output=generate(question, golden_context), # from the generator itself
    retrieval_context=golden_context,                 # from golden dataset
)
metrics = [FaithfulnessMetric(...), AnswerRelevancyMetric(...)]
evaluate(test_cases=[...], metrics=metrics)
```

A performance note stated directly: DeepEval's `evaluate()` runs all test cases **in parallel**, not sequentially — this is why a 15-row eval finishes quickly rather than taking 15× a single call's latency.

---

## 5. Baseline results, and why Faithfulness beats Answer Relevancy by default

| Metric | Baseline score |
|---|:---:|
| Faithfulness | **91%** |
| Answer Relevancy | **73%** |

**The explanation given for this gap is a genuinely useful mental model:** the generator is explicitly instructed, in its own system prompt, to answer *from the given context*. Modern LLMs have strong instruction-following, so "stay faithful to what I hand you" is a comparatively easy instruction to satisfy — the model has direct textual material to lean on. But *"is this answer actually relevant to the question"* is a separate, harder judgment the prompt doesn't directly optimize for — an answer can be 100% faithful to the context and still miss what was actually asked. **Faithfulness is easier to score well on than Answer Relevancy by default, and this generalizes beyond this one project.**

---

## 6. Improving the generator — prompt engineering only

Just as the retriever had 3–4 real levers (chunk size, embedding model, reranker), the generator has essentially **two**: swap in a stronger model, or improve the system prompt. This session sticks with GPT-4o-mini and iterates purely on the prompt — run the eval, look at *which* test cases failed and *why* (`include_reason=True` output), feed those failures back into a prompt refinement, repeat 3–4 times. The rules that accumulated into the final prompt, added incrementally in response to specific observed failures:

- Use only information present in the context; do not add outside knowledge (already present).
- **Do not strengthen or overstate claims** — if the context says two things are "different," don't upgrade that to "distinct methods" or otherwise stronger wording than the source supports.
- The context is an informal lecture-transcript excerpt — **synthesize and rephrase** it; don't require the answer to match the context's exact wording.

**Result after 3–4 prompt-refinement iterations:**

| Metric | Baseline | After prompt tuning |
|---|:---:|:---:|
| Faithfulness | 91% | **96%** |
| Answer Relevancy | 73% | **92%** |

**An explicit overfitting warning accompanies this result:** because the prompt was refined by staring directly at *this* golden dataset's failures, there's a real risk the prompt has been tuned to this specific test data rather than to genuine general quality — a form of overfitting. The instructor flags this and says the real test of whether it generalizes comes next: running the *same* generator inside the full pipeline, where the context comes from the actual retriever instead of the hand-picked golden context.

---

## 7. Building and testing the full pipeline

`src/rag_pipeline.py` is pure glue code: a `RAGPipeline` class that takes a query, sends it to the retriever (the reranking retriever from Lesson 13), converts the returned chunks to a context string, sends question + context to the generator, and returns the answer. A live smoke test with the question *"What is drift and why does it matter after deployment?"* confirms the connected pipeline produces a coherent, correctly-cited answer.

### The RAG Triad, defined against the three real pairs

| Metric | Pair | 
|---|---|
| **Faithfulness** | context ↔ answer |
| **Answer Relevancy** | question ↔ answer |
| **Contextual Relevancy** | question ↔ context — *newly introduced this session* |

**The key structural difference from the component-level evals, called out explicitly:** the *calculation method* for Faithfulness and Answer Relevancy is identical to what was just done — the only thing that changed is **where the context comes from**. At the component level it came from the golden dataset; at the pipeline level it comes from the live retriever. Same metric, same formula, different (and now real) input.

### Contextual Relevancy — how it's calculated

Reference-free, just like Answer Relevancy — no golden context needed, only the golden dataset's *questions*:

1. Send the question to the retriever (nothing else needed); get back k contexts (chunks).
2. Break **each** retrieved chunk into claims (not the answer this time — the *context itself*). With k=5 chunks each yielding a few claims, you might get e.g. 15 total claims across all 5 chunks.
3. For each of those 15 claims, ask the judge: is this claim relevant to answering the question?
4. Contextual Relevancy = (claims judged relevant) / (total claims across all retrieved chunks).

**Worked example:** 15 claims across 5 retrieved chunks, 10 of them judged relevant to the question → Contextual Relevancy = 10/15 ≈ 67% for that question, averaged across the golden set for the final score.

`evals/eval_rag_pipeline.py` follows the same three-part DeepEval pattern, with `actual_output` now coming from the real `RAGPipeline`'s generator call and `retrieval_context` coming from the real `RAGPipeline`'s retriever call — not from the golden dataset at all, except for the input question.

---

## 8. The curious case: good retriever, bad Contextual Relevancy

### The result

| Metric | Score |
|---|:---:|
| Faithfulness (pipeline level) | 92–93% |
| Answer Relevancy (pipeline level) | 86–87% |
| **Contextual Relevancy** | **42–43%** |

This is confusing on its face: the *same* retriever independently scored **99% recall and 89% precision** in Lesson 13. How can a retriever be simultaneously excellent (by recall/precision) and terrible (by contextual relevancy)?

### Working through it live

The instructor poses this directly to the audience as a diagnostic exercise, then walks through the resolution:

- **Precision** asks: of the chunks retrieved, how many are *useful, whole chunks*? If a chunk contains the information needed to answer the question anywhere inside it, that whole chunk counts as a "correct" chunk for precision purposes.
- **Contextual Relevancy** asks something finer-grained: break each retrieved chunk into individual claims and check *each claim* for relevance. A chunk can be "correct" at the whole-chunk level (contributing to a good precision score) while still containing substantial irrelevant filler at the claim level — e.g. a 5-line chunk where only 2 lines are actually relevant to the question and the other 3 are unrelated tangent.

**The resolution, stated directly:** *"The problem isn't how many correct chunks we're bringing (that's recall) or how much noise exists across the whole set (that's precision) — it's how much noise exists **within each individual chunk**, and that's exactly what Contextual Relevancy measures, at the claim level rather than the whole-chunk level."* A retriever can score well on both recall and precision while still fetching chunks that are only partially relevant internally — and this pipeline is exactly that case.

**The lever this points to:** shrinking chunk size should reduce the amount of irrelevant filler inside each individual chunk, which should raise Contextual Relevancy — flagged as worth trying, with the caveat that it may trade off against the other metrics (smaller chunks can split information that needs to stay together, hurting recall).

**The pragmatic call made in the lesson:** since Faithfulness, Answer Relevancy, recall, and precision are *all* healthy, a comparatively low Contextual Relevancy is judged acceptable for now — the end answers are still coming out good — rather than something that must be fixed immediately before moving on.

---

## 9. Experiment tracking with Confident AI

DeepEval's parent product, **Confident AI**, is shown briefly as a way to persist every eval run (not just print it to the terminal): running `deepeval login` and the standard eval command uploads the run's pass/fail counts and per-test-case detail to a hosted dashboard, where configuration settings (chunk size, model, etc.) can be logged alongside each run — the same experiment-tracking idea introduced conceptually in Lesson 12, now shown as a real, working tool (an alternative to setting up MLflow yourself).

---

## 10. Key terms

| Term | Meaning |
|---|---|
| **Faithfulness (generator)** | Fraction of the generated answer's claims that are actually supported by the given context — not a measure of correctness. |
| **Answer Relevancy** | Fraction of the generated answer's claims that actually help address the question asked — reference-free, doesn't require a golden context. |
| **Contextual Relevancy** | Fraction of *all claims across all retrieved chunks* that are relevant to the question — a finer-grained, claim-level companion to precision's whole-chunk-level measurement. |
| **RAG Triad** | Faithfulness (context↔answer) + Answer Relevancy (question↔answer) + Contextual Relevancy (question↔context), evaluated on the connected, live pipeline. |
| **Component-level vs. pipeline-level** | Same metric formulas; the only difference is whether context comes from a golden dataset (component-level, isolating the generator) or from the live retriever (pipeline-level). |

---

## ✍️ Notes / follow-ups
- Remaining in the roadmap: application-level eval (Correctness, Completeness, Style), safety evals, ops evals, then regression testing and online eval — the next sessions in this arc. Application-level quality starts immediately in [Lesson 15 — Mastering G-Eval](15-mastering-g-eval-deterministic-judge.md).
- Key habit: **when a metric result contradicts an earlier, seemingly-related metric result, don't assume a bug — work out what the two metrics are actually measuring at different granularities before concluding something is wrong.**
