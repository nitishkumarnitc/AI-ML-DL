# 15 · Sample project — Agentic Coding Evaluator (contract)

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- actually EXECUTES two candidate "agent-generated" solutions per task across 3 coding tasks, catches the exact runtime failure each flawed candidate produces, grades both against a reusable rubric, and prints a reviewer-style comparison. `--report-file` exports the full report as markdown. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Three small coding tasks, each with a spec (goal + constraints + acceptance criteria), a normal test case, and a deliberately-added **edge-case** test — then two candidate solutions per task (one flawed, one correct) that get **actually run**, not just eyeballed, and graded against the rubric from [`23_ai-coding-agents-and-code-eval` Lesson 2](../../23_ai-coding-agents-and-code-eval/02-evaluating-ai-generated-code.md).

## 🧠 Why this mirrors the real job
- "Evaluate AI-generated code, identifying errors, hallucinations, and opportunities for improvement" → each flawed candidate encodes a real hallucination pattern (invented API, reversed logic, missed edge case) that the harness catches by **execution**, not inspection.
- "Compare outputs across multiple AI systems and document findings" → the summary table compares both candidates across all three tasks on identical criteria.
- "Draft best practices... emphasizing clarity in communication and reproducibility" → the reviewer notes follow the 4-part finding template from [Lesson 3](../../23_ai-coding-agents-and-code-eval/03-agentic-coding-review-workflow.md): what was produced, why it's wrong, how it fails, and the reproduction.

## 🧰 Prerequisites
- Comfortable reading/writing Python; no AI/ML background needed.
- ~3–4 hours.

## 🧰 Tools, libraries & skills used here
- **Execution-based grading**: candidates are real Python functions, actually called with real inputs — the harness doesn't guess whether code is correct, it runs it and observes.
- **Hallucination-pattern tagging**: each flawed candidate is built around one of the four patterns from [Lesson 2](../../23_ai-coding-agents-and-code-eval/02-evaluating-ai-generated-code.md#22-the-four-patterns-to-hunt-for) — invented API, wrong signature, plausible-but-wrong logic, or a missed edge case — and the report names which one fired.
- **Edge-case-first testing**: every task's rubric includes at least one test a "happy path only" solution would fail — the same discipline that catches a coding agent that only tested the obvious case.
- **What a real gig adds on top**: an actual coding agent (Claude Code, Copilot, Cursor, Codex CLI, Gemini CLI) generating the candidates live instead of hand-authored strings, and a platform (Mercor, Turing, Outlier, Handshake AI) to submit graded comparisons at scale.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| (none) | — | pure stdlib — `exec` to run candidate source, nothing external |

## 🪜 Step-by-step

### 1. Write the task spec — goal, constraint, acceptance criteria
```markdown
Task: has_duplicates(items) -> bool
Goal: Return True if the list contains any repeated value.
Acceptance: passes on an empty list, a list with no duplicates, AND a list with a duplicate.
```
That third case is the edge case a rushed agent (or a rushed candidate solution) tends to get backwards.

### 2. Write two candidate implementations — one flawed, one correct
```python
# Candidate A (flawed) — plausible-but-wrong logic, reads fine, fails the duplicate case
def has_duplicates(items):
    return len(items) == len(set(items))

# Candidate B (good)
def has_duplicates(items):
    return len(items) != len(set(items))
```

### 3. Run both against the normal case AND the edge case — actually execute them
```python
namespace = {}
exec(candidate_source, namespace)
fn = namespace["has_duplicates"]
result = fn(*test_args)          # really calls it; a real error surfaces here, not a guess
```

### 4. Grade against the rubric and name the failure precisely
```markdown
## Task 1 — Candidate A (flawed)
Grade: 1/3 tests passed
- ✅ empty list -> False
- ✅ no duplicates -> False
- ❌ [duplicate present] -> expected True, got False
Pattern: plausible-but-wrong logic (Lesson 2 pattern 3) — the comparison is backwards.
Reviewer note: a developer trusting this would ship a dedup-check that never fires,
silently allowing duplicate records through.
```

### 5. Repeat across tasks, then summarize
```markdown
| Task | Candidate A | Candidate B | Pattern (A) |
|---|---|---|---|
| has_duplicates | 1/3 | 3/3 | plausible-but-wrong logic |
```

## ✅ Deliverable
Three tasks with specs, both candidates actually executed against normal + edge-case tests, per-task graded reviews naming the exact hallucination pattern, and the summary comparison table.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`23_ai-coding-agents-and-code-eval`](../../23_ai-coding-agents-and-code-eval/README.md) is the full lesson set behind this project · [RL Env / Task Author](../12_rl-environment-task-author-contract/project.md) is the natural next step if you want to author formal graders instead of ad hoc comparisons.
