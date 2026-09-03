# 06 · Requirements — Manufacturing: CV Quality Inspection

> **Shared block:** [`../00_requirements_all_systems.md#6-manufacturing--computer-vision-quality-inspection`](../00_requirements_all_systems.md#6-manufacturing--computer-vision-quality-inspection) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the latency budget, and the cost arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. Why the output is three-way, not binary

The shared NFRs set two targets that pull directly against each other:

```
Escape rate      ≤ 0.2%  of DEFECTIVE units reaching the customer   (recall pressure)
False reject     ≤ 1.5%  of ALL units wrongly scrapped              (precision pressure)
```

On a rare-positive problem these cannot both be met by a single threshold on a single score. Tightening to catch more defects raises false rejects steeply, because the score distributions overlap in a region where genuinely ambiguous units live.

### The resolution

| Output | Meaning | Destination | Bounded by |
|---|---|---|---|
| **pass** | Confidently good | Continues down the line | — |
| **fail** | Confidently defective | Diverted to scrap/rework | False-reject budget (1.5%) |
| **review** | Genuinely ambiguous | Held for a quality engineer | **Human capacity (3% of units)** |

`review` converts an impossible binary decision into a **deferred** one. The cost is human attention, and that is capped at ~3% of units by staffing (one quality engineer per line).

> **The consequence for the model's objective, stated plainly:** this is not "maximise accuracy." It is **minimise escapes subject to false-reject ≤ 1.5% and review-volume ≤ 3%** — a constrained optimisation with two capacity ceilings, one of which is a headcount. The same capacity-caps-the-threshold pattern as [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) and [`../07_insurance_claims_automation/`](../07_insurance_claims_automation/).

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Two independently-configurable thresholds per product/line | `T_fail` and `T_review` set separately; changeable by audited config without redeploying edge software |
| **FR-12** | P0 | Review volume is enforced, not merely targeted | If review volume exceeds capacity for a shift, `T_review` auto-tightens and the event is logged — the queue must never grow unbounded |
| **FR-13** | P1 | Cost-weighted thresholds | Thresholds derived from the *unit* economics of that product (scrap value vs escape cost), not a single plant-wide number |

---

## B. Defects are rare *and* open-ended — the modelling consequence

This is the constraint that determines the model architecture, and it is easy to get wrong by treating inspection as a standard classification problem.

### The reality

| Property | Implication |
|---|---|
| ~50 labelled examples per defect class **per year** | Insufficient for a supervised class in the usual sense |
| New defect modes appear on supplier/tooling/material change | The class set is **not closed** — tomorrow's defect may be unlike anything in training |
| Good units are abundant and highly consistent | The *normal* distribution is very well characterised |
| Defect appearance varies wildly within a class | Intra-class variance often exceeds inter-class |

### The design that follows

Run **two models in parallel**, fused:

| Model | Learns | Catches | Cost |
|---|---|---|---|
| **Supervised classifier** | Known defect classes | Familiar defects, with a class label useful for root-cause work | 45 ms |
| **Anomaly detector** | The *normal* manifold only | Anything unfamiliar, including never-before-seen defect modes | 30 ms, **overlapped ⇒ free** |

> **The anomaly model is the answer to open-endedness, and running it in parallel makes it free.** In series it would add 30 ms to every unit and threaten the budget; overlapped with the supervised model it costs nothing and buys detection of defect types no classifier has seen. FR-5 is satisfied by architecture, not by hoping the classifier generalises.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-14** | P0 | Anomaly score is independent of the supervised class set | Verified by holding out an entire defect class from supervised training and confirming the anomaly model still flags it for review |
| **FR-15** | P0 | New defect classes addable with few examples | A new class reaches usable performance with ≤ 20 labelled examples (few-shot / embedding-space method), without a full retrain |
| **FR-16** | P1 | Class-agnostic escape monitoring | Escapes found downstream (customer returns, final QA) are traced back to their inspection record and classified as *known-class miss* vs *unknown-mode miss* — these have different fixes |

FR-16 matters because the two miss types demand different responses: a known-class miss means retune or retrain; an unknown-mode miss means the anomaly model's threshold or feature space needs work. Without the distinction you apply the wrong fix.

---

## C. The build-versus-rent arithmetic

The shared block gives the headline. The reasoning is worth making explicit because it inverts the usual cloud-first default.

```
Workload: 12 lines × continuous inference × 16 h/day, ~100% duty cycle during shifts
          Latency-bound (200 ms cycle) and network-independent (FR-4)

RENT (cloud GPU, per the shared assumptions register at ~$1.00/GPU-hour):
  12 GPUs × $1.00 × 24 h × 730 h/month  ≈ $210,000/month
  ...and this does not even work, because FR-4 forbids network dependence.

OWN (on-prem edge boxes):
  12 boxes × ~$8,000 capex          = $96,000        (ASSUMPTION: A10G-class equivalent)
  3-year straight-line amortisation = $96,000 / 36  ≈ $2,700/month
```

**Roughly 75× cheaper, and it's the only option that satisfies FR-4 anyway.**

### The general principle

| Duty cycle | Latency needs | Correct choice |
|---|---|---|
| Bursty, low average utilisation | Tolerant | **Rent** — you pay only for what you use |
| Continuous, high utilisation | Tight | **Own** — rental amortises against nothing |
| Continuous + network-independent | Tight | **Own, on-prem** — no alternative exists |

> This is the same reasoning that makes cloud correct for [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/) (spiky, network-native) and wrong here. **The instinct to default to cloud is a habit, not an analysis** — and the discriminator is duty cycle.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-17** | P0 | Inference hardware is on-premises, per line | No inference request leaves the plant network |
| **FR-18** | P1 | Hardware failure of one line's box does not stop other lines | Independent boxes; a spare unit is held on site with a documented swap procedure |

---

## D. What "never the bottleneck" actually requires

FR-1 says inspect every unit at line rate without becoming the bottleneck. Making that precise, because "fast enough on average" is not the requirement.

| Property | Requirement | Why |
|---|---|---|
| **p99, not mean, inside cycle time** | p99 < 150 ms against a 200 ms cycle | A unit arriving every 200 ms means a 250 ms outlier **stops the line** |
| **Bounded worst case** | No unbounded work in the inference path | A retry loop or a dynamic-shape reallocation can spike arbitrarily |
| **Fail-safe on timeout** | If inference exceeds budget, emit a default verdict rather than stalling | The line must keep moving |
| **Graceful on hardware degradation** | Thermal throttling must degrade *accuracy* (smaller model), not *latency* | Slower inference stops production; a slightly worse model does not |

### The fail-safe direction question

If inference times out, what verdict is emitted? This is a genuine design decision with no universally right answer:

| Default | Consequence | When correct |
|---|---|---|
| **`review`** | Unit held; review queue grows | **Chosen default.** Preserves both quality targets at the cost of human attention, and timeouts should be rare enough not to flood the queue |
| `pass` | Potential escape | Only if escapes are cheap and scrap is expensive — unusual |
| `fail` | Guaranteed scrap of a probably-good unit | Wasteful; also a timeout storm becomes a scrap storm |

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-19** | P0 | Inference timeout emits `review`, never `pass` or a stall | Injected timeout test: verdict emitted within budget, line does not stop, unit is held |
| **FR-20** | P1 | Thermal/resource degradation reduces model size, not throughput | Under simulated thermal limit, latency stays inside budget with a documented accuracy drop |

---

## E. Additional non-goals (beyond the shared block)

- **Not** actuating the line — the system emits a verdict; the PLC/MES decides what to do with it. This keeps the system out of machine-safety scope.
- **Not** dimensional metrology (separate, higher-precision instruments with different calibration requirements).
- **Not** root-cause diagnosis of process drift — it surfaces evidence for engineers rather than concluding.
- **Not** cloud inference (FR-4/FR-17 forbid the dependency).
- **Not** replacing final human QA on safety-critical units.
- **Not** retaining every pass image — 100% retention is unaffordable and unnecessary (all fails + a 2% pass sample).

---

## F. Open questions carried into the HLD

Beyond the shared block's list:

1. **What is the true cycle time, and is it stable across products?** Every latency number derives from 200 ms. A 100 ms cycle for one product line forces model compression or a second inference box for that line.
2. **How many labelled examples exist *today* per defect class?** If it's single digits for most, v1 must be anomaly-led with supervised classification added incrementally — a materially different rollout, and FR-15's few-shot requirement becomes the primary path rather than a convenience.
3. **Is a false reject scrap or rework?** If units can be reworked, the 1.5% ceiling loosens considerably and the thresholds move. This single answer changes the operating point more than any modelling improvement.
4. **Who owns the defect taxonomy?** FR-15/FR-16 assume someone maintains class definitions. Without an owner, labels drift and the model degrades silently.
5. **What downstream signal reveals escapes?** FR-16 requires tracing customer returns or final-QA findings back to an inspection record — which needs unit-level traceability to exist end-to-end, not just within this system.

---

**Next:** [`02_hld.md`](02_hld.md) →
