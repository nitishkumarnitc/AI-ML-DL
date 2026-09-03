# 11 · Sample project — Agent Evaluation & Data-Pipeline Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- compares TWO judges against human labels on 20 transcripts, reporting raw agreement AND Cohen's kappa (the naive judge's kappa is ~0.47 despite 75%+ raw agreement -- barely better than chance). `--report-file` exports a markdown comparison. See [`project/`](project/) for the full source.

## 🎯 What you'll build
An **LLM-as-judge eval harness** for an agent's answers, validated against your own human labels on the same examples — proving the judge is trustworthy before you rely on it at scale.

## 🧠 Why this mirrors the real job
- "Design eval suites... LLM-as-judge, benchmarks; guard against contamination/saturation" → you build the judge, then interrogate whether it agrees with a human.
- "Turn agent runs into clean, gradable data and dashboards teams trust" → the deliverable is a trust number (agreement rate), not just judge scores.

## 🧰 Prerequisites
- Python, an LLM API (for the judge) — reuse the agent from [Agentic AI Engineer's project](../04_agentic-ai-engineer/project.md) or any Q&A function.
- ~4–5 hours.

## 🧰 Tools, libraries & skills used here
- **LLM-as-judge methodology**: an automated grader compared directly against human labels on the *same* transcripts — the only way to know whether an automated judge can be trusted before pointing it at 10,000 unlabeled transcripts.
- **A deliberately flawed judge** (biased toward confident-sounding phrasing) — this mirrors a real, widely-documented failure mode of LLM judges, and the harness is built to catch it rather than assume the judge is right.
- **Agreement-rate analysis and a dashboard-style summary** (`Counter`-based grade distribution) — the concrete artifacts an eval engineer hands to a team before they ship a new grading pipeline.
- **What a real eval pipeline adds on top**: a real LLM as the judge (with a carefully engineered rubric prompt), eval/observability platforms (**Braintrust**, **LangSmith**, **Arize Phoenix**, **W&B Weave**) to store and version large batches of graded transcripts, statistical agreement measures beyond raw percentage (Cohen's kappa), and a human-labeling tool (**Label Studio**) for collecting the ground truth at scale.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| re (stdlib) | built in | not used for logic here, kept for extensibility of the judge's text checks |
| collections.Counter (stdlib) | built in | the grade-distribution dashboard summary |

## 🪜 Step-by-step

### 1. Generate 20 agent transcripts
```python
tasks = [
    "What was total revenue across Q1 and Q2?",
    "Summarize this email in one sentence: ...",
    # ... 20 varied tasks
]
transcripts = [{"task": t, "answer": run_agent(t)} for t in tasks]
```

### 2. Human-label a subset first — before building the judge
```python
# You grade these 20 yourself: correct / partially correct / wrong, plus a one-line reason.
human_labels = [
    {"task": t["task"], "answer": t["answer"], "human_grade": "correct", "reason": "..."}
    for t in transcripts
]
```
Do this step honestly and *before* looking at what a judge would say — otherwise you'll unconsciously anchor to the judge.

### 3. Build the LLM-as-judge
```python
JUDGE_PROMPT = """You are grading an AI agent's answer to a task.
Task: {task}
Agent's answer: {answer}

Grade as exactly one of: correct, partially_correct, wrong.
Then give a one-sentence reason. Respond as JSON: {{"grade": "...", "reason": "..."}}"""

import json

def judge(task, answer):
    raw = call_llm(JUDGE_PROMPT.format(task=task, answer=answer))
    return json.loads(raw)

judged = [{"task": t["task"], "answer": t["answer"], **judge(t["task"], t["answer"])} for t in transcripts]
```

### 4. Measure judge-vs-human agreement
```python
def agreement_rate(human_labels, judged):
    matches = sum(
        1 for h, j in zip(human_labels, judged)
        if h["human_grade"] == j["grade"]
    )
    return matches / len(human_labels)

rate = agreement_rate(human_labels, judged)
print(f"judge/human agreement: {rate:.0%}")
```
Also look at the *disagreements* specifically — is the judge systematically too lenient, too harsh, or fooled by confident-sounding wrong answers (a very common LLM-judge failure mode)?

### 5. Build the dashboard-style summary
```python
def summarize(judged):
    from collections import Counter
    counts = Counter(j["grade"] for j in judged)
    total = len(judged)
    return {grade: f"{n}/{total} ({n/total:.0%})" for grade, n in counts.items()}

print(summarize(judged))
```

## ✅ Deliverable
- `human_labels` and `judged` side by side, agreement rate, and a short list of the disagreement cases with your read on *why* the judge got it wrong.
- The summary dashboard table (grade distribution across the 20 transcripts).
- One paragraph: would you trust this judge to run unsupervised on 10,000 transcripts? What agreement rate would make you comfortable, and what's the plan if it's not there yet (more examples in the judge prompt? a stricter rubric? a second judge for disagreement cases?).

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`16_evals`](../../16_evals/README.md) — the core (LLM-as-judge, offline/online) · [`10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) Lessons [4](../../10_rl-environments-and-infra/04-task-generation-and-data-pipelines.md), [5](../../10_rl-environments-and-infra/05-designing-rigorous-graders.md), [6](../../10_rl-environments-and-infra/06-running-frontier-models-and-failure-analysis.md).
