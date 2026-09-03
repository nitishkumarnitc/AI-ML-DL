# 06 · Production & Interview — Manufacturing: CV Quality Inspection

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)

---

## 4.1 AI-specific concerns

| Concern | How it shows up here | What we do about it |
|---|---|---|
| **Rare positives** | ~2% defect rate, and ~50 labelled examples per class **per year**. A model predicting "pass" always scores 98% accuracy | Never report accuracy. The objective is *minimise escapes subject to false-reject ≤ 1.5% and review ≤ 3%* — a constrained optimisation, not a classification score. Class-balanced sampling and focal-style losses in training; escape/false-reject/review-volume as the only reported metrics |
| **Open-ended class set** | Tomorrow's defect may resemble nothing in training, whenever a supplier, tool or material changes | The parallel anomaly model (FR-5, FR-14), **verified by the leave-one-class-out test** in [`03_lld.md#33`](03_lld.md#33-core-algorithms). Without that test you have an anomaly model; you do not know it works |
| **Silent domain drift** | Lens fouling, LED ageing and fixture wear degrade accuracy with **no error, no exception and no complaint from the model** | Per-line image-domain drift monitoring against that line's own baseline. This is the fastest signal available — days ahead of escape reports, which arrive weeks later as shipped product |
| **Label noise on a rare-positive problem** | An engineer's disposition is the only ground truth, and engineers genuinely cannot always tell | `disposition = unclear` is a first-class value. Forcing binary labels poisons a training set where every positive is precious. Inter-rater agreement sampled monthly |
| **Calibration bootstrapping** | The anomaly baseline must come from **human-verified** good units, not model-passed units | Bootstrapping from model-passed units bakes the classifier's blind spots into the detector, correlating the two failure modes and destroying the independence FR-14 requires |
| **Thermal non-stationarity** | An edge box in a plant runs hot; sustained throttling costs 20–30% of inference throughput | FR-20 tiering: degrade **accuracy**, never latency. Every unit tagged `degraded_model` so escape analysis can segment by tier — otherwise a July thermal problem is misdiagnosed as a model regression |
| **Human capacity as the real constraint** | Review volume is capped at 3% by staffing — one quality engineer per line | The capacity governor sheds the **lower-yield** stream (anomaly escalations) and never the supervised ones, and never disables the anomaly net entirely (`ceil = 0.95`). Same pattern as [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) (1,200 cases/day) and [`../07_insurance_claims_automation/`](../07_insurance_claims_automation/) |
| **Escape feedback latency** | The metric that matters most (escape rate) is measured weeks later, downstream | Two-speed monitoring: drift + score distributions in **minutes**, escape rate in **weeks**. Never wait for the slow signal to detect a fast problem |
| **Cost asymmetry drives everything** | escape ₹18,500 · scrap ₹340 · review ₹22 | Human review is **two orders of magnitude cheaper than either error**. This single ratio is why a three-way output beats a binary one, and why the anomaly model routes to `review` rather than `fail` |

---

## 4.2 Operations & runbook

### Dashboards

**Per line, on the plant floor** (visible to the shift, not buried in a tool):

| Panel | Alert |
|---|---|
| Inspection p99 latency vs 150 ms SLO | > 130 ms for 5 min |
| Verdict mix — pass / fail / review % | review > 3% of shift budget pace |
| False-reject estimate (from dispositions) | > 1.5% rolling 8 h |
| Review queue depth vs shift capacity | > 80% at any point |
| Current model tier (full / medium / small) | any tier below `full` for > 30 min |
| Timeout rate | > 0.1% of units |
| GPU temperature and utilisation | temp > nominal for 15 min |
| Drift: brightness / contrast / sharpness vs baseline | any > 3σ |
| Anomaly-score p95 vs baseline p95 | > 1.5× baseline |

**Fleet-wide, for the quality organisation:**

| Panel | Alert |
|---|---|
| Escape rate by line, by defect class, 4-week trailing | > 0.2% |
| **`blind_escape_rate`** — escapes on units with no retained image | rising trend (evidence to raise the 2% sample) |
| Miss-type split: known-class vs unknown-mode (FR-16) | unknown-mode share rising ⇒ anomaly work, not retraining |
| Model version distribution across 12 lines | any skew > 1 version |
| `auto_tightened` threshold events per shift | > 2 per line per week ⇒ structural capacity problem |
| Review disposition mix, incl. `unclear` rate | `unclear` > 15% ⇒ imaging or taxonomy problem, not a model problem |
| Cost per unit inspected | — |

> **The two panels nobody thinks to build, and both earn their place:** `blind_escape_rate` is how a sampling decision made in a design review gets revisited with evidence instead of opinion. The `unclear` disposition rate is a **quality signal about your imaging setup** — if engineers cannot tell from the retained image, no model will do better from the same image, and the fix is lighting or resolution, not training.

### On-call triage order

When a line reports a problem, work this order. It is ordered by *frequency × cheapness to check*, not by severity:

1. **Is the line still moving?** If yes, you have time. If no, get a verdict flowing — force `review` for everything if necessary — and diagnose second. A stopped line costs more per minute than any quality error.
2. **Check the model tier.** A degraded tier explains most sudden accuracy complaints and is a five-second check. Thermal, not model.
3. **Check drift panels before touching the model.** Brightness/contrast/sharpness out of band ⇒ **clean the lens, check the lighting**. This is the single most common root cause and the most commonly misdiagnosed one.
4. **Check `calib_version` age and recent maintenance.** Was the lens cleaned or a fixture serviced in the last 24 h? A stale baseline after cleaning flags *everything* as anomalous — maintenance doing its job correctly can cause a scrap storm.
5. **Check for a threshold change.** `threshold_set` history for that `(line, sku)`. Also check for `auto_tightened` rows — the governor may have moved the bar during a busy shift.
6. **Check for a product changeover.** SKU mismatch against the loaded threshold set.
7. **Check the model version** against the fleet. Version skew makes escapes untraceable and is worth ruling out early.
8. **Only now consider the model.** Compare current score distributions against the shadow-mode record for this line. If the distributions are unchanged, **the model is not your problem** — go back to steps 3–6.

> **Step 8 last, on purpose.** The instinct when quality drops is to retrain. In this system the model is rarely the cause: physical causes (optics, lighting, fixtures), configuration causes (thresholds, SKU) and environmental causes (thermal) are collectively far more common, and all are cheaper to check and faster to fix. Retraining in response to a dirty lens produces a model trained to accept fouled images — which is worse than doing nothing, because it is durable.

### Rollback

| Situation | Action | Time to safe |
|---|---|---|
| **New model spiking false rejects** | Automatic — the rollout controller rolls back on a false-reject band deviation; signed incumbent artifact is resident locally | < 2 min, no network needed |
| Threshold change causing scrap | `PUT` the previous `threshold_set_id` (immutable history makes this a one-liner); takes effect next unit | < 1 min |
| Governor stuck at ceiling, queue overflowing | Pin thresholds manually, staff an extra reviewer, escalate. **Do not raise `ceil` to 1.0** | Minutes, but structural |
| Edge box hardware failure | On-site spare, documented swap (FR-18). Spare pulls that **line's** baseline and threshold set on boot | Target < 30 min |
| Bad calibration published | Revert `calib_version`, restore the prior baseline. Units inspected in the window are re-flagged for review | < 5 min + a re-review batch |
| Plant network outage | **No action.** Line tier is independent by design; ring buffer holds 72 h. Verify buffer headroom | 0 — this is the designed-for case |

> **The rollback that must work offline is the model rollback**, because a bad model and a network outage can co-occur — and a plant network problem is a plausible *cause* of a botched rollout. Hence the incumbent artifact stays resident on local disk. A rollback that requires the network is not a rollback.

---

## 4.3 Common mistakes

Mistakes I would expect to see in this design, and what each costs:

1. **Reporting accuracy.** At a 2% defect rate, "98% accurate" is what you get by predicting `pass` unconditionally. Any metric that looks good on a degenerate model is not a metric.

2. **Binary pass/fail.** Forces one threshold to serve two irreconcilable NFRs (escape ≤ 0.2%, false reject ≤ 1.5%). Either escapes or scrap goes out of budget — there is no threshold that satisfies both, and hunting for one is the trap.

3. **Cloud inference.** ~$210k/month against ~$2.7k on-prem, **and** it violates FR-4 — a WAN blip stops 12 production lines. The cloud-first instinct is a habit, not an analysis; the discriminator is duty cycle.

4. **Running the anomaly model in series.** It becomes 30 ms on every unit and threatens the budget. In parallel it is free. Same model, same accuracy, one is affordable.

5. **Letting the anomaly model condemn units.** Unfamiliar ≠ defective. Every legitimate process change — new supplier, cleaned lens, repositioned fixture — becomes a scrap event at 5 units/s.

6. **Localising every unit.** 20 ms × 100% instead of 20 ms × 2%. That is the difference between ~120 ms and ~140 ms typical, and it spends the thermal headroom on passes.

7. **A fleet-wide drift baseline.** Hides exactly the per-line degradation the monitor exists to find. Each station has its own lighting and lens history.

8. **Bootstrapping the anomaly baseline from model-passed units.** Bakes the classifier's blind spots into the detector, correlating the failure modes and voiding FR-14's independence.

9. **Stalling on timeout.** The line must keep moving. Emitting `review` costs human attention; stalling costs production. FR-19 exists because this choice is not close.

10. **Degrading latency under thermal pressure instead of accuracy.** Slower inference stops the line. A slightly worse model does not. FR-20.

11. **Retaining every image.** ~$18k/month of storage for data almost never read. All fails + a 2% pass sample gives you review material, retraining negatives and a drift baseline.

12. **Storing verdicts only for fails.** Makes a recall investigation impossible for passed units — which are the ones a recall is about. Verdict rows are 134 B; this saves nothing and forfeits the traceability obligation.

13. **Deploying a model to 12 lines at once.** The blast radius is 12 lines × 5 units/s of good product going to scrap. Shadow → canary → staged fleet.

14. **Retraining in response to drift.** A dirty lens is a cleaning work order. Fixture drift is a mechanical work order. Retraining bakes the fault in permanently.

15. **Treating thresholds as code.** They must change without redeploying edge software (FR-11) — but as *audited config* with a two-person rule and a replay-based impact projection, not as an unlogged runtime knob.

16. **Not classifying escape miss types.** `known_class_miss` and `unknown_mode_miss` demand different fixes. Applying the wrong one wastes a release cycle and leaves the real gap open.

17. **Letting the capacity governor reach 1.0.** Silently disables FR-5's open-endedness protection during exactly the busy shift when you most need it.

18. **Actuating the line.** Emitting a verdict keeps this system out of machine-safety scope. Driving a diverter puts it in, with an entirely different certification burden.

---

## 4.4 Interview follow-ups

**"How do you validate the anomaly model actually catches unseen defects?"**
Leave-one-class-out: remove a class entirely from supervised training, fit the anomaly model on verified-good units only, then score held-out examples of the removed class. Gate on escape rate ≤ 20% on the unseen mode. Run it for every class, every release. Without this you have an anomaly model and no evidence it works — and the aggregate metrics will not tell you, because the unseen-mode cases are by construction absent from your test set.

**"Escape rate is 0.2% and false reject is 1.5%. Which do you tune first, and why?"**
Neither, first — I would establish which one is actually binding, then check whether false rejects are **scrap or rework**. If units can be reworked, the 1.5% ceiling loosens substantially and the whole operating point moves. That single answer changes the thresholds more than any modelling improvement, and it is open question #3 in [`01_requirements.md`](01_requirements.md). Tuning before answering it is optimising against the wrong constraint.

**"The plant network is down for four days. What happens?"**
Days 1–3: nothing visible. The line tier has no runtime dependency on the plant or cloud tiers; models and baselines are local; the ring buffer holds 72 h. From hour 72 the buffer evicts, oldest **pass-sample** images first, then fail images, **never verdict rows** — because verdict rows are the legal traceability obligation at 134 B each while images are 400 KB. What you lose is retraining material and review images, not the ability to inspect or to answer a recall.

**"A quality engineer says the model got worse this week. Walk me through it."**
Model tier first (thermal, five seconds). Then drift panels — brightness, contrast, sharpness against that line's baseline. Then `calib_version` age and the maintenance log. Then threshold history, including `auto_tightened` rows. Then SKU changeover. Then fleet version skew. **The model comes last**, because physical, configuration and environmental causes are far more common and much cheaper to check. If score distributions are unchanged against the shadow record, the model is not the problem, and retraining would encode whatever actually is.

**"Why can the anomaly model send a unit to review but not to fail?"**
Because it measures unfamiliarity, not defectiveness. A unit is unfamiliar for many benign reasons: a new supplier's surface finish, a legitimate material variation, a fixture moved this morning, a lens that was just cleaned. If unfamiliar meant scrap, the first hour after any legitimate process change would consume the entire 1.5% false-reject budget in minutes. The cost is that an unfamiliar-and-genuinely-defective unit consumes human attention rather than being handled automatically — correct at ₹22 review vs ₹340 scrap vs ₹18,500 escape.

**"How do you set thresholds without a shipping experiment?"**
Replay. Because raw scores are stored for every unit, a proposed threshold set is replayed against 14 days of real production — ~4.1M units — projecting false-reject rate, review volume and escape estimate before it touches a line. The API rejects the change if any projection breaches its ceiling. This is why storing scores for all units, not just fails, pays for itself: it converts a judgement call into a measurement.

**"What breaks at 10× — 120 lines?"**
Not inference; that scales linearly with boxes, which is the point of per-line hardware. What breaks is **organisational**: version control across 120 stations, per-line drift baselines, label logistics, and above all **review capacity** — 120 quality engineers is a staffing programme, not a config change. Investment shifts to automated disposition of high-confidence reviews. At 100× the binding constraint is **taxonomy governance**: no central team maintains thousands of defect-class variants, so you go hierarchical (plant-local classes rolling into global families) and **anomaly-first**, adding supervised classes only where volume justifies.

**"What would you cut to ship in six weeks?"**
Keep: the two-model fusion, the three-way verdict, the watchdog, per-line on-prem inference, verdict traceability for all units. Cut: conditional localisation (engineers can look at the image), few-shot class addition, the capacity governor (staff to a fixed conservative `t_review_ano` and monitor manually), and automated escape classification (do it by hand — there are few enough). What I would **not** cut is the drift monitor, because without it the system degrades silently and you find out from customer returns weeks later, which is the failure mode that destroys trust in the whole programme.

**"Precision floor of 0.70 — where does that come from?"**
Trust economics, not statistics. If more than roughly three in ten flagged units turn out good, engineers stop believing the flags and start rubber-stamping the queue — at which point the review class is theatre and its 3% cost buys nothing. The number is a behavioural threshold about human attention, and it is a harder constraint than any accuracy target because violating it silently disables a subsystem you are still paying for.

---

## 4.5 Glossary

| Term | Meaning here |
|---|---|
| **Cycle time** | 200 ms — the interval between units arriving at the station. The binding constraint; every latency number derives from it |
| **Escape** | A defective unit that passed inspection and reached the customer. Target ≤ 0.2% of defective units |
| **False reject** | A good unit wrongly failed. Ceiling 1.5% of *all* units |
| **Review** | The third verdict: genuinely ambiguous, held for a human. Capped at 3% of units by staffing |
| **`T_fail` / `T_review`** | Independently configurable thresholds (FR-11). `T_fail` governs condemnation; `T_review` governs escalation to a human |
| **Known-class miss** | An escape of a defect class the supervised model was trained on. Fix: retune or retrain |
| **Unknown-mode miss** | An escape of a mode neither model registered. Fix: anomaly feature space or threshold. **Different fix — this is why FR-16 classifies them** |
| **Anomaly score** | Mahalanobis distance from a unit's embedding to the line's normal manifold. Measures *unfamiliarity*, not defectiveness |
| **Normal manifold** | The distribution of embeddings of human-verified good units for one line under one calibration |
| **`ano_score_norm`** | Anomaly score divided by the baseline's 99.9th percentile, clamped to [0,1]. What thresholds compare against |
| **Shrinkage covariance** | Ledoit–Wolf regularisation of the sample covariance toward a diagonal target. Required — the raw inverse amplifies noise at these dimensions |
| **Line tier / plant tier / cloud tier** | The three tiers, separated by binding constraint: cycle time, durability, training. The line tier has **no** runtime dependency on the others |
| **Watchdog** | An independent timer that emits `review` if inference misses its deadline (FR-19). Independent because a stalled thread cannot report its own stall |
| **Model tier** | full (45 ms) / medium (28 ms) / small (16 ms). Thermal pressure degrades **accuracy**, never latency (FR-20) |
| **`calib_version`** | The lighting/lens calibration in force. Resets on cleaning or maintenance; invalidates the baseline |
| **Capacity governor** | The controller that tightens `t_review_ano` when review volume outpaces shift capacity (FR-12). Adjusts only the anomaly threshold, and never to 1.0 |
| **Ring buffer** | 72 h local store for images and telemetry, off the inference path. What makes the offline requirement achievable |
| **Shadow mode** | New model scores live units without acting on verdicts. Paired comparison against the incumbent on the *same* units |
| **`blind_escape_rate`** | Escapes found on units whose image was not retained. The evidence for revisiting the 2% pass-sample rate |
| **Duty cycle** | Fraction of time the hardware is actually working. Continuous + latency-bound is what inverts the build-vs-rent decision (~75×) |

---

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)
