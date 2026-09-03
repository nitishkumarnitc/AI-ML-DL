# 11 · Requirements — HR: Recruitment & Candidate Matching

> **Shared block:** [`../00_requirements_all_systems.md#11-hr--recruitment--candidate-matching`](../00_requirements_all_systems.md#11-hr--recruitment--candidate-matching) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the ~1,570 ms latency budget, and the cost arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. Why "never auto-reject" must be architectural, not procedural

FR-3 says the system never auto-rejects; the NFR table pins auto-rejections at **0** and calls it a compliance boundary rather than a tunable. That phrasing is doing real work, and it is worth making explicit what it costs to honour.

### A.1 The weak form and the strong form

| | Guarantee | Survives |
|---|---|---|
| **Policy** — "we don't use the reject endpoint" | A convention | Nothing. A bug, a new client, a well-meaning automation, a change of PM |
| **Config** — `AUTO_REJECT_ENABLED=false` | A flag | Until someone flips it, and flags get flipped during incidents |
| **Threshold** — "reject below score 0.2" | A number | Nothing — it *is* auto-rejection with extra steps |
| **Architecture** — **there is no reject endpoint** | A property of the system | A bug, a new client, an automation, a change of management |

Only the last one is a guarantee. The system's write surface for candidate outcomes is a **single endpoint that requires an authenticated human actor id and returns 400 without one.** There is no batch variant, no service-account path, and no score threshold anywhere in the codebase that maps to an outcome.

> **The general principle, and it recurs across this folder:** when a requirement is a legal boundary rather than a quality target, implement it as something the system *cannot* do, not something it *chooses* not to do. The same move as the immutable on-path audit write in [`../04_healthcare_clinical_ai/`](../04_healthcare_clinical_ai/) and the single-use partial unique index in [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/).

### A.2 What this costs, honestly

Human review capacity becomes the throughput ceiling. At 50k applications/day, if every application must be seen by a person before rejection, that is a staffing figure the product must be designed around — the same **human-capacity-sets-the-operating-point** pattern as [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) (1,200 cases/day), [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/) (3% review), and [`../07_insurance_claims_automation/`](../07_insurance_claims_automation/).

The resolution is not to weaken FR-3. It is to be precise about what "reviewed" means:

| Interpretation | Feasible at 50k/day? | Lawful? |
|---|---|---|
| A recruiter reads every CV in full | No | Yes |
| A recruiter sees every candidate in a ranked list and acts on the list | **Yes** | **Depends on jurisdiction — this is open question 1** |
| Below-threshold candidates are hidden and never shown | Yes | **No** — that is auto-rejection by omission |

The middle row is the design, and the third row names the trap: **ranking is not rejection, but hiding is.** A candidate ranked 480th of 500 has been ranked; a candidate filtered out of the response has been rejected by a machine. So the API returns **all** candidates, ordered — never a truncated shortlist — and pagination is a UI affordance over a complete list, not a cut.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | No API path produces a candidate rejection without an authenticated human actor | Code and API audit: no endpoint, batch job, or threshold maps a score to an outcome. Attempted service-account call returns 400 |
| **FR-12** | P0 | Ranked responses are complete, never truncated | Every applicant for a requisition appears in the ordered result; no minimum-score cut-off exists at any layer |
| **FR-13** | P0 | Every outcome records the human actor and the evidence they saw | Audit row contains actor id, the ranked list version, the score and rationale presented at that moment |
| **FR-14** | P1 | Review-capacity load is measured and surfaced | Requisitions whose applicant volume exceeds review capacity are flagged to the recruiting lead — a staffing signal, not a reason to filter |

---

## B. The real fairness problem is proxies, not protected attributes

FR-4 requires excluding protected characteristics and proxies, and marks it **tested**. Excluding the attributes is the easy half; it is also the half that creates false confidence.

### B.1 What a blocklist catches, and what it misses

```
Blocked outright:   name · photo · age / DOB · gender · ethnicity ·
                    marital status · nationality
```

That list is straightforward and insufficient, because the following are all **job-relevant-looking features that carry protected information**:

| Feature | What it correlates with | Why it's tempting |
|---|---|---|
| **Postcode / address** | Ethnicity, socioeconomic status — often strongly | "Commute distance is operationally relevant" |
| **University attended** | Socioeconomic status, sometimes ethnicity and age | Genuinely predictive of some outcomes |
| **Career-gap length** | Parental leave ⇒ gender; illness ⇒ disability | "Continuity of experience" |
| **Graduation year** | **Age, almost exactly** | Implied by any education record |
| **Total years of experience** | Age, strongly | Seems like the most job-relevant feature imaginable |
| **First-language fluency phrasing** | National origin | Extracted from CV prose |
| **Sports, societies, hobbies** | Class, gender, religion | "Cultural signal" |
| **CV formatting and length** | Age, socioeconomic background, and country of education | Nobody intends this as a feature; a text embedding picks it up anyway |
| **Employer names** | All of the above, via employer demographics | "Relevant experience" |

The last two are the interesting ones because they are not features anyone *chose*. An embedding of raw CV text encodes writing style, formatting conventions and vocabulary — all of which carry demographic signal. **A model that never sees a single blocklisted field can still rank on protected characteristics.**

### B.2 So the test cannot be a blocklist audit

The only defensible test is adversarial:

> **Train a model to predict each protected attribute from exactly the features the ranker uses. If it succeeds meaningfully better than the base rate, those features encode that attribute — regardless of what they are named.**

```
For each protected attribute A:
    train  P(A | ranker_features)   on the audit population
    if AUC(P) > threshold:
        the feature set leaks A. Find which features carry it and decide.
```

This flips the question from *"did we exclude the bad fields?"* (answerable and misleading) to *"can the information be recovered?"* (the question the law is actually about). It also produces something actionable: feature-importance over the *probe* model tells you which of your job-relevant features is carrying the leak.

### B.3 And then a judgement call the architecture cannot make

Suppose the probe shows that `years_of_experience` leaks age with high AUC. It almost certainly does. What now?

| Option | Consequence |
|---|---|
| Drop it | Lose the single most job-relevant feature in recruitment |
| Keep it | Accept a known age proxy in an automated employment-decision tool |
| Bucket it coarsely (0–2, 3–5, 6–10, 10+) | Reduces resolution and reduces leakage; a genuine middle path |
| Replace with **evidence of demonstrated capability** rather than duration | Better on both axes and much harder to build |

> **This is a legal and product decision, not an engineering one**, which is shared open question 4 (university/employer prestige) generalised. What engineering owes here is *making the trade visible and measured* — the probe AUC, the accuracy delta from each option, and a recorded decision with an owner. A system that silently keeps the proxy because it improves NDCG has made the decision without telling anyone.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-15** | P0 | Adversarial proxy detection over the live feature set | For each protected attribute, a probe model trained on ranker features; AUC reported per release and gated |
| **FR-16** | P0 | Text embeddings of raw CV prose are excluded from ranking features | Ranking operates on extracted structured evidence; free-text embeddings may be used for *retrieval recall*, never as a scoring feature |
| **FR-17** | P0 | Every retained feature with a known proxy relationship has a recorded decision | A feature register naming the leakage, the mitigation chosen, the accuracy cost, and the accountable owner |
| **FR-18** | P1 | Redaction happens at parse time, not query time | Protected fields never enter the evidence store used for ranking; they are written to separated storage accessible only to the audit path |

> **FR-18 is the structural version of FR-4.** Redacting at query time means the protected data is present in the ranking store and one bad join away from a feature. Redacting at parse time means it was never there.

---

## C. FR-9 is the most dangerous requirement in the system

The shared block flags this itself. It is worth being blunt about why, because FR-9 is also the most *attractive* requirement — recruiter advance/reject decisions are abundant, free, and exactly the label shape a ranker wants.

### C.1 The mechanism

```
Historical recruiter decisions  ──►  training labels  ──►  ranker
        │                                                    │
        │ contain whatever bias the                          │ reproduces it,
        │ recruiters exhibited                               │ now at scale
        │                                                    │ and with an
        └────────────────────────────────────────────────────┘ air of objectivity
```

And the part that makes it hard to catch: **every offline metric improves.** Precision, NDCG, agreement-with-recruiter — all go up, because the metric *is* agreement with the biased labels. A model that perfectly reproduces a discriminatory screening process scores 1.0.

> **This is the same structural trap as accuracy on a rare-positive problem in [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/), and it is worse here**, because there the degenerate model is obviously degenerate, while here it looks like a triumph. A fairness metric is not a refinement on top of an accuracy metric; it is the only thing that distinguishes learning the job from learning the bias.

### C.2 The decision

**v1 does not train on recruiter decisions.** The ranker scores **job-relevant evidence against requisition requirements** — skill overlap, demonstrated scope, credential match, recency — with weights derived from job analysis rather than learned from outcomes.

That is a real cost: the ranker is less personalised and probably less accurate at predicting who the recruiter would have picked. Which is the point — *predicting the recruiter* is not the objective. **Predicting job-relevant capability is**, and those two objectives only coincide if the historical recruiters were unbiased, which is the assumption under examination.

### C.3 What would make FR-9 safe enough to enable

Not "monitor it", which is the shared block's phrasing and is too weak on its own. Concretely:

| Guard | Why |
|---|---|
| **Label on *later-stage outcomes*, not screening decisions** | Passed-the-interview or performed-well-in-role is closer to capability than "a recruiter liked the CV". Much sparser, much slower, much better |
| **Fairness gate on the trained model, not just the pipeline** | Selection-rate ratio ≥ 0.8 as a release blocker (FR-5's NFR), evaluated on a held-out audit population |
| **Counterfactual testing** | Perturb a proxy-carrying feature and check the rank shift. Large shifts on demographic proxies are a finding |
| **Shadow-only until proven** | Score without acting; compare against the evidence-based ranker; promote only if fairness *and* quality both hold |
| **A named owner who can veto** | Because the metric that catches this failure is the one everyone is incentivised to explain away |

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-19** | P0 | v1 ranking weights derive from job analysis, not learned recruiter preference | Documented derivation; no training label sourced from screening decisions |
| **FR-20** | P0 | Any future outcome-trained model runs shadow-only until it passes fairness *and* quality gates | Shadow comparison recorded; promotion requires both, and a named approver |
| **FR-21** | P1 | Counterfactual sensitivity testing on proxy-carrying features | Report rank-shift distribution when a proxy feature is perturbed; large shifts investigated before release |

---

## D. Auditing requires the data that auditing is meant to protect

Shared open question 2 names a genuine catch-22 and it deserves a design answer rather than a shrug.

```
FR-5 requires selection-rate ratios by protected group.
Computing them requires knowing candidates' protected group.
Collecting protected attributes for hiring is restricted in many markets.
```

### D.1 The standard resolution, and its honest weaknesses

**Voluntary self-identification, stored separately from the ranking path.**

```
Application  ──►  parse  ──►  evidence store  ──►  ranker  ──►  ranked list
                    │                                              │
                    │ optional self-ID, explicit consent,           │
                    │ stated purpose: fairness auditing only        │
                    ▼                                              ▼
              PROTECTED ATTRIBUTE STORE ──────────────────►  audit join
              (separate schema · separate access ·          (aggregate only,
               no service account shared with ranking)       k-anonymity floor)
```

Properties that make this defensible:

| Property | Why it matters |
|---|---|
| **Voluntary and consented, with the purpose stated** | It is the only lawful basis in most markets |
| **Separated storage, separate credentials** | The ranking service physically cannot read it. Not "does not" — *cannot* |
| **Aggregate-only access** | The audit produces group rates, never per-candidate attributes joined to scores |
| **k-anonymity floor on reported cells** | A group of 3 candidates in one requisition is identifiable; suppress and roll up |
| **Never a feature, enforced by schema separation** | The strongest available version of FR-4 |

And the weaknesses, stated plainly because an audit built on self-ID has real limits:

- **Response bias.** Self-ID rates differ by group, so the audit population is not the applicant population. The ratio you compute is an estimate with unknown skew, and it should be reported with the response rate beside it.
- **Small requisitions are unauditable.** A 40-applicant requisition cannot support a group-level ratio. Auditing must roll up to **requisition families** (role type × level × region) over a time window — which the shared NFR already says, and which means a single biased requisition can hide inside a fair family.
- **Non-response is not random.** Candidates who decline to self-identify may do so for reasons correlated with the thing being measured.

> **The honest framing: this audit detects systematic disparate impact across families over time. It does not certify any individual requisition as fair, and claiming otherwise is the failure mode.** Saying so in the reporting is part of the design, because a compliance artefact that overstates its own strength is worse than one that states its limits.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-22** | P0 | Protected attributes in separated storage with no ranking-path access | Ranking service credentials cannot read the store; verified by test |
| **FR-23** | P0 | Audit reporting is aggregate with a k-anonymity floor | Cells below `k` suppressed and rolled up; no per-candidate attribute join is possible through any interface |
| **FR-24** | P0 | Self-ID response rate reported alongside every ratio | A ratio without its response rate is not a finding |
| **FR-25** | P1 | Audit rolls up to requisition families with a stated minimum sample | Families defined and owned; per-requisition ratios reported only above the minimum, otherwise explicitly "insufficient sample" |

---

## E. Explainability is a product surface, not a model property

FR-7 requires explaining, on request, what evidence a ranking was based on, and the NFR sets **100% coverage**. Two consequences that shape the architecture.

### E.1 Post-hoc attribution is not sufficient

A SHAP plot is not an explanation a candidate or a tribunal can use. What is needed is **evidence citation**: for each score driver, the span of the CV that supports it.

```
Rank 12 of 340.

Matched requirements:
  ✓ Kubernetes in production        → "…owned the K8s migration for 40 services…"  [CV p2, ln 14–15]
  ✓ Team leadership, 3+ years       → "…led a team of 6 engineers, 2021–2024…"     [CV p1, ln 22]
  ✗ Financial-services domain       → no supporting evidence found
  ~ Go (required)                   → "…Go, Rust…" listed in skills, no project evidence  [CV p3, ln 4]
```

That is auditable, contestable and actionable. It also has a useful side effect: **a candidate can correct it.** "No supporting evidence found for financial services" is a claim a candidate can rebut, which turns explainability from a compliance cost into a data-quality mechanism.

### E.2 Which means citation binding is on the critical path

The latency budget spends **400 ms — the largest single line — on evidence-citation binding**, more than the ranking model itself (240 ms). That allocation is the requirement showing up in the architecture: an explanation generated later, on request, would be a *reconstruction* of a decision rather than a record of it, and reconstructions drift from what actually happened as models and features change.

Similarly, **fairness telemetry is on-path (60 ms)**, per the shared block's note. Emitting it lazily would allow a requisition to be ranked without ever being audited — and the failure would be invisible, because the ranking still worked.

> **Both allocations follow the same rule: if a compliance artefact is produced off the critical path, there exists a code path that produces the decision without it.** Put it on-path and pay the milliseconds. There is 1,430 ms of headroom precisely so this is affordable.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-26** | P0 | Explanations cite CV spans, not feature importances | Every score driver resolves to a document span with page and line offsets |
| **FR-27** | P0 | Explanations are generated with the ranking and persisted, not reconstructed on request | The audit trail contains the rationale as presented; regenerating it later is never necessary |
| **FR-28** | P0 | Fairness telemetry is emitted on the ranking path | No code path produces a ranked list without incrementing selection-rate counters |
| **FR-29** | P1 | Candidates can contest a "no evidence found" finding | A correction channel; corrections update the evidence store and are logged as a parse-quality signal |

---

## F. Additional non-goals (beyond the shared block)

- **Not** a personalised ranker in v1 — no learning from recruiter behaviour (FR-19), deliberately.
- **Not** free-text CV embeddings as scoring features (FR-16) — retrieval recall only.
- **Not** a shortlist generator — the ranked list is complete (FR-12); truncation is rejection by omission.
- **Not** an inference engine for missing attributes — no predicting seniority, salary expectation, or anything else the candidate did not state.
- **Not** a candidate-sourcing tool (v1) — inbound applicants only, which keeps the audit population well-defined.
- **Not** video, voice, or assessment scoring — weak validity and heavy regulatory exposure, per the shared non-goals.
- **Not** a certification of fairness for any individual requisition (§D.1) — the audit detects systematic impact across families.

---

## G. Open questions carried into the HLD

Beyond the shared block's four:

1. **What counts as an "automated decision" in the applicable jurisdictions?** If presenting a ranked list is itself regulated, §A.2's middle row collapses and human review must be deeper — which is a staffing question with a large number attached. This is the single answer that most changes the product.
2. **What is the self-ID response rate, by group?** FR-24 makes it reportable; the *design* question is what response rate makes the audit meaningful at all. Below some level, the ratio is noise wearing a compliance badge.
3. **Who owns the feature register (FR-17), and can they say no?** A proxy decision made by whoever is optimising NDCG will go one way every time.
4. **What is the review capacity per recruiter per day, really?** FR-14 surfaces the load; the ceiling determines whether FR-3 is operationally sustainable or merely stated.
5. **Is there a later-stage outcome label available at all?** §C.3's safest version of FR-9 needs interview or on-role performance data. If the organisation does not record it, the safe path to a learned ranker does not exist and v1's job-analysis weighting is not a stepping stone — it is the design.

---

**Next:** [`02_hld.md`](02_hld.md) →
