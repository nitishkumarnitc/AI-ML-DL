# 04 · Evals are the deliverable

> ← [`03-discovery-and-scoping.md`](03-discovery-and-scoping.md) · **Index:** [`README.md`](README.md) · **Next:** [`05-prompt-and-context-engineering-in-the-field.md`](05-prompt-and-context-engineering-in-the-field.md) →
>
> **Methodology prerequisite:** [`../16_evals/`](../16_evals/README.md) covers the *how* — RAG triad, G-Eval, LLM-as-judge, DeepEval, contextual recall/precision. This file is the *field* layer: building an eval with someone else's data, someone else's experts, and someone else's definition of "good."

---

## 4.1 The claim

> **In an FDE engagement, the eval harness is the deliverable. The prototype is a by-product.**

That sounds like an exaggeration until you list what the eval actually buys you:

| It buys | Why that's worth more than the prototype |
|---|---|
| **A written definition of "good"** | Which does not exist anywhere in the customer's organisation, and which two of their stakeholders disagree about |
| **The disagreement, surfaced early** | Two experts labelling the same 20 cases will conflict. Finding that in week one is cheap; finding it at UAT is a crisis |
| **A number instead of a feeling** | Converts "this doesn't feel right" into "faithfulness dropped from 0.91 to 0.84 on the invoice segment" |
| **An honest accuracy conversation** | You cannot promise a number without a way to measure it. The eval is what makes your commitments credible |
| **A safe model-upgrade path** | When a new model ships, you re-run the suite in an hour instead of re-litigating quality for a fortnight |
| **The artifact that survives you** | The prototype gets rewritten. The golden set and rubric outlive three implementations and are the core of the handover |

And the reverse claim: **an engagement with a great prototype and no eval is a demo with a longer runway.** You have no way to know if it got worse, no way to defend the accuracy number, and nothing to hand over.

---

## 4.2 Do this first: measure human agreement

This is the highest-leverage single action available to an FDE in week one, and most people skip it.

### The move

Before you measure the model, take 20–30 real examples and have **three of the customer's experts label them independently.** Then measure how often they agree with each other.

### Why it changes everything

```
Scenario A — experts agree on 28/30 cases (93%)
  → the task is well-defined; a 90% model target is credible
  → disagreements are edge cases worth reading

Scenario B — experts agree on 21/30 cases (70%)
  → THE TASK IS NOT WELL DEFINED
  → a "95% accuracy" target is not merely hard, it is INCOHERENT —
    there is no single correct answer for 30% of inputs
  → the correct next move is NOT modelling. It is a definition workshop.
```

In scenario B, any model you build will be measured against whichever expert happens to review it, and it will fail. You will spend three months tuning against noise.

> **Say it in the room, in week one:** *"Before we set an accuracy target, I want to know what your own experts agree on. If they agree 93% of the time, 90% is a sensible target. If they agree 70% of the time, then '95% accurate' doesn't have a meaning yet and our first job is a definition workshop, not a model."*
>
> This is the sentence that establishes you as someone who has done this before. It also pre-empts the single most common way FDE engagements go bad: an accuracy target agreed casually in month one that turns out to be above the human ceiling.

### The arithmetic, done properly

Raw agreement overstates things, because some agreement happens by chance. Use **Cohen's kappa** for two raters, **Fleiss' kappa** for three or more.

```python
def cohens_kappa(a: list, b: list) -> float:
    """Agreement between two raters, corrected for chance."""
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n          # observed agreement
    labels = set(a) | set(b)
    pe = sum((a.count(l)/n) * (b.count(l)/n) for l in labels)   # chance agreement
    return (po - pe) / (1 - pe)

# Worked example: 3 experts, 30 claims, label = approve / review / deny
expert1 = ['approve']*18 + ['review']*8 + ['deny']*4
expert2 = ['approve']*16 + ['review']*9 + ['deny']*5   # (aligned per-item in reality)
# raw agreement 70%, kappa ≈ 0.52
```

Read kappa like this:

| κ | Reading | What you do |
|---|---|---|
| > 0.80 | Strong. Task is well defined | Set a model target near the human rate |
| 0.60–0.80 | Moderate. Usable, with known ambiguity | Target the agreed subset; route the ambiguous band to review |
| 0.40–0.60 | **Weak. The definition is the problem** | **Definition workshop before modelling.** Say so |
| < 0.40 | The task as stated isn't a task | Reshape the problem or qualify out ([03](03-discovery-and-scoping.md)) |

### The disagreement analysis is the real prize

Don't stop at the number. Pull the cases the experts disagreed on and read them together. Almost always you find **two or three recurring patterns**, and each one is a decision the customer has never made explicitly:

> *"You disagreed on 9 cases. Seven of them are the same thing: when the invoice total doesn't match the line items, Priya treats it as a data-entry error and approves, Sanjay treats it as a discrepancy and reviews. That's not a model problem — that's a policy you haven't written down. Which is it?"*

You have just delivered more value than a month of prompt tuning, and the customer will remember it. This is the *deliverable-is-the-insight* pattern from [01](01-what-the-role-actually-is.md) in its purest form.

---

## 4.3 Building the golden dataset

### Stratify — never hand-pick, never pure-random

Hand-picked examples measure your taste. Pure-random under-samples the hard cases that determine whether you ship.

```python
# Target: ~150 examples. Stratify along the dimensions that DRIVE difficulty,
# which you learned during discovery and shadowing.
STRATA = {
    # intent × data-completeness — the two dimensions that actually mattered
    ('status',    'note_answers'):       30,
    ('status',    'note_insufficient'):  25,   # ← 31% of real traffic. Do not skip
    ('reschedule','note_answers'):       15,
    ('approval',  'any'):                20,   # ← a WRITE action, different risk class
    ('complaint', 'any'):                15,   # ← must never be auto-drafted
    ('multi_intent','any'):              20,   # ← the demo never tested this
    ('unclear',   'any'):                15,
    ('adversarial','any'):               10,   # ← injection, prompt-fishing, abuse
}
```

Four rules that matter more than the sample size:

| Rule | Why |
|---|---|
| **Include the segment you'd rather exclude** | A set with no ambiguous cases proves nothing and hides your real accuracy |
| **Include adversarial cases from the start** | Users fish for numbers and confirmations. Prompt-level defences aren't enough — see [`../03_llm-security-and-guardrails/`](../03_llm-security-and-guardrails/README.md) |
| **Record the real distribution separately from the sample** | You'll oversample hard cases for signal, then re-weight to report a true production number. **Keep both, and label which is which in every report** |
| **Freeze a held-out slice** | ~20% you never look at while iterating, or you'll overfit to your own eval within three weeks |

### 150 is usually the right size

| Size | Verdict |
|---|---|
| 20–30 | Enough for inter-rater agreement, not for a claim about accuracy |
| **100–200** | **The sweet spot.** Labellable in a day or two of expert time; ±4–8pp resolution — enough to detect the differences that matter |
| 500+ | Better statistics, and expert labelling time becomes the constraint. Reserve for the final production gate |

The binding constraint is never compute — it's **how many hours of a busy expert you can get.** Budget that explicitly and treat it as the scarce resource it is: two focused hours with the right person beats a week of asynchronous labelling by the wrong one.

---

## 4.4 The rubric

A rubric the expert hasn't signed off is your opinion with formatting. Get it agreed in a working session, on real examples.

### Shape it as independent dimensions, not one score

A single 1–5 "quality" score is uninterpretable — it can't tell you *why* something regressed. Decompose:

```yaml
# rubric.yaml — service-advisor reply drafting
dimensions:
  factual_grounding:
    weight: BLOCKING          # any failure = the whole example fails
    question: "Does every fact (date, price, part, status) appear verbatim in the note?"
    pass: "All facts traceable to the source note"
    fail: "Any invented or inferred fact"
    why_blocking: "A wrong pickup date is a customer in a waiting room. No amount of
                   tone quality compensates."

  answers_the_question:
    weight: 3
    scale:
      3: "Directly answers what was asked"
      2: "Partially answers, or answers an adjacent question"
      1: "Does not address the question"

  honest_when_unknown:
    weight: BLOCKING
    question: "If the note cannot answer, does the draft say so instead of guessing?"
    why_blocking: "This is the behaviour that makes the system trustworthy at 74%
                   instead of dangerous at 74%."

  tone_appropriate:
    weight: 2
    scale: {3: "Sounds like this advisor", 2: "Generic but acceptable", 1: "Off"}

  length:
    weight: 1
    scale: {3: "2–3 sentences", 2: "Slightly long", 1: "Wall of text"}
```

### The design decision that matters: blocking dimensions

Most rubrics average everything. That's wrong when errors are **asymmetric**.

A draft with perfect tone, ideal length, and a fabricated pickup date is not "80% good." **It is a failure**, because the one thing it got wrong is the thing that puts a customer in a waiting room for a car that isn't ready.

So: factual grounding and honest-refusal are **blocking**. Fail either and the example fails, regardless of everything else. Tone and length are weighted contributors.

> This mirrors a pattern that recurs throughout [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md): **hard constraints are filters, not scores.** It shows up in the [e-commerce agent](../28_ai-system-design-by-industry/01_ecommerce_shopping_agent/) (budget is a filter, not a ranking weight), [real-estate search](../28_ai-system-design-by-industry/09_realestate_search_valuation/) (a stated budget can't be outvoted by similarity), [travel](../28_ai-system-design-by-industry/10_travel_planning_assistant/) (an infeasible itinerary isn't a worse itinerary — it isn't an itinerary), and [healthcare](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/) (citation accuracy ≥ 0.99 is a gate). Putting a boundary into a weighted average is one of the most common and most damaging modelling errors in applied AI work.

### Three-way outputs beat binary

If your rubric only has pass/fail, you'll be forced to choose between missing bad outputs and rejecting good ones. Add the third option:

| Output | Meaning | Bounded by |
|---|---|---|
| `pass` | Confidently good — ship it | — |
| `fail` | Confidently bad — block it | Your false-reject budget |
| **`review`** | Genuinely ambiguous | **Human capacity ([03.5](03-discovery-and-scoping.md))** |

The `review` band is how you satisfy two conflicting targets at once. It's the resolution used in the [manufacturing](../28_ai-system-design-by-industry/06_manufacturing_cv_inspection/) design (escape ≤ 0.2% *and* false-reject ≤ 1.5%, impossible on one threshold) and the [claims](../28_ai-system-design-by-industry/07_insurance_claims_automation/) design.

---

## 4.5 A runnable harness

Small enough to write on day three, useful for the whole engagement. No dependencies beyond the standard library plus whatever calls your model.

```python
"""eval_harness.py — the FDE's first real deliverable.

Design constraints that matter in the field:
  1. Runnable by someone who isn't you (handover).
  2. Every result traceable to an example id (arguing about aggregates is useless).
  3. Blocking dimensions enforced structurally, not by convention.
  4. Reports the TRUE production number and the STRATIFIED number separately.
"""
from dataclasses import dataclass, field
import json, statistics, hashlib


@dataclass
class Example:
    id: str
    inputs: dict
    stratum: tuple                 # e.g. ('status', 'note_insufficient')
    expected: dict = field(default_factory=dict)   # expert labels
    weight: float = 1.0            # for re-weighting strata → true distribution


@dataclass
class Result:
    example_id: str
    stratum: tuple
    output: str
    scores: dict                   # dimension -> score or bool
    blocked_by: list               # blocking dimensions that failed
    passed: bool
    latency_ms: int
    cost_usd: float
    trace: dict = field(default_factory=dict)


BLOCKING = {'factual_grounding', 'honest_when_unknown'}


def grade(example: Example, output: str, judges: dict) -> dict:
    """judges: dimension -> callable(example, output) -> score|bool.

    Deterministic checks first (cheap and exact), LLM judges only where a
    human genuinely needs to be approximated. Most 'AI eval' problems are
    string-matching problems in disguise.
    """
    return {dim: fn(example, output) for dim, fn in judges.items()}


def run_suite(examples, model_fn, judges) -> list:
    results = []
    for ex in examples:
        t0 = now_ms()
        out, usage = model_fn(ex.inputs)
        scores = grade(ex, out, judges)
        blocked = [d for d in BLOCKING if scores.get(d) is False]
        results.append(Result(
            example_id=ex.id, stratum=ex.stratum, output=out, scores=scores,
            blocked_by=blocked,
            passed=(not blocked) and weighted_score(scores) >= PASS_THRESHOLD,
            latency_ms=now_ms() - t0,
            cost_usd=usage_cost(usage),
        ))
    return results


def report(results, examples) -> dict:
    """Two headline numbers, and never only one of them."""
    by_id = {e.id: e for e in examples}
    stratified = mean(r.passed for r in results)

    # Re-weight to the REAL production distribution. This is the number the
    # customer should quote, and it is usually LOWER than the stratified one
    # because we deliberately oversampled hard cases.
    total_w = sum(by_id[r.example_id].weight for r in results)
    true_rate = sum(by_id[r.example_id].weight * r.passed for r in results) / total_w

    return {
        'stratified_pass_rate': round(stratified, 3),
        'production_weighted_pass_rate': round(true_rate, 3),   # ← quote THIS
        'blocking_failures': {
            d: sum(1 for r in results if d in r.blocked_by) for d in BLOCKING
        },
        'by_stratum': {
            str(s): round(mean(r.passed for r in results if r.stratum == s), 3)
            for s in {r.stratum for r in results}
        },
        'p95_latency_ms': percentile([r.latency_ms for r in results], 95),
        'cost_per_example_usd': round(mean(r.cost_usd for r in results), 5),
        'cost_per_PASS_usd': round(
            sum(r.cost_usd for r in results) / max(sum(r.passed for r in results), 1), 5
        ),   # ← the number that gets signed. See 07.
        'n': len(results),
    }
```

### The three lines that make this a professional artifact

1. **`production_weighted_pass_rate`** alongside the stratified rate. You oversampled hard cases for signal; report the true number too, and label which is which. Quoting only the stratified number is how a 74% becomes a 61% in front of a stakeholder three weeks later.
2. **`by_stratum`** breakdown. An aggregate of 74% hides "94% on answerable status, 31% on insufficient-note" — and those need completely different fixes.
3. **`cost_per_PASS_usd`**, not cost per call. See [07](07-unit-economics.md); this is the number that survives a CFO.

### Deterministic checks before LLM judges

Cheaper, exact, faster, and reproducible. Reach for an LLM judge only when you're genuinely approximating human judgement.

```python
def factual_grounding(ex, output) -> bool:
    """BLOCKING. Every date, price and part number in the output must appear
    verbatim in the source note. No model call needed — and a model judge would
    be *worse* here, because this is exactly the kind of check an LLM does
    unreliably and a regex does perfectly."""
    note = ex.inputs['note']
    for token in extract_dates(output) + extract_money(output) + extract_parts(output):
        if token not in note:
            return False
    return True


def honest_when_unknown(ex, output) -> bool:
    """BLOCKING. If the expert marked the note as insufficient, the draft must
    hedge rather than answer."""
    if ex.expected.get('note_answers') is True:
        return True
    return any(p in output.lower() for p in
               ("let me check", "i'll confirm", "i'll follow up", "don't have"))
```

| Use a deterministic check when | Use an LLM judge when |
|---|---|
| Grounding, format, presence/absence, numeric bounds, policy keywords | Tone, helpfulness, coherence, "would the expert send this" |
| You can express the rule exactly | The rule is a judgement |
| It's a blocking dimension | It's a weighted contributor |

> **Validate the LLM judge against your experts before trusting it.** Run it on the 30 examples your experts labelled and compute agreement between judge and human — the same kappa you computed in 4.2. A judge with κ = 0.45 against your experts is generating numbers, not measurements. [`../16_evals/`](../16_evals/README.md) covers G-Eval and judge calibration properly.

---

## 4.6 Wiring it into the customer's CI

An eval that only you run is a personal tool. An eval in their pipeline is an asset.

```yaml
# .github/workflows/eval.yml — runs on every prompt/config change
on:
  pull_request:
    paths: ['prompts/**', 'config/**', 'src/**']

jobs:
  eval:
    steps:
      - run: python -m eval_harness --suite golden_v3 --report report.json
      - run: python -m eval_harness --gate report.json
        # Gate fails the PR when:
        #   production_weighted_pass_rate drops > 2pp vs main
        #   ANY blocking-dimension failure count increases
        #   p95 latency regresses > 15%
        #   cost_per_PASS increases > 20%
      - uses: actions/upload-artifact@v4
        with: {name: eval-report, path: report.json}
```

Two things make this valuable rather than ceremonial:

**Gate on the blocking dimensions absolutely.** An increase in fabricated facts fails the build even if the aggregate score improved. A change that's more accurate overall and hallucinates more is not an improvement.

**Gate on cost and latency too.** Otherwise quality improvements silently arrive as a 3× cost increase, discovered on an invoice.

---

## 4.7 The ceiling conversation

Eventually you'll need to say a number out loud. Here's the shape that works, using real numbers from the running example.

> "Here's where we are, measured on 150 real messages your team labelled.
>
> **The human baseline:** your three senior advisors agreed on 88 of 100 cases. Kappa 0.79. So ~88% is roughly the ceiling for 'correct' on this task, because for about 12% of messages your own experts don't agree on the right reply.
>
> **The system:** 74% of drafts are send-as-is, and 91% are send-or-minor-edit. On the two things that matter most — inventing facts, and guessing when the note doesn't have the answer — we're at zero and zero on this set, because those are hard-blocked rather than scored.
>
> **The combined system,** with the 9% low-confidence band routed to a full manual write: more accurate than today *and* about four minutes faster per advisor-hour.
>
> **What I can't promise** is 95%, because 95% is above what your own experts agree on. If that's the requirement, the honest answer is that this task needs a clearer policy first — and I can tell you exactly which three ambiguities drive most of the disagreement."

### Why this works

| Move | Effect |
|---|---|
| Human baseline first | Reframes from "is the AI good enough" to "is the *system* better than today" — the only question that matters |
| Two accuracy numbers | Send-as-is and send-with-edit are different products; conflating them is how expectations break |
| Blocking dimensions called out separately | Shows the dangerous failures are structurally prevented, not statistically unlikely |
| The combined-system number | Nobody buys a model. They buy an outcome |
| An explicit refusal to promise 95% | **This is the credibility move.** An FDE who never says "I can't" is not believed when they say "I can" |

---

## 4.8 Common eval mistakes in the field

> - **Mistake:** Building the prototype first, the eval later → **Why it's wrong:** you tune against your own taste for three weeks, then discover the expert disagrees → **Do instead:** golden set and rubric before serious iteration.
> - **Mistake:** Skipping inter-rater agreement → **Why it's wrong:** you commit to a target that may be above the human ceiling, and then chase noise → **Do instead:** 30 examples, 3 experts, week one.
> - **Mistake:** Hand-picked eval examples → **Why it's wrong:** measures your taste, not the distribution → **Do instead:** stratify on the dimensions that drive difficulty.
> - **Mistake:** One averaged quality score → **Why it's wrong:** can't tell you *what* regressed, and it averages away asymmetric errors → **Do instead:** independent dimensions with blocking ones enforced structurally.
> - **Mistake:** Reporting only the stratified number → **Why it's wrong:** you oversampled hard cases; the number will move when someone re-derives it → **Do instead:** report both, labelled.
> - **Mistake:** Aggregate-only reporting → **Why it's wrong:** 74% overall can be 94%/31% across two segments needing different fixes → **Do instead:** always break down by stratum.
> - **Mistake:** LLM judge for grounding → **Why it's wrong:** it's a string-matching problem, and LLMs do it unreliably while regex does it perfectly → **Do instead:** deterministic checks for anything expressible as a rule.
> - **Mistake:** Trusting an unvalidated LLM judge → **Why it's wrong:** you've replaced a measurement with a generated number → **Do instead:** compute judge-vs-expert kappa first.
> - **Mistake:** No held-out slice → **Why it's wrong:** you overfit your own eval in three weeks and won't know → **Do instead:** freeze 20%.
> - **Mistake:** Eval only you can run → **Why it's wrong:** dies with your engagement → **Do instead:** in their CI, with a gate.
> - **Mistake:** Gating on quality but not cost/latency → **Why it's wrong:** improvements arrive as a 3× bill → **Do instead:** gate all four.

---

## 4.9 Interview signal

Expect: *"How would you know whether your solution is good enough to ship?"*

> "I'd start before the model, with the customer's own experts. Thirty real examples, three experts labelling independently, and I measure Fleiss' kappa. If they agree 93% of the time, a 90% target is credible. If they agree 70% of the time — kappa around 0.5 — then '95% accurate' doesn't have a meaning yet, and the first deliverable is a definition workshop rather than a model. That conversation in week one prevents the most common way these engagements fail.
>
> Then a stratified golden set, 100–200 examples, sampled along whatever dimensions drive difficulty — deliberately including the segments I'd rather exclude. Rubric decomposed into independent dimensions, with the safety-critical ones **blocking** rather than weighted: a reply with perfect tone and a fabricated pickup date isn't 80% good, it's a failure. Deterministic checks for anything expressible as a rule — grounding is string matching, not a judgement — and an LLM judge only for things like tone, validated against the experts' own labels first.
>
> I'd report two numbers, always: the stratified rate and the production-weighted rate, because I oversampled hard cases. Plus a per-segment breakdown, since 74% overall might be 94% on one segment and 31% on another and those need different fixes. And I'd put it in their CI gating on quality, blocking-dimension counts, latency and cost-per-success — so it survives after I leave. That harness is the thing I'd actually consider the deliverable; the prototype gets rewritten."

---

> ← [`03-discovery-and-scoping.md`](03-discovery-and-scoping.md) · **Index:** [`README.md`](README.md) · **Next:** [`05-prompt-and-context-engineering-in-the-field.md`](05-prompt-and-context-engineering-in-the-field.md) →
