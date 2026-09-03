# 03 · Discovery and scoping

> ← [`02-the-demo-to-production-gap.md`](02-the-demo-to-production-gap.md) · **Index:** [`README.md`](README.md) · **Next:** [`04-evals-are-the-deliverable.md`](04-evals-are-the-deliverable.md) →

---

## 3.1 What discovery is for

Not requirements gathering. You're answering three questions, in this order:

1. **Is there a real workflow here?** (Someone does this task today, repeatedly, and you can name them.)
2. **Is the value real and attributable?** (If it worked perfectly, something measurable changes.)
3. **Is it buildable in this environment?** (Data, access, review capacity, compliance.)

Any "no" means qualify out or reshape. **Discovering a "no" in week two is a success**; discovering it in month four is the characteristic FDE failure.

The mistake is treating discovery as a phase that ends. It doesn't — but the *concentrated* version happens in the first two weeks, and what you learn there determines whether the next five months are worth anything.

---

## 3.2 The questions that actually work

Bad discovery asks about pain points and gets a wish list. Good discovery asks about **observable behaviour** and gets the truth.

### The workflow questions

| Ask | Why it works |
|---|---|
| **"Walk me through the last time someone did this. What did they open first?"** | Gets the *actual* workflow, not the described one. People describe their process as tidier than it is. "First they open the DMS, then paste into Excel, then check Slack" — that's three systems the org chart didn't mention |
| "Can I watch someone do it?" | Two hours of shadowing beats ten hours of meetings. **Ask for this on day one; it's the highest-value request you'll make** |
| "How long does it take, and what's the slowest part?" | Locates the bottleneck, which is often not where the AI would go |
| "What do they do when the information isn't there?" | Reveals the honest-refusal requirement most designs skip |
| "Who else touches this before it's done?" | Finds the stakeholders who weren't invited to this meeting and will veto in month three |

### The value questions

| Ask | Why it works |
|---|---|
| **"If this worked perfectly, what would you stop doing?"** | The sharpest question in the set. If nobody can answer, **there is no value** — only interest. Vague answers here predict a dead pilot |
| "How many of these per day? Per peak day?" | Cost and latency arithmetic; also whether it's worth doing at all |
| "What's the cost of being wrong, in money?" | Sets your thresholds. Asymmetric costs change the whole design ([07](07-unit-economics.md)) |
| "What happens today when it goes wrong?" | Reveals error tolerance. A workflow with a downstream check tolerates 80%; one that emails a customer directly does not |
| "Who gets the credit if this works?" | Cynical, and it identifies your real champion |

### The feasibility questions

| Ask | Why it works |
|---|---|
| **"Where does the data live, who owns access, and how long does an access request take?"** | The real blocker, always. Ask in week one for what you need in week three |
| "Who checks the output, and how many can they check per shift?" | **Sets your operating threshold — see 3.5. This is the question most people never ask** |
| "Has anyone tried to automate this before? What happened?" | The graveyard tells you the constraint. "We tried in 2022 and legal killed it" is the most useful sentence in discovery |
| "What would your security team need before this touches customer data?" | Starts the 7-week clock now instead of in month three |
| "Is there a system of record I'd need to write to?" | Read-only pilots ship; write integrations are a different project |

### The two questions I'd never skip

> **"Show me the five worst examples, not the five best."**
>
> Everyone offers clean examples. The distribution of *hard* cases determines your accuracy, and asking for it signals you've done this before. You'll also learn whether they *have* hard examples catalogued — if not, nobody has measured this task.

> **"When we hit 80% instead of 99%, what do we do with the other 20%?"**
>
> Asked in week one, this is a design question and they'll engage. Asked in month three, it's an excuse and they'll hear it as one. **The answer to this question is your actual product architecture** — it tells you whether you're building automation or a review queue.

---

## 3.3 The shadowing session

Two hours watching one person work is worth more than any interview. What to record:

| Watch for | Because |
|---|---|
| Every application they open | The integration surface. Usually 2× what you were told |
| Copy-paste between systems | Each one is a missing API and a manual step you could remove |
| Where they hesitate | Genuine ambiguity — these become your hard eval cases |
| What they check twice | Their own trust threshold; tells you what your output must show |
| Shortcuts and workarounds | The real process. Also where the undocumented business logic lives |
| Interruptions | Fragmented attention shapes the UX. An advisor between two customers won't read a paragraph |
| **What they ignore** | Fields, alerts, and screens nobody looks at. Don't build another one |

Then ask, at the end: *"What did you do just now that you'd do differently if you had more time?"* That's where quality is currently being traded away, and it's often the real opportunity.

---

## 3.4 Red flags

Ranked by how reliably each one predicts a dead engagement.

| Red flag | What it means | What to do |
|---|---|---|
| **Nobody can name the person who does this task today** | There is no workflow. You're building for an imagined user | Stop. Find the real task or qualify out |
| **"We want to use AI"** with no named problem | Solution hunting for a problem, usually board-driven | Reframe hard: "what's the most expensive repeated decision your team makes?" Or decline |
| **Champion can't get you data access** | They lack the authority to make this succeed | Escalate to someone who can, in week one. If nobody, the deal dies in month three |
| **Success criteria change between meetings** | No single owner, or competing agendas | Force a written definition signed by one named person before building |
| **"It just needs to feel right"** | Unshippable — no measurable target | Convert to a rubric with the expert ([04](04-evals-are-the-deliverable.md)) or don't start |
| **"We need 99% accuracy"** with no error-cost analysis | They haven't thought about it. Sometimes 99% is genuinely needed; usually 85% + review is better and cheaper | Run the error-cost conversation ([10](10-stakeholder-communication.md)) |
| **No one will own it after you leave** | Guaranteed decay, however good it is | Make naming an owner an exit criterion |
| **The reviewer has no spare capacity** | Your review queue has nowhere to go, so thresholds will be forced loose | Design for their actual capacity from the start (3.5) |
| **Legal/security not yet involved and "it'll be fine"** | 7 weeks of unpriced calendar | Get them in a room in week one |
| Enthusiasm concentrated in one person | Single point of failure; champions change jobs | Build a second relationship deliberately |

> **The two-flag rule:** one red flag is a thing to manage. Two or more from the top five means the engagement will probably fail, and your most valuable contribution is saying so early and clearly, with the reasoning written down. That's not defeatism — it's the finding, and it's what you're paid for.

---

## 3.5 The question almost nobody asks

> **"Who reviews the output, and how many can they review per shift?"**

This single answer determines your operating threshold, and it's usually discovered too late.

The pattern recurs across essentially every human-in-the-loop AI system. In the twelve worked designs in [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md), **human review capacity — not model quality — set the operating threshold in five of them**:

| Design | The capacity that set the threshold |
|---|---|
| [Banking fraud](../28_ai-system-design-by-industry/02_banking_fraud_detection/) | 1,200 analyst cases/day = 0.00046% of transactions |
| [Manufacturing CV](../28_ai-system-design-by-industry/06_manufacturing_cv_inspection/) | One quality engineer per line ⇒ review capped at ~3% of units |
| [Insurance claims](../28_ai-system-design-by-industry/07_insurance_claims_automation/) | Handler queue depth caps straight-through economics; SIU capacity caps fraud-referral precision |
| [HR recruitment](../28_ai-system-design-by-industry/11_hr_recruitment_matching/) | Recruiter reading capacity ⇒ only top-N ranking quality matters |
| [Dev-tools agent](../28_ai-system-design-by-industry/12_devtools_coding_agent/) | PR review capacity, which becomes *the* bottleneck at scale |

### Why it matters so concretely

Suppose your classifier can hit 85% precision at 60% recall, or 70% precision at 90% recall. Which do you ship?

**You cannot answer without the capacity number.**

```
Volume: 2,000 items/day
Reviewer capacity: 1 person × 6 hrs × 40 items/hr = 240 items/day  (12% of volume)

Option A — 85% precision, 60% recall:
    flags ~14% of volume = 280 items/day  →  EXCEEDS capacity by 17%
    → queue grows daily → within a week someone waves items through uninspected
    → which is the worst outcome available, because it's invisible

Option B — 70% precision, 90% recall:
    flags ~26% of volume = 520 items/day  →  EXCEEDS capacity by 117%
    → collapses immediately

Option C — 92% precision, 40% recall:
    flags ~9% of volume = 180 items/day   →  FITS, with 25% headroom
    → catches less, and every caught item actually gets looked at
```

Option C is worse on every model metric and it's the right answer — until they staff a second reviewer, at which point A becomes viable. **The threshold is a staffing decision wearing a modelling costume.**

And note the failure mode in Option A: an unbounded queue doesn't fail loudly. It fails by someone under pressure approving a batch without reading it, which looks like success in every dashboard. If capacity is exceeded, the honest design *auto-tightens the threshold and logs the trade* rather than letting the queue rot — that's the pattern used in the manufacturing and claims designs above.

---

## 3.6 Scoping: from a wish to a first milestone

Customers describe end states. Your job is to find the smallest slice that proves or kills the thesis.

### Slicing rules

| Rule | Why |
|---|---|
| **Slice by decision, not by feature** | "Draft replies to answerable status questions" beats "handle inbound messages" |
| **Read-only before write** | A write integration adds auth, idempotency, rollback, and a compliance review. Prove value read-only first |
| **One user, one workflow, one data source** | Every extra one multiplies integration and disagreement |
| **Pick the slice with the cheapest ground truth** | If you can't label it, you can't improve it |
| **Deliberately include the hard segment** | A slice that excludes ambiguity proves nothing. Include it and route it to review |

### The scoping one-pager

Write this, get it signed, before building. One page, and it settles most later arguments.

```markdown
# [Use case] — Scope v1

## The decision we're automating
One sentence. Not a feature — a decision someone makes today.

## Who does it today
Name/role. Volume per day and per peak day.

## In scope (v1)
- ...   (3–5 bullets max)

## Explicitly OUT of scope (v1)
- ...   ← THE MOST IMPORTANT SECTION. What they'll assume is included.

## What "good" means
Metric, target, and how it's measured. Names the eval set.

## The human-in-the-loop design
Who reviews what, at what volume, with how much capacity.
Threshold implied by that capacity: ___

## Data we need
Source · owner · access status · request date · expected date

## Assumptions we're making
Numbered. Each one a thing that would change the design if wrong.

## Open questions blocking us
Numbered, each with an owner and a date.

## Production exit criteria         ← see 09; write this NOW, not later
Accuracy on the golden set: ___
Volume: ___    p95 latency: ___
Reviewer capacity allocated: ___
Security review: scheduled by ___ on ___
Named owner after handover: ___
Signed: ______________ (the person who can say no)
```

> **The "explicitly out of scope" section earns its place every time.** Half of all scope disputes are about something never discussed. Writing them down converts a future argument into a present, cheap conversation — and it's much easier to add something to v2 than to remove it from someone's expectation of v1.

---

## 3.7 Qualifying out without getting fired

Sometimes the honest answer is "not this, not yet." Delivering that is a skill.

### The structure that works

**1. Lead with what you found, not with the verdict.**
> "I spent the week with three of your adjusters and pulled 200 real claims."

**2. Give the specific blocker, with a number.**
> "Of those 200, 61% are missing at least one field the coverage decision needs — the data isn't in the system at intake, it comes in later by email. So an automated decision would be guessing on six of ten claims."

**3. Say what that means plainly.**
> "That means an auto-decision product can't hit a defensible accuracy bar on this data, however good the model is. I don't want to build something that looks like it works."

**4. Bring the adjacent thing that *is* buildable.** This is the step that keeps you hired.
> "But the same week showed something else. Your adjusters spend about 40 minutes per claim finding and re-keying those missing fields from email threads. That's an extraction problem on documents you already have, ground truth is cheap because the adjuster's own final entry *is* the label, and it's read-only so no compliance review. If we cut 40 minutes to 8, that's the same business outcome by a different route."

**5. Offer the decision, don't make it.**
> "I think that's the better first project. Happy to be wrong — if you'd rather test the auto-decision thesis anyway, I'd want two weeks and an agreement that we kill it if the field-completeness number holds."

### Why this works

You've demonstrated you did the work, you've been specific rather than pessimistic, you've protected them from a failure, you've kept the value conversation alive, and you've left them in control. **The customer who hears this well becomes a reference; the one who hears "no" without an alternative becomes a churn risk.**

And in the rare case they insist on the doomed path: state the concern once in writing, agree a kill criterion, and then build it properly. Repeating the objection is not diligence, it's insubordination with extra steps. Their business, their call — your job is to make sure the decision was informed.

---

## 3.8 Discovery output artifacts

Discovery produces four things. If you have all four in two weeks, you're ahead.

| Artifact | Why it matters |
|---|---|
| **The scoping one-pager, signed** | Settles later disputes; forces a single owner |
| **A stratified sample of real data**, with the distribution documented | The single most valuable technical asset you'll acquire. Everything downstream depends on it |
| **A red-flag / risk register** with owners and dates | Makes the invisible schedule risk visible |
| **The human baseline number** (even a rough one) | You cannot have an accuracy conversation without it — [04](04-evals-are-the-deliverable.md) |

---

## 3.9 Interview signal

Discovery shows up in the loop as: *"A customer says they want to use AI to improve their support operation. What do you do?"*

Weak answers start proposing architectures. Strong answers ask questions, and the *choice* of questions is the signal:

> "First I'd want to watch someone do the job for two hours — the described workflow and the real one are never the same. Then five questions. What would you stop doing if this worked perfectly, because if nobody can answer that there's interest but no value. How many of these per day and per peak day, for the cost and latency arithmetic. Who reviews the output and how many can they review per shift — that number sets my confidence threshold, and it's the question people skip. What's the cost of being wrong in money, because asymmetric error costs change the whole design. And where does the data live, who owns access, how long does a request take — I want to file that request in week one for what I need in week three. Then I'd ask for their five *worst* examples, not their best, because the hard distribution is what determines whether this lands."

That answer signals you've been burned before, which is exactly the signal the round is testing for.

---

> ← [`02-the-demo-to-production-gap.md`](02-the-demo-to-production-gap.md) · **Index:** [`README.md`](README.md) · **Next:** [`04-evals-are-the-deliverable.md`](04-evals-are-the-deliverable.md) →
