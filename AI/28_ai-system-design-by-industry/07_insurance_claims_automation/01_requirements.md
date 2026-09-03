# 07 · Requirements — Insurance: Claims Automation

> **Shared block:** [`../00_requirements_all_systems.md#7-insurance--claims-automation`](../00_requirements_all_systems.md#7-insurance--claims-automation) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the 10.5-minute latency budget, and the ~$12.7k/month cost arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The clock is a hard constraint, and it is not a latency SLO

Every other system in this collection has latency targets that are *product* commitments — miss them and the experience degrades. Here, "0 statutory deadline breaches" is a **regulatory** commitment, and the units are days, not milliseconds.

That difference has three consequences most designs miss.

### A.1 The deadline is per-claim, not per-request

```
p95 ingestion→triage < 15 min      ← a throughput/latency SLO. Violating it is a bad day.
statutory deadline (e.g. 30 days)  ← a legal obligation. Violating it is a penalty and a
                                     regulatory report, per claim, regardless of volume.
```

A system can hit its p95 perfectly and still breach deadlines, because the clock runs during the parts of the process the pipeline does not control: waiting on a claimant document, waiting on a police report, waiting in a handler queue that is four days deep. **The clock is a property of the claim, not of the pipeline.**

### A.2 Therefore deadline tracking is a first-class component, not a report

FR-6 requires escalation *before* breach. That means:

| Property | Requirement |
|---|---|
| Deadline computed at intake | From product + jurisdiction + loss date + claim type, not from a global constant |
| Clock pauses are explicit | Many jurisdictions pause the clock while awaiting claimant information — **which pauses are legitimate must be encoded, not inferred** |
| Escalation is proactive | Warning thresholds at (say) 60% and 85% of remaining time, escalating to a named owner |
| Priority feeds the queue | A claim nearing its deadline must jump the handler queue automatically |

> **The subtle failure:** a design that tracks deadlines but does not let them **reorder work** produces perfect dashboards and breaches anyway. The tracker must be an input to queue priority, not a monitor beside it.

### A.3 The tension, made concrete

| | Fraud investigation | Statutory clock |
|---|---|---|
| Wants | Time — records, interviews, adjuster visits | Resolution inside N days |
| Typical duration | Weeks | Fixed |
| Cost of getting it wrong | Paying a fraudulent claim (leakage) | Penalty + regulatory attention |

You cannot investigate everything and meet the clock; you cannot investigate nothing and control leakage. **This is why triage is the highest-value model in the system** — it is the component that decides where the scarce resource (time and investigator attention) is spent.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Deadline table is data, not code | Statutory clocks configurable per (product, jurisdiction, claim type) with effective dates; changeable without deploy; every change audited |
| **FR-12** | P0 | Clock pause events are explicit and typed | Only enumerated pause reasons (e.g. `awaiting_claimant_docs`) stop the clock; each pause records who/what triggered it and when it resumes |
| **FR-13** | P0 | Deadline proximity drives queue order | Handler and SIU queues are ordered by a priority function that includes remaining time; verified by injecting a near-deadline claim and observing it surface to the top |
| **FR-14** | P1 | Breach is impossible to reach silently | Escalation at 60% and 85% of remaining time; at 95% a named owner is paged; a breach generates an incident record automatically |

---

## B. Lazy extraction — why the workflow beats the model card

The shared cost block lists "extract only fields the triage decision needs" as a −30% lever. It deserves elevating to a requirement, because it is a **structural** decision that is invisible if you evaluate extraction in isolation.

### B.1 The eager design (and why it looks reasonable)

```
intake → OCR all pages → extract ALL fields from ALL documents → validate → triage
```

It is simple, it caches well, and extraction accuracy is easy to measure. It is also wasteful, because ~35% of claims settle straight-through and those need only a handful of fields.

### B.2 The lazy design

```
intake → classify docs → extract the COVERAGE-CRITICAL field set
                         ↓
                    can we decide?  ── yes, confident straight-through → settle
                         │ no
                         ↓
                    extract the NEXT tier of fields (damage detail, third-party info,
                                                     medical codes, prior-claim keys)
                         ↓
                    triage → handler / SIU  (who trigger further extraction on demand)
```

| Field tier | Fields | Extracted for |
|---|---|---|
| **Tier 0 — coverage critical** | policy number, loss date, cause of loss, claimed amount, claimant identity | **Every claim** |
| **Tier 1 — triage inputs** | damage description, third parties, prior-claim keys, document consistency signals | Claims not confidently straight-through |
| **Tier 2 — handler detail** | line-item invoices, medical codes, repair estimates, narrative reports | On handler/SIU demand |

### B.3 Why this is not premature optimisation

Extraction is **~7.5 of the 10.5 minute** budget and **~85% of cost**. It is the dominant term on both axes simultaneously. A change that removes work from it is the single highest-leverage change available — and it comes from reading the workflow, not from swapping models.

> **The honest caveat:** lazy extraction adds a real cost. Tier-0-only claims have *less* evidence available if they are later disputed or audited, and re-extraction on demand means the handler waits. The resolution is that Tier 2 extraction is *triggered but not blocking* — it starts as soon as the claim leaves straight-through, so it is usually finished before the handler opens the claim.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-15** | P0 | Tiered, decision-driven extraction | Tier 0 for all claims; higher tiers triggered by routing outcome. Measured: ≥ 30% reduction in extraction tokens vs eager baseline at equal triage quality |
| **FR-16** | P1 | Speculative Tier-2 extraction on non-straight-through claims | Tier 2 begins at the moment of routing, off the critical path, so handler wait is not increased |
| **FR-17** | P1 | Any field an automated decision relied on is retained verbatim with its source | Field value, page, bounding box, confidence, and extractor version stored — a decision must be reconstructable years later |

---

## C. Confidence gating: the difference between accuracy and safety

FR-2 requires ≥ 0.96 field-level F1 **and** confidence gating. The second half is what makes the first half safe.

A 0.96 F1 extractor is wrong on roughly 1 field in 25. If a wrong `loss_date` silently flows into coverage validation, the system can deny a covered claim or pay an uncovered one — both expensive, both hard to detect.

| Confidence | Action |
|---|---|
| High | Use the value automatically |
| Medium | Use it, but **cross-validate** against another document in the bundle or against the policy record |
| Low | **Do not decide.** Route to handler with the field flagged and the source page shown |

> **The key asymmetry:** the cost of a low-confidence field routing a claim to a handler is minutes of human time. The cost of a low-confidence field silently driving a coverage decision is a wrong settlement plus a compliance finding. **Never let an uncertain extraction reach an automated decision** — the gate belongs before validation, not after.

Cross-document reconciliation deserves its own line: a claim bundle usually states key facts more than once (FNOL form, police report, invoice header). **Agreement across independent documents is stronger evidence than any single extractor's confidence score**, and disagreement is a fraud signal in its own right.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-18** | P0 | No automated decision on a low-confidence field | Straight-through settlement blocked if any Tier-0 field is below its threshold; the claim routes to handler with the field highlighted |
| **FR-19** | P0 | Cross-document reconciliation of key facts | Where a fact appears in ≥ 2 documents, agreement is required; disagreement raises confidence-fail **and** contributes a fraud indicator |
| **FR-20** | P1 | Per-field, per-document-type thresholds | Thresholds tuned per field (a misread claimed amount is not equivalent to a misread middle name) |

---

## D. The fraud label problem — why quoted recall is optimistic

Shared open question 3 says confirmed-fraud labels are biased. The consequence is large enough to state as a requirement.

### D.1 The bias mechanism

```
Claims                 → SIU investigates a subset (chosen by today's rules/heuristics)
                       → some subset of those is CONFIRMED fraudulent
Training labels        = confirmed fraud ∪ (assumed-legitimate everything else)
```

Fraud that today's heuristics never referred is labelled **legitimate**. A model trained on this learns to reproduce the existing referral policy, and its measured recall — computed against confirmed cases — looks excellent because the denominator is exactly the population the old policy already caught.

### D.2 The mitigations, in order of value

| Mitigation | What it buys | Cost |
|---|---|---|
| **Random-holdout referrals** — investigate a small random sample regardless of score | The only genuinely unbiased estimate of prevalence and recall | A few unbiased investigations per week of SIU capacity |
| **Leakage-based labels** — retrospective audit of *paid* claims | Finds fraud that was never referred | Slow, sampled, expensive |
| **Recovery/subrogation outcomes** | A real financial signal, not an opinion | Long lag |
| **Treat "not investigated" as unlabelled, not negative** | Prevents the model asserting innocence it has no evidence for | Positive-unlabelled learning is harder to build and explain |

> **The uncomfortable point I would say out loud in a review:** without a random holdout, we cannot know our fraud recall. We can only know how well we imitate the previous referral policy. Buying that estimate costs a handful of investigations per week and it is the cheapest genuine measurement in the system — the same argument as the holdout in [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/), and it is worth more here because label latency is measured in months.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-21** | P0 | Random-holdout referral stream | A configurable small fraction of claims referred to SIU independent of score, labelled, and excluded from threshold tuning; used solely for unbiased prevalence/recall estimation |
| **FR-22** | P1 | Labels carry provenance and maturity | Each fraud label records its source (SIU confirmation, retrospective audit, recovery outcome, holdout) and age; immature label windows excluded from evaluation |
| **FR-23** | P1 | SIU referrals are ranked by expected recovery, not probability | Referral order = P(fraud) × exposure, so scarce investigator time goes to the largest preventable loss |

---

## E. Catastrophe surge is a functional requirement

25k/day peak against 8k/day normal is ~3× in the shared table's own arithmetic; the narrative "10×" refers to the **48-hour spike within** a CAT event, where a single region floods.

> **Reconciling the two numbers explicitly, because a reviewer will ask:** the 25k/day figure is a *sustained daily peak* used for capacity sizing. The ~10× figure describes the *instantaneous regional spike* — a hailstorm generating in one afternoon what that region normally produces in weeks. Sizing for the sustained peak and *queueing* the instantaneous spike is the correct combination; sizing for the instantaneous spike would mean paying for idle capacity all year.

### What surge actually breaks

| Breaks | Why | Response |
|---|---|---|
| **Extraction throughput** | The expensive stage, now 3× | Autoscale; degrade to cheap extractor for CAT-typical simple claims |
| **Handler capacity** | Headcount does not autoscale | Raise straight-through aggressiveness for the CAT peril specifically |
| **The clock** | Deadlines keep running while queues deepen | Deadline-driven priority (FR-13) becomes the primary scheduler |
| **Fraud models** | CAT claims look anomalous *as a population* — same peril, same region, same week | **Suppress population-level anomaly features during a declared CAT**, or the whole event is flagged |
| **Cost** | 3× volume at unchanged unit cost | Accepted; CAT response is what the reserve exists for |

The fraud row is the one that catches people. A model using "unusual concentration of similar claims" as a signal will, during a hailstorm, flag the entire legitimate event.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-24** | P0 | Declared CAT mode | An operator-declarable event (peril, region, date range) that adjusts extraction tier defaults, straight-through thresholds, and fraud feature sets; every change audited and reversible |
| **FR-25** | P0 | Population-concentration fraud features suppressed under CAT | Verified by replay of a historical CAT: referral rate stays within normal bounds |
| **FR-26** | P1 | Surge does not degrade the audit trail | Audit writes remain synchronous and complete at 3× volume (load-tested) |

---

## F. Why the audit write is on-path here

[`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) puts audit writes **off-path** — a 60 ms authorisation cannot afford a synchronous durable write, and a lost audit row there is recoverable from the transaction record.

This system does the opposite, and the reason is domain, not engineering:

| | Fraud authorisation (§02) | Claims settlement (§07) |
|---|---|---|
| Budget | 60 ms | 15 min |
| Cost of a synchronous write | Material fraction of budget | 15 s of 10.5 min — noise |
| Regulatory posture | Decision reconstructable from the transaction | **The audit record *is* the regulatory artifact** |
| If the write is lost | Recoverable | A settlement with no defensible basis |

> **Same technique, opposite call, and the discriminator is what the record is *for*.** Naming the reason — not just the choice — is what makes this a design decision rather than a preference.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-27** | P0 | Audit write is synchronous and precedes action | No settlement, denial, or SIU referral is emitted before its audit record is durably committed; verified by fault injection at the audit store |

---

## G. Additional non-goals (beyond the shared block)

- **Not** autonomous denial. Denials require human authorisation, always — FR-18's gate plus this rule mean the system's automated authority is *pay* and *route*, never *refuse*.
- **Not** a fraud *determination*. The system scores and refers; SIU determines.
- **Not** a replacement for the deadline table's legal source of truth — compliance owns the clock table, engineering owns its enforcement.
- **Not** medical adjudication or bodily-injury reserving.
- **Not** litigation management.
- **Not** re-underwriting at claim time.

---

## H. Open questions carried into the HLD

Beyond the shared block's four:

1. **Which clock pauses are legitimate, per jurisdiction?** FR-12 is unimplementable without this, and getting it wrong in the permissive direction manufactures breaches; in the restrictive direction it manufactures phantom breaches that erode trust in the tracker.
2. **What is the handler queue's real depth today?** Straight-through economics are only meaningful against it. If handlers are already two weeks deep, 35% straight-through is a capacity intervention, not an efficiency gain — a different business case entirely.
3. **Are policy wordings machine-encodable for the top perils?** If yes, coverage validation stays deterministic (auditable, cheap, testable). If no, an LLM-assisted path with human confirmation is needed and the straight-through rate drops materially.
4. **Can a CAT be declared quickly enough to matter?** FR-24 assumes a human declares it. If declaration lags the claim spike by two days, the fraud-suppression benefit is mostly lost and automatic detection is needed instead.
5. **What is the actual cost of leakage vs the cost of a delayed settlement?** Every threshold in the system trades these against each other, and nobody can set them without the ratio.

---

**Next:** [`02_hld.md`](02_hld.md) →
