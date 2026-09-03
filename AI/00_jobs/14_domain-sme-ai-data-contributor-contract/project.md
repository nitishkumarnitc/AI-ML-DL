# 14 · Sample project — Domain SME / AI Data Contributor (contract)

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- grades both candidate answers for all 5 questions across 3 DIFFERENT domains (coding, personal finance, statistics) and prints reviewer-style notes. `--report-file` exports the full report as markdown. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Five hard questions in a domain you know, each with a reference answer and a grading rubric, plus graded model outputs (one good, one subtly wrong) with reviewer-style feedback that flags exactly what's wrong — the actual contract deliverable format.

## 🧠 Why this mirrors the real job
- "Write, review, or grade model outputs in your area of expertise; craft hard questions/tasks" → the five questions are the core artifact.
- "Produce reference answers and rubrics; flag where the model is subtly wrong" → this is the skill that pays — not "is this right," but "here is precisely how it's wrong."
- If you don't have a specialized domain, use **coding** — the "domain SME" work for coding is exactly this pattern, and it's this repo's own on-ramp into [RL Env / Task Author](../12_rl-environment-task-author-contract/project.md).

## 🧰 Prerequisites
- Deep-enough knowledge of one domain (yours, or coding if none other applies).
- An LLM to generate the two candidate answers per question (or write them yourself to simulate "model output").
- ~4–5 hours.

## 🧰 Tools, libraries & skills used here
- **Rubric-based grading**: each question has a point-weighted rubric of independently-checkable criteria, not a single right/wrong judgment — the actual format vendor platforms require so grading is auditable and consistent across many reviewers.
- **Reviewer-style consequence notes**: explaining *why* a wrong answer is dangerous (what a reader would wrongly conclude and do) is the specific skill that separates a paid SME contribution from a simple thumbs-down.
- **Domain-agnostic pattern**: the harness (`grade_answer`) doesn't care what the domain is — swap the questions/rubric/candidates for law, medicine, or finance and the same grading discipline applies.
- **What a real contribution pipeline adds on top**: an actual LLM generating the candidate answers (including deliberately-flawed ones, for training signal), a labeling platform (**Label Studio**, **Scale**, **Surge**, **Outlier**, **Mercor**) to submit and track rubric-graded work at scale, and often a second-reviewer pass to check the rubric itself for gaps before it's trusted.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| (none) | — | pure functions over the questions/rubrics -- no imports needed beyond the built-ins |

## 🪜 Step-by-step

### 1. Write 5 hard questions — not trivia, judgment calls
Good SME questions have a correct answer that requires real expertise to verify, and ideally a common wrong answer that *looks* plausible. Example (coding domain):
```markdown
Q1: Is `list.append()` thread-safe in CPython? Explain why or why not, referencing the GIL.
Q2: Why can `datetime.now()` cause subtly non-reproducible test failures, and what's the fix?
Q3: What's wrong with catching `Exception` broadly in a retry loop around a network call?
```

### 2. For each question, write the reference answer + rubric
```markdown
Q1 reference answer: Yes, `list.append()` is effectively atomic in CPython due to the GIL —
no two Python-level operations can interleave inside the single bytecode operation involved.
Rubric:
  - [2 pts] Says "yes, thread-safe" (not "no")
  - [2 pts] Correctly attributes it to the GIL, not to some list-specific lock
  - [1 pt]  Notes this is a CPython implementation detail, not a language guarantee
```

### 3. Generate two candidate "model answers" per question
```python
GOOD_PROMPT = "Answer accurately and completely: {question}"
SUBTLE_ERROR_PROMPT = ("Answer this, but make one subtle but plausible-sounding factual "
                        "error a non-expert wouldn't catch: {question}")

good_answer = call_llm(GOOD_PROMPT.format(question=Q1))
flawed_answer = call_llm(SUBTLE_ERROR_PROMPT.format(question=Q1))
```
(If you'd rather not prompt a model to be subtly wrong, write the flawed answer yourself — e.g. one that says "yes, thread-safe, because Python lists have an internal lock per object," which sounds right but misattributes the mechanism.)

### 4. Grade both against your rubric — write it like a real reviewer would
```markdown
## Q1 — Candidate A (flawed)
Grade: 2/5
- ✅ [2 pts] Says "thread-safe" — correct conclusion.
- ❌ [0/2 pts] Attributes it to "an internal lock per list object" — this is WRONG. CPython
  lists have no per-object lock; the guarantee comes from the GIL serializing bytecode
  execution. A reader trusting this explanation would misunderstand *why* it's safe and could
  wrongly assume other operations (e.g. `+=` on a shared counter) are equally safe, which they
  are not for compound statements.
- ❌ [0/1 pt] Doesn't mention this is CPython-specific (fails under free-threaded builds/PyPy).
```
The "why this matters" sentence is the actual value an SME adds — not just marking wrong, but explaining the *consequence* of trusting the wrong answer.

### 5. Repeat for all 5 questions, then summarize
```markdown
| Question | Candidate A grade | Candidate B grade | Most common flaw type |
|---|---|---|---|
| Q1 | 2/5 | 5/5 | mechanism misattribution |
```

## ✅ Deliverable
5 questions + reference answers + rubrics, both candidate answers per question, full graded reviews for all 10, and the summary table.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
For the coding/agent domain specifically: [`10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) and [`16_evals`](../../16_evals/README.md) show how this exact skill turns into gradable training signal · [RL Env / Task Author](../12_rl-environment-task-author-contract/project.md) is the natural next step up.
