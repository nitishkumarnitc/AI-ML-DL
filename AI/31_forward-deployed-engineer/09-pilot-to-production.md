# 09 · Pilot to production

> ← [`08-security-and-enterprise-blockers.md`](08-security-and-enterprise-blockers.md) · **Index:** [`README.md`](README.md) · **Next:** [`10-stakeholder-communication.md`](10-stakeholder-communication.md) →

---

## 9.1 The trap

Most AI pilots don't fail. They **succeed and then dissolve.**

The pattern is so consistent it's almost a script:

```
Week 1-3    Pilot built. Works well on the curated set. Demo goes brilliantly.
Week 4-8    A few users try it. Positive. "This is great, when can we roll out?"
Week 9-12   Enthusiasm plateaus. Usage drifts down. The FDE is pulled to a new account.
Week 13+    "We're still evaluating." Nobody says no. Nobody says go.
Month 6     Quietly not mentioned in the QBR.
```

Nothing broke. There was never a defined finish line, so nothing ever crossed it.

### Why "no exit criteria" is fatal rather than merely untidy

| Without written criteria | With them |
|---|---|
| "Is it good enough?" is a matter of opinion, re-litigated monthly | It's a measurement, settled once |
| Every stakeholder has a private bar | One bar, agreed, visible |
| Success is unfalsifiable, so it's also unclaimable | You can declare done and mean it |
| The decision needs a champion with energy | The decision is pre-made; it just needs the number |
| Scope creeps to fill the ambiguity | New requests are visibly v2 |

> **The single highest-leverage thing an FDE does in week one is write down what production means, and get one named person to sign it.** Everything in this file is downstream of that.

---

## 9.2 The exit-criteria document

Written in week one — **not at the end of the pilot**, when writing it looks like moving the goalposts.

```markdown
# [Use case] — Production exit criteria
Owner (can say go/no-go): __________________     Date agreed: ________

## 1. Quality
  Metric:            production-weighted pass rate on golden_v3 (150 examples)
  Bar:               ≥ 70%
  Blocking dims:     fabricated_fact = 0, dishonest_when_unknown = 0
  Measured by:       eval harness in CI, run by [their engineer], not by us
  Human baseline:    88% expert agreement (κ 0.79) — the ceiling, for context

## 2. Volume and performance
  Volume:            1,160 drafting-eligible messages/day, peak 1,800
  p95 latency:       < 3 s
  Availability:      99.5%, degraded mode = advisor writes manually

## 3. The human loop
  Reviewer:          the service advisor, in-flow
  Capacity:          ~200 reviews/advisor/day at 18 s each
  Threshold implied: auto-draft only the ≤ 12% band that fits capacity
  Escalation:        complaints never auto-drafted (hard rule, not a threshold)

## 4. Enterprise gates
  Security review:   owner ______, booked for ______      status: ______
  DPIA:              required? Y/N   owner ______         status: ______
  SSO / RBAC:        IdP ______, owner ______             status: ______
  Audit logging:     per-decision record, retention ___   status: ______
  Kill switch:       operable by ______ without engineering

## 5. Operational readiness
  Runbook:           written, and ______ has executed it end-to-end once
  Dashboards:        [named], readable by someone who didn't build them
  Alerts:            routed to ______ (a rota, not a person)
  Rollback:          rehearsed on ______

## 6. Handover
  Named owner after we leave:  ______________
  They have:  repo access · eval harness · runbook · on-call rota entry
  They have DONE:  one eval run · one rollback · one incident dry-run

## 7. Explicitly NOT in v1
  - ...        ← the section that prevents half of all scope disputes

## Sign-off
  ______________ (owner)      ______________ (security)     ______________ (us)
```

### The three lines that do the most work

**"Measured by: eval harness in CI, run by *their* engineer."** If only you can produce the number, the number isn't trusted and the handover hasn't happened.

**"They have DONE: one eval run, one rollback, one incident dry-run."** Having access is not the same as having done it. A runbook nobody has executed is fiction — see 9.5.

**Section 7.** Every scope dispute I've seen was about something never discussed. Writing it down converts a future argument into a cheap present conversation.

---

## 9.3 Ratchet the pilot toward reality

A pilot that stays comfortable proves nothing. Each stage should remove one crutch.

| Stage | What's real | What crutch is removed | What you learn |
|---|---|---|---|
| **0 · Bench** | Curated examples, you drive | — | Approach is viable |
| **1 · Shadow** | **Real live traffic**, output logged, nobody sees it | Curated data | The true distribution. **The cheapest, most under-used stage** |
| **2 · Assisted** | Real users see output, one workflow, you're on call | Your hand on the wheel | Whether people actually use it |
| **3 · Default** | It's the default path; opt-out available | Your presence | Whether it survives a bad day |
| **4 · Production** | Scaled, integrated, owned by them | You | Whether it survives *you* |

### Shadow mode is the stage people skip

Running against live traffic with the output going nowhere costs almost nothing and answers the questions that matter:

- What's the **real** input distribution, versus the sample you were given?
- What's the accuracy on it, un-curated?
- What's the p95 latency at real volume, and real peak?
- What does it actually cost per day?
- Which segments fail, and are they the ones you predicted?

> **Shadow mode is free evidence.** It's the reason the [manufacturing design](../28_ai-system-design-by-industry/06_manufacturing_cv_inspection/) runs shadow → canary → fleet, and why the [dev-tools design](../28_ai-system-design-by-industry/12_devtools_coding_agent/) insists offline evaluation systematically overstates real performance. If you take one process idea from this file, take this one: **never go from bench to users without a week of shadow.**

### The gate between stages

Don't advance on enthusiasm. Advance on a number:

```
0 → 1   eval pass rate ≥ bar on the golden set; blocking dims clean
1 → 2   shadow accuracy within 5pp of golden-set accuracy
        (a bigger gap means your golden set is unrepresentative — fix that first)
2 → 3   ≥ 60% of users choose it when it's optional; review time ≤ budget
3 → 4   all of section 4 and 5 of the exit-criteria doc, signed
```

The `1 → 2` gate is subtle and valuable: if shadow accuracy is far below golden-set accuracy, **your eval set is wrong**, and fixing that is more urgent than fixing the model.

---

## 9.4 What "production" actually requires

Beyond the code working. Walk this and mark each row done / not-done.

```
CORRECTNESS
  [ ] Eval in their CI, gating merges, run by their engineer
  [ ] Accuracy known PER SEGMENT, not just aggregate
  [ ] Blocking checks enforced in code, not prompt instructions
  [ ] A held-out slice never used for iteration

RELIABILITY
  [ ] Timeouts, retries, backoff on every external call
  [ ] Idempotency on every write
  [ ] Explicit unknown state where a timeout is ambiguous
  [ ] Honest refusal path users trust
  [ ] Degraded mode defined, and it's a working product not an error page

OPERATIONS
  [ ] p95 measured at real peak, not estimated
  [ ] Cost per successful outcome tracked, with a budget alarm
  [ ] Dashboards a non-author can read
  [ ] Alerts routed to a ROTA, not a person
  [ ] Prompt/model/config versioned; rollback rehearsed
  [ ] Kill switch operable without engineering

ENTERPRISE
  [ ] Security review closed, findings remediated
  [ ] Audit record per decision, retention agreed
  [ ] SSO / RBAC live
  [ ] Data residency confirmed in writing

PEOPLE
  [ ] Users trained; at least one internal advocate
  [ ] Named owner, who has done a real eval run and a real rollback
  [ ] Runbook executed end-to-end by someone who isn't you
  [ ] Exit criteria signed
```

---

## 9.5 The handover that actually works

The test of a handover is not "did I write documentation." It's **can this survive an incident at 2am with me unreachable.**

### Documentation nobody reads vs documentation that works

| Doesn't work | Works |
|---|---|
| A 40-page design doc | A one-page runbook with the five things that go wrong and what to do |
| "Here's the repo" | A recorded 30-minute walkthrough of the three files that matter |
| A README | **A dry-run where they break it and fix it while you watch** |
| Slack availability "if you need anything" | A dated end-of-support with a named escalation path |

### The four-part handover

**1. The runbook, structured by symptom not by component.** Nobody at 2am reads a component diagram. They read symptoms.

```markdown
# Runbook — draft-reply service

## Symptom: advisors report drafts are wrong / weird
1. Check the model-version dashboard. Did a deploy land in the last 24h?
   → if yes, roll back: `./rollback.sh <previous_version>` (takes ~40s)
2. Check the eval dashboard. Did the nightly run regress?
   → if pass rate dropped >5pp, roll back and page [rota]
3. Check the drift panel: are inbound message lengths/formats unusual?
   → a DMS export change upstream is the usual cause. Contact [their DMS owner]
4. If none of the above, the model is probably NOT the problem.
   Check whether the notes themselves changed — pull 10 recent notes and read them.

## Symptom: latency high / advisors waiting
...

## Symptom: cost alarm fired
...

## Symptom: it's producing nothing at all
...

## How to turn it off
`./kill-switch.sh` — or in the admin UI, Settings → AI Drafting → Disable.
Advisors fall back to manual composition. No data is lost. Safe to leave off.
```

**2. The dry run.** Sit with the new owner and have them do it: run the eval suite, roll back a version, trigger and silence an alert, operate the kill switch. **This is the actual handover.** Everything else is preparation for it.

**3. A dated end of support.** "I'm on call for you until 30 April; after that the path is [rota], and I'm reachable via [AE] for anything genuinely stuck." Open-ended availability sounds generous and prevents ownership from ever transferring.

**4. The decision log.** The single most valuable artifact for whoever inherits this, because it prevents them undoing your work for reasons you already considered.

```markdown
## Why complaints are never auto-drafted
Not a threshold — a hard rule. Liability: a templated apology to a genuinely
angry customer escalates. Reviewed with [legal contact] on 12 Feb.
Do not "improve" this by adding a confidence threshold.

## Why we send facts through a verbatim check instead of prompting
Prompt-level "never invent a price" was violated on 11/150 examples (v6).
Instructions are priors, not guarantees. See evals/CHANGELOG.md v7.

## Why the eval set oversamples insufficient-note cases
31% of real notes can't answer the question asked. A set without them showed
91% and production showed 68%. Keep the stratification.

## Why we did NOT build the write-back integration
Scoped out of v1 deliberately: needs a new service account, a sandbox they
don't have, and a compliance review. Revisit when acceptance >70% sustained
for a quarter — that's the evidence that makes the security conversation easy.
```

---

## 9.6 Making yourself redeployable

If you're the runbook, you're stuck — and so is the account, because your company can't send you anywhere else.

| Signal you're stuck | Fix |
|---|---|
| Only you can run the eval | Put it in their CI; watch their engineer run it |
| Only you know why a threshold is set where it is | Decision log |
| You're in their on-call rota | Get a named owner into it before you leave |
| They Slack you directly for routine questions | Route through the rota deliberately, from day one of handover |
| The demo only works when you drive it | That's not a product yet |

> **The honest incentive problem:** being indispensable feels like job security and is the opposite. An FDE who can't leave has one account; an FDE who leaves working systems behind has a track record. Optimise for the second.

---

## 9.7 When to kill it

Sometimes the right call is to stop. Say it clearly and early.

| Signal | Reading |
|---|---|
| Shadow-mode accuracy far below golden-set, and the gap is data not model | The information isn't there. No model fixes it |
| Users don't choose it when it's optional | It's not solving their problem, whatever the metrics say |
| Review time exceeds time saved | Net negative — see the [07](07-unit-economics.md) arithmetic |
| Nobody will own it after handover | It will decay; ship it anyway and it becomes a liability |
| The champion has left and nobody replaced them | Find a new champion or stop |
| Exit criteria have been renegotiated twice | There is no bar, so there is no finish line |

The framing that keeps you trusted:

> "I want to be straight with you. We're at 68% on the golden set, and the gap to the 80% bar we agreed is almost entirely one segment: the 31% of repair orders where the note genuinely doesn't contain the answer. No model fixes that — the information isn't recorded. So I'd rather stop here than spend another six weeks appearing to make progress.
>
> Two options. We can narrow the scope to the answerable 69%, which hits the bar comfortably and still saves your advisors about 22 hours a day. Or we go upstream and fix note quality at intake, which is a bigger project with a bigger payoff. What I don't recommend is continuing as-is."

You've killed the current shape, kept the value alive, and been the person who told them the truth first. **That's the reputation worth having.**

---

## 9.8 Interview signal

Expect: *"Your pilot went well but it's been 'in evaluation' for three months. What happened, and what would you do differently?"*

> "What happened is there was never a written finish line, so 'is it good enough' stayed a matter of opinion and got re-litigated every month until the energy ran out. Nothing broke — the pilot just never crossed a line that didn't exist.
>
> What I'd do differently is write the production exit criteria in week one, before the pilot starts, and get one named person to sign it. Accuracy bar on a specific golden set with the blocking dimensions called out; volume and p95; who reviews the output and what their actual capacity is; which enterprise gates apply and who owns each; and a named owner after handover. Writing it at the end looks like moving the goalposts. Writing it at the start makes the decision pre-made — it just needs the number.
>
> Second thing: ratchet the pilot so each stage removes a crutch, and gate the transitions on numbers rather than enthusiasm. The stage people skip is shadow mode — live traffic, output logged, nobody sees it. It's nearly free and it tells you the real distribution, the real accuracy, the real p95 and the real daily cost. And there's a diagnostic in it: if shadow accuracy is far below golden-set accuracy, my eval set is unrepresentative, and fixing that matters more than fixing the model.
>
> And I'd treat the handover as an event, not a document. The test isn't whether I wrote a runbook — it's whether their engineer has personally run the eval, rolled back a version, and operated the kill switch while I watched. Plus a decision log explaining why things are the way they are, so nobody undoes a deliberate choice six months later for a reason I already considered."

---

> ← [`08-security-and-enterprise-blockers.md`](08-security-and-enterprise-blockers.md) · **Index:** [`README.md`](README.md) · **Next:** [`10-stakeholder-communication.md`](10-stakeholder-communication.md) →
