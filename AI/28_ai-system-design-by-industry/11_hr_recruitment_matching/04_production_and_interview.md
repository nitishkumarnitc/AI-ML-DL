# 11 · Production & Interview — HR: Recruitment & Candidate Matching

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)

---

## 4.1 AI-specific concerns

| Concern | How it shows up here | What we do about it |
|---|---|---|
| **The best label is the most dangerous label** | Recruiter advance/reject decisions are abundant, free and exactly the shape a ranker wants — and they encode whatever bias those recruiters had | v1 does not train on them (FR-19). Weights come from job analysis. The cost is real: the ranker is worse at predicting *who the recruiter would have picked*, which is not the objective |
| **Bias improves every offline metric** | A model reproducing a discriminatory screen scores 1.0 on agreement-with-recruiter, precision and NDCG | The fairness gate is the **only** metric that distinguishes learning the job from learning the bias, so it is release-blocking and evaluated in the same function as quality (`release_gate`) |
| **Proxies, not protected attributes** | A model that never sees a name ranks on age via `graduation_year`, `total_experience_months` and CV formatting | Adversarial probes over the **live feature set** (FR-15): can a protected attribute be *recovered* from what we kept? Probe feature-importance names the carrier |
| **Embeddings are unauditable proxies** | An embedding of CV prose carries writing style, formatting conventions and vocabulary — all demographically loaded, across 768 uninspectable dimensions | Embeddings are used for **retrieval recall only, never as a scoring feature** (FR-16). This is a real capability sacrifice, taken deliberately |
| **Hallucinated evidence** | A normalisation LLM asked to extract will happily assert | Every evidence item must resolve to a real span of a real document version — enforced by `CHECK`, so an invented item is **unrepresentable**, not merely detected. The LLM may point at text; it may never assert |
| **Explaining rank requires explaining absence** | The obvious implementation lists what the candidate *has*, which flatters and explains nothing | Citation binding iterates **requirements**, not matched evidence, so `no_evidence_found` is first-class — and contestable (FR-29) |
| **Parse quality is upstream of everything** | Below 0.95 F1, ranking is confident, well-cited nonsense | Per-**field** F1, not aggregate. Below the floor: `EVIDENCE_INCOMPLETE` → manual review. **Never ranked low** — that is rejection by ordering |
| **Human capacity is the throughput ceiling** | FR-3 means people, not machines, make every rejection | Capacity surfaced as a **staffing** signal (FR-14). The forbidden response is filtering low scorers — the same human-capacity pattern as [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) and [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/), but here the cap is a *legal* boundary rather than an economic one |
| **The audit needs the data the audit protects** | FR-5 needs protected attributes; FR-4 forbids their use | Separate schema, separate credentials, aggregate-only view with a k-anonymity floor in its definition. Resolved structurally, not procedurally |
| **The audit can overstate itself** | A ratio over 62% self-ID is an estimate with unknown skew | `basis_sufficient` + `self_id_response_rate` on every response. Below a minimum the API will report `FAIL` but **never** `pass` — a false pass is the dangerous direction |
| **Evaluation is a gate, not a score** | "Is the ranking good?" is contestable; "is the selection-rate ratio ≥ 0.8?" is not | Fairness in CI beside precision. Related: [`../../16_evals/`](../../16_evals/) for eval-gate mechanics, and [`../../../Shared/03_llmops/04-cicd-with-eval-gates.md`](../../../Shared/03_llmops/04-cicd-with-eval-gates.md) |

---

## 4.2 Operations & runbook

### Dashboards

**Compliance — reviewed on a schedule with a named owner, not watched for spikes:**

| Panel | Alert |
|---|---|
| **Selection-rate ratio by family × attribute** | any family < 0.8 with sufficient basis |
| **Self-ID response rate, by group** | < minimum, or a group's rate dropping — the audit is losing its basis |
| Families reported `insufficient_sample` | rising share ⇒ family taxonomy needs consolidation |
| **Probe AUC per protected attribute** | any above ceiling |
| Suppressed audit cells | rising ⇒ `k` floor biting; consider window widening |
| **Outcomes with `actor_type != 'human'`** | **> 0 is a page.** Should be structurally impossible |
| **Ranked lists with `applicants_ranked < applicants_total`** | **> 0 is a page.** Should be structurally impossible |
| Unregistered-feature drop alerts | any ⇒ a process failure upstream, name the modeller |

**Quality:**

| Panel | Alert |
|---|---|
| Parse field F1, **per field** | any field < 0.95 |
| `EVIDENCE_INCOMPLETE` rate | > 3%, or a step change ⇒ an intake format changed |
| OCR share of intake (expected ~25%) | large move ⇒ channel mix changed |
| Citation coverage | **< 100%** — FR-7 is absolute |
| Contest rate, and **contest upheld rate** | upheld rate rising ⇒ parse regression that F1 missed |
| Ranking p95 vs 3 s | > 2.5 s |
| JD quality flag rate | **near zero ⇒ the check broke** |

**Operational:**

| Panel | Alert |
|---|---|
| Review capacity: applications per recruiter per day vs ceiling | > 80% |
| Requisitions with applicants un-actioned > 14 days | any ⇒ candidates in limbo is its own harm |
| Cost per application (expected ~$0.0016) | > $0.05 |

> **Three panels that are unusual and each catches something nothing else does:**
>
> - **`actor_type != 'human'` and truncated lists are pages, despite being structurally impossible.** That is the reason to monitor them: a non-zero value means a constraint was dropped in a migration or a code path bypassed the API. You monitor the things you believe cannot happen precisely because you would otherwise never find out that your belief became false.
> - **Contest *upheld* rate.** Field F1 is measured against a labelled sample that may not represent live intake. Candidates contesting a false `no_evidence_found` are an unbiased, self-motivated audit of parse quality on real documents — often catching regressions the F1 metric misses.
> - **JD quality flag rate near zero is the alarm.** Real requisitions contain exclusionary phrasing at a measurable rate. Zero means the check stopped running, and the cheapest fairness lever in the system is silently off.

### On-call triage order

**First: is this a compliance incident or a quality problem?** They have different urgency, different owners, and different escalation paths.

**Compliance (escalate before diagnosing):**

1. **`actor_type != 'human'`, or a truncated ranked list.** Stop. Both should be impossible. **Disable the affected path**, then find out how the constraint was lost. This is a potential unlawful-automated-decision event, and the notification obligations may have clocks on them.
2. **Live selection-rate breach on a deployed model.** Roll back. A live fairness breach is a compliance incident, not a quality regression, and the rollback decision does not wait for a root cause.
3. **Self-ID response rate collapse.** The audit is losing its basis. Ratios continue to compute and become progressively meaningless — the failure mode where the artefact looks healthy and proves nothing.
4. **Unregistered-feature alerts.** A feature reached the pipeline without a registered decision. Find out whether it shipped.

**Quality:**

5. **Parse F1 per field.** A single field collapsing (usually dates or employment durations) is the common cause of ranking complaints and is a five-second check.
6. **`EVIDENCE_INCOMPLETE` rate step change.** Almost always an intake format change — a new ATS integration, a new CV template, a channel sending images where it used to send PDFs.
7. **Contest upheld rate.** Rising means parse quality dropped in a way F1 did not catch.
8. **Only then the ranker.** Compare score distributions against the incumbent on the same requisitions.

> **The rule: never respond to a capacity problem by filtering.** When review volume exceeds capacity — and it will — the pressure to hide low scorers is enormous, it will be framed as an operational necessity, and it is the exact violation FR-3 exists to prevent. The lawful responses are more reviewers, better requisition targeting (FR-8), or a product change to application intake. **Filtering is not on the list**, and this belongs in the runbook rather than in someone's memory because the pressure arrives during an incident.

### Rollback

| Situation | Action | Time to safe |
|---|---|---|
| Bad ranker deploy (quality) | Standard rollback; ranking is stateless | < 5 min |
| **Live fairness breach** | Roll back **immediately**, before root cause. Then audit which decisions were made under the bad model | < 5 min + a decision review |
| Feature enabled in error | `enabled = FALSE` in the register — takes effect on the next ranking, no deploy | < 1 min |
| Parse model regression | Roll back the parse model; **re-parse affected applications as new `document_version`s** | Minutes + a re-parse backlog |
| Constraint lost in a migration | Restore the constraint; **audit every row written in the window** | Immediate, then a full sweep |
| Citation binding failure | **Do not serve rankings without citations** — fail the request instead | Immediate |

> **The last row is the one that will be argued about.** When citation binding breaks, the tempting move is to serve rankings without explanations and fix it later — the ranking is still useful, after all. But FR-7's 100% coverage is statutory in some markets, and a ranked list with no recorded basis produces decisions that cannot be explained afterwards. **Fail the request.** Degraded mode is chronological/manual review, which is lawful, because the system never had rejection authority to lose.
>
> And note what the fairness rollback requires beyond the rollback itself: a **review of decisions made under the bad model**. Rolling back stops new harm; it does nothing about candidates already rejected under a model with a 0.70 ratio. Who reviews those, and on what basis, should be decided before it happens.

---

## 4.3 Common mistakes

1. **Implementing "never auto-reject" as a policy or a flag.** Flags get flipped; policies get forgotten during integrations. The guarantee has to be that **no endpoint exists**.

2. **Returning a top-N shortlist.** The single most natural API design here, and it is auto-rejection by omission. Complete ordered list, always.

3. **A score threshold anywhere in the system.** That is auto-rejection with extra steps, however it is described in the config.

4. **Auditing the blocklist instead of probing the feature set.** "We excluded name, age and gender" creates false confidence. The question is whether the information is *recoverable*.

5. **Using CV text embeddings as scoring features.** Fast, effective, and it distributes demographic signal across dimensions nobody can inspect — making FR-4 unauditable rather than satisfied.

6. **Redacting at query time.** The protected data is then in the ranking store, one bad join from being a feature.

7. **Protected attributes in the same schema, different table.** A join is a typo away. Separate schema, separate credentials, tested.

8. **Training on recruiter decisions because the labels are free.** Reproduces bias while improving every offline metric. The most attractive and most dangerous decision available.

9. **Ranking a badly-parsed CV low.** They land last, a top-down recruiter never reaches them, and OCR has effectively rejected a candidate.

10. **Explaining with SHAP.** Not an explanation a candidate or a tribunal can use or contest. Cite spans.

11. **Generating explanations on request.** A reconstruction, not a record — and it drifts as models change. Generate with the ranking and persist it.

12. **Listing only matched evidence in the explanation.** Rank is driven by what is missing. An explanation without absences explains nothing.

13. **Fairness telemetry batched from logs.** Log loss becomes audit loss, silently. On-path.

14. **Fairness on a dashboard instead of in the CI gate.** Nobody blocks a release on a dashboard, and the quality win always has a champion.

15. **Per-requisition selection-rate ratios.** Noise presented as compliance. Roll up to families with a minimum sample.

16. **Reporting a ratio without the self-ID response rate.** A 0.92 ratio over 15% self-identification is not a finding.

17. **Reporting 1.0 for a homogeneous group.** A false pass, and false passes are the direction that causes harm.

18. **Filtering when review capacity is exceeded.** The violation arrives disguised as operational necessity. It belongs in the runbook as forbidden.

19. **Mutating evidence spans on re-parse.** Earlier explanations then point at different text and the audit trail becomes fiction. New `document_version`.

20. **Budgeting only for inference.** Inference is ~$0.0016/application, 30× inside the ceiling. The real cost is governance — the fairness suite, probe maintenance, and human review capacity.

---

## 4.4 Interview follow-ups

**"How do you guarantee the system never auto-rejects?"**
By not building the capability. There is no reject endpoint, no batch outcome endpoint, no service-account path to an outcome, and no configuration key mapping a score to a decision. The outcome API requires a user token and returns 403 with an error that names the requirement and offers no workaround. Underneath, `recruiting.outcome` has `CHECK (actor_type = 'human')`, so a machine-authored row is unrepresentable even if the API were bypassed. Two independent layers, which is proportionate for a legal boundary — one layer is one refactor from gone. The difference between this and a policy is that a policy is a promise and this is a property.

**"Isn't a ranked list already a decision?"**
That is the sharpest question in this design and I would flag it as the open question that most changes the product. My position: ranking is not rejection, but **hiding is** — so the API returns every applicant, ordered, and never truncates. Pagination is a display affordance over a complete list. But if the applicable jurisdiction treats presenting a ranked order as itself an automated decision, then human review must be deeper than acting on a list, and that is a staffing number, not an architecture change. I would want that answered by counsel per market before scaling, and I would treat "we present a ranked list" as a claim that needs a legal sign-off rather than an engineering position.

**"You excluded name, age, gender and photo. Are you done?"**
No, and that is the point. Graduation year is age almost exactly. Total experience months is age, strongly. Postcode correlates with ethnicity. Career-gap length picks up parental leave and illness. And an embedding of CV prose carries writing style and formatting, which carry education country and socioeconomic background — a proxy nobody chose. So the test is adversarial: train a probe to predict each protected attribute **from the features the ranker actually uses**. If it succeeds above a ceiling, those features encode that attribute regardless of their names, and the probe's feature importances tell me which one carries it. That flips the question from "did we exclude the bad fields" — answerable and misleading — to "can the information be recovered", which is what the law is about.

**"Your probe says `total_experience_months` leaks age at AUC 0.81. Now what?"**
It is a legal and product decision, and my job is to make it visible and measured rather than to make it quietly. I put four options in front of the owner with numbers attached: drop it (and I measure the NDCG cost), coarsen it into buckets (measure both leakage and cost), replace duration with demonstrated-capability evidence (best on both axes, most expensive to build), or keep it with a recorded justification. Whatever is chosen goes in the feature register with the probe AUC, the mitigation, the measured accuracy cost, a rationale, and a named owner who is **not the modeller** — because a proxy decision made by whoever is optimising NDCG goes one way every time. What must not happen is the feature staying because it improves a metric and nobody being told what it costs.

**"Why won't you train on recruiter decisions? That's free labelled data."**
Because it is the most attractive and most dangerous decision available. Those labels contain whatever bias the recruiters exhibited, and a model that reproduces a discriminatory screen perfectly scores 1.0 on agreement, precision and NDCG. Every offline metric improves — which is what makes it so hard to catch. So v1 ranks job-relevant evidence with job-analysis weights, and it is genuinely worse at predicting who the recruiter would have picked. That is not a regression; predicting the recruiter is not the objective. If we later want a learned ranker, the safe version labels on **later-stage outcomes** — interview pass, on-role performance — which are sparser and slower and much closer to capability, runs shadow-only, and promotes only on fairness *and* quality with a named approver. And I would check first whether the organisation even records those outcomes; if not, the safe path does not exist and job-analysis weighting is the design rather than a stepping stone.

**"How do you audit fairness if you cannot collect protected attributes?"**
Voluntary self-identification with explicit consent and a stated purpose, in a **separate schema with separate credentials**. The ranking service's database role has no grant on it — not "does not read", cannot read, verified by a CI test that asserts the grant fails. The audit role cannot read raw rows either; it sees one aggregate view with a k-anonymity floor of 20 in the view definition, so the floor cannot be forgotten by a query author. And I would be explicit about the limits: with a 62% response rate the ratio is an estimate over the self-identified population with unknown skew, so every response carries the response rate and a `basis_sufficient` flag. Below a minimum the API reports `FAIL` but never `pass` — an unfounded pass is the direction that causes harm.

**"A new model improves NDCG by 3 points and moves the age ratio to 0.70. Ship it?"**
No, and the system will not let me. `release_gate` evaluates quality, fairness ratios and probe AUC in one function and returns one list of blockers, so there is no path that passes the quality check without passing the others. The blockers here would name the ratio, the family, and the specific feature the probe implicated. That is the gate working rather than malfunctioning — and it is worth saying that this is exactly the release that ships in a system where fairness is *monitored*: the quality win is quantified and has a champion, and the fairness regression is a chart nobody was blocking on.

**"What is actually expensive here?"**
Not inference. Parsing plus ranking plus citations comes to about $0.0016 per application against a $0.05 ceiling — 30× inside budget. The expensive part is **governance**: maintaining the fairness test suite, running and interpreting adversarial probes as the feature set changes, owning the feature register, defining and maintaining requisition families, and above all the **human review capacity** FR-3 mandates. That is labour and tooling. A design that costs only the model has costed the wrong system, and the right conclusion from a 30× cost surplus is to spend it on the audit apparatus rather than on a bigger model.

**"What breaks at 10×?"**
Human review capacity, and it is not close. Parsing and ranking scale horizontally and cost almost nothing; FR-3 makes people the ceiling. 500k applications a day cannot be reviewed by any plausible recruiting organisation. The honest answer is that this stops being primarily an engineering problem: engineering can improve ranking quality so attention is better spent, improve requisition targeting so fewer unqualified applications arrive, and add internal mobility — but at some volume the **product** must change (invite-only requisitions, staged intake) rather than the architecture bending FR-3. At 100× the binding constraint is jurisdictional fragmentation, and per-market policy becomes first-class deployment configuration rather than conditionals in code.

**"What would you cut to ship in three months?"**
Keep every compliance boundary: no reject endpoint, complete responses, parse-time redaction, store separation, on-path citations and telemetry, and the fairness gate in CI. Cut FR-10 internal mobility, FR-8 JD quality checking, the contest channel (handle corrections by email initially), multi-language parsing, and the counterfactual sensitivity suite. I would ship with a **narrower feature set** than I could — fewer features means fewer proxy decisions, and a simpler ranker whose fairness I can actually defend beats a better one whose behaviour I cannot explain. What I would not cut is the audit apparatus, because a system that ranks candidates without it is not a v1 of this product; it is a different and unlawful product.

---

## 4.5 Glossary

| Term | Meaning here |
|---|---|
| **Automated employment-decision tool** | The regulated category this system sits in. Drives the audit, notice and human-involvement requirements — and the applicable rules differ by jurisdiction (open question 1) |
| **Auto-rejection** | A candidate outcome authored by a machine. Target **0**, enforced by there being no endpoint and by `CHECK (actor_type = 'human')` |
| **Rejection by omission** | Truncating a ranked list. Ranking is not rejection; **hiding is** — hence FR-12's complete responses |
| **Rejection by ordering** | Ranking a badly-parsed CV low so a top-down reviewer never reaches them. Why `EVIDENCE_INCOMPLETE` routes to review, not to a low score |
| **Selection-rate ratio** | Advance rate of the lowest group ÷ the highest, per requisition family. **≥ 0.8, release-blocking**. Four-fifths-rule style |
| **Requisition family** | Role type × level × region. The unit of audit, because a single requisition cannot support a group ratio |
| **`basis_sufficient`** | Whether self-ID response rate supports a finding. Below the minimum the audit may report `FAIL` but never `pass` |
| **Proxy** | A feature that carries a protected attribute without naming it — graduation year, tenure, postcode, CV formatting |
| **Adversarial probe** | A model trained to predict a protected attribute *from the ranker's own features*. High AUC means the feature set leaks, whatever the features are called |
| **Feature register** | The table gating which features reach the model. `enabled = FALSE` by default; enabling a proxy-carrying feature requires a mitigation, a measured accuracy cost and a named owner who is not the modeller |
| **Redaction split** | The parse-time fork sending job-relevant evidence to `recruiting` and self-ID to `protected`. FR-18 |
| **Store separation** | `REVOKE ALL ON SCHEMA protected FROM ranking_svc`. The single line that makes FR-4 structural |
| **k-anonymity floor** | `HAVING COUNT(*) >= 20` inside the audit view. Prevents the compliance mechanism from leaking what it protects |
| **Evidence item** | An extracted claim **with a span** — page, line, char offsets, verbatim quote. Without a span it is an assertion and the `CHECK` refuses it |
| **`document_version`** | Immutable parse version. Re-parses create a new one so earlier explanations keep pointing at the text they described |
| **Citation binding** | Mapping score drivers to CV spans, iterating **requirements** so absences appear. 400 ms, on-path — larger than the model |
| **`no_evidence_found`** | A first-class, **contestable** finding. Explains rank, and invites the correction that makes it a data-quality signal |
| **`weak_evidence`** | A skill listed but not demonstrated. Distinct from `met`, because collapsing them either rewards list-padding or penalises real skill |
| **`rationale_shown`** | The citation set **as displayed** to the recruiter, persisted. Never recomputed — a regenerated explanation is a plausible one, not a true one |
| **`release_gate`** | One function returning quality, fairness and proxy blockers in one list. The architectural form of "fairness is a requirement" |
| **Job-analysis weights** | Ranking weights derived from analysis of the role, not learned from screening decisions (FR-19) |

---

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)
