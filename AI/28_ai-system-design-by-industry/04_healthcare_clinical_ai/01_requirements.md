# 04 · Requirements — Healthcare Clinical Decision Support & Medical Documents

> **Shared block:** [`../00_requirements_all_systems.md#4-healthcare--clinical-decision-support--medical-documents`](../00_requirements_all_systems.md#4-healthcare--clinical-decision-support--medical-documents) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the latency budget, and the capacity arithmetic. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. "Decision support" as architecture, not a disclaimer

FR-5 says no autonomous clinical action. That sentence is doing structural work, and it's worth tracing what it produces.

| Because the system only *advises*… | …the architecture must have |
|---|---|
| A clinician is the decision-maker | **No write path to the EHR.** Not "a write path we don't use" — no credential, no endpoint |
| The clinician must be able to check the system's claims | **Mandatory span-level citations** on every clinical assertion (FR-1) |
| The clinician must know when the system doesn't know | **A refuse path that actually fires** (FR-3), measured at ≥ 0.95 recall on an unanswerable set |
| Liability attaches to what the clinician was shown | **Disclosure audit** — what, to whom, when, from which model/prompt/guideline versions (FR-6) |
| The system must not drift into diagnosis | **No tool that proposes a diagnosis or an order.** Capability removed, not discouraged |

> **Why this framing is load-bearing rather than legal boilerplate.** Regulators in several jurisdictions distinguish software that *informs* a clinician from software that *makes* a clinical determination — the latter attracts medical-device obligations. FR-5 is drawn to keep the system unambiguously on the informing side, and **scope creep here crosses a regulatory line rather than merely adding features**. That makes it a non-goal with teeth.

**The tension to name honestly:** FR-8 (drug-interaction and allergy surfacing) edges toward the boundary, because surfacing "this combination is contraindicated" is close to a determination. The mitigation is that FR-8 draws from a **maintained clinical knowledge base**, not from the LLM's parametric memory, and presents the knowledge base's own statement with its citation. The system is a *retrieval surface* for a curated source, not an opinion generator.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | No EHR write credential exists in any service in this system | Verified by infrastructure audit, not by code review |
| **FR-12** | P0 | Clinical assertions are attributable to a source *type* | Every assertion labelled: `patient_record` \| `guideline` \| `knowledge_base`. The model may not emit an unlabelled clinical claim |

FR-12 matters because the three source types carry different authority and different staleness risks, and a clinician reads them differently. Collapsing them into undifferentiated prose destroys information the clinician needs.

---

## B. Citation semantics — what ≥ 0.99 accuracy actually requires

The shared NFR sets citation accuracy ≥ 0.99, the strictest number in this folder. Making it operational.

### What a citation is

| Component | Requirement |
|---|---|
| **Document identity** | Stable id + version (documents get amended) |
| **Span** | Character or token offsets into that document version, not "somewhere in this note" |
| **Rendered text** | The exact quoted span, shown to the clinician on hover/expand |
| **Source type** | Per FR-12 |
| **Date** | Of the source document, not of retrieval — a 2019 note and a 2026 note carry different weight |

### What counts as a citation failure

| Failure | Severity | Why |
|---|---|---|
| Citation points to a document that doesn't contain the claim | **Critical** | Manufactures false confidence — the clinician checks, sees a plausible source, and trusts it |
| Citation points to the right document, wrong span | **Critical** | Same effect; a clinician verifying by reading the span is misled |
| Claim has no citation | High | Detectable by the clinician, so less dangerous than a wrong one |
| Citation is to a superseded document version | High | The information may have been amended |
| Span is correct but truncated so as to change meaning | **Critical** | e.g. citing "penicillin allergy" from a span reading "no penicillin allergy" |

> **The ordering here is the point: a wrong citation is worse than a missing one.** A missing citation prompts scepticism; a wrong one invites trust. That's why the NFR is set at 0.99 rather than a more comfortable 0.95, and why verification is a **pipeline stage** rather than a prompt instruction.

### How 0.99 is achieved (mechanism, not aspiration)

Three layers, because no single one gets to 0.99:

1. **Citation pre-binding** — before the LLM runs, each retrieved chunk is bound to its `(document_id, version, start_offset, end_offset)`. The model is given opaque chunk handles and asked to cite handles, **not to construct citations**. This eliminates the largest failure class: fabricated document references.
2. **Post-generation verification** — every emitted claim/citation pair is checked: does the cited span actually support this claim? Implemented as an entailment check against the span text.
3. **Truncation guard** — spans are expanded to sentence boundaries before display, and negation-bearing tokens (`no`, `denies`, `ruled out`, `negative for`) trigger a mandatory wider window. This specifically targets the "cited 'penicillin allergy' from 'no penicillin allergy'" failure.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-13** | P0 | The model cites opaque handles, never constructs document references | Zero citations in output that don't resolve to a handle issued in that request |
| **FR-14** | P0 | Every claim/citation pair is entailment-verified before display | Verification recall ≥ 0.98 on a labelled set of correct/incorrect pairings |
| **FR-15** | P0 | Negation-aware span expansion | On a negation eval set, 100% of spans containing a negation token are shown with the negation intact |

---

## C. The refuse path, and why it must be measured

FR-3 requires an explicit "insufficient information in the record" response. Systems routinely ship this requirement and never verify it fires.

### Why refusal is hard here

The model has strong parametric medical knowledge. Asked "what is this patient's ejection fraction?" with no echocardiogram in the retrieved context, the failure mode is not silence — it's **a plausible general answer**, because the model knows what typical values look like. That is the most dangerous output this system can produce: clinically plausible, patient-specific-sounding, and unsupported.

### The measurement

| Eval set | Construction | Target |
|---|---|---|
| **Unanswerable-from-record** | Real clinical questions paired with records that genuinely lack the answer | Refuse-path recall ≥ 0.95 |
| **Answerable control** | Same questions, records that *do* contain the answer | Over-refusal ≤ 0.05 — refusing everything is not a solution |
| **Partially answerable** | Record contains related but insufficient evidence | Must state what it found *and* what's missing |

> **Both halves are required.** A system that refuses everything scores perfectly on the first set and is useless. The pair of metrics is the requirement, and reporting only refusal recall would be a way of hiding an unusable system behind a safety number.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-16** | P0 | Refuse path measured on paired unanswerable/answerable sets | Recall ≥ 0.95 with over-refusal ≤ 0.05, both gated in CI |
| **FR-17** | P1 | Partial answers state their gap explicitly | On the partially-answerable set, ≥ 0.90 of responses name the missing evidence type |

---

## D. The PHI egress decision (the highest-leverage open question)

Whether Protected Health Information may leave the institution's boundary determines the entire design.

| Scenario | Consequence |
|---|---|
| **BAA + zero-retention with a hosted frontier model** | Design as documented. Frontier quality, ~$0.030/summary, standard operational model |
| **No BAA obtainable** | **Self-hosted only.** Changes simultaneously: quality (smaller models), latency (own GPU serving), cost (GPU fleet rather than per-token), and operational burden (model serving becomes ours) |
| **De-identification before egress** | Attractive but fragile: clinical narrative is notoriously re-identifiable, and de-identification errors are breaches. Also degrades quality, since names/dates carry clinical meaning ("post-op day 3") |

**Design stance taken here:** assume a BAA with zero-retention terms **and** build the abstraction that makes the self-hosted path available — a model-serving interface with no provider-specific assumptions, so the fallback is a configuration change rather than a rewrite.

**Requirement added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-18** | P0 | Model access is behind a provider-agnostic interface | A self-hosted model can be substituted without changes outside the serving adapter |
| **FR-19** | P0 | PHI egress is logged per request | Which fields left the boundary, to which endpoint, under which agreement — queryable for audit |

---

## E. Additional non-goals (beyond the shared block)

- **Not** a medical device seeking regulatory clearance in v1 — and note that FR-5/FR-11 exist to keep it that way.
- **Not** de-identification as a substitute for a BAA (see §D).
- **Not** ambient recording without explicit consent capture (FR-9's documentation draft requires it).
- **Not** patient-facing without clinician approval (FR-10 keeps a clinician in the loop).
- **Not** population-level analytics or research querying — a different consent basis entirely.
- **Not** imaging interpretation.

---

## F. Open questions carried into the HLD

Beyond the shared block's list:

1. **Is a BAA with zero-retention actually obtainable from the chosen provider?** §D — the single highest-leverage unknown, because a "no" changes cost, latency, and quality simultaneously.
2. **Who authors and signs off the clinical eval set?** A groundedness benchmark written without clinician review is not a safety argument. This needs a named clinical owner, and it's a staffing question before it's a technical one.
3. **Does the guideline corpus carry version and date metadata at source?** FR-4 is unimplementable if it doesn't, and retrofitting versioning onto an unversioned corpus is a data-engineering project in its own right.
4. **What is the institution's document-amendment model?** Citations point at document *versions*; if amendments overwrite in place, historical citations silently become wrong.
5. **Is there an existing CDS alerting system this must not conflict with?** Two systems surfacing contradictory guidance to the same clinician is worse than either alone.

---

**Next:** [`02_hld.md`](02_hld.md) →
