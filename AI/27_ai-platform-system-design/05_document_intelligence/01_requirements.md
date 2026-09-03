# 01 · Requirements — Document Intelligence System

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#5-large-scale-document-intelligence-system`](../00_requirements_all_systems.md#5-large-scale-document-intelligence-system)

---

## 1.1 Problem & users

### What breaks today

An organization receives ~500k documents/day — invoices, contracts, forms, scanned images — and turns
them into structured records by hand. Consequences, in the order the business feels them:

1. **Cost scales linearly with volume.** Manual data entry at ~30 s/document is a tax that grows with
   the business.
2. **Latency is measured in days.** Documents queue behind human capacity, so downstream processes
   (payment, fulfilment, compliance) wait.
3. **Error rates are invisible.** Nobody double-keys 500k documents, so the manual baseline's accuracy
   is unknown — which makes it hard to argue the automation is *better* rather than merely faster.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **Downstream system (primary)** | Consume trustworthy structured records | Correct typed fields, with a confidence signal it can act on |
| **Human reviewer** | Fix only what needs fixing | Land on the uncertain *field*, not re-key a whole page |
| Operations lead | Hit throughput within budget | Auto-approval rate high; queue not growing |
| Compliance | Prove where a value came from | Lineage from value → field → region → page → source |

### The defining property

**This is a throughput-bound asynchronous pipeline, not a latency-bound request path** — and that single
fact changes nearly every decision relative to [01](../01_production_rag_system/README.md) and
[02](../02_customer_support_agent/README.md):

| | Interactive systems (01, 02) | This system |
|---|---|---|
| Optimize for | p95 **TTFT** in milliseconds | **Documents per second** |
| Failure response | Fail fast, tell the user | **Retry patiently**; the queue absorbs it |
| Scaling signal | Request concurrency | Queue depth |
| "Available" means | Answers are being served | **Uploads are being accepted** |
| Cost driver | Tokens | **Human review time** |

**The last row is the one that reorders the whole design** — see
[§1.6](#16-capacity--cost-estimation).

> **Mental model:** the system is a **mailroom with an expert clerk and a supervisor's desk.** The clerk
> opens everything and fills in what they're sure about; anything doubtful goes to the supervisor's desk
> with the doubtful line flagged.
>
> *Where the analogy breaks:* a human clerk *knows* when they're unsure. A model's raw output
> probability is a poor proxy for correctness unless deliberately calibrated — which is why
> [FR-5](#extraction--confidence) is P0 and why calibration gets its own monitored metric
> ([§4.1](04_production_and_interview.md#41-ai-specific-concerns)).

---

## 1.2 Functional requirements

### Ingestion

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Ingest PDF (native + scanned), TIFF, JPEG, PNG, DOCX | ≥ 99.5% accepted without crash on a 10k stratified sample |
| **FR-8** | P0 | Async processing with **idempotent retries** | Re-submitting a document never double-writes a record |
| FR-10 | P1 | Handle 500-page documents without timeout | Page-level parallelism |
| FR-11 | P1 | Dead-letter queue + replay | **No silent drops** |

**FR-8's phrasing matters.** At-least-once queue delivery means a document *will* be processed twice
occasionally. Without idempotency that produces duplicate invoices in a payment system — a far worse
outcome than a dropped document, because it moves money.

### Recognition & parsing

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-2** | P0 | OCR scanned pages | Character error rate < 2% on the benchmark set |
| **FR-3** | P0 | Layout parsing: tables, columns, headers, key-value regions | Table-structure F1 ≥ 0.85 |
| FR-9 | P1 | Classify document type before extraction | ≥ 0.97 accuracy |

**Layout parsing is a distinct requirement from OCR, not an implementation detail of it.** OCR returns
characters and their positions; it does not tell you that three of those numbers are a table row whose
header is two inches above. Extraction quality depends far more on layout structure than on raw
character accuracy — a 1% CER with correct table structure beats 0.2% CER with rows and headers
detached.

### Extraction & confidence

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-4** | P0 | Extract a typed schema per document class | Field accuracy ≥ 0.95 on P0 fields |
| **FR-5** | P0 | **Per-field confidence score** | **Calibrated**: low-confidence fields correlate with actual errors (ECE < 0.05) |
| **FR-6** | P0 | Validation rules — totals sum, dates plausible, IDs well-formed | Violations **flagged, never silently corrected** |
| FR-12 | P1 | Full lineage: page → region → field → value | Auditable end to end |
| FR-13 | P2 | Active learning from human corrections | Corrections become training data |

**FR-5 is the highest-leverage requirement in the system**, because it directly sets the auto-approval
rate and therefore the human review bill ([§1.6](#16-capacity--cost-estimation)). Note the acceptance
criterion is *calibration*, not confidence magnitude — a model that reports 0.99 on everything has high
confidence and zero information.

**FR-6 says "never silently corrected" deliberately.** A pipeline that notices an invoice's line items
don't sum to its total and quietly adjusts one has destroyed the evidence that something was wrong.
Flagging surfaces a real problem — possibly a genuinely malformed document, possibly an extraction
error, and the reviewer needs to know which.

### Human review

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-7** | P0 | Review queue for low-confidence / failed validation | **Prioritized by value × uncertainty** |

**Prioritization is what makes the queue economically sensible.** A $2 invoice with one uncertain field
and a $2M contract with the same uncertainty are not equally urgent. Ranking by expected cost of error
means the highest-value uncertainty gets human attention first — and if the queue backs up, the right
things are still getting reviewed.

---

## 1.3 Non-functional requirements

### Throughput & latency

| NFR | Target | Why this number |
|---|---|---|
| Sustained throughput | 500k docs/day ≈ **6 docs/s** | Business volume |
| Peak throughput | **25 docs/s** | 4× diurnal peak, from observed upload patterns |
| E2E latency | p95 < 5 min · p99 < 30 min | Async SLA to downstream systems. **p99 is deliberately loose** — a 500-page document legitimately takes longer |
| Page throughput | ~46 pages/s average | 4M pages/day; the actual sizing unit |

**The sizing unit is pages, not documents.** An 8-page average hides an 800-page tail, and a pipeline
sized on document count will be swamped by a handful of large contracts. Page-level parallelism
([FR-10](#ingestion)) exists so one large document doesn't monopolize a worker for an hour.

### Availability & durability

| NFR | Target | Why |
|---|---|---|
| **Ingestion accept** | **99.9%** | **Rejecting an upload is the unacceptable failure** — the source may not exist elsewhere |
| Processing availability | No hard SLO | The queue absorbs outages; processing can pause for an hour |
| **Source durability** | **99.999999999% (11 nines)** | Source documents must never be lost; they're often the legal record |
| Extraction durability | 11 nines | 7-year retention |

**Splitting "availability" into accept vs process is the important move.** They have completely
different costs and consequences: making ingestion highly available is cheap (a small stateless API plus
object storage), while making *processing* highly available means idle GPU capacity. Conflating them
leads to over-engineering the expensive half.

### Quality & cost

| NFR | Target | Why |
|---|---|---|
| Field accuracy (P0) | ≥ 0.95 | Below this, review volume kills the ROI |
| Field accuracy (P1) | ≥ 0.85 | Lower-stakes fields |
| **Auto-approval rate** | **≥ 70%** | **The entire business case** — see [§1.6](#16-capacity--cost-estimation) |
| **Calibration (ECE)** | **< 0.05** | Miscalibration fails silently in the expensive direction |
| Cost | ≤ $0.05/document | vs ~$1.50 manual entry |
| Retention | 7 years, source + extractions | Compliance |

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Synchronous/real-time extraction** | Async only. A sync API is a different, latency-bound design | A genuine interactive use case — then it's a separate service with its own SLOs |
| **Handwriting recognition** | Print only in v1; handwriting needs different models and much lower accuracy expectations | Material handwritten volume — and a renegotiated accuracy NFR |
| Document *generation* | Read-only | — |
| Languages beyond English/Spanish | v1 scope | Volume in another language exceeds ~5% |
| **Fully eliminating human review** | The target is 70% auto-approval, not 100%. The last 30% is where genuinely ambiguous documents live | Never realistically — but each point of improvement is worth ~$98k/year |
| Semantic understanding of contracts | Field extraction, not clause interpretation | That's [`21_.../02_document_intelligence_agent`](../../21_ai-system-design-deep-dives/02_document_intelligence_agent.md) |

**"Fully eliminating human review" as an explicit non-goal matters** because it's the natural
stakeholder ask. Pushing auto-approval from 70% toward 100% means progressively accepting worse
decisions on progressively more ambiguous documents; the marginal document is one a *human* finds hard.
The honest framing is that review is a permanent component whose volume we optimize.

---

## 1.5 Latency budget

E2E p95 < 5 min, measured upload → structured record available. **Async, so this is a throughput budget
expressed as latency** — most of it is queue wait, not compute.

### An 8-page document, p95

| # | Stage | Budget | Notes |
|---|---|---:|---|
| 1 | Upload accept + object-store write | 2 s | Must be fast and always succeed — the availability requirement |
| 2 | Ingest queue wait | 20 s | Absorbs the 4× peak |
| 3 | Classify document type | 3 s | One small-model call |
| 4 | Page split | 2 s | |
| 5 | Page queue wait | 30 s | |
| 6 | **OCR — 8 pages in parallel** | **25 s** | Slowest page, not the sum |
| 7 | Layout parse (8 pages, parallel) | 12 s | |
| 8 | Extract queue wait | 20 s | |
| 9 | **Field extraction** | **35 s** | LLM call over parsed text + layout |
| 10 | Validation rules | 1 s | Deterministic |
| 11 | Confidence scoring + routing | 2 s | |
| | **Total (auto-approved path)** | **≈ 2 min 32 s** | vs 5 min SLO → ~2.5 min headroom ✅ |

**Queue waits are ~70 s of the ~152 s total**, and that's by design — queues are what let the system
absorb a 4× peak without provisioning 4× the workers. Compressing them would mean over-provisioning for
a peak that occurs a few hours a day.

### The review path is not in the SLO

```
Auto-approved:  ≈ 2.5 min  ✅ within SLO
Needs review:   ≈ 2.5 min + HUMAN QUEUE TIME (minutes to hours)
```

**Human review time is deliberately excluded from the E2E SLO**, because it's bounded by staffing rather
than engineering. Including it would make the SLO unachievable and mask the part the pipeline actually
controls. The review queue gets its own separate operational target (oldest-item age).

### The 500-page tail

```
500-page document, page-level parallelism at 20 concurrent pages:
  OCR:    500 pages ÷ 20 parallel × ~3 s ≈ 75 s
  Layout: 500 ÷ 20 × ~1.5 s              ≈ 38 s
  Extract: multi-pass over sections       ≈ 180 s
  ⇒ ≈ 5–6 min — exceeds p95, lands inside the p99 < 30 min budget ✅
```

**This is why p99 is 30 min rather than 6.** A single SLO covering both an 8-page invoice and a 500-page
contract would either be unachievably tight or meaninglessly loose.

---

## 1.6 Capacity & cost estimation

### Volume

```
500,000 documents/day
Assume 8 pages/document (assumption A1)  ⇒  4,000,000 pages/day
```

### OCR — where self-hosting wins ~100×

```
Option A — cloud OCR API (assume ~$1.50 per 1,000 pages):
  4,000,000 ÷ 1,000 × $1.50 = $6,000/day  ≈ $180,000/month

Option B — self-hosted OCR on GPU (assume 40 pages/s/GPU — assumption A3):
  4,000,000 ÷ 40 = 100,000 GPU-seconds/day ≈ 27.8 GPU-hours/day
  at ~$2/GPU-hour ≈ $56/day  ≈ $1,700/month

⇒ Self-hosting is ~107× cheaper.
```

> **Why the opposite conclusion to [04](../04_llm_inference_platform/01_requirements.md#16-capacity--cost-estimation),
> where self-hosting an LLM lost by ~10×?** Three reasons, and they're the general test for when
> self-hosting wins:
> 1. **Utilization.** This workload is steady and enormous — 4M pages/day keeps GPUs near-saturated,
>    versus the 60% assumed for interactive LLM serving.
> 2. **Model size.** An OCR model is a few hundred MB, so KV cache and batching constraints
>    ([04 §1.5](../04_llm_inference_platform/01_requirements.md#15-the-memory-arithmetic-that-sizes-everything))
>    simply don't bind.
> 3. **Per-unit API pricing is high relative to the compute.** $1.50/1,000 pages is expensive for work
>    that takes 25 ms of GPU time.

### LLM extraction

```
Extraction runs on PARSED TEXT, not every page image — one call per document:
  Assume 3,000 input / 400 output tokens per document, small tier
  (3000/1e6 × $0.15) + (400/1e6 × $0.60) = $0.00045 + $0.00024 = $0.00069/doc
  500,000 × $0.00069 ≈ $345/day
```

### Storage

```
Source: 500k docs × 8 pages × ~200 KB ≈ 800 GB/day ≈ 24 TB/month
  Hot (30 d):    24 TB  @ ~$0.023/GB/mo ≈  $550/month
  Cold (7 yr):  ~2 PB   @ ~$0.004/GB/mo ≈ $8,000/month at steady state
  ⇒ Lifecycle transitions after 90 days are essential, not optional
Extractions: small (structured JSON) — negligible
```

### The total, and the finding

```
Compute + storage (self-hosted OCR):
  OCR         $56/day
  Extraction $345/day
  Storage     ~$20/day (hot tier, amortized)
             ─────────
             ≈ $421/day  ⇒  ≈ $0.0008/document   ✅ vs the $0.05 ceiling

HUMAN REVIEW at 70% auto-approval:
  30% × 500,000 = 150,000 documents/day to review
  150,000 × 30 s ÷ 3,600 = 1,250 reviewer-hours/day
  1,250 × $15/hr = $18,750/day  ≈ $562,500/month

⇒ HUMAN REVIEW IS 45× TOTAL COMPUTE COST.
```

> **⚠️ This is the finding that should reorder the engineering plan.** The instinct is to optimize OCR
> and inference cost. But compute is $421/day against $18,750/day of human time — **shaving 50% off all
> compute saves $210/day; raising auto-approval by 1 point saves $270/day.**
>
> | Auto-approval | Reviewers needed | Review cost/day | vs 70% baseline |
> |---:|---:|---:|---:|
> | 60% | ~1,667 hr | $25,000 | +$6,250 |
> | **70%** | ~1,250 hr | **$18,750** | — |
> | 80% | ~833 hr | $12,500 | **−$6,250** |
> | 90% | ~417 hr | $6,250 | **−$12,500** |
>
> **Each percentage point ≈ $270/day ≈ $98k/year.** Which is why
> [FR-5](#extraction--confidence) (calibrated per-field confidence) is the highest-leverage requirement
> in the document, and why review-*efficiency* work (landing the reviewer on the right field, good
> keyboard flow) has an ROI most engineers would not guess.

### Worker sizing

```
OCR:      4M pages/day ÷ 40 pages/s/GPU = 27.8 GPU-hr/day ⇒ ~2 GPUs at steady state,
          ~6 for the 4× peak (or autoscale on queue depth)
Extraction: 500k LLM calls/day ≈ 6 QPS ⇒ trivial against a hosted API
Parse/layout: CPU-bound, ~20 workers
Reviewers: 1,250 hr/day ÷ 8 hr shifts ≈ 156 FTE  ← by far the largest "resource" in the system
```

**156 reviewers versus 6 GPUs** is the sizing comparison that makes the point better than any argument.

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | 8 pages/document average | Medium | OCR cost and page throughput scale linearly |
| **A2** | **70% auto-approval achievable** | **Low** | **Directly scales the dominant cost.** At 50%, review costs $31k/day and the ROI weakens sharply. The number to validate first |
| **A3** | Self-hosted OCR reaches ~40 pages/s/GPU | Medium | Benchmark it; falls back to cloud OCR at ~100× cost |
| A4 | ~30 s human review per flagged document | Medium | Linear in review cost; **improvable by UI design**, which is unusually high-ROI here |
| A5 | Document classes are known and finite | Medium | Open-set extraction is much harder; see [Q1](#open-questions) |
| A6 | ~200 KB/page storage | Medium | Storage scales linearly; lifecycle policy absorbs it |

**A2 is the assumption the business case rests on**, and it can't be validated by reasoning — it needs a
labelled pilot on real documents measuring what fraction can be extracted confidently *and correctly*.
Note the two failure directions: a pipeline that auto-approves 90% while being wrong on 10% is far worse
than one that auto-approves 60% correctly.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | How many document classes, and are they known upfront? | Closed-set classification + per-class schemas vs open-set extraction — **materially different systems** | Business |
| **Q2** | **Is a wrong auto-approved field recoverable downstream?** | Sets the confidence threshold policy. If a wrong invoice total triggers an irreversible payment, thresholds must be far more conservative and 70% may be unreachable | Finance / Ops |
| **Q3** | What is the *current* manual error rate? | Without it, we can't claim the system is better — only faster. And "better than humans" is the easier bar | Ops |
| **Q4** | Who owns validation rules per document class? | Rules are domain knowledge, not engineering; unowned rules rot | Business |
| Q5 | Is review staffing elastic? | Determines whether queue backlog is an alert or an accepted condition | Ops |

**Q2 is the one that could invalidate the target.** If a wrongly-extracted total flows straight into an
irreversible payment, the acceptable false-approval rate collapses, thresholds tighten, and auto-approval
may land near 40% rather than 70% — halving the business case. **Ask it before committing to the
number.**

**Q3 is the question nobody asks and everybody should.** If manual entry is 97% accurate, a 95%-accurate
pipeline is a regression dressed as automation. If manual is 92%, the same pipeline is an improvement.
The baseline changes what "good" means.

---

**Next:** [02_hld.md →](02_hld.md) — architecture, OCR build-vs-buy, extraction strategy, confidence-driven routing, failure modes, and the scale plan.
