# 13 · Sample project — Prompt Engineer / AI Interaction Designer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- scores FOUR prompt variants (including a majority-vote ensemble) on a 20-example eval set, prints accuracy + a full confusion matrix per variant, and picks a winner. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Three prompt variants for one task, a 10-example eval set, and a measured winner — proving a prompt improvement with numbers instead of "this one feels better."

## 🧠 Why this mirrors the real job
- "Craft and iterate prompts... build prompt libraries and patterns" → you'll produce a small reusable library, not a one-off.
- "Pair with evals to measure prompt changes" → this repo's own "how to stand out" advice for this role is literally the project: pair every prompt improvement with an eval showing the lift.

## 🧰 Prerequisites
- Python, an LLM API.
- ~3–4 hours.

## 🧰 Tools, libraries & skills used here
- **Controlled prompt-variant comparison**: zero-shot, few-shot, and structured-reasoning "prompt styles" implemented as three separate classifiers, scored on the *same* held-out eval set — the only way to know a prompt change is actually an improvement.
- **Eval-first iteration**: the harness (`score`) is written before declaring a winner, and per-example results are inspected, not just the aggregate accuracy — aggregate numbers hide which *kind* of example a prompt style fails on.
- **A reusable prompt-library entry** as the output artifact — the actual shape prompt engineering work takes on a real team (a documented, versioned prompt with a measured accuracy attached).
- **What real prompt engineering adds on top**: actual LLM calls with real zero-shot/few-shot/chain-of-thought prompts, structured-output enforcement (JSON mode, Pydantic validation), and dedicated tooling (**promptfoo**, **PromptLayer**, **LangSmith**, **OpenAI Evals**) to run this exact comparison automatically across many more examples and prompt variants.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| (none) | — | pure functions over the eval set -- no imports needed beyond the built-ins |

## 🪜 Step-by-step

### 1. Pick one concrete, checkable task
Example: **classify support-ticket urgency** into `low` / `medium` / `high`. Checkable = you can write a right answer per example.

### 2. Build a 10-example eval set with ground truth
```python
EVAL_SET = [
    {"ticket": "App crashes on login for all users since this morning.", "expected": "high"},
    {"ticket": "Small typo in the settings page label.", "expected": "low"},
    {"ticket": "Export to CSV is slow for large accounts.", "expected": "medium"},
    # ... 10 total, cover ambiguous cases too, not just obvious ones
]
```

### 3. Write three prompt variants
```python
PROMPT_ZERO_SHOT = """Classify this support ticket's urgency as low, medium, or high.
Ticket: {ticket}
Urgency:"""

PROMPT_FEW_SHOT = """Classify ticket urgency as low, medium, or high.
Example: "Typo on homepage" -> low
Example: "Payments failing for 10% of users" -> high
Example: "Feature request: dark mode" -> low

Ticket: {ticket}
Urgency:"""

PROMPT_STRUCTURED_COT = """Classify this support ticket's urgency.
First, in one sentence, reason about scope (how many users?) and severity (data loss? workaround exists?).
Then output your final answer as JSON: {{"reasoning": "...", "urgency": "low|medium|high"}}

Ticket: {ticket}"""
```

### 4. Run all three against the eval set
```python
import json

def score_variant(prompt_template, parse_fn):
    correct = 0
    for item in EVAL_SET:
        raw = call_llm(prompt_template.format(ticket=item["ticket"]))
        predicted = parse_fn(raw)
        if predicted == item["expected"]:
            correct += 1
    return correct / len(EVAL_SET)

def parse_plain(raw):
    return raw.strip().lower()

def parse_json(raw):
    return json.loads(raw)["urgency"].lower()

results = {
    "zero_shot": score_variant(PROMPT_ZERO_SHOT, parse_plain),
    "few_shot": score_variant(PROMPT_FEW_SHOT, parse_plain),
    "structured_cot": score_variant(PROMPT_STRUCTURED_COT, parse_json),
}
print(results)
```

### 5. Look at *which* examples each variant got wrong
Accuracy alone hides the story. Tabulate per-example results across all three variants — often one variant is better on obvious cases but worse on ambiguous ones, which matters for the recommendation.

### 6. Pick a winner and justify it
Not just "highest accuracy" — factor in prompt length/cost (few-shot costs more tokens per call) and reliability of the output format (does structured JSON ever fail to parse?).

## ✅ Deliverable
- The three prompts + eval results table (accuracy per variant, plus per-example pass/fail).
- A short "prompt library" entry for the winner: the final prompt text, when to use it, and its measured accuracy — written so a teammate could reuse it without re-deriving anything.

## ⏱️ Time box
An afternoon.

## 🔁 Where to go deeper
[`01_prompt-engineering`](../../01_prompt-engineering/README.md) — the core · [`16_evals`](../../16_evals/README.md) — how to measure prompt changes rigorously · [`14_memory`](../../14_memory/README.md) · [`15_mcp`](../../15_mcp/README.md) — instructions/tool-description design, the same discipline applied to agents.
