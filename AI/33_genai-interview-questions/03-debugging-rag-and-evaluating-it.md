# 03 · Debugging RAG in production, and how to evaluate it

> ← [`02-model-selection-and-system-architecture.md`](02-model-selection-and-system-architecture.md) · **Index:** [`README.md`](README.md) · **Next:** [`04-production-cost-latency-and-monitoring.md`](04-production-cost-latency-and-monitoring.md) →

---

## Q3 — Your RAG system is giving wrong answers in production. How do you debug it?

**The framing the interviewer is testing for:** they're not asking "did you build a RAG system" — they're asking whether you know the actual failure surface once it's live and occasionally hallucinating.

### The debugging order (verbatim structure)

**1. Check the retrieved documents/chunks first.** Are the right chunks even being retrieved? Print or inspect the chunks directly (via a debugger panel in your UI) — read them and confirm whether the retrieved content actually contains the answer.

**2. Check chunk size.** Too small → **loses context** (the answer is split across chunks and neither has enough of it). Too large → **introduces noise** (irrelevant content dilutes the relevant part, and the model has to find the needle).

**3. Check reranking.** You may be retrieving the correct chunk in your top-10, but if it's not near the top after reranking, the generation step may never "see" it clearly enough. Confirm reranking is actually applied and working.

**4. Check the embedding model.** Is it the right embedding model for your domain? (Named example: don't use a generic open-source embedding model on medical data if a domain-appropriate one exists.)

**5. Only then, check whether the LLM is ignoring context** — i.e. confirm your prompt is actually context-sensitive and instructs the model to ground its answer in what was retrieved.

> **The analogy:** *"Like a teacher giving a wrong answer — first check whether they read the right book, then check whether they read the right page. Only after that do you consider whether the teacher (the LLM) itself is the problem."*
>
> **The stated rule of thumb: "80% of RAG bugs occur at retrieval time, not in the LLM. Always investigate the retriever first."**

---

## Q21 — How do you measure/evaluate a RAG system?

The presenter's structure: **three levels**, evaluate at each independently rather than one blended score.

### Level 1 — Chunk / retrieval level

Is the *right* chunk actually being retrieved?

- **Precision** — of the retrieved chunks, how many are actually relevant
- **MRR (Mean Reciprocal Rank)** — how high up the correct chunk ranks
- **Recall** — of all relevant chunks that exist, how many were retrieved
- BLEU / ROUGE-style overlap scores can also be used here

### Level 2 — Generation level

Is the generated *response* correct, given what was retrieved?

- Requires a **ground truth** answer to compare against
- BERT similarity score against ground truth
- BLEU score against ground truth

### Level 3 — End-to-end evaluation

The full pipeline, evaluated as a whole — this is explicitly attributed to **"RAGAS"** in the transcript (rendered as "Regas"):

- **Faithfulness** — is the answer grounded in the retrieved context (not invented)
- **Answer relevance** — does the answer actually address the query
- **Context recall / context relevance** — did the retrieval step surface what was needed

**Interview structure:** answer chunk-level → generation-level → end-to-end, in that order. "If you answer like this, the interviewer can't refuse it."

---

## Q22 — How do you detect hallucinations automatically in production?

Five techniques given:

| Technique | How it works |
|---|---|
| **Faithfulness scoring (via RAGAS)** | Flags answers that don't align with the retrieved context |
| **Consistency checking** | Ask the LLM the **same question three times**. If the answers differ meaningfully, flag it as uncertain / potentially hallucinating |
| **Citation checking** | Does the answer actually cite something traceable to the source |
| **Confidence scoring** | Use the model's own (or a secondary) confidence signal |
| **Cross-model verification** | Use a **second LLM to verify the first LLM's** answer |

### The worked example

> A medical chatbot is asked the **same drug-dosage question five times**. It returns five different doses (50mg, 75mg, 100mg, 50mg, 200mg). That inconsistency **is** the hallucination signal — the system flags the response and shows the user: *"High uncertainty detected, please verify with a doctor."*

This is the consistency-check technique in action — the disagreement across repeated calls is the detector, no separate ground truth needed.

---

## Q24 — How do you build a regression test suite for an LLM app?

Steps, in order:

**1.** Collect **100–500 real user queries from production** that represent typical usage.

**2.** Have **humans create the ideal/expected answer** for each of those queries (this is effectively human-in-the-loop labelling — described in the transcript as tied to the RLHF idea of using human feedback as ground truth).

**3.** Define **automatic metrics**: exact match for factual answers, and use an LLM-as-judge for open-ended format/quality validation.

**4.** **Run the full suite every time a prompt changes** — before deploying.

### The worked example

> A team changed **one word** in their customer-support chatbot's system prompt — from "be **helpful**" to "be **brief**." Running the regression suite revealed **brief answers were 40% less satisfactory** for technical use cases. Because they tested before deploying, they caught it and reverted. Without a regression suite, they would have shipped a measurably worse prompt straight to production.

---

## Q25 — What's the difference between offline and online evaluation?

| | Offline evaluation | Online evaluation |
|---|---|---|
| Where it runs | On a **fixed dataset**, before deployment | On **live production traffic** |
| Speed | Fast, repeatable | Slower — needs real traffic to accumulate |
| What it's good for | Regression testing, comparing models, A/B experiment setup | Real user behavior, catching drift as it actually happens |
| Risk | May not reflect real user behavior | Real-world testing alone is risky — you're experimenting on real users |

> **The analogy:** *"Offline is like a medicine trial on a controlled patient population in a lab. Online is like post-launch monitoring of a real patient — it can reveal effects the lab trial never showed. Labs can't catch every real-world case, but real-world testing alone is risky. You need both."*

---

> ← [`02-model-selection-and-system-architecture.md`](02-model-selection-and-system-architecture.md) · **Index:** [`README.md`](README.md) · **Next:** [`04-production-cost-latency-and-monitoring.md`](04-production-cost-latency-and-monitoring.md) →
