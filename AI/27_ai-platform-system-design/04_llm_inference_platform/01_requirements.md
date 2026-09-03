# 01 · Requirements — LLM Inference Platform

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#4-llm-inference-platform`](../00_requirements_all_systems.md#4-llm-inference-platform)

---

## 1.1 Problem & users

### Establish why self-hosting at all

This is the **build** side of a build-vs-buy decision whose buy side is
[09](../00_requirements_all_systems.md#9-multi-provider-llm-platform). Before designing anything, the
driver has to be named, because **the cost case usually fails** ([§1.6](#16-capacity--cost-estimation)).

| Legitimate driver | Why it forces self-hosting |
|---|---|
| **Data residency / privacy** | Regulation or contract forbids sending content to a third party. No amount of provider assurance substitutes |
| **Latency floor** | Network round trip to a provider is unavoidable; on-prem GPUs remove it. Matters for [08](../00_requirements_all_systems.md#8-real-time-ai-voice-assistant)-class workloads |
| **Cost at sustained high volume** | Real, but **only above ~80% utilization with reserved pricing** — see [§1.6](#16-capacity--cost-estimation) |
| **Model customization** | Serving your own fine-tunes or LoRA adapters |
| **Deprecation independence** | Providers retire models on their schedule; weights you host don't move |

**If none of these apply, don't build this — use [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform).**
Open question [Q1](#open-questions) exists to force that answer before implementation.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **Application engineer (primary)** | Get inference from an endpoint | An OpenAI-compatible URL. **They should never need to know a GPU exists** |
| Platform SRE | Keep GPUs busy and healthy | Utilization ≥ 60%; no OOM; rolling updates drop nothing |
| Finance | Predictable spend | Cost per million tokens comparable to the API alternative |
| Security | Content stays inside the boundary | No egress to third parties |

### The defining constraint

**KV cache is the scarce resource, not model weights.** This is the fact that shapes every decision
downstream, and the one most designs miss — see [§1.5](#15-the-memory-arithmetic-that-sizes-everything).

> **Mental model:** the GPU is a **restaurant**; model weights are the **kitchen equipment** (fixed
> cost, installed once); KV cache is the **table space** (consumed per diner, for as long as they
> stay). Concurrency is limited by tables, not by ovens.
>
> *Where the analogy breaks:* a diner's table need is known on arrival; a request's KV footprint
> **grows as it generates**, and its final length is unknown at admission. That's why admission control
> must reason about *projected* footprint and why eviction/preemption exists at all.

---

## 1.2 Functional requirements

### Serving

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | OpenAI-compatible `/v1/chat/completions`, streaming + non-streaming | Existing SDKs work with only a base-URL change |
| **FR-2** | P0 | Serve ≥ 3 model sizes concurrently | 8B, 24B, 70B class |
| **FR-6** | P0 | Route by requested model; **fallback on capacity loss** | Explicit fallback chain; never a silent model substitution |
| FR-9 | P1 | Rolling model updates with **zero dropped requests** | Drain + blue/green |
| FR-11 | P2 | LoRA adapter hot-swap on a shared base | Multiple tenant fine-tunes without extra GPUs |

**FR-1's phrasing matters.** "OpenAI-compatible" is a *migration* requirement — the platform's adoption
depends on a one-line change in consuming apps. A bespoke API, however elegant, means 30 teams each
doing an integration project, and adoption stalls.

**FR-6 says "never a silent substitution" deliberately.** Falling back from a 70B to an 8B model changes
output quality materially. The caller must be told which model actually served the request
([§3.2](03_lld.md#32-api-contracts)), or they'll debug quality regressions that are really routing
events.

### Throughput & capacity

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-3** | P0 | **Continuous batching** | ≥ 5× throughput vs static batching at equal latency |
| **FR-4** | P0 | Per-tenant rate limits — **both RPM and TPM** | 429 with `Retry-After` |
| **FR-5** | P0 | Autoscale on **queue depth**, not CPU | Scale-up completes < 3 min |
| FR-7 | P1 | Prefix/KV cache reuse across requests | ≥ 30% TTFT reduction on shared system prompts |
| FR-10 | P1 | Speculative decoding for the large tier | Measured TPOT improvement without quality loss |

**Why both RPM and TPM.** Requests-per-minute alone lets one tenant send 10 requests with 32k contexts
and consume the entire KV budget — starving everyone while technically respecting the limit. Tokens-per-minute
is the limit that actually corresponds to the scarce resource. **Rate limiting on request count alone is
a common and expensive mistake in inference platforms.**

### Observability

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-8 | P1 | Per-request metrics: tokens, TTFT, TPOT, queue time, GPU, KV occupancy | Prometheus-scrapeable |

---

## 1.3 Non-functional requirements

### Latency

| NFR | Target | Why this number |
|---|---|---|
| **TTFT (8B)** | p95 < 400 ms | Self-hosting's main win is beating provider network latency; a slower TTFT forfeits it |
| **TTFT (70B)** | p95 < 900 ms | Larger prefill; still competitive with hosted frontier models |
| **TPOT** | < 25 ms → **≥ 40 tok/s** | Below ~20 tok/s reads as slow to a human reader. TPOT, not TTFT, governs *sustained* feel |
| Queue wait | p95 < 200 ms | Above this, add capacity — queueing means demand exceeds admission |
| Scale-up | < 3 min | Model load time dominates; sets how bursty a load the platform can absorb |

**TTFT and TPOT are separate metrics measuring separate phases.** TTFT is dominated by **prefill** —
processing the whole prompt, which is compute-bound and parallel. TPOT is dominated by **decode** —
generating one token at a time, which is memory-bandwidth-bound and sequential. Optimizations that help
one often hurt the other, so a single "latency" number would hide the trade.

### Throughput & efficiency

| NFR | Target | Why |
|---|---|---|
| Throughput (8B, batched) | ≥ 2,500 output tok/s per 8×H100 node | The utilization target that drives unit cost |
| **GPU utilization** | **≥ 60% average** | **Below this, self-hosting loses to APIs on cost** — it's an economic threshold, not a vanity metric |
| Max context | 32k tokens | The KV-cache memory driver ([§1.5](#15-the-memory-arithmetic-that-sizes-everything)) |

### Reliability & cost

| NFR | Target | Why |
|---|---|---|
| Availability | 99.9% | Multi-AZ; **GPU capacity, not software, is the practical constraint** |
| Cost | ≤ $0.30 per 1M output tokens (8B) | Must beat the API alternative to justify existing — ⚠️ **shown unachievable in [§1.6](#16-capacity--cost-estimation)** |
| Rolling update | Zero dropped requests | Drain-then-swap |

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Training / fine-tuning** | Serving only. Adapters are *consumed*, not produced | A separate training platform |
| **Serving third-party APIs** | That's [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform). **This platform serves weights we host** | — |
| Non-text modalities | Text only in v1 | Vision/audio models need different memory profiles and batching |
| **Per-request GPU isolation** | Batching across tenants is the entire efficiency mechanism | A tenant contractually requires physical isolation — then they get dedicated pools and pay for them |
| Guaranteeing output parity with hosted models | A self-hosted 8B is not a hosted frontier model | — |

**"Per-request GPU isolation" is worth stating explicitly** because it's a natural security ask that is
fundamentally incompatible with the economics. Batching requests from different tenants into one forward
pass is what produces the 5× throughput; isolating them means paying ~5× more. If a tenant needs it,
they need a dedicated pool and a different price.

---

## 1.5 The memory arithmetic that sizes everything

**This calculation determines the entire design.** Everything in the HLD follows from it.

### Model weights — the fixed cost

```
70B-class model, parameter memory:
  fp16 (2 bytes/param):   70e9 × 2   = 140 GB  → needs 2× H100-80GB, tensor-parallel
  int8 (1 byte/param):    70e9 × 1   =  70 GB  → fits 1× H100-80GB, ~10 GB left for KV ⇒ tiny batch
  int4 (0.5 bytes/param): 70e9 × 0.5 =  35 GB  → 1× H100, ~45 GB for KV ⇒ real batching possible
```

**Quantization is not primarily a cost optimization — it's what makes batching possible at all.** int8
leaves so little headroom that concurrency collapses; int4 frees the KV budget the scheduler needs.

### KV cache — the variable cost, and the actual constraint

For each token generated, the model caches Key and Value tensors per layer so it needn't recompute
attention over the whole prefix. That cache is **per-request** and **grows with sequence length**.

```
70B-class configuration (assumption A3):
  layers = 80 · kv_heads = 8 (GQA) · head_dim = 128 · fp16 KV (2 bytes)

KV per token = 2 (K and V) × layers × kv_heads × head_dim × bytes
             = 2 × 80 × 8 × 128 × 2
             = 327,680 bytes ≈ 327 KB per token

One 32k-context request: 32,000 × 327 KB ≈ 10.5 GB   ← for a SINGLE request
```

### The concurrency ceiling

```
On 1× H100-80GB with int4 weights (35 GB), leaving ~45 GB usable for KV:

  Full 32k contexts:  45 GB / 10.5 GB  ≈  4 concurrent requests
  Realistic 4k:       45 GB / 1.31 GB  ≈  34 concurrent requests
  Short 512-token:    45 GB / 0.16 GB  ≈  280 concurrent requests
```

> **⚠️ The design consequence, and the thing most inference designs get wrong: concurrency is a
> function of context length, not a fixed number.** A platform advertising "34 concurrent requests"
> collapses to 4 the moment users send long prompts. This is why:
>
> - **Admission control must be KV-aware** — admit on projected footprint, not request count.
> - **Rate limiting needs TPM, not just RPM** ([FR-4](#throughput--capacity)) — token volume is what
>   consumes the scarce resource.
> - **Paged KV allocation matters** — fixed-size per-request reservation wastes most of the budget on
>   requests that finish early.
> - **GQA is load-bearing.** With full multi-head attention (64 heads rather than 8 kv-heads), KV per
>   token would be ~8× larger — 2.6 MB/token, making a single 32k request need ~84 GB and be
>   *unservable on one GPU*. Modern models use GQA specifically to make long contexts affordable.

### Prefill vs decode — why one number won't do

```
Prefill (processing the prompt):  compute-bound, parallel across all prompt tokens
  → dominates TTFT; benefits from batching prompts together

Decode (generating tokens):       memory-bandwidth-bound, strictly sequential
  → dominates TPOT; benefits from batching many requests' single next-tokens

⇒ These two phases compete for the same GPU, and optimizing one can starve the other.
  A scheduler must decide, every step, how much prefill vs decode work to admit.
```

**This tension is the core scheduling problem** and the reason continuous batching exists — see
[§2.2](02_hld.md#22-component-choices).

---

## 1.6 Capacity & cost estimation

### Node throughput and unit cost

```
Assume (A1): 8×H100 node at ~$32/hr on-demand ≈ $23,000/month
Assume (A2): 8B model, int8, continuous batching → ~2,500 output tok/s sustained per node

Monthly output capacity at 100% utilization:
  2,500 tok/s × 2,592,000 s/month ≈ 6.48 billion output tokens

Cost per 1M output tokens at 100% utilization:  $23,000 / 6,480 ≈ $3.55
Cost per 1M output tokens at the 60% target:    $3.55 / 0.6    ≈ $5.92
```

### The comparison that decides whether to build this

| Option | Cost per 1M output tokens | Verdict |
|---|---:|---|
| **Self-hosted 8B @ 60% util, on-demand** | **≈ $5.92** | — |
| Hosted **small**-tier API | ≈ $0.60 | **Self-hosting is ~10× worse** ❌ |
| Hosted **frontier**-tier API | ≈ $15.00 | Self-hosting is ~2.5× better ✅ |
| Self-hosted @ 85% util, reserved (−65%) | ≈ $1.47 | Beats small-tier? Still ~2.4× worse ❌ |
| Self-hosted 70B @ 85% util, reserved | ≈ $6–8 | Beats frontier-tier by ~2× ✅ |

**The stated NFR of ≤ $0.30 per 1M output tokens is unachievable** — it is below even the
100%-utilization figure by an order of magnitude.

### The honest conclusion

**Self-hosting a small model to save money does not work.** Three defensible positions:

| Position | When it's right |
|---|---|
| **1. Don't build it.** Use [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform) | No residency/latency/privacy driver, and workloads suit small models |
| **2. Build it for large models only** | Replacing frontier-tier API usage, where $6–8 vs $15 is a real 2× win at scale |
| **3. Build it for a non-cost driver, and say so** | Residency, privacy, or a latency floor. **Then stop justifying it on cost** and set the NFR to "within 2× of the API alternative" |

> **Recommendation: resolve [Q1](#open-questions) before writing any code.** If the answer is "we want
> to save money on our 8B workload," the correct engineering response is *"the arithmetic says
> otherwise, here it is."* That answer is worth more than a beautifully-designed platform serving a
> purpose it can't fulfil.

### GPU count sizing

```
Assume peak demand of 20,000 output tok/s across all models (assumption A4):

  8B tier  (60% of traffic): 12,000 tok/s ÷ 2,500 per node ≈  5 nodes
  24B tier (30%):             6,000 tok/s ÷ 1,100 per node ≈  6 nodes
  70B tier (10%):             2,000 tok/s ÷   400 per node ≈  5 nodes
                                                             ────────
                                                             16 nodes = 128 H100s
  At ~$23k/node/month ≈ $368k/month

⇒ Procurement, not budget, is often the binding constraint (Q2).
  128 H100s is not an order that is filled next week.
```

**Larger models produce fewer tokens/s per node** — 70B at ~400 tok/s vs 8B at ~2,500 — because decode
is memory-bandwidth-bound and a bigger model moves more bytes per token. Hence the 70B tier needs
nearly as many nodes as the 8B tier for a tenth of the traffic.

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | GPU at ~$32/hr per 8×H100 node, on-demand | Medium | **Reserved/spot cuts 60–70% and materially changes the build-vs-buy conclusion.** Re-run before deciding |
| **A2** | ~2,500 output tok/s per node for 8B batched | **Low** | **Benchmark before committing.** Varies hugely with context length, batch composition, and quantization |
| **A3** | 70B config: 80 layers, 8 kv-heads, 128 head_dim | Medium | KV arithmetic scales proportionally; recompute for the actual model |
| **A4** | Average context ~4k, peak 20k tok/s demand | **Low** | **Long contexts collapse concurrency** — 32k contexts reduce it ~8× ([§1.5](#the-concurrency-ceiling)) |
| A5 | int4 quantization is quality-acceptable | Medium | int8 halves the KV budget and collapses batch size |
| A6 | Traffic mix 60/30/10 across tiers | Low | Changes node allocation, not the architecture |

**Ranked by decision impact: A1 > A2 > A4.** A1 and A2 jointly determine whether the platform should
exist; A4 determines how much hardware it needs.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | **What is the actual non-cost driver?** | If there isn't one, [§1.6](#16-capacity--cost-estimation) says cancel and use [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform). **Resolve first** | Product / Security |
| **Q2** | Is 128 H100s procurable on the required timeline? | Supply, not budget, is often the real constraint | Infrastructure |
| **Q3** | What is the real context-length distribution? | Assumption A4 — it sets concurrency and therefore node count | Us — measure from [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform)'s logs |
| Q4 | Is cross-tenant batching acceptable to Security? | If not, dedicated pools and ~5× the cost | Security |
| Q5 | Who owns model-version selection and deprecation? | Governance; otherwise every team pins a different version forever | Platform |

**Q3 is answerable today without building anything** — if [09](../00_requirements_all_systems.md#9-multi-provider-llm-platform)
is already logging requests, the context-length distribution is sitting in those logs. Measuring it
converts the lowest-confidence assumption into data.

---

**Next:** [02_hld.md →](02_hld.md) — continuous vs static batching, paged KV, KV-aware admission control, why queue depth is the autoscaling signal, failure modes, and the scale plan.
