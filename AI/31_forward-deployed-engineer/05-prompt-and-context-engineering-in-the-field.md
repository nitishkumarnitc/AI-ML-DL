# 05 · Prompt and context engineering in the field

> ← [`04-evals-are-the-deliverable.md`](04-evals-are-the-deliverable.md) · **Index:** [`README.md`](README.md) · **Next:** [`06-agents-tools-and-integration.md`](06-agents-tools-and-integration.md) →
>
> **Prerequisite:** [`../01_prompt-engineering/`](../01_prompt-engineering/README.md) for technique, [`../12_rag/`](../12_rag/README.md) and [`../20_data-engineering-for-rag/`](../20_data-engineering-for-rag/README.md) for retrieval. This file is about *what to reach for first* when accuracy is 61% and the customer is watching.

---

## 5.1 This is 10% of the job — spend it well

From [02.4](02-the-demo-to-production-gap.md): prompt and model work is about a tenth of a real engagement. Data access is 30%, evals 20%.

That's not a reason to be careless with it. It's a reason to be **ruthlessly ordered** about it, because the temptation under pressure is to spend three days rewriting a prompt when the actual problem is that 31% of the source notes don't contain the answer.

> **The single most useful diagnostic question:** *"Is this a prompting problem, a context problem, or a data problem?"*
>
> - **Prompting** — the information is in the context and the model didn't use it correctly
> - **Context** — the information exists somewhere but didn't reach the model
> - **Data** — the information doesn't exist anywhere
>
> Most "the model is bad" complaints are context problems. Most "we need a better model" requests are data problems. **Prompt work fixes only the first category, and it's the smallest of the three.**

---

## 5.2 The fix ladder

When accuracy is below target, work this order. It's sorted by cost-to-try divided by expected-gain, which is a different order from the one most people use.

| # | Move | Typical gain | Cost | When it's the answer |
|---|---|---|---|---|
| 1 | **Read 20 failures individually** | — | 1 hour | **Always first.** You cannot fix a distribution you haven't looked at |
| 2 | **Fix the retrieval, not the prompt** | +10–25pp | hours | The context didn't contain the answer. This is the most common real cause |
| 3 | **Add an honest-refusal path** | +0pp accuracy, huge trust | hours | Some inputs are unanswerable. Converting confident-wrong → "let me check" changes the product |
| 4 | **Decompose the task** | +8–20pp | a day | One prompt doing classification + extraction + generation. Split it |
| 5 | **Few-shot from *their* data** | +5–15pp | hours | Format and tone mismatches. Their own past outputs are the best examples |
| 6 | **Structured output + validation** | +5–15pp | hours | Parse failures and format drift masquerading as accuracy problems |
| 7 | **Move the constraint out of the prompt** | +5–20pp | hours | "Never invent a price" as an instruction is a suggestion; as a post-check it's a guarantee |
| 8 | **Prompt rewrite / clarify instructions** | +3–10pp | hours | Genuine ambiguity in the instruction |
| 9 | **Bigger model** | +3–8pp | minutes to try | **Try it early as a *diagnostic*, adopt it late.** See 5.3 |
| 10 | **Fine-tune** | +5–15pp on narrow tasks | weeks | Stable task, thousands of examples, and you've exhausted 1–9 |

### The two that get skipped and shouldn't

**#1, reading failures.** Twenty individual failures read end-to-end will tell you which of the ten moves you need. Skipping it means guessing, and guessing costs days. Do this before touching anything.

**#7, moving constraints out of the prompt.** This is the highest-leverage architectural move in the list and it isn't prompt engineering at all:

```python
# WEAK — the constraint is a request. The model complies ~95% of the time,
# and the 5% is exactly the dangerous case.
prompt = """Draft a reply. NEVER state a price or date not in the note."""

# STRONG — the constraint is enforced. Compliance is 100% by construction.
draft = llm(prompt)
for token in extract_dates(draft) + extract_money(draft):
    if token not in note:
        draft = regenerate_with_feedback(draft, f"'{token}' is not in the note")
        # ...and if it fails twice, fall back to the safe template.
```

The general rule, which recurs throughout [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md): **anything you'd be embarrassed to explain to a regulator belongs in code, not in a prompt.** A prompt instruction is a strong prior; a validator is a guarantee. Customers understand this distinction immediately and it raises their confidence in you.

---

## 5.3 The bigger-model question

Customers ask "would a better model fix it?" constantly. Answer it with an experiment, not an opinion — and run the experiment early for information, not as a solution.

```
Run the same eval suite across tiers. Real shape of results on a grounded
extraction-and-drafting task:

  small model      58%   $0.0008/call    620ms
  mid model        69%   $0.004/call     980ms
  frontier         74%   $0.021/call    1,400ms
  frontier + the fixes from 5.2 (#2,3,4,7)   →   89%

  small + the same fixes                     →   84%
```

Two conclusions, and the second is the one worth carrying:

**The fixes are worth more than the model upgrade** (+15pp vs +16pp, but the fixes compose with *any* model and cost nothing per call).

**The small model with good engineering beats the frontier model with bad engineering**, at 4% of the cost. So the tier decision should be made *after* the engineering, not instead of it.

> **Use the model-tier sweep as a diagnostic:** if the frontier model doesn't materially beat the small one, the problem is not model capability — it's context or data. That's a five-minute experiment that saves a week of arguing.

And when the customer pushes for the frontier model anyway: run the [07](07-unit-economics.md) arithmetic. At 200k calls/month, $0.0008 vs $0.021 is $160 vs $4,200. Sometimes that's obviously worth it. Often it isn't, and the numbers settle it without an argument.

---

## 5.4 Context engineering on someone else's data

This is where the real accuracy lives, and it's mostly not prompting.

### The four failures, in order of frequency

| Failure | Symptom | Fix |
|---|---|---|
| **The answer isn't in the retrieved context** | Model hedges or invents | Fix retrieval. Measure **contextual recall** before anything else ([`../16_evals/`](../16_evals/README.md)) |
| **The answer is there but buried** | Inconsistent — works sometimes | Rerank; cut context; put the critical span first |
| **Conflicting information in context** | Model picks arbitrarily | Resolve upstream, or make the conflict explicit and let the model flag it |
| **The answer doesn't exist anywhere** | Everything fails on this segment | **Not a model problem.** This is a finding to report, not a bug to fix |

> **Measure retrieval separately from generation, always.** If contextual recall is 0.6, your generation ceiling is 0.6 and every hour spent on the prompt is wasted. This decomposition is the single most useful debugging move in applied RAG work, and customers find it genuinely clarifying: "the model isn't hallucinating, we're not giving it the document."

### Their data will be worse than the sample

Every time. Budget for it:

| Reality | Consequence |
|---|---|
| Median note is 84 chars of shorthand | Chunking strategies designed for documents are wrong |
| Three date formats in one field | Normalise before retrieval, not in the prompt |
| Free text where an enum should be | 40 spellings of the same status |
| Truncated fields from a legacy migration | Some records are unanswerable and you must detect it |
| Two systems disagree about the same entity | Pick a precedence rule *with the customer*, and write it down |
| Copy-pasted email chains inside a "notes" field | The note contains three timestamps, two of them irrelevant |

**Write a data profiler before you write a prompt.** Field fill rates, length distributions, format variants, duplicate rates. It takes an hour, it reframes the whole engagement, and it's the artifact that makes the customer trust your later claims — see the profiler in [11](11-the-fde-toolkit.md).

---

## 5.5 Prompt structure that survives production

Not tricks. Structural properties that matter when someone else maintains it.

```python
# prompts/draft_reply.v7.md  — versioned as a FILE, never inline in code
"""
ROLE
You draft short text replies for an auto-service advisor to review before sending.

RULES  (hard — violations are caught downstream, but don't produce them)
1. Use only facts present in the REPAIR ORDER NOTE below.
2. If the note cannot answer the question, say you'll check and follow up.
   Do not guess at parts, pricing, or timing.
3. 2–3 sentences. No greeting beyond a first name.

OUTPUT — JSON only
{
  "can_answer": true|false,
  "draft": "...",
  "facts_used": ["7/29", "oil change"],   // must appear verbatim in the note
  "confidence": 0.0-1.0
}

REPAIR ORDER NOTE
{note}

CUSTOMER MESSAGE
{message}

EXAMPLES
{few_shot}    // drawn from THIS advisor's actual sent replies
"""
```

Five properties that matter:

| Property | Why it earns its place |
|---|---|
| **In a versioned file, not a string literal** | You'll compare v6 and v7 on the eval suite. Inline prompts can't be diffed or rolled back |
| **`facts_used` returned explicitly** | Makes the grounding check trivial and exact. **Asking the model to declare its evidence is the cheapest hallucination defence available** |
| **`can_answer` as a separate field** | Turns refusal into a structured decision you can route on, not a phrase you regex for |
| **`confidence` self-report** | Weakly calibrated, but useful for *ranking* which outputs to review first. Never use it as a hard gate |
| **Few-shot from this specific user's history** | Tone is per-advisor. Generic examples produce generic voice, which two of twelve advisors will reject outright |

### The `facts_used` trick generalises

Any task where the model must ground itself in provided material: have it **enumerate the evidence it used**, then verify each item programmatically. It works because checking is cheap and exact while generating is probabilistic. Variants of this appear in the [healthcare](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/) design (opaque citation handles plus entailment verification, citation accuracy ≥ 0.99) and the [HR](../28_ai-system-design-by-industry/11_hr_recruitment_matching/) design (score drivers bound to CV character offsets).

---

## 5.6 What to hand over

Prompt work is easy to leave in an unmaintainable state. Minimum viable handover:

```
prompts/
  draft_reply.v7.md          # current
  draft_reply.v6.md          # previous, kept for comparison
  CHANGELOG.md               # what changed, eval delta, WHY
config/
  models.yaml                # tier per task + fallback chain
  thresholds.yaml            # confidence cuts, with the capacity reasoning noted
evals/
  golden_v3.jsonl            # the labelled set
  rubric.yaml                # what "good" means, signed by whom
  README.md                  # how to run it, in three commands
```

The `CHANGELOG.md` is the part people skip and the part that matters most:

```markdown
## v7 (2026-03-14)
Added `facts_used` output + programmatic grounding check.
Moved "never invent a price" from prompt instruction to post-validation.
  eval: production-weighted 68% → 74%
  blocking (fabricated fact): 11 → 0        ← the reason for the change
  cost: +4% (one extra output field)
Why: v6's prompt-level constraint was violated on 11/150. Instructions are
priors, not guarantees. See 05.2 #7.
```

Six months from now, someone will consider reverting this to simplify the prompt. That paragraph is what stops them.

---

## 5.7 Interview signal

Expect: *"Your accuracy is 61% and the customer expected 90%. Walk me through what you do."*

> "First, I don't touch the prompt. I read twenty individual failures end to end, because I can't fix a distribution I haven't looked at, and I want to know which of three things I'm dealing with: is the information in the context and the model got it wrong — a prompting problem; is it available but didn't reach the model — a context problem; or does it not exist anywhere — a data problem. Most 'the model is bad' complaints turn out to be the second, and most 'we need a better model' requests turn out to be the third.
>
> Concretely I'd measure retrieval separately from generation. If contextual recall is 0.6 then my generation ceiling is 0.6 and prompt work is wasted. Then I'd look at whether the failures cluster in one segment — 61% overall might be 90% on answerable inputs and 20% on a segment where the source data simply doesn't contain the answer, and that second group isn't a bug, it's a finding: those need an honest-refusal path, not a better prompt.
>
> I'd also run the model-tier sweep early, as a diagnostic rather than a fix — if the frontier model doesn't beat the small one materially, it confirms the problem is context or data. And I'd move any safety-critical constraint out of the prompt into a validator, because 'never invent a price' as an instruction is complied with about 95% of the time and the 5% is exactly the dangerous case.
>
> Then I'd go back to the customer with the segment breakdown rather than the aggregate, because 'we're at 61%' starts an argument and 'we're at 90% on the 70% of inputs where your notes contain the answer, and here's what we do with the other 30%' starts a design conversation."

---

> ← [`04-evals-are-the-deliverable.md`](04-evals-are-the-deliverable.md) · **Index:** [`README.md`](README.md) · **Next:** [`06-agents-tools-and-integration.md`](06-agents-tools-and-integration.md) →
