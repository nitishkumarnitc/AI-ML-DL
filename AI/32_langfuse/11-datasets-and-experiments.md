# 11 · Datasets and Experiments

> ← [`10-scores-and-user-feedback.md`](10-scores-and-user-feedback.md) · **Next:** [`12-prompt-management.md`](12-prompt-management.md) →

---

Scores tell you whether *this* answer was good. Experiments tell you whether **the new version is better than the old one** — which is the question you cannot answer by eyeballing a few examples, and the one that decides whether you should ship.

The problem, restated from [`../30_langsmith/14-evaluation-datasets-and-annotation.md`](../30_langsmith/14-evaluation-datasets-and-annotation.md): a change can **improve some cases and break others**, and there is no compiler to tell you. You edit a prompt, test the three examples in your head, all three improve, you ship — with no idea what happened to the other 300.

---

## 1. Create a dataset

```python
from langfuse import get_client

langfuse = get_client()

langfuse.create_dataset(
    name="hr-policy-qa",
    description="Golden Q&A for the HR policy chatbot",
)

langfuse.create_dataset_item(
    dataset_name="hr-policy-qa",
    input={"question": "How many casual leaves do I get per year?"},
    expected_output={"answer": "12 casual leaves per calendar year."},
)

langfuse.create_dataset_item(
    dataset_name="hr-policy-qa",
    input={"question": "What is the notice period for a senior engineer?"},
    expected_output={"answer": "90 days."},
)

# ⭐ The most important item in the set.
langfuse.create_dataset_item(
    dataset_name="hr-policy-qa",
    input={"question": "Can I take unlimited leave whenever I want?"},
    expected_output={"answer": "REFUSE"},
    metadata={"case": "unanswerable_from_corpus"},
)
```

> **That third item is the one most evaluation sets omit, and it is the one that catches Story C.**
>
> Almost every golden set consists of questions *with answers*, which measures **recall** and never measures **restraint**. A RAG system's most dangerous failure is answering confidently when it should have declined — that is exactly what told the employee there was no leave policy. So the set must contain questions the corpus cannot answer, whose expected output is a refusal. **Nothing else tests grounding.**

### Grow the dataset from production

The highest-value source of items is your own failures. From lesson 10: a trace with a thumbs-down already contains the exact input, and the UI supports promoting traces to dataset items.

```
production trace that got it wrong
      │  add to dataset, correct the expected output
      ▼
dataset item
      │
      ▼
every future experiment is tested against it
      │
      ▼
that specific failure can never silently return
```

**Users report a bug once; it stays fixed.** That is how an LLM application becomes reliable over time — not through better prompts in the abstract, but through an accumulating library of real failures that every change is re-checked against. And the dataset doesn't need to be big to start: **ten real failures beats a hundred synthetic questions**, because the ten are things that actually happened.

---

## 2. Run an experiment

```python
result = langfuse.run_experiment(
    name="rag-v3-stricter-prompt",
    description="Tighten grounding instruction; require citations",
    data=langfuse.get_dataset("hr-policy-qa"),
    task=my_task,
    evaluators=[correct_refusal, has_citation, faithfulness],
    run_evaluators=[average_faithfulness],
    max_concurrency=4,
    metadata={"prompt_version": "v3", "git_sha": os.getenv("GIT_SHA", "dev")},
    run_name="rag-v3",
)
```

`data` takes either a LangFuse dataset or a local list — useful for a quick local check before you commit items.

---

## 3. The task function

```python
def my_task(*, item, **kwargs):
    # item carries input, expectedOutput, metadata
    return rag_pipeline(item.input["question"])
```

Keyword-only, and **accept `**kwargs`** — it keeps your task working when the SDK passes additional arguments in a later version. Cheap insurance against a breaking upgrade.

The task is your application. Whatever it returns is what the evaluators judge, so return the thing you actually want scored — not a wrapper object.

---

## 4. Evaluators

### Item-level — one per dataset item

```python
from langfuse import Evaluation

def correct_refusal(*, input, output, expected_output, metadata, **kwargs):
    should_refuse = expected_output["answer"] == "REFUSE"
    said_dunno = any(p in output.lower() for p in
                     ("i don't know", "i do not know", "not in the provided context"))
    return Evaluation(
        name="correct_refusal",
        value=1.0 if said_dunno == should_refuse else 0.0,
        comment=f"expected_refusal={should_refuse}, refused={said_dunno}",
    )


def has_citation(*, output, **kwargs):
    return Evaluation(name="has_citation", value=float("[" in output))
```

### Run-level — once over all results

```python
def average_faithfulness(*, item_results, **kwargs):
    vals = [r.evaluations["faithfulness"] for r in item_results
            if "faithfulness" in r.evaluations]
    return Evaluation(name="avg_faithfulness", value=sum(vals) / len(vals) if vals else 0.0)
```

| | Receives | Returns |
|---|---|---|
| **`evaluators`** | One item's `input`, `output`, `expected_output`, `metadata` | An `Evaluation` per item |
| **`run_evaluators`** | `item_results` — all outcomes | An `Evaluation` for the run |

> **Run-level evaluators are for the metrics that only exist in aggregate**: mean score, pass rate, worst-case, the fraction of items above a threshold. An item-level evaluator cannot compute "90% of items passed" because it only ever sees one.
>
> **Note the exact `Evaluation` import and field names against the [SDK reference](https://python.reference.langfuse.com/langfuse) for your installed version.** The shape above is from the current docs; this is the sort of surface that has moved across major versions, and I would rather say so than have you debug a name.

### The LLM judge, when you actually need one

```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class Judgement(BaseModel):
    score: int = Field(ge=0, le=1, description="1 if every claim is supported, else 0")
    reasoning: str

judge = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Judgement)

def faithfulness(*, input, output, expected_output, **kwargs):
    v = judge.invoke(
        "Grade this RAG answer for FAITHFULNESS. Score 1 only if every claim "
        "is supported by the reference.\n"
        f"Question: {input['question']}\nReference: {expected_output['answer']}\n"
        f"Answer: {output}"
    )
    return Evaluation(name="faithfulness", value=float(v.score), comment=v.reasoning)
```

**Temperature 0 and structured output**, or your evaluation is itself non-deterministic and you have moved the problem rather than solved it. And **always return the reasoning** — when a score is 0, the `comment` is what tells you why, and without it you are back to guessing.

But first: most checks don't need a judge. Citation presence, JSON validity, length, refusal detection, schema conformance — all deterministic, free and instant. Reach for code first (lesson 10 §5).

---

## 5. Reading the results

Results are written back as **scores on traces**, and when the data came from a LangFuse dataset the run appears as a **dataset run** in the UI, comparable side by side with previous runs.

> **The per-item comparison is where the real information is, and the aggregate can actively mislead you.**
>
> ```
> Experiment            avg_faithfulness    items regressed
> rag-v2 (incumbent)         0.78                  —
> rag-v3 (candidate)         0.81            ⚠️  3 previously-passing
> ```
>
> An aggregate that improved 0.78 → 0.81 **while three previously-passing items now fail** is a bad trade wearing a good number. That is "improve some cases but break others" made visible — and it is invisible in the mean. Always look at the per-item diff before shipping on an aggregate.

---

## 6. ⭐ Gate CI on it

The point of all of this.

```python
# tests/test_rag_quality.py
import os
from langfuse import get_client

def test_no_quality_regression():
    langfuse = get_client()
    result = langfuse.run_experiment(
        name="ci-regression",
        data=langfuse.get_dataset("hr-policy-qa"),
        task=my_task,
        evaluators=[correct_refusal, has_citation, faithfulness],
        metadata={"git_sha": os.getenv("GIT_SHA", "dev")},
    )
    langfuse.flush()

    scores = aggregate(result)          # per your result shape

    # refusals: ZERO tolerance — answering an unanswerable question is a safety failure
    assert scores["correct_refusal"] >= 1.0, "a refusal case regressed"

    # faithfulness: fractional bar, because judge scores are noisy
    assert scores["faithfulness"] >= 0.90, "faithfulness dropped below 0.90"
```

**Note the asymmetry in those two thresholds — it is deliberate.** Refusals are held at **1.0** so a single regression fails the build, because answering a question the corpus cannot support is the Story C failure and it is a safety issue. Faithfulness gets a fractional bar because LLM-judge scores are genuinely noisy and a hard 1.0 would fail the build on evaluator variance.

> **Match the strictness of the gate to the cost of the failure**, not to the convenience of the number. A gate that fails spuriously gets disabled within a month, and then you have neither the gate nor the honesty of admitting you removed it.

Same discipline as the release gate in [`../28_ai-system-design-by-industry/11_hr_recruitment_matching/`](../28_ai-system-design-by-industry/11_hr_recruitment_matching/): **a metric that is not a gate is not a requirement.** A fairness or quality number on a dashboard loses every argument against a quality win that has a champion.

For pipeline shape see [`../../Shared/03_llmops/04-cicd-with-eval-gates.md`](../../Shared/03_llmops/04-cicd-with-eval-gates.md); for choosing the metrics, [`../16_evals/`](../16_evals/).

---

## 7. Offline and online

| | When | Purpose |
|---|---|---|
| **Offline** (this lesson) | Pre-deploy, fixed dataset | **Regression gate.** The only mechanism that catches a problem *before* users see it |
| **Online** (lesson 10) | Continuously, live traffic | Drift detection on real inputs you never anticipated |

Both matter and neither substitutes. Offline is the gate; online is the smoke detector. Only offline runs before the deploy.

---

## Recap

- `create_dataset` · `create_dataset_item` · `get_dataset` · **`run_experiment`**.
- **Include unanswerable questions whose expected output is a refusal.** Otherwise you measure recall and never restraint — and restraint is what Story C failed.
- **Grow the dataset from production failures.** Ten real ones beat a hundred synthetic.
- Task: `def task(*, item, **kwargs)` — accept `**kwargs` for forward compatibility.
- **`evaluators`** run per item; **`run_evaluators`** run over `item_results` for aggregate-only metrics.
- Judges: **temperature 0, structured output, always return reasoning**. But deterministic code first.
- **The per-item diff matters more than the aggregate** — 0.78→0.81 with three regressions is a bad change.
- **Gate CI on it**, with strictness matched to the cost of failure: refusals at 1.0, noisy judge metrics fractional.
- Verify `Evaluation` and result field names against the SDK reference for your version.

---

## Self-check

1. Why is "I tested my new prompt on five examples and all five improved" not evidence?
2. Which dataset item type do most sets omit, and which failure does its absence let through?
3. Aggregate faithfulness rose and you roll back anyway. What did you see?
4. Give three checks you should write in Python rather than paying a judge for.
5. Why hold refusal accuracy at 1.0 but faithfulness at 0.90?

---

**Next:** [`12-prompt-management.md`](12-prompt-management.md) →
