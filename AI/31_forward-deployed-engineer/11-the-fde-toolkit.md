# 11 · The FDE toolkit

> ← [`10-stakeholder-communication.md`](10-stakeholder-communication.md) · **Index:** [`README.md`](README.md) · **Next:** [`12-the-interview-loop.md`](12-the-interview-loop.md) →

**Six things you rebuild at every customer.** Build them once, generically, and you show up to a new engagement with a working start instead of a blank editor. All code is stdlib-only Python — deliberately, because you rarely control the customer's environment and dependency friction on day one is a real cost.

---

## 11.1 The data profiler — run this before you write a prompt

Answers "how messy is their data, really" in an hour instead of a week of surprises.

```python
"""profiler.py — run against ANY list-of-dicts on day one.

    python profiler.py sample_export.jsonl

Prints fill rates, length distributions, format-variant counts, and
duplicate rates per field. This is the artifact that reframes the whole
engagement, and it's the thing that makes your later claims credible —
see 05.4.
"""
import json, re, sys, statistics
from collections import Counter, defaultdict


def load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def profile_field(name, values):
    non_null = [v for v in values if v not in (None, "", "null", "N/A")]
    fill_rate = len(non_null) / len(values) if values else 0
    out = {'field': name, 'n': len(values), 'fill_rate': round(fill_rate, 3)}

    strings = [v for v in non_null if isinstance(v, str)]
    if strings:
        lengths = [len(s) for s in strings]
        out['len_median'] = statistics.median(lengths)
        out['len_p95'] = sorted(lengths)[int(0.95 * len(lengths))] if lengths else 0
        out['distinct_ratio'] = round(len(set(strings)) / len(strings), 3)

        # Detect date-format inconsistency — the most common silent killer.
        date_formats = Counter()
        for s in strings:
            if re.search(r'\d{4}-\d{2}-\d{2}', s):   date_formats['iso'] += 1
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', s): date_formats['slash'] += 1
            elif re.search(r'\d{1,2}-[A-Za-z]{3}-\d{2,4}', s): date_formats['dmon'] += 1
        if sum(date_formats.values()) > 5:
            out['date_formats'] = dict(date_formats)

    return out


def profile_dataset(records) -> list:
    fields = defaultdict(list)
    for r in records:
        for k, v in r.items():
            fields[k].append(v)
    return sorted(
        [profile_field(k, v) for k, v in fields.items()],
        key=lambda f: f['fill_rate']
    )


def print_report(profiles, n_records):
    print(f"\n{'='*70}\n{n_records} records\n{'='*70}")
    for p in profiles:
        flag = "⚠️ " if p['fill_rate'] < 0.9 else "   "
        print(f"{flag}{p['field']:25} fill={p['fill_rate']:.0%}", end="")
        if 'len_median' in p:
            print(f"  len(median/p95)={p['len_median']}/{p['len_p95']}"
                  f"  distinct={p['distinct_ratio']:.0%}", end="")
        if 'date_formats' in p:
            print(f"  ⚠️  MIXED DATE FORMATS: {p['date_formats']}", end="")
        print()
    low_fill = [p for p in profiles if p['fill_rate'] < 0.9]
    if low_fill:
        print(f"\n⚠️  {len(low_fill)} field(s) below 90% fill — "
              f"these will drive your honest-refusal rate.")


if __name__ == '__main__':
    records = load(sys.argv[1])
    print_report(profile_dataset(records), len(records))
```

Run this in the first meeting where you get real data. The mixed-date-format flag alone has saved me a day of confusing prompt debugging more than once — the failure looked like a model problem and was a parsing problem three layers upstream.

---

## 11.2 The eval harness — see [04.5](04-evals-are-the-deliverable.md) for the full version

The complete implementation lives there, with blocking dimensions, stratified vs production-weighted reporting, and cost-per-success. Bring that file's `eval_harness.py`, not a rewrite — it's already built for handover, with the property that someone who isn't you can run it.

---

## 11.3 The kappa calculator — 20 lines, run it in week one

```python
"""kappa.py — inter-rater agreement. See 04.2 for why this comes before
anything else you build.

    python kappa.py labels.csv
    # labels.csv: item_id,rater1,rater2,rater3
"""
import csv, sys
from collections import Counter
from itertools import combinations


def cohens_kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def fleiss_kappa(rows):
    """rows: list of {rater: label} dicts, one per item."""
    labels = sorted({l for row in rows for l in row.values()})
    n_raters = len(rows[0])
    P = []
    for row in rows:
        counts = Counter(row.values())
        p_i = sum(counts[l] * (counts[l] - 1) for l in labels) / (n_raters * (n_raters - 1))
        P.append(p_i)
    P_bar = sum(P) / len(P)
    p_j = [sum(1 for row in rows if l in row.values()) / (len(rows) * n_raters) for l in labels]
    P_e = sum(p ** 2 for p in p_j)
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else 1.0


def interpret(k):
    if k > 0.80:  return "STRONG — task is well-defined. Target near this rate."
    if k > 0.60:  return "MODERATE — usable. Route the ambiguous band to review."
    if k > 0.40:  return "WEAK — the definition is the problem, not the model."
    return "The task as stated isn't a well-formed task."


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        reader = csv.DictReader(f)
        rows = [{k: v for k, v in r.items() if k != 'item_id'} for r in reader]

    raters = list(rows[0].keys())
    print(f"Fleiss' kappa ({len(raters)} raters, {len(rows)} items): "
          f"{fleiss_kappa(rows):.3f}")
    for r1, r2 in combinations(raters, 2):
        k = cohens_kappa([row[r1] for row in rows], [row[r2] for row in rows])
        print(f"  {r1} vs {r2}: κ={k:.3f}")
    print(f"\n→ {interpret(fleiss_kappa(rows))}")
```

Deliver the output verbatim, in the room, in week one: *"Fleiss' kappa across your three experts is 0.52 — weak. Before we set an accuracy target, I think we need a definition workshop."* That sentence is worth more than a month of tuning against noise.

---

## 11.4 The cost calculator — the arithmetic from [07](07-unit-economics.md), runnable

```python
"""unit_economics.py — turns raw numbers into the 51x-style slide.

    python unit_economics.py
"""
from dataclasses import dataclass


@dataclass
class Inputs:
    volume_per_day: int
    eligible_fraction: float        # gated by intent/triage before reaching the model
    success_rate: float             # from your eval, production-weighted
    cost_per_attempt_usd: float
    human_minutes_per_success: float
    human_minutes_wasted_per_failure: float   # time spent reviewing a rejected output
    loaded_hourly_rate_usd: float
    working_days_per_month: int = 22


def unit_economics(i: Inputs) -> dict:
    eligible = i.volume_per_day * i.eligible_fraction
    successes = eligible * i.success_rate
    failures = eligible * (1 - i.success_rate)

    cost_per_success = i.cost_per_attempt_usd / i.success_rate

    time_saved_hr = successes * i.human_minutes_per_success / 60
    time_wasted_hr = failures * i.human_minutes_wasted_per_failure / 60
    net_hours_per_day = time_saved_hr - time_wasted_hr

    daily_cost = eligible * i.cost_per_attempt_usd
    daily_value = net_hours_per_day * i.loaded_hourly_rate_usd

    return {
        'eligible_per_day': round(eligible),
        'successes_per_day': round(successes),
        'cost_per_attempt': round(i.cost_per_attempt_usd, 4),
        'cost_per_SUCCESS': round(cost_per_success, 4),          # ← the real number
        'net_hours_saved_per_day': round(net_hours_per_day, 1),
        'ratio_value_to_cost': round(daily_value / daily_cost, 1) if daily_cost else float('inf'),
        'monthly_cost_usd': round(daily_cost * i.working_days_per_month),
        'monthly_value_usd': round(daily_value * i.working_days_per_month),
        'NET_POSITIVE': net_hours_per_day > 0,                   # ← the sanity check
    }


if __name__ == '__main__':
    for label, i in {
        'current (74% acceptance)': Inputs(2000, 0.58, 0.74, 0.021, 2.4, 0.3, 38),
        'degraded (40% acceptance)': Inputs(2000, 0.58, 0.40, 0.021, 2.4, 0.3, 38),
        'the danger zone (20%, slow review)':
            Inputs(2000, 0.58, 0.20, 0.021, 2.4, 0.75, 38),
    }.items():
        r = unit_economics(i)
        flag = "✅" if r['NET_POSITIVE'] else "❌ NET NEGATIVE"
        print(f"\n{label}  {flag}")
        for k, v in r.items():
            print(f"  {k:28} {v}")
```

The third scenario is the one to keep re-running as acceptance changes — it's the failure mode from [07.1](07-unit-economics.md) where the token bill stays cheap while the *system* makes people slower, and this calculator is what catches it before a customer does.

---

## 11.5 The grounding checker — a generalisable fact-verification gate

Works for any task where the model must draw only from provided material: claims processing, clinical summarisation, contract review, support drafting.

```python
"""grounding.py — verifies claimed facts exist in the source.

Generalises the pattern from 05.5's facts_used field: have the model
DECLARE its evidence, then check the declaration programmatically. Checking
is cheap and exact; generating is probabilistic. Don't trust one without
the other.
"""
import re
from dataclasses import dataclass


DATE_RE  = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b')
MONEY_RE = re.compile(r'[$₹£€]\s?[\d,]+(?:\.\d{2})?')
NUM_RE   = re.compile(r'\b\d+(?:\.\d+)?\s?(?:%|percent|units?|days?)\b')


@dataclass
class GroundingResult:
    passed: bool
    ungrounded: list       # tokens claimed but not found in source
    checked: list          # tokens verified present


def extract_claims(text: str) -> list:
    """Pull the fact-shaped tokens worth verifying. Extend per-domain —
    part numbers, SKUs, account IDs, whatever your task's dangerous
    fabrications look like."""
    return DATE_RE.findall(text) + MONEY_RE.findall(text) + NUM_RE.findall(text)


def normalise(token: str) -> str:
    return re.sub(r'[,\s]', '', token.lower())


def check_grounding(output: str, source: str) -> GroundingResult:
    claims = extract_claims(output)
    source_norm = normalise(source)
    checked, ungrounded = [], []
    for claim in claims:
        if normalise(claim) in source_norm:
            checked.append(claim)
        else:
            ungrounded.append(claim)
    return GroundingResult(passed=not ungrounded, ungrounded=ungrounded, checked=checked)


def grounded_generate(prompt_fn, source: str, max_retries=2):
    """The full loop: generate, check, retry with the violation named,
    fall back to a safe template rather than shipping an ungrounded claim."""
    for attempt in range(max_retries):
        output = prompt_fn(source, feedback=None if attempt == 0 else last_result.ungrounded)
        last_result = check_grounding(output, source)
        if last_result.passed:
            return output, last_result
    return SAFE_FALLBACK_TEMPLATE, last_result   # never ship an ungrounded claim


SAFE_FALLBACK_TEMPLATE = (
    "I want to make sure I give you accurate information — let me confirm "
    "the details and follow up shortly."
)
```

This is the same technique underlying citation accuracy ≥ 0.99 in the [healthcare design](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/) and score-driver-to-CV-span binding in the [HR design](../28_ai-system-design-by-industry/11_hr_recruitment_matching/) — moving a hard constraint from a prompt instruction into a programmatic gate. Reuse the *shape*, not the regexes, per domain.

---

## 11.6 The stratified sampler — build the golden set correctly

```python
"""sampler.py — stratified sampling for the golden set. See 04.3.

    python sampler.py all_records.jsonl strata.yaml 150
"""
import json, random, sys
from collections import defaultdict


def stratify(records: list, key_fn, targets: dict) -> dict:
    """key_fn maps a record to its stratum key, e.g. (intent, has_answer).
    targets maps stratum key -> desired sample count."""
    buckets = defaultdict(list)
    for r in records:
        buckets[key_fn(r)].append(r)

    sample, shortfalls = [], {}
    for stratum, n_wanted in targets.items():
        pool = buckets.get(stratum, [])
        if len(pool) < n_wanted:
            shortfalls[stratum] = (len(pool), n_wanted)
        sample += random.sample(pool, min(n_wanted, len(pool)))

    return {
        'sample': sample,
        'shortfalls': shortfalls,      # ← report these; a shortfall means the
                                       #   stratum is rare in reality, which is
                                       #   itself a finding worth stating
        'true_distribution': {k: len(v) / len(records) for k, v in buckets.items()},
    }
```

**Report `true_distribution` alongside the sample, always.** It's what lets you compute the production-weighted pass rate later ([04.5](04-evals-are-the-deliverable.md)) instead of quoting a number measured on a distribution you deliberately distorted.

---

## 11.7 A prototype scaffold that's actually handoff-ready

The structural pattern from [05.6](05-prompt-and-context-engineering-in-the-field.md), as a starting repo layout. Copy this on day one of every engagement rather than starting from a single script.

```
project/
  prompts/
    <task>.v1.md              # versioned files, never inline strings
    CHANGELOG.md
  config/
    models.yaml                # tier + fallback chain per task
    thresholds.yaml             # confidence cuts, WITH the capacity reasoning noted
  evals/
    golden_v1.jsonl
    rubric.yaml
    eval_harness.py             # from 04.5
    README.md                   # three commands to run it
  src/
    grounding.py                 # from 11.5
    profiler.py                  # from 11.1
  runbook.md                     # from 09.5, symptom-first
  decision_log.md                 # from 09.5, WHY not WHAT
  exit_criteria.md                # from 09.2, signed
```

**The two files people forget and that matter most: `decision_log.md` and `exit_criteria.md`.** Everything else is buildable in a day; those two only have value if they're written *as decisions happen*, not reconstructed at the end.

---

## 11.8 Interview signal

Expect: *"Walk me through the first three things you'd build at a new customer."*

> "First a data profiler — run it against whatever real sample I can get on day one. Fill rates, length distributions, date-format consistency, duplicate rates. It's an hour of work and it reframes the whole engagement before I write a single prompt; the mixed-date-format flag alone has saved me a day of debugging that looked like a model problem and was actually three layers upstream.
>
> Second, an inter-rater agreement check. Twenty to thirty real examples, three of their experts labelling independently, Fleiss' kappa. If it's above 0.8 the task is well-defined and I can set a credible target. If it's around 0.5, I tell them in the room that we need a definition workshop before we need a model.
>
> Third, the eval harness — golden set, rubric with blocking dimensions for the failures that actually matter, deterministic checks before any LLM judge, reporting both the stratified and the production-weighted pass rate. That's genuinely the deliverable, not the prototype, and I build it to be runnable by their engineer from day one rather than something only I can operate — because the moment only I can run it, it hasn't actually been handed over."

---

> ← [`10-stakeholder-communication.md`](10-stakeholder-communication.md) · **Index:** [`README.md`](README.md) · **Next:** [`12-the-interview-loop.md`](12-the-interview-loop.md) →
