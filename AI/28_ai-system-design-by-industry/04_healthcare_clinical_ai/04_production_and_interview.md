# 04 · Production & Interview — Healthcare Clinical AI

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

| Concern | How this design handles it |
|---|---|
| **Token cost** | ~$0.030/summary against a **$0.40 ceiling** — 13× headroom. Breakdown: frontier LLM $0.0285 (6,000 in / 700 out), rerank ~$0.001, guardrail ~$0.00014. At 125k summaries/day ⇒ **~$112k/month**. Comfortably funded, which is itself the finding: **spend the headroom on correctness** (second-pass verification, self-consistency on high-risk claims) rather than on features |
| **Latency budget** | Sums to **~1,700 ms against a 2,000 ms TTFT SLO**. Two non-negotiables inside it: the **80 ms blocking authorisation** (caching it would create a window where revoked access works) and **overlapped-but-retractable verification** (which imposes a UI requirement) |
| **Model routing & fallback** | Frontier only for narration — no routing, because a cheaper model on clinical summarisation is a false economy at this cost level. Fallback chain: provider → secondary → **structured-facts-only view** (allergies, meds, problems, recent labs rendered from the structured store with citations). That degraded mode is fully grounded because it's a *rendering*, not a generation |
| **Evaluation** | Four gated suites, all requiring clinical sign-off: **citation accuracy** (≥ 0.99, span-level), **groundedness** (≥ 0.98), **paired refusal** (recall ≥ 0.95 *and* over-refusal ≤ 0.05 — both directions, per FR-16), and **adversarial cross-patient** (must be 0). CI blocks on any regression; a prompt change is a release |
| **Hallucination / groundedness** | Three structural layers rather than one statistical hope: (1) structured facts are **rendered, not generated**; (2) the model cites **opaque handles** it cannot fabricate (FR-13); (3) every claim/span pair is **entailment-verified** with a negation guard (FR-14/15). Any uncited clinical claim is stripped |
| **Guardrails** | Input: scope check (a diagnosis request is refused at the API layer with 422, not left to the model). Output: uncited-claim strip, PHI-leak check, entailment verification. **Fail closed** throughout — the degraded state is "no summary," which is exactly the pre-existing workflow |
| **Prompt injection** | Lower surface than the marketplace case, but real: clinical notes contain free text authored by many people, and a note could contain instruction-shaped text. Treated as untrusted data; the model has **no tools and no write path** (FR-11), so the worst outcome is a bad summary caught by verification — not an action. See [`../../21_ai-system-design-deep-dives/06_prompt_injection_defense.md`](../../21_ai-system-design-deep-dives/06_prompt_injection_defense.md) |
| **Prompt / version management** | `prompt_version`, `model_version`, **and every `guideline_version` relied upon** persisted per disclosure. The guideline versions matter as much as the model: "per the 2019 guideline" and "per the 2026 guideline" are different clinical statements |
| **Drift** | Retrieval quality on a fixed clinician-authored query set (weekly); **citation-verification failure rate** as the fastest quality signal; guideline staleness against `review_due_on`; and refusal-rate band monitoring in both directions |
| **PII / PHI** | The dominant compliance concern. Provider-agnostic adapter (FR-18) so self-hosting is a config change; **per-request egress logging** (FR-19); infrastructure-level egress allow-list so an application bug cannot send PHI to a non-BAA endpoint |
| **Observability** | Every disclosure records what was **displayed** (not merely generated), which chunks were shown, all version stamps, the verification verdicts, and the authorisation decision id. Queryable by patient and by clinician — both are audit questions that get asked |
| **Non-determinism** | `temperature=0` for the summarisation path. Full reproducibility of a past disclosure comes from the stored `response_text` plus resolvable citations, not from re-running the model — **the record is the artifact**, not the reproduction |
| **Cold start & capacity** | Cold patient partitions cost latency on first access (budget absorbs it); partitions pre-warmed for patients with scheduled appointments — cheap and high-hit-rate. Reranker GPU pool autoscaled on queue depth |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| TTFT p50/p95/p99 | p95 > 2 s for 5 min |
| **Cross-patient assertion failures** | **any** → page immediately, security incident |
| **Citation verification failure rate**, by reason | > 2% overall; **any** `negation_inverts_claim` spike |
| Uncited-claim strip rate | > 1% (suggests prompt regression) |
| **Refusal rate** (both directions) | outside 5–20% band — high *or* low |
| Over-refusal on the answerable control set | > 0.05 |
| Authorisation latency p99 / error rate | p99 > 120 ms, or any error spike |
| Guideline staleness (`review_due_on` passed) | any cited guideline overdue |
| PHI egress destinations | **any** endpoint not on the allow-list |
| Structured-facts-only fallback rate | > 2% of requests |
| Disclosure write failures | **any** — a displayed summary without a record is a compliance defect |
| Partition cold-start latency | p95 > 400 ms |

### On-call triage order

1. **Any cross-patient assertion failure?** Stop everything. This is a potential reportable breach. The assertion hard-fails the request rather than filtering, so no leak reached a clinician — but the bug must be found before the system continues serving. Page security and clinical leadership.
2. **Disclosure writes failing?** Take the feature offline. A summary displayed without an audit record cannot be un-displayed, and the audit *is* the liability artifact. This is the one failure where degrading to "no service" is unambiguously correct.
3. **Citation verification failures spiking?** Check for a prompt or model change first (auto-revert if one is in canary). A `negation_inverts_claim` spike is the highest-severity variant — it means meaning-inverting citations are being attempted.
4. **Refusal rate out of band?** Both directions are incidents. Too high = the system is useless and clinicians will abandon it (and that abandonment is hard to reverse). Too low = it's answering things it shouldn't.
5. **PHI egress anomaly?** Infrastructure allow-list should have blocked it; if a new destination appeared, treat as a security incident regardless of whether data actually left.
6. **Latency breach?** Check reranker queue depth and partition cold-start rate. Do not "fix" it by shortening the authorisation timeout.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| Prompt | Revert `prompt_version` pointer | seconds |
| Model | Adapter config flip; previous model warm | < 1 min |
| Verification thresholds | Config revert — but **only upward** (stricter) without clinical review | seconds |
| Chunker / offsets | **Hard** — requires re-ingestion and re-binding. Hence offset stability is a CI-tested contract | hours |
| Guideline version | Mark superseded; previous version remains citable for audit | minutes |

---

## 4.3 Common mistakes

> - **Mistake:** One global vector index with a `patient_id` post-filter → **Why it's wrong:** post-filtering leaks through relevance signals and breaks top-k semantics, and a single cross-patient hit is reportable → **Do instead:** per-patient partitions, so no code path searching across patients exists.
> - **Mistake:** Filtering out a wrong-patient chunk when detected → **Why it's wrong:** it masks a bug that must be found; the system continues serving with a known scope violation → **Do instead:** hard-fail the request and raise a security incident.
> - **Mistake:** Letting the model write citations like `[Progress Note, 2026-06-02]` → **Why it's wrong:** plausible-looking references are trivially fabricated, and 0.99 accuracy is unreachable → **Do instead:** opaque per-request handles the model cannot invent.
> - **Mistake:** Treating a citation as verified because the document is right → **Why it's wrong:** the span matters; citing "penicillin allergy" from a span reading "no penicillin allergy" is a direct hazard → **Do instead:** span-level entailment with a negation guard and sentence-boundary expansion.
> - **Mistake:** Caching the patient-authorisation decision → **Why it's wrong:** creates a TTL-length window in which revoked access still works → **Do instead:** block for the 80 ms; it's the price of the guarantee.
> - **Mistake:** Paraphrasing allergies and medications through the model → **Why it's wrong:** these are the highest-consequence facts and the least appropriate to generate → **Do instead:** render from the structured store with citations; let the model narrate around them.
> - **Mistake:** Shipping the refuse path without measuring it → **Why it's wrong:** the model has strong parametric medical knowledge, so its failure mode is a *plausible* answer, not silence — and untested refusal simply doesn't fire → **Do instead:** paired unanswerable/answerable eval sets gated in CI.
> - **Mistake:** Reporting only refusal recall → **Why it's wrong:** a system that refuses everything scores perfectly and is unusable → **Do instead:** gate over-refusal too; both directions are the requirement.
> - **Mistake:** Overwriting documents on amendment → **Why it's wrong:** every historical citation silently starts pointing at different text, and audit records become false → **Do instead:** version documents; citations bind to a version.
> - **Mistake:** Asynchronous audit write → **Why it's wrong:** correct for a payment path ([`../02_banking_fraud_detection/`](../02_banking_fraud_detection/)), wrong here — the record is the legal artifact and the disclosure has already happened → **Do instead:** synchronous, before display.
> - **Mistake:** Asking the LLM about drug interactions → **Why it's wrong:** unversioned, unauditable, silently drifts between model versions, and edges toward a clinical determination → **Do instead:** a maintained knowledge base surfaced with its own citation.
> - **Mistake:** Using de-identification as a substitute for a BAA → **Why it's wrong:** clinical narrative is notoriously re-identifiable and de-identification errors are breaches; it also degrades quality, since dates carry clinical meaning → **Do instead:** obtain a BAA, or self-host.

---

## 4.4 Interview follow-ups

**Q: 4.8 billion chunks. How do you index that?**
I don't. The requirement forbids cross-patient retrieval, so no query ever spans patients — which means this isn't one 4.8-billion-vector problem, it's **two million independent ~2,400-chunk problems**. Each is small enough for an exact brute-force scan in under a millisecond, so I don't need ANN at all, and I get exact recall rather than an approximation I'd have to reason about clinically. The hot set is ~8% of patients (90-day activity), so ~384M chunks resident. **The reframing came from reading FR-2, not from a better index** — and it's the single highest-leverage move in the design.

**Q: Why is a wrong citation worse than a missing one?**
Because of what each does to the clinician's behaviour. A missing citation prompts scepticism — they go read the record themselves. A wrong citation *invites* trust: they click it, see a real document from the right patient, skim a plausible span, and accept the claim. The system has then manufactured false confidence, which is worse than having said nothing. That asymmetry is why the NFR is 0.99 rather than a more comfortable 0.95, and why verification is a pipeline stage instead of a prompt instruction. The specific failure I'd design against first is truncation inverting a negation.

**Q: You have 13× cost headroom. Why not use a cheaper model and save money?**
Because at $112k/month against a $0.40-per-summary ceiling, cost isn't the binding constraint — **correctness is**, and this is the one system in the set where I have budget to spend on being right. So I spend it: a second-pass entailment verifier, self-consistency checks on high-risk claim classes (allergies, medications, negations), and a stricter guardrail model. Recognising when you have headroom to spend on correctness rather than reflexively optimising cost is a real design skill, and the opposite call from [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/), where cost forced a change to the product itself.

**Q: What happens if you can't get a BAA?**
The design changes materially and I'd want that surfaced early rather than discovered late — it's the highest-leverage open question in the requirements. Self-hosting shifts quality (smaller models), latency (our own GPU serving, so TTFT is ours to hit), cost (a GPU fleet instead of per-token), and operational burden (model serving becomes our on-call). That's why FR-18 puts model access behind a provider-agnostic adapter: the fallback is a configuration change and a capacity plan, not a rewrite. What I would *not* do is de-identify and proceed — clinical narrative is highly re-identifiable, de-identification errors are themselves breaches, and stripping dates removes clinically meaningful information like "post-op day 3."

**Q: The system refuses too often and clinicians stop using it. What went wrong?**
Probably that I gated only refusal recall and not over-refusal. FR-16 requires both, on paired eval sets, precisely because a system that refuses everything looks perfect on a safety metric and is worthless. Operationally I alarm on the refusal rate leaving a band in *either* direction, and I treat "too high" as an incident with the same seriousness as "too low" — arguably more, because clinician abandonment is very hard to reverse once it happens. If it did happen, I'd look first at whether `classify_required_evidence` is over-specifying what a question needs.

**Q: Walk me through a regulator asking what a clinician was shown last March.**
Query `disclosures` by patient and date. It returns the exact `response_text` **as displayed** — including any retractions, so it reflects what the clinician actually saw rather than what the model generated — plus every chunk shown with document ids and versions, the claim-to-handle citations with their verification verdicts, the model and prompt versions, every guideline version relied upon, and the authorisation decision that permitted the access. Citations resolve to the *cited document version*, and if that document was later amended, resolution says so explicitly rather than silently showing current text. The design decision that makes this work is versioning documents instead of overwriting them.

**Q: Why keep the audit write on the critical path when system 02 explicitly took it off?**
Because the domain constraint is opposite. In the payment path, a synchronous audit write puts the audit store's availability inside a transaction that must never be blocked — so it goes off-path with reconciliation. Here, the disclosure *is* the liability artifact: a summary shown to a clinician with no record that it was shown is a compliance defect that cannot be repaired afterwards, because the disclosure already happened. Same mechanism, opposite call, and being able to explain why is more useful than a general rule about audit writes.

**Q: How is this not a medical device?**
Because it informs rather than determines, and that's enforced structurally rather than promised. There is no EHR write credential anywhere in the system (FR-11, verified by infrastructure audit rather than code review), no tool that proposes an order or a diagnosis, and a diagnosis request is refused at the API layer with a 422 rather than left to the model to decline. The place this genuinely gets uncomfortable is FR-8, drug interactions — surfacing "this combination is contraindicated" is close to a determination. The mitigation is that it comes from a maintained clinical knowledge base and is presented as that source's statement with its citation, so the system is a retrieval surface for a curated source rather than an opinion generator. I'd want a regulatory review of that specific boundary rather than asserting it myself.

**Q: What would you build first?**
The structured-facts view — allergies, active problems, current medications, recent labs, rendered from the structured store with citations, and no LLM at all. It's useful on day one, it's fully grounded by construction, it's the degraded mode the whole system falls back to, and building it first forces the extraction and citation-binding infrastructure to be correct before any generation is layered on. I'd add narration only once citation verification is measurably at target on a clinician-reviewed eval set.

**Q: What breaks at 100×?**
The per-patient partitioning assumption, and it's a genuine redesign rather than a knob. At 200M patients even an 8% hot set is 16M partitions and ~38B resident chunks, so partition metadata and cold-start management dominate. I'd move the partition boundary from *patient* to *encounter* — a query touches the relevant care episode plus a patient-level summary layer — which keeps scans small but adds a hard problem: deciding which encounters are relevant to a question without searching all of them. Secondarily, verification becomes the dominant compute, so I'd tier it: a cheap check on all claims and expensive entailment only on a clinically-reviewed list of high-risk claim classes.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Decision support (vs determination)** | Software that informs a clinician rather than making a clinical decision | An architectural constraint (no write path, no order tools) that keeps the system off the medical-device boundary |
| **Per-patient partition** | One small index per patient; no global index exists | Turns a 4.8B-vector problem into 2M tiny ones and makes cross-patient leakage structurally impossible |
| **Opaque citation handle** | Per-request token (`h1`, `h2`) the model cites instead of writing a document reference | Eliminates fabricated citations — the model cannot invent a handle it wasn't given |
| **Citation span** | `(document_id, version, start_offset, end_offset)` plus the exact quoted text | "Somewhere in this note" is not a citation a clinician can verify |
| **Entailment verification** | Checking that a cited span actually supports the claim made | The layer that gets citation accuracy to 0.99 |
| **Negation guard** | Span expansion + scope check when negation tokens are present | Prevents citing "penicillin allergy" from "no penicillin allergy" |
| **Offset drift** | Chunker changes shifting span offsets so citations silently mis-resolve | Why offset stability is a CI-tested contract |
| **Document versioning** | Amendments create a new version rather than overwriting | Without it, historical citations and audit records silently become false |
| **`refuted` status** | An explicit record that a finding was ruled out | "No penicillin allergy" is data, not an absent row |
| **Refuse path** | Explicit insufficient-evidence response naming what's missing | The model's failure mode is a *plausible* answer, not silence |
| **Over-refusal** | Refusing questions the record can actually answer | The failure that looks like safety and is actually uselessness |
| **Structured-facts view** | Allergies/meds/problems/labs rendered from typed storage with citations | The degraded mode — fully grounded because it's a rendering, not a generation |
| **Disclosure record** | Synchronous audit of what was displayed, to whom, when, under which versions | Liability attaches to what the clinician saw, so it's on-path |
| **Patient-scope authorisation** | Blocking, uncached check of a current treatment relationship | Caching it would create a window where revoked access still works |
| **Scope-violation assertion** | Runtime check that every returned chunk belongs to the requested patient | Hard-fails rather than filtering, so a bug is loud instead of silent |
| **BAA** | Business Associate Agreement permitting PHI processing by a vendor | Whether one exists determines hosted vs self-hosted, and therefore cost, latency, and quality |
| **Guideline version + date** | Mandatory provenance on clinical guidance | Outdated guidance is a safety issue; unversioned corpora make FR-4 unimplementable |
| **Clinical knowledge base** | Maintained source for interactions/allergies, cited directly | Keeps FR-8 out of the model's parametric memory |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../05_logistics_forecast_optimisation/`](../05_logistics_forecast_optimisation/)
