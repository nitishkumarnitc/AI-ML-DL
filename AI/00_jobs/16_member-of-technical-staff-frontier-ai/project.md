# 16 · Sample project — Member of Technical Staff, Frontier AI

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- clusters raw ops-signal notes into candidate hypothesis categories (ops-to-research translation), then runs FIVE research claims through a signal-judgment quality gate, printing a verdict + specific falsifiable next step for every claim that isn't ready to externalize. `--report-file` exports the full report as markdown. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Two linked deliverables that are the actual day-to-day of this role: (1) turning a pile of messy, free-text ops notes into candidate research categories by pattern, and (2) running five "here's a result" claims through a signal-trustworthiness checklist that outputs a hard verdict — **STRONG** (safe to report/ship against) or **BLOCKED** (not ready) — with the exact, specific reason and next step, never a vague "needs more work."

## 🧠 Why this mirrors the real job
- "Translate ambiguous, real-world behavior into structured evaluation frameworks and new data categories" → the note-clustering step is exactly this, made concrete: raw complaints in, a candidate category with a count out.
- "Strong judgment around research signal quality and when work is (or is not) ready to be externalized" → the quality-gate checklist (sample size, annotator agreement, contamination, reproducibility) is the actual mechanism, not a vibe.
- "Act as a quality gate: block claims, pause work, or force scope changes" → every BLOCKED verdict comes with a specific, falsifiable next step, per [Lesson 10 §3](../../10_rl-environments-and-infra/10-ops-to-research-translation-and-signal-judgment.md#3-being-the-quality-gate--what-blocking-a-claim-actually-looks-like) — never "needs more work" with no path forward.

## 🧰 Prerequisites
- No AI/ML background required; comfort with basic statistics reasoning (what a sample size or agreement rate implies) helps.
- ~3–4 hours.

## 🧰 Tools, libraries & skills used here
- **Pattern-then-hypothesis clustering**: a simple keyword-tag pass over free-text notes, standing in for the real first step of ops-to-research translation — noticing what recurs before reaching for any tooling.
- **A four-check signal-trustworthiness gate**: sample size vs. a pre-agreed minimum, annotator/judge agreement vs. threshold, contamination risk, and reproduction on a fresh sample — the same four checks from [Lesson 10 §2](../../10_rl-environments-and-infra/10-ops-to-research-translation-and-signal-judgment.md#2-research-signal-judgment-when-is-a-result-trustworthy).
- **Falsifiable next steps**: every failing check maps to one specific corrective action, not a generic "investigate further."
- **What a real role adds on top**: an actual pipeline of production incident reports / contractor disagreement logs instead of hand-authored notes, a real annotator-agreement measurement (e.g. Cohen's kappa) instead of a stated rate, and a stakeholder-facing writeup translating the verdicts into investment decisions.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| (none) | — | pure stdlib — keyword matching + rule-based checks, no imports needed |

## 🪜 Step-by-step

### 1. Collect the raw ops signal (or, here, read the sample notes)
```python
OPS_NOTES = [
    "agent gave a confident wrong total after combining 3 spreadsheet formulas",
    "agent lost track of the running total across several linked cells",
    "agent refused to answer a simple one-step lookup, seemed overly cautious",
    # ...
]
```

### 2. Tag each note against candidate category keywords and count
```python
hits_per_category = {}
for note in OPS_NOTES:
    for category in tag_note(note):
        hits_per_category[category] = hits_per_category.get(category, 0) + 1
```
A category with multiple independent hits (from different notes, different wording) is a candidate hypothesis worth structuring into a real eval category. A category with one hit is an anecdote, not a pattern yet.

### 3. For each research claim, run the four-check gate
```python
def evaluate_signal(report):
    checks = []
    checks.append(check_sample_size(report))
    checks.append(check_agreement(report))
    checks.append(check_contamination(report))
    checks.append(check_reproducibility(report))
    verdict = "STRONG" if all(c.passed for c in checks) else "BLOCKED"
    return verdict, checks
```

### 4. For a BLOCKED verdict, always attach the specific next step
```markdown
## Claim: "Agent fails multi-hop spreadsheet tasks 60% of the time"
Verdict: BLOCKED
- [FAIL] sample_size: 8 < required minimum 30
- [PASS] annotator_agreement: 95% >= threshold 85%
- [PASS] contamination: checked, no leakage risk found
- [FAIL] reproducibility: not yet tested on a fresh held-out sample
Next steps: (1) collect samples up to the minimum of 30 before repeating this
claim; (2) re-run on a fresh, held-out sample before trusting the number.
```

### 5. Summarize across all claims
```markdown
| Claim | Verdict | Failing checks |
|---|---|---|
| Multi-hop spreadsheet 60% failure | BLOCKED | sample_size, reproducibility |
```

## ✅ Deliverable
The ops-note category breakdown (pattern step), all five claims run through the four-check gate with full per-check detail, the specific next step attached to every BLOCKED verdict, and the summary table.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`10_rl-environments-and-infra` Lesson 10](../../10_rl-environments-and-infra/10-ops-to-research-translation-and-signal-judgment.md) is the full lesson behind this project · Lessons [4](../../10_rl-environments-and-infra/04-task-generation-and-data-pipelines.md) and [6](../../10_rl-environments-and-infra/06-running-frontier-models-and-failure-analysis.md) are the single-task-level version of the same skills.
