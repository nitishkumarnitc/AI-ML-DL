# 07 · Unit economics

> ← [`06-agents-tools-and-integration.md`](06-agents-tools-and-integration.md) · **Index:** [`README.md`](README.md) · **Next:** [`08-security-and-enterprise-blockers.md`](08-security-and-enterprise-blockers.md) →

---

## 7.1 The only cost number that matters

Not cost per token. Not cost per API call. Not even cost per request.

> **Cost per successfully completed business outcome.**

Everything else is an input to that number, and quoting anything else in front of someone who controls a budget marks you as an engineer rather than someone they can plan with.

### The arithmetic, done once, properly

Running example — drafting service-advisor replies:

```
INPUTS  (measured, not assumed)
  inbound messages/day                    2,000
  of which drafting is attempted            58%   → 1,160/day   (intent-gated)
  draft accepted as-is or minor edit         74%   →   858/day   (from the eval)
  cost per attempt                       $0.021
  advisor time saved per accepted draft   2.4 min  (measured, not claimed)
  loaded advisor cost                     $38/hr

COST
  per attempt                            $0.0210
  per ACCEPTED draft   = 0.021 / 0.74  = $0.0284       ← the real unit cost
  per day              = 1,160 × 0.021 = $24.36
  per month (22 days)                  = $536

VALUE  (net of time WASTED reading and discarding the 302 rejected drafts —
        the honest number, not the gross one)
  time saved/day    = 858 accepted × 2.4 min      =  +34.3 hr
  time wasted/day   = 302 rejected × 0.3 min      =   −1.5 hr
  net time saved/day                              =  +32.8 advisor-hours
  value/day       = 32.8 × $38         = $1,246
  value/month                          = $27,412

RATIO                                    51×
PAYBACK on a $40k implementation          ~6 weeks
```

**51× is the number you put on the slide — net of the rejected-draft cost, not the gross accepted-draft figure.** A slide built on the gross number (ignoring what rejects cost) overstates the case and is the first thing a sharp CFO will ask about.

### Why the success rate belongs in the denominator

This is the move most people miss:

```
cost per attempt   = $0.021           ← the number in the API docs
success rate       = 74%
cost per SUCCESS   = $0.028           ← the number that's true
                                        (human baseline: 2.4 min × $38/hr loaded
                                         rate = $1.52/item ⇒ still ~54× cheaper)

If the success rate were 40%:
cost per SUCCESS   = $0.053           ← still ~29× cheaper than the human baseline
```

Two conclusions, and the second is the important one:

**The ROI story is robust to a mediocre model.** Even at 40% acceptance the ratio is enormous, because the human baseline is expensive. So "we need a better model to justify the cost" is almost always a false argument at these price points.

**The ROI story is *not* robust to a bad workflow fit.** What kills the economics isn't the model — it's the review burden. Look what happens when acceptance drops and every rejected draft costs advisor time to read:

```
  acceptance 74%:  858 accepted × 2.4 min saved     = +34.3 hr
                   302 rejected × 0.3 min wasted    =  −1.5 hr    → NET +32.8 hr ✅  (the 51× above)

  acceptance 40%:  464 accepted × 2.4 min saved     = +18.6 hr
                   696 rejected × 0.3 min wasted    =  −3.5 hr    → NET +15.1 hr ✅

  acceptance 20% AND rejected drafts take 45s to
  read and discard:
                   232 accepted × 2.4 min           =  +9.3 hr
                   928 rejected × 0.75 min          = −11.6 hr    → NET −2.3 hr ❌
```

**At 20% acceptance with a slow review, the system makes advisors slower while the token cost stays trivially cheap.** That's the failure mode to watch: it's a *workflow* failure that no cost dashboard will show you, and it's why review time per item is a first-class metric rather than a UX detail.

---

## 7.2 The four numbers to measure from week one

Instrument these before anyone asks. They take an afternoon and they answer 80% of the questions you'll get for six months.

| Metric | Why | How to get it |
|---|---|---|
| **Cost per attempt** | Input to everything | Token accounting per call, tagged by task |
| **Success rate** (per segment) | The denominator | Your eval + production acceptance tracking |
| **Human time saved per success** | The value side. **Measure it — don't accept a claim** | Time the task with and without, on real users. 20 samples is enough |
| **Human time spent on rejects** | The hidden cost that kills cases | Instrument the review UI: seconds per item |

> **Measure the human baseline yourself.** The customer's estimate of how long the task takes is reliably wrong, usually low by 30–50%, because they're remembering the fast case. Sit with someone and time twenty of them. This single measurement is often the strongest thing in your final business case, and it takes two hours.

---

## 7.3 Where the money actually goes

Cost shape differs sharply by architecture, and knowing which regime you're in tells you where to optimise.

| Architecture | Dominant cost | Lever that matters |
|---|---|---|
| **Single-shot generation** (draft a reply, classify, extract) | Token spend, roughly linear in volume | Model tier, prompt length, caching |
| **RAG** | Tokens, plus retrieval infra | Context length — the biggest single lever. Rerank so you can send less |
| **Agent loop** | **Tokens, dominated by the loop multiplier** | Step count, early abandonment, prompt caching on the stable prefix |
| **Classical ML + LLM only at the edges** | Infra, not tokens | Usually already cheap. Don't add an LLM to the hot path |
| **On-prem / edge inference** | Hardware amortisation | **Duty cycle decides build-vs-rent** |

Two of these carry a non-obvious lesson worth having ready.

**Agent loops multiply everything.** In the [dev-tools design](../28_ai-system-design-by-industry/12_devtools_coding_agent/), LLM spend is **96% of total system cost** — because every call in a 46-step loop pays again. That's the inverse of the fraud and manufacturing designs where storage and hardware dominate. So in an agentic engagement, step count *is* the cost model, and early abandonment is a first-class feature rather than an optimisation.

**Duty cycle inverts the cloud default.** In the [manufacturing design](../28_ai-system-design-by-industry/06_manufacturing_cv_inspection/), continuous inference on 12 production lines costs **~$210k/month rented versus ~$2.7k/month amortised on-prem — about 75× cheaper to own.** Cloud is right for spiky workloads and badly wrong for continuous ones. Most engineers default to cloud out of habit rather than analysis; being able to name the discriminator (duty cycle) is a strong signal.

---

## 7.4 The levers, in order

When cost is over budget, work this order.

| # | Lever | Typical saving | Cost of pulling it |
|---|---|---|---|
| 1 | **Don't call the model** — gate on a cheap classifier first | **50–90%** | Hours. Often the single biggest win |
| 2 | **Template the structured parts** | 40–70% | Hours, and the output usually gets *better* |
| 3 | Prompt caching on the stable prefix | 20–50% on repeated context | Trivial |
| 4 | Cut context length (rerank, send less) | 20–40% | Hours; also improves accuracy |
| 5 | Route by difficulty — small model first, escalate | 30–60% | A day. Needs a confidence signal |
| 6 | Smaller model everywhere | 60–90% | Accuracy cost; measure on the eval suite |
| 7 | Cache identical/near-identical requests | 10–30% | Cache-invalidation risk |
| 8 | Batch where latency allows | 20–50% | Only if the workflow tolerates delay |

### Lever 1 is the one people skip

The biggest cost win is usually **not calling the model at all.**

In the running example, 42% of inbound messages should never reach the drafter — they're reschedules, approvals, and complaints. A cheap intent classifier in front cut spend by 42% *and* improved safety, because complaints must never be auto-drafted. **The cost optimisation and the correctness requirement were the same change.** That happens more often than you'd expect, and it's worth looking for deliberately.

Similarly in the [e-commerce design](../28_ai-system-design-by-industry/01_ecommerce_shopping_agent/): triggering the agent only on high-intent sessions took cost from **$4.34M to $52k/month** — an ~83× reduction from deciding *when* to invoke, not how.

### Lever 2, with the worked case

The [travel design](../28_ai-system-design-by-industry/10_travel_planning_assistant/) has the cleanest example. The naive design narrates three itineraries with a frontier model:

```
narration = 3 × (2,200 in + 350 out) = $0.0356/session   ← 95% of session cost
at a 4% book rate: $0.0356 / 0.04    = $0.935 per booking
ceiling                              = $0.250 per booking      ✗  3.7× OVER
```

The fix isn't a smaller model — it's **not using a model.** An itinerary is a table; rendering it as a table costs nothing and reads better. The LLM writes one comparative sentence: *"the 07:40 saves two hours for ₹1,800 more."* Result: ~$0.010/session, ~$0.25/booking.

> **The general rule, and it's the most common cost error in agent designs:** *using an LLM where a template suffices.* Structured data has a structured presentation. Paying frontier rates to produce a worse table is the archetypal mistake, and the arithmetic catches it before shipping.

---

## 7.5 The business case one-pager

What you hand the person who signs. One page, and it should survive being forwarded without you in the room.

```markdown
# [Use case] — Business case

## The outcome
Advisors spend 34 fewer hours/day on status replies.        ← outcome, not feature

## Measured, not estimated
  Human baseline:      2.4 min/reply, timed over 20 samples with 3 advisors
  Volume:              2,000 inbound/day; 1,160 drafting-eligible (58%, measured)
  Acceptance:          74% as-is or minor edit (150-example labelled eval)
  Review cost:         18 s/item average (instrumented)

## Cost
  Per attempt          $0.021
  Per accepted draft   $0.028         ← success rate in the denominator
  Per month            $536
  Implementation       $40,000 one-off

## Value  (NET of rejected-draft review time — see 07.1)
  32.8 advisor-hours/day × $38/hr = $1,246/day = $27,412/month

## Ratio and payback
  51× ongoing · ~6 weeks payback

## What would break this
  1. Acceptance below ~25% with review >45s/item makes it NET NEGATIVE
     → monitored; alarm at acceptance <50%
  2. Volume below 600/day makes implementation payback >6 months
  3. Advisor review capacity is the ceiling: 1 advisor can review ~200/day

## What we are NOT claiming
  Not headcount reduction. Advisors handle more customers, not fewer advisors.
  (Say this explicitly — someone will otherwise assume it, and it changes
   who supports the project.)
```

The last two sections are what make it credible. **A business case with no failure conditions reads as a sales document.** Naming the two conditions under which your own project is a bad idea is what makes the 51× believable — and it pre-commits you to monitoring the right thing.

---

## 7.6 Latency economics

Latency is a cost, in a currency the finance conversation doesn't capture.

| Latency | Effect on the workflow |
|---|---|
| < 1 s | Feels instant; the user stays in flow |
| 1–3 s | Fine for a considered action. Advisors between customers tolerate this |
| 3–10 s | The user context-switches. **You've now added a task-resumption cost that can exceed the time saved** |
| > 10 s | Must be asynchronous. Redesign the workflow, don't just add a spinner |

> **The non-obvious point:** a 12-second response that saves 2 minutes of work often doesn't get used, because the user tabs away and loses the thread. **Latency below the context-switch threshold is worth more than accuracy above the review threshold.** Measure how long users actually wait before switching — it's usually 4–6 seconds — and treat that as a hard budget.

And when you can't hit it: make the wait *productive*. Stream. Show the retrieved evidence first while the draft generates. The [e-commerce design](../28_ai-system-design-by-industry/01_ecommerce_shopping_agent/) budgets time-to-first-token at ~1,140ms against a 1,200ms SLO for exactly this reason — perceived latency is the metric, not total latency.

---

## 7.7 Common mistakes

> - **Mistake:** Quoting cost per token or per call → **Why it's wrong:** it's not a business number, and it ignores the success rate → **Do instead:** cost per successful outcome.
> - **Mistake:** Accepting the customer's estimate of the human baseline → **Why it's wrong:** reliably 30–50% low, because they remember the fast case → **Do instead:** time twenty real instances yourself.
> - **Mistake:** Ignoring the cost of rejected outputs → **Why it's wrong:** at low acceptance with slow review, the system makes people *slower* while looking cheap → **Do instead:** instrument seconds-per-review and put it in the model.
> - **Mistake:** Optimising the model tier before the invocation gate → **Why it's wrong:** not calling the model is a 50–90% saving; a tier change is 60% with an accuracy cost → **Do instead:** gate first.
> - **Mistake:** Using an LLM to render structured data → **Why it's wrong:** the most common cost error in agent designs, and it produces a worse artifact → **Do instead:** template it; use the model for the judgement.
> - **Mistake:** Defaulting to cloud inference → **Why it's wrong:** for continuous high-duty-cycle workloads, owning can be ~75× cheaper → **Do instead:** let duty cycle decide.
> - **Mistake:** A business case with no failure conditions → **Why it's wrong:** reads as sales material and doesn't survive scrutiny → **Do instead:** name the two conditions that make your own project a bad idea.
> - **Mistake:** Treating latency as a UX detail → **Why it's wrong:** past the context-switch threshold the time saved evaporates → **Do instead:** measure it, budget for perceived latency, stream.
> - **Mistake:** Claiming headcount reduction without being asked → **Why it's wrong:** it changes who supports the project, usually badly → **Do instead:** state explicitly what you're not claiming.

---

## 7.8 Interview signal

Expect: *"How would you evaluate whether this is worth building?"* or *"The customer says it's too expensive. What do you do?"*

> "First I'd reframe the number. Cost per call isn't a business number — the number that matters is cost per successfully completed outcome, with the success rate in the denominator. If it's $0.021 per attempt at 74% acceptance, the real unit cost is $0.028, and I'd put that against a measured human baseline. And I'd measure that baseline myself rather than take their estimate, because customers are reliably 30–50% low — they remember the fast case.
>
> Usually that arithmetic ends the conversation, because at these price points the ratio against a loaded human hour is often 50× or more. What's interesting is that the ROI story is robust to a mediocre model but *not* to a bad workflow fit. If acceptance drops to 20% and reading each rejected output costs 45 seconds, the system makes people slower while the token bill stays trivially cheap. So I instrument review time per item as a first-class metric, not a UX detail.
>
> If it's genuinely over budget, I'd work the levers in order of saving-per-hour-of-work, and the first one is *don't call the model* — a cheap classifier gating which requests reach it. In one case that was 42% of traffic that should never have hit the expensive path, and the cost fix and the safety fix turned out to be the same change. Second is templating anything structured, which is the most common cost error I see — paying frontier rates to render a table that reads better as a table. Model tier comes much later, because it trades accuracy and the gate doesn't.
>
> And I'd hand over a one-pager with the two conditions under which this is a bad idea, because a business case without failure conditions reads as a sales document and doesn't survive being forwarded."

---

> ← [`06-agents-tools-and-integration.md`](06-agents-tools-and-integration.md) · **Index:** [`README.md`](README.md) · **Next:** [`08-security-and-enterprise-blockers.md`](08-security-and-enterprise-blockers.md) →
