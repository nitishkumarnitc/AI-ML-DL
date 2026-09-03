# 14 · Evaluation, Datasets and Annotation

> ← [`13-monitoring-and-alerting.md`](13-monitoring-and-alerting.md) · **Next:** [`15-prompt-experimentation.md`](15-prompt-experimentation.md) →

---

Lesson 13 ended on the gap: every monitoring metric is mechanical, so a confidently-wrong system looks perfectly healthy. Evaluation closes that gap.

> **Scope note.** The video covers evaluation as an overview — it shows where the features live in the UI and explicitly defers the depth to a future course. This lesson keeps the video's framing and definitions, and adds working code, because "there is an Evaluators tab" isn't something you can act on. The SDK material below is marked ⭐. If you want evaluation in real depth, [`AI/16_evals/`](../16_evals/) in this repo is sixteen lessons on exactly that, and the two are complementary: that folder is the *theory and metrics*, this lesson is *the platform mechanics*.

---

## The problem evaluation solves

From the video's slide:

> **LLM behaviour can be unpredictable.** A small change in prompts, models or retrieval logic can improve some cases but **break others**. Evaluation provides an **objective, repeatable** way to track performance over time, ensuring that new versions are actually better and **preventing regressions**.

The sentence that matters is *"improve some cases but break others."* This is the core difficulty and it has no analogue in ordinary software.

Change a prompt. Test it on the three examples you have in your head. All three improved. Ship it. **You have no idea what happened to the other 300 cases** — and unlike a code change, there is no type system, no compiler, no unit test that fails. The improvement and the regression are both invisible.

You changed nothing about the user's input. The user asks the same question. The output is materially different. **How do you know the new version is better than the last?** Eyeballing a few examples in a chat window is not evidence.

---

## What LangSmith provides

> **Evaluation in LangSmith** helps you systematically measure the quality of your LLM outputs. You can run tests against **gold-standard datasets** and apply **custom evaluation metrics** such as faithfulness, relevance and completeness. LangSmith supports multiple approaches: **automated scoring with LLM-as-a-judge**, **semantic similarity checks**, and even **custom Python evaluators**.

Both **offline** and **online**.

### The three approaches

| Approach | How | Good for | Weak at |
|---|---|---|---|
| **LLM-as-a-judge** | A model scores the output against a rubric | Open-ended quality: helpfulness, tone, faithfulness | Costs tokens; the judge has its own biases; needs its own validation |
| **Semantic similarity** | Embed output and reference, compare | "Roughly the right content" | Rewards paraphrase over correctness — a fluent wrong answer can score well |
| **Custom Python** | Any function you write | Anything deterministic: JSON validity, schema conformance, forbidden strings, citation presence, numeric tolerance | Only checks what you thought to check |

> **Order of preference, which the video doesn't state and which saves real money:** reach for **custom Python first**. It is free, instant, and perfectly reliable for everything mechanically checkable. A large fraction of what teams reach for an LLM judge to assess — is the JSON parseable, does it cite a source, is it under the length limit, did it refuse when it should have — is a five-line assertion. Save the judge for what genuinely needs judgement.

### Offline vs online

| | When | Purpose |
|---|---|---|
| **Offline** | Before deploy, against a fixed dataset | **Regression gate.** The only mechanism that catches a problem before users see it |
| **Online** | Continuously, on live traffic | Catch quality drift in production, on real inputs you never anticipated |

Both matter. Offline is the gate; online is the smoke detector. In the UI, online evaluators are attached per project: **Tracing Projects → project → Evaluators**.

### Prebuilt evaluators

The UI offers ready-made ones, including:

- **Hallucination** — is the answer grounded in the retrieved context?
- **Conciseness** — is it unnecessarily verbose?
- **Code checking** — does generated code hold up?

…plus your own custom definitions.

---

## Datasets

Evaluation needs something to evaluate **against**. That is a dataset: input/expected-output pairs.

> **LangSmith provides tools to build datasets for evaluation and fine-tuning.** You can do **manual annotation** and store **dataset versions** for reuse across projects.

Sources: a public benchmark, or — usually better — one you build for **your** use case.

### The killer feature: promote a trace to a dataset row

**Any trace → `Add to Dataset`.** The trace becomes a row: its input becomes the dataset input, its output the starting point for the expected output (which you then correct).

This is the payoff of the "unified platform" claim from lesson 02, and it's worth stating as a loop because it's the single most valuable workflow in the product:

```
production traffic
      │
      ▼
  a trace where the app got it WRONG
      │  Add to Dataset
      ▼
  dataset row  (input + the CORRECT expected output)
      │
      ▼
  every future version is tested against it
      │
      ▼
  that specific failure can never silently return
```

**Every bug becomes a permanent regression test, in two clicks.** That is the mechanism by which an LLM application gets reliable over time. Not better prompts in the abstract — an accumulating library of real failures that the system is re-checked against forever.

It is the LLM equivalent of "write a failing test, then fix it", and the reason it is so valuable here is that LLM bugs are *hard to reproduce by hand*. The trace has the exact input already captured.

### Annotation

Label outputs — was this right or wrong, and how wrong? LangSmith provides **annotation queues**: a work list where a human sees each output and scores it. Annotations are stored with the dataset, versioned, and reusable across every project in your account.

Worked example from the video: you are building a customer chatbot. Along the way you accumulate a dataset of **the most common questions and their expected answers**, and that dataset then tests **every future version** of the application.

### Versioning

Datasets are versioned. This matters more than it sounds: if the dataset changes, scores from before and after are not comparable. Pinning a version is what makes "we improved from 0.71 to 0.83" an actual claim rather than a coincidence of the test set changing.

---

## ⭐ Running an evaluation in code

*Added — the working mechanics the video defers.*

### Create a dataset

```python
from langsmith import Client

client = Client()

dataset = client.create_dataset(
    dataset_name="hr-policy-qa",
    description="Golden Q&A for the HR policy chatbot",
)

client.create_examples(
    dataset_id=dataset.id,
    examples=[
        {
            "inputs":  {"question": "How many casual leaves do I get per year?"},
            "outputs": {"answer": "12 casual leaves per calendar year."},
        },
        {
            "inputs":  {"question": "What is the notice period for a senior engineer?"},
            "outputs": {"answer": "90 days."},
        },
        {
            # A question the corpus cannot answer — the app MUST refuse.
            "inputs":  {"question": "Can I take unlimited leave whenever I want?"},
            "outputs": {"answer": "REFUSE"},
        },
    ],
)
```

> **That third row is the most important one in the dataset.** It is Story C, encoded as a test. Most evaluation sets only contain questions with answers, which measures recall and never measures *restraint*. A RAG system's most dangerous failure is answering confidently when it should have said "I don't know" — so **your dataset must contain unanswerable questions whose expected output is a refusal.** Nothing else tests grounding.

### Write evaluators

```python
# --- deterministic: cheap, instant, perfectly reliable ---
def refuses_when_it_should(outputs: dict, reference_outputs: dict) -> dict:
    should_refuse = reference_outputs["answer"] == "REFUSE"
    said_dunno = any(
        p in outputs["answer"].lower()
        for p in ("i don't know", "i do not know", "not in the provided context")
    )
    return {"key": "correct_refusal", "score": int(said_dunno == should_refuse)}


def cites_a_source(outputs: dict) -> dict:
    return {"key": "has_citation", "score": int("[" in outputs["answer"])}


# --- LLM-as-a-judge: for what genuinely needs judgement ---
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class Judgement(BaseModel):
    score:     int = Field(ge=0, le=1, description="1 if faithful to context, else 0")
    reasoning: str

judge = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Judgement)

def faithfulness(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    verdict = judge.invoke(
        "You are grading a RAG answer for FAITHFULNESS.\n"
        "Score 1 only if every claim in the answer is supported by the reference.\n"
        f"Question: {inputs['question']}\n"
        f"Reference: {reference_outputs['answer']}\n"
        f"Answer: {outputs['answer']}"
    )
    return {"key": "faithfulness", "score": verdict.score, "comment": verdict.reasoning}
```

Two details that matter in practice: give the judge **temperature 0** and **structured output**, or your evaluation is itself non-deterministic and you have moved the problem rather than solved it. And return a `comment` — when a score is 0, the reasoning is what tells you *why*, and without it you're back to guessing.

### Run it

```python
from langsmith import evaluate

def target(inputs: dict) -> dict:
    return {"answer": rag_chain.invoke(inputs["question"])}

results = evaluate(
    target,
    data="hr-policy-qa",
    evaluators=[refuses_when_it_should, cites_a_source, faithfulness],
    experiment_prefix="rag-v3-stricter-prompt",
    metadata={"prompt_version": "v3", "git_sha": os.getenv("GIT_SHA", "dev")},
    max_concurrency=4,
)
```

Every run appears in LangSmith as an **experiment**, side-by-side comparable with previous experiments per example. The per-example diff is where the real information is: an aggregate score that went from 0.78 to 0.81 while **three previously-passing examples now fail** is a bad trade you would never see in the average. That is "improve some cases but break others", made visible at last.

### Gate CI on it

```python
# tests/test_rag_quality.py
def test_no_quality_regression():
    results = evaluate(target, data="hr-policy-qa",
                       evaluators=[refuses_when_it_should, faithfulness])
    df = results.to_pandas()
    assert df["feedback.correct_refusal"].mean() >= 1.0, "a refusal case regressed"
    assert df["feedback.faithfulness"].mean()   >= 0.90, "faithfulness dropped below 0.90"
```

**This is the point of the whole lesson.** A prompt change that breaks grounding now fails CI, exactly like a type error. Story C cannot reach production twice.

Note the asymmetry in those two thresholds, which is deliberate: refusals are held at **1.0** (a single regression fails the build) because answering an unanswerable question is a safety failure, while faithfulness is a fractional bar because judge scores are noisy. **Match the strictness of the gate to the cost of the failure**, not to the convenience of the number.

See [`Shared/03_llmops/04-cicd-with-eval-gates.md`](../../Shared/03_llmops/04-cicd-with-eval-gates.md) for the pipeline shape, and [`AI/16_evals/`](../16_evals/) for choosing the metrics.

---

## Recap
 
- Evaluation exists because a change can **improve some cases and break others**, invisibly.
- Three approaches: **LLM-as-a-judge**, **semantic similarity**, **custom Python**. Reach for Python first — most checks are mechanical and free.
- **Offline** = pre-deploy regression gate (the only one that catches problems before users). **Online** = live drift detection.
- Prebuilt evaluators: hallucination, conciseness, code checking.
- **`Add to Dataset` turns any trace into a permanent regression test in two clicks.** This is the mechanism by which LLM apps get reliable.
- Datasets are **versioned** — pin the version or your score comparisons are meaningless.
- **Include unanswerable questions whose expected answer is a refusal.** Nothing else tests grounding.
- Judges: temperature 0, structured output, and always return the reasoning.
- The **per-example diff** matters more than the aggregate.
- **Gate CI on evaluation**, with strictness matched to the cost of the failure.

---

## Self-check

1. Why is "I tested my new prompt on five examples and all five improved" not evidence?
2. Give three checks you should write as Python rather than paying an LLM judge for.
3. What single dataset row type do most evaluation sets omit, and which failure does its absence let through?
4. Aggregate faithfulness rose 0.78 → 0.81 and you roll back anyway. What did you see?
5. Why hold refusal accuracy at 1.0 but faithfulness at 0.90?

---

**Next:** [`15-prompt-experimentation.md`](15-prompt-experimentation.md) →
