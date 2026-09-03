# 07 · Production & Interview — Insurance: Claims Automation

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

| Concern | How this design handles it |
|---|---|
| **Token cost** | **~$12.7k/month ≈ $0.053/claim**, of which extraction is ~85%. Three composable levers: layout models on templated pages (−60% on those pages), cheap-extractor-first with VLM escalation (−45% blended), and **lazy tiered extraction (−30%, FR-15)**. The last is the interesting one because it comes from reading the workflow rather than the model card |
| **Latency budget** | ~10.5 min against a 15 min p95 SLO, 4.5 min headroom sized for CAT queue depth. Extraction is ~7.5 of the 10.5 min — the dominant term on both latency and cost simultaneously, which is why it gets the optimisation attention |
| **The regulatory clock** | A **separate concern from latency**, in days not minutes, and the reason the deadline service is a first-class component with its own store, its own scanner, and **no dependency on the pipeline** — the guarantee must survive the outage during which claims stall and the clock keeps running |
| **Model routing & fallback** | Small model for classification, frontier VLM for extraction, **deterministic rules for coverage**, GBDT for fraud, calibrated classifier for triage. Fraud scorer unavailable ⇒ no straight-through above a value floor; coverage data unavailable ⇒ no straight-through at all |
| **Evaluation** | Extraction measured **per field per document type**, never in aggregate — aggregate F1 hides handwritten and foreign-language documents, which is exactly where errors are expensive. Triage measured by handler override rate. Fraud measured against the **random holdout** (FR-21) and nothing else |
| **Hallucination / groundedness** | Every extracted field carries `document_id`, `page_number`, `bbox`, and verbatim `value_text` (FR-17). A field with no source is not a field. Coverage decisions are rule-by-rule outcomes, not generated prose |
| **Guardrails** | The confidence gate as a **hard blocker not a weight** (FR-18); **no autonomous denial, ever**; hard value ceilings with no fuzzy band; enumerated pause reasons rejected at the API boundary (FR-12); synchronous pre-action audit (FR-27) |
| **Prompt injection** | **Real and specific here.** Claim documents are attacker-supplied — a claimant can put text in a PDF. Mitigations: extraction outputs are **structured fields validated against types and ranges**, never free-form instructions; document text never enters a decision prompt as instructions; and coverage validation is a rules engine, so injected text has nothing to steer. The residual risk is the narrative-inconsistency LLM feature, which is why it emits a *feature into the GBDT* rather than a score |
| **Version management** | Every decision row pins `coverage_ruleset_ver`, `fraud_model_ver`, `triage_model_ver`, `threshold_ver`, `extractor_version` per field, **and `fraud_feature_set`** — because a referral made under CAT suppression is not comparable to one made under the standard set |
| **Drift** | Document-mix drift (new insurer partner ⇒ new form layouts), extraction-confidence calibration drift, fraud-pattern drift, and **claim-mix drift during CAT**. The first is the most common and shows up as a straight-through rate drop before it shows up as an accuracy drop |
| **Label latency** | Handler decisions: hours. SIU outcomes: weeks. Retrospective audit and recovery outcomes: **months**. `fraud_labels` records source, confidence, and maturity so immature windows are excluded from evaluation (FR-22) |
| **Selection bias** | The design's most important epistemic problem. "Not investigated" is stored as `UNLABELLED`, not `legitimate`, and FR-21's random holdout is the only source of an unbiased recall estimate |
| **PII / residency** | Heavy: medical records, police reports, financial detail, photographs of homes and vehicles. Field-level encryption for special-category data, jurisdiction-pinned storage, role-scoped access, and the claimant-facing status API deliberately exposes **workflow state only** — no scores, no reason codes |
| **Cold start** | A new product or jurisdiction needs a **clock table entry before any claim can be accepted** — absent it, intake refuses rather than guessing a deadline. Straight-through is disabled for a new product until extraction confidence is calibrated on its document types |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| **Deadline distribution** — claims by clock fraction (0–60 / 60–85 / 85–95 / 95–100%) | any claim > 95% · **any breach = sev1** |
| Breaches this month, by product and jurisdiction | > 0 |
| Escalations fired at 85% / 95% | trend up week-over-week |
| Claims paused > 90 days (stale, not breaching) | > 50 |
| Ingestion → triage p95 | > 12 min |
| **Straight-through rate**, by product | < 30% |
| Confidence-gate block rate, **by field and document type** | any field > 15% |
| Extraction confidence calibration (predicted vs observed accuracy) | ECE > 0.05 |
| Handler queue depth and age p95 | age > 2 business days |
| Handler **override rate** of triage route | > 12% |
| SIU referral rate, precision, and queue age | precision < 0.40 |
| **Holdout-derived fraud recall estimate** | trending down |
| Withdrawn CAT referrals | (informational, but investigators must see it) |
| Fraud graph component growth | new component > 20 nodes |
| Audit write latency and failure rate | any failure |
| Cost per claim | > $0.07 |

### On-call triage order

1. **Is any claim past 95% of its clock?** This is the only alarm with a legal consequence. Confirm the escalation fired and a named owner has it. If the pipeline is stalled, route those specific claims to handlers for manual handling — the deadline does not care why we were slow.
2. **Is the deadline service healthy?** It is the one component whose failure breaks the regulatory guarantee rather than the product. Escalation runs from cached deadlines; recompute on recovery and reconcile.
3. **Is the audit store failing?** The system fails **closed** by design (FR-27): decisions accumulate unemitted. Claims are delayed, not wrong. Fix the store; the workflow engine replays. Do not disable the ordering to "unblock" — that is the one change that turns a delay into a compliance finding.
4. **Is straight-through rate down?** Almost always the confidence gate, and almost always one document type. Check gate block rate by document type; a new partner's form layout is the usual cause, and the fix is extractor work, not threshold relaxation.
5. **Is the handler queue deepening toward breach?** The `handler_capacity_breach_risk` branch is now firing and relaxing thresholds automatically. That is working as designed, but leadership must know we are trading leakage for deadlines — surface it, do not let it stay in a log.
6. **Is SIU precision below 0.40?** Investigators lose confidence in referrals below that and start ignoring the queue, which is worse than a smaller queue. Tighten the referral threshold and re-check expected-recovery ranking.
7. **Is a regional referral spike underway?** Suspect an undeclared CAT. Provisional suppression should already have engaged; get the declaration made so the withdrawal and re-ranking are auditable.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Thresholds (triage, gate, referral) | Config revert, versioned | seconds |
| **Clock table entry** | Effective-dated revert; **in-flight claims unaffected** by construction | seconds |
| Coverage ruleset | Versioned revert; replay affected claims through the previous ruleset to quantify impact | minutes |
| Fraud model | Pointer flip to previous version | < 1 min |
| Extractor version | Pointer flip; **claims mid-extraction re-run** rather than mixed-version | minutes |
| CAT declaration | Reversible and versioned; claims re-scored under the standard set, emitted decisions flagged not retracted | minutes |
| Triage model | Fall back to the v1 rules decision table — kept alive precisely as a rollback target | < 1 min |

> Keeping the rules-based triage table alive as a rollback target is worth the maintenance cost. It is the only fallback that is auditable line-by-line on a day when someone is asking why the model routed a claim.

---

## 4.3 Common mistakes

> - **Mistake:** Treating the statutory deadline as a latency SLO → **Why it's wrong:** they are different in kind. p95 can be perfect while claims breach in a four-day-deep handler queue, because the clock runs during the parts of the process the pipeline does not control → **Do instead:** a per-claim clock with typed pauses, proactive escalation, and — critically — deadline-driven queue ordering.
> - **Mistake:** Tracking deadlines without letting them reorder work → **Why it's wrong:** produces excellent dashboards and breaches anyway → **Do instead:** the tracker is an *input to queue priority* (FR-13), not a monitor beside it.
> - **Mistake:** Putting deadline tracking inside the pipeline → **Why it's wrong:** the outage that stalls claims is exactly when the clock matters most → **Do instead:** an independent service and scanner with no pipeline dependency.
> - **Mistake:** Eager full extraction of every field from every document → **Why it's wrong:** ~35% of claims need five fields; extraction is 85% of cost and 70% of latency → **Do instead:** tiered, decision-driven extraction.
> - **Mistake:** Treating extraction confidence as a weight in the routing decision → **Why it's wrong:** a low-confidence `loss_date` can flip a coverage outcome; no amount of counter-evidence makes an unread field readable → **Do instead:** a hard blocker before validation.
> - **Mistake:** An LLM reading policy wordings to decide coverage → **Why it's wrong:** not reproducible, not auditable rule-by-rule, and a wrong answer is a wrongful denial → **Do instead:** a versioned rules engine; use the LLM to *author* rule encodings for human approval.
> - **Mistake:** Autonomous denial → **Why it's wrong:** a denial is an adverse action with appeal rights; nobody can defend "the model denied it" → **Do instead:** the system's automated authority is *pay* and *route*, never *refuse*.
> - **Mistake:** Labelling never-investigated claims as legitimate → **Why it's wrong:** the model learns to reproduce the old referral policy and reports excellent recall against a denominator the old policy already caught → **Do instead:** `UNLABELLED` plus a random holdout.
> - **Mistake:** Ranking SIU referrals by fraud probability → **Why it's wrong:** a 0.9-probability $180 claim outranks a 0.5-probability $60k claim, and investigator time is the scarce resource → **Do instead:** rank by P(fraud) × exposure.
> - **Mistake:** Population-concentration fraud features left active during a CAT → **Why it's wrong:** a hailstorm *is* a concentration of similar claims; the model refers the entire legitimate event on the worst possible week → **Do instead:** a declarable CAT mode that removes (not zeroes) those features, with a model variant trained for it.
> - **Mistake:** Sizing capacity for the average → **Why it's wrong:** CAT is when the system matters most and when the clock is least forgiving → **Do instead:** size for the sustained peak, queue the instantaneous spike, and make surge behaviour a functional requirement.
> - **Mistake:** Free-text pause reasons → **Why it's wrong:** becomes "awaiting stuff" within a month, and the clock stops being defensible → **Do instead:** enumerate per clock rule and reject at the API boundary.
> - **Mistake:** Asynchronous audit writes copied from the fraud-detection design → **Why it's wrong:** here the audit record *is* the regulatory artifact, and 15 s of a 10.5 min budget is noise → **Do instead:** synchronous, pre-action, fail closed.
> - **Mistake:** Storing only the normalised field value → **Why it's wrong:** a dispute three years later is about what the document said, not what the parser made of it → **Do instead:** verbatim text plus page and bbox.

---

## 4.4 Interview follow-ups

**Q: You called triage the highest-value model. Why not extraction — it's 85% of your cost?**
Cost share is not value share. Extraction is a *capability*; triage is the *decision*. The system exists to reconcile two things that genuinely conflict — a statutory clock measured in days and a fraud investigation measured in weeks — and triage is the only component that allocates the scarce resources those two demands compete for. Improving extraction F1 from 0.96 to 0.97 changes the gate-block rate slightly. Improving triage changes how 240,000 claims a month are routed, which changes both leakage and deadline exposure. I'd also note that extraction being 85% of cost is precisely why the *workflow* decision (lazy extraction) beat any model decision on cost.

**Q: Why is the confidence gate a hard blocker? Surely a strong coverage result should count for something.**
Because the two aren't commensurable. A clean coverage validation says "given these facts, the claim is covered." If one of those facts is a `claimed_amount` we read at 0.71 confidence off a photographed invoice, the coverage result is confidently answering the wrong question. No amount of downstream certainty repairs an uncertain input. The asymmetry decides it: a blocked claim costs a handler about twenty seconds — we show them the invoice page with the bounding box highlighted — while an uncertain field driving an automated settlement costs a wrong payment plus a compliance finding. And that twenty-second cost is exactly what lets me keep the gate strict; without FR-17's provenance the gate would be a full manual re-read and the pressure to relax it would be enormous.

**Q: Your audit write is synchronous. In the fraud-detection design you argued the opposite. Which is right?**
Both, and the discriminator is what the record is *for*. In card authorisation the budget is 60 ms and the decision is reconstructable from the transaction record — the audit row is a convenience, so a synchronous durable write is an unaffordable cost for a recoverable loss. Here the budget is 15 minutes, the write is 15 seconds, and the audit record **is** the regulatory artifact: a settlement whose basis cannot be produced is a finding regardless of whether the money was right. Same technique, opposite call. I'd be suspicious of an engineer who applied one pattern to both, in either direction — it would mean they'd copied a decision instead of making one.

**Q: What happens when the handler queue can't absorb the work?**
Triage's capacity layer relaxes the straight-through threshold for otherwise-clean claims, and it records `capacity_adjusted = true` with reason `handler_capacity_breach_risk`. That is an explicit decision to accept a small amount of avoidable leakage rather than breach statutory deadlines, and I want it visible in the decision record rather than happening as an unlogged queue overflow. The reason it has to be automatic is the alternative: an unbounded queue means claims silently age past their deadlines, which is the failure the whole design exists to prevent. It is the same structure as the review-queue cap in [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/) and the analyst queue in [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) — **human capacity sets the operating threshold, not model quality** — and in all three the right move is to make the trade explicit rather than let capacity express itself as decay.

**Q: How do you know your fraud recall is 0.60?**
Honestly, without a random holdout I wouldn't. Confirmed-fraud labels exist only for claims SIU chose to investigate, so a model trained on them learns the existing referral policy, and recall measured against those same confirmed cases has a denominator the old policy already caught. It looks excellent and means very little. FR-21 buys the real measurement: refer a small random fraction regardless of score, investigate them, and use that stream — and only that stream — for prevalence and recall estimation. It costs a handful of investigations a week and it's the cheapest genuine measurement in the system. I'd rather report a lower number I can defend than a higher one I can't.

**Q: A hailstorm hits. Walk me through what the system does.**
Volume in one region spikes toward 10× within hours, and the referral monitor sees it first: fraud referrals in that region jump six-fold on hail-pattern claims. Population-concentration features are suppressed **provisionally** at that point, before any human declares anything, because waiting for a declaration would flood SIU for hours with the legitimate event. Ops then declares the CAT — peril, region, date range — which retro-attributes in-flight claims, confirms the suppression, and re-ranks the SIU queue, withdrawing referrals that existed only because of population features. Those withdrawals are logged with a reason so investigators don't experience them as lost work. From there, extraction defaults to the cheap-first tier for CAT-typical simple claims, straight-through thresholds loosen for the declared peril, and deadline-driven priority becomes the primary scheduler. The clock, notably, does not care that there was a hailstorm.

**Q: Why suppress those features rather than set them to zero?**
Because zero is a value the model reads. A GBDT trained with `similar_claims_same_region_7d` present has learned splits on it, and feeding it zero during a CAT tells it "this claim is unusually isolated" — which is both false and, in some trees, a fraud signal in its own right. So the features are removed and the model has a CAT-suppressed variant trained without them. It costs a second model artifact and it's the difference between suppression working and suppression producing new, weirder errors.

**Q: What's the highest-consequence silent failure in this design?**
A wrong row in the clock table. Every other failure is loud: services alarm, queues deepen, accuracy drops. A wrong `duration_days` for one (product, jurisdiction) produces confident, precise, wrong deadlines for every claim in that class — and the system will cheerfully report zero breaches against a deadline that isn't the legal one. That's why FR-11 makes the table effective-dated, audited, and citation-bearing, why `clock_rule_version` is pinned per claim so a correction can't retroactively re-date claims in flight, and why there's a daily diff against compliance's source of truth. It's also a good illustration that the riskiest part of a regulated system is often a configuration table rather than a model.

**Q: What would you build first?**
The deadline service and the audit trail — before any model. They're the two things whose absence is a compliance problem rather than an efficiency problem, and both are useful immediately against the *manual* process: a compliance team that can see every claim's clock and escalate before breach is better off on day one, with handlers doing all the work. Then extraction with the confidence gate but **no straight-through** — running in shadow, so I can measure the gate-block rate per document type and calibrate confidence against handler-confirmed values on real claims. Straight-through settlement only turns on when I can show the gate's calibration per document type. Fraud scoring comes after that, and the random holdout starts on the same day the scorer does, not later — retrofitting an unbiased baseline once thresholds are tuned is much harder than starting with one.

**Q: What breaks at 100×?**
Two things change in kind rather than degree. Extraction economics invert: at 336M pages a month, fine-tuned in-house models per document type are obviously correct, and the frontier VLM becomes the fallback for genuinely novel documents rather than the workhorse. More interestingly, human review stops being a capacity problem and becomes an organisational one — 800k claims/day at even 10% review is 80k reviews/day, and at that point the design question isn't "how do we route to handlers" but "what does a handler do that the system cannot." The honest answer reshapes the product: handlers become exception specialists and quality auditors, and the system needs a **sampling-based quality regime** rather than per-claim review. The rest of 100× is arithmetic; that part is a redesign.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **FNOL** | First Notice of Loss — the initial claim report | The entry point; often the only structured document |
| **Statutory clock** | Regulated maximum time to resolve a claim | A legal obligation in days, categorically different from a latency SLO |
| **Clock pause** | A jurisdiction-permitted suspension of the deadline | Must be typed and enumerated (FR-12) or the clock stops being defensible |
| **Straight-through** | Settled with no human touch | ≥ 35% target; the business case |
| **Leakage** | Money paid that should not have been | The cost side of loosening thresholds |
| **SIU** | Special Investigations Unit — fraud investigators | Scarce, slow, and the capacity ceiling on referral precision |
| **Triage** | The route decision: straight-through / handler / SIU | The highest-value model; allocates the scarce resources |
| **Capacity layer** | Converts triage's *preference* into an actual assignment | Prevents routing 60% of claims into a pool that absorbs 20% |
| **Tiered extraction** | Extracting only the fields the next decision needs | −30% cost; the workflow lever that beats model swaps |
| **Confidence gate** | Hard block on automated decisions using uncertain fields | Where extraction accuracy becomes extraction *safety* |
| **Cross-document reconciliation** | Requiring agreement where a fact appears twice | Stronger evidence than any single confidence score; disagreement is also a fraud signal |
| **Corroboration bonus** | Confidence credit for independent agreement | Two documents at 0.88 beat one at 0.95 |
| **CAT event** | Declared catastrophe (peril + region + dates) | Adjusts extraction defaults, thresholds, and the fraud feature set |
| **Population-concentration features** | "Many similar claims here this week" | Must be suppressed under CAT — the concentration *is* the event |
| **Expected recovery** | P(fraud) × exposure | The correct currency for ranking investigator time |
| **Random-holdout referral** | Investigating a small random sample regardless of score | The only unbiased recall estimate available |
| **Selection bias (fraud labels)** | Labels exist only where the old policy referred | Makes naive recall describe imitation, not detection |
| **`UNLABELLED`** | Never investigated, therefore unknown | Collapsing this to "legitimate" is the classic error |
| **Label maturity** | Time for an outcome to become knowable | Immature windows must be excluded from evaluation |
| **On-path audit** | Audit committed before the action is emitted | Here the record *is* the regulatory artifact — opposite call from §02 |
| **Effective-dated clock table** | Statutory rules as versioned data with citations | Regulations change by regulation, not by release |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../08_media_recommendation_ranking/`](../08_media_recommendation_ranking/)
