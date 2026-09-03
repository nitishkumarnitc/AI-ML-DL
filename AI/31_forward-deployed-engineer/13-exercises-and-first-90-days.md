# 13 · Exercises and the first 90 days

> ← [`12-the-interview-loop.md`](12-the-interview-loop.md) · **Index:** [`README.md`](README.md)

---

## 13.1 Drills — do these before the interview, not during it

Role-play is not a reading skill. Reading [10](10-stakeholder-communication.md) and believing you could improvise it under pressure is the single most common overconfidence in this loop.

| Drill | How | Repeat until |
|---|---|---|
| **The non-determinism answer, out loud** | Say [10.3](10-stakeholder-communication.md)'s answer from memory, in your own words, to a mirror or a friend playing the VP | You can do it in under 90 seconds without notes |
| **The kappa pitch** | Explain why 0.5 agreement means "definition workshop, not model" to someone with zero ML background | They understand it on the first pass |
| **The bad-news delivery** | Pick a real slip from your own work history. Deliver it using [10.2](10-stakeholder-communication.md)'s structure: finding → specific number → plain meaning → option | It feels natural, not scripted |
| **Cost teardown** | Take any AI product you use. Estimate cost per attempt, guess a success rate, compute cost per success. Compare to what a human doing the same task would cost | You can do the arithmetic in your head in under a minute |
| **The design-round rejection habit** | For any system design question, force yourself to name one rejected alternative with a reason before describing your chosen approach | It becomes automatic, not an afterthought |
| **Read one `28_` design as a customer conversation** | Pick the design nearest your target company's industry. Read the HLD aloud as if explaining it to that customer, not to an engineer | You naturally translate jargon without being asked to |

> **The mirror drill matters more than it sounds.** The gap between "I understand this technique" and "I can produce it under mild stress in real time" is exactly the gap the interview is measuring, and it's invisible until you actually try to talk without notes.

---

## 13.2 A weekend project that proves the whole thesis

If you want one artifact that demonstrates every idea in this tutorial at once, build this.

**Pick any real, boring workflow you have access to** — your own inbox triage, a friend's small business's customer questions, a public dataset with a plausible business framing. Then:

1. **Discovery, on yourself as the "customer."** Write the scoping one-pager from [03.6](03-discovery-and-scoping.md). What would you stop doing if this worked?
2. **Get a real human baseline.** Time yourself doing the task 15–20 times. This is your kappa proxy if you can rope in a second labeller.
3. **Build the eval harness before the prototype.** Golden set, rubric with at least one blocking dimension, deterministic checks first. Use [11.2](11-the-fde-toolkit.md) or the full version in [04.5](04-evals-are-the-deliverable.md).
4. **Build the smallest thing that could work**, then run it against the eval.
5. **Compute the real unit economics** with [11.4](11-the-fde-toolkit.md)'s calculator. Say honestly whether it's worth it.
6. **Write the one-page business case** from [07.5](07-unit-economics.md), including the section on what would make this a bad idea.
7. **Write a runbook and a decision log**, even though you're the only user.

This takes a weekend and produces something you can talk about concretely in every round of an FDE interview — because it's not a toy demo, it's the actual FDE motion end to end, on a problem small enough to finish.

---

## 13.3 Portfolio spine — what to have ready before you apply

Not a list of projects. A list of **evidence for specific claims** the loop will test.

| Claim the loop tests | Evidence to have ready |
|---|---|
| "I measure before I build" | A kappa number you computed on real data, and what you did with it |
| "I know the difference between demo and production" | A specific project where you can state the demo number and the real number, and explain the gap |
| "I think in unit economics" | A cost-per-success calculation you've actually run, with the failure-cost term included |
| "I ship under ambiguity" | A story where you were handed an underspecified brief and wrote your assumptions down before coding |
| "I handle non-determinism conversations" | The 90-second version of [10.3](10-stakeholder-communication.md), genuinely internalised |
| "I know when to say no" | A real instance of qualifying something out, with the alternative you offered |
| "I design for someone else's mess" | A project with real integration pain — a bad API, a timeout, a partial failure you handled explicitly |

If you're short on real work history for any row, **the weekend project in 13.2 fills all seven** — which is the point of designing it that way.

---

## 13.4 The 30/60/90, written to survive contact

Interviewers ask for this. Most candidates give a plan that's really a wish list. This one is built from the failure modes named throughout the tutorial, so each phase closes a specific risk rather than just describing activity.

### Days 1–30 — discovery, and start every clock that isn't yours

| Do | Closes the risk of |
|---|---|
| Shadow the real user for at least two hours, on the real workflow | Building for an imagined workflow ([01.4](01-what-the-role-actually-is.md), [03.3](03-discovery-and-scoping.md)) |
| Ask the twelve discovery questions from [03.2](03-discovery-and-scoping.md), especially "what would you stop doing" and "who reviews the output" | Solving a problem with no value, or setting a threshold with no capacity number |
| Run the data profiler on the first real sample you get | Discovering data reality in week six instead of week one |
| Run the kappa check with three of their experts on 20–30 examples | Committing to an accuracy target above the human ceiling |
| **File every data-access request you'll need by week six, in week one** | The 15% access-chasing tax that eats every unbudgeted schedule |
| **Ask who runs security review and book a slot, even provisionally** | The 7-week clock starting in month three |
| Write the scoping one-pager and get it signed | Scope disputes about things nobody discussed |

**End of day 30 deliverable:** a signed scope, a data profile, a kappa number, a filed set of access requests, and a booked (or explicitly scheduled) security-review conversation. Notably: **no prototype is required by day 30**, and building one anyway is a trap — see the Demo Machine failure mode in [01.8](01-what-the-role-actually-is.md).

### Days 31–60 — the eval, then the smallest real thing

| Do | Closes the risk of |
|---|---|
| Build the golden set, stratified, including the segment you'd rather exclude | An eval that measures your taste, not the distribution |
| Build the rubric with the customer's expert in the room, blocking dimensions named | An unshippable "it should feel right" standard |
| Build the prototype **against** the eval, not before it | Tuning for three weeks against your own judgement |
| Run shadow mode on live traffic before any real user sees output | Discovering the true distribution after committing to a UI |
| Report the demo-to-real accuracy gap honestly, with the segment breakdown | The single most common way trust breaks in month two |
| Write the exit-criteria document and get it signed | The pilot that dissolves for lack of a finish line |

**End of day 60 deliverable:** a working eval-gated prototype in shadow mode, a signed exit-criteria document, and a clear number for where accuracy stands against the human ceiling.

### Days 61–90 — the production pilot, and make yourself redeployable

| Do | Closes the risk of |
|---|---|
| Move to assisted mode with a small real user group | Skipping straight from shadow to full rollout |
| Instrument cost-per-success and review-time-per-item from day one of assisted mode | Discovering the economics are net-negative after scaling |
| Put the eval in their CI, run by their engineer | An eval that dies with you |
| Write the runbook, symptom-first, and do one dry run with the named owner | A handover that's a document nobody's executed |
| Write the decision log as decisions happen, not retrospectively | Someone undoing a deliberate choice for a reason you already considered |
| Send the weekly written update every week, including the weeks with bad news | Trust decaying silently until a date slips visibly |
| Identify the v2 backlog explicitly, separate from v1 | Absorbing scope creep instead of deferring it visibly |

**End of day 90 deliverable:** a production-pilot-track system with a named owner who has personally run the eval and one rollback, a business case with honest failure conditions, and — critically — **you are not the runbook.** If day 91 arrived and you disappeared, the thing would keep running.

---

## 13.5 The check that ties it together

At any point in the 90 days, one question tells you if you're on track:

> **If I got hit by a bus tomorrow, what would happen to this project?**

Days 1–30: "It would stall, because nothing's built yet — but the scope, the data profile, and the access requests are all written down, so whoever takes over starts from real information instead of zero."

Days 31–60: "The prototype would sit unfinished, but the eval harness and the exit criteria survive intact, so the next person knows exactly what 'done' means and can measure against it."

Days 61–90: "It would keep running, because the eval is in their CI, the runbook has been executed by someone else, and there's a named owner who isn't me."

If your honest answer at any checkpoint is "it would just stop, and nobody would know why or what to do next" — that's the signal to redirect, regardless of how good the underlying work is. **Redeployability is not the last thing you build. It's the property every other artifact in this tutorial is quietly designed to produce.**

---

> ← [`12-the-interview-loop.md`](12-the-interview-loop.md) · **Index:** [`README.md`](README.md)
