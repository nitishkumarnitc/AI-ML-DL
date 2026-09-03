# 04 · Production & Interview — LLM Inference Platform

> **Phase 4 of 4** · [← LLD](03_lld.md) · [README](README.md)

---

## 4.1 AI-specific concerns

### Cost — the concern that questions the project

Fully worked in [§1.6](01_requirements.md#16-capacity--cost-estimation). The summary:

| Option | Cost / 1M output tokens | Verdict |
|---|---:|---|
| Self-hosted 8B @ 60% util, on-demand | ≈ $5.92 | vs $0.60 hosted small ⇒ **~10× worse** ❌ |
| Self-hosted 8B @ 85% util, reserved | ≈ $1.47 | Still ~2.4× worse than small-tier ❌ |
| Self-hosted 70B @ 85% util, reserved | ≈ $6–8 | vs $15 frontier ⇒ **~2× better** ✅ |

**Utilization is the only real cost lever**, and it's why `GPU utilization ≥ 60%` is an *economic*
threshold rather than a vanity metric. Everything that improves utilization — continuous batching,
paged KV, queue-depth autoscaling — is a cost control.

**The honest position: don't justify this platform on cost for small models.** Name the residency,
latency, or privacy driver ([Q1](01_requirements.md#open-questions)).

### Latency — two metrics, not one

| Metric | Phase | Bound by | Improved by |
|---|---|---|---|
| **TTFT** | Prefill | Compute | Chunked prefill · prefix cache reuse · warm capacity · short queues |
| **TPOT** | Decode | **Memory bandwidth** | Continuous batching · int4 weights · speculative decoding |

**They trade against each other**, which is why a single "latency" number would hide the real decision.
Prioritizing prefill improves TTFT for new requests while spiking TPOT for everyone already generating
([F3](02_hld.md#25-failure-modes--blast-radius)); prioritizing decode does the reverse. The scheduler's
per-iteration prefill token budget *is* that dial.

### Evaluation

Evaluation here differs from every other system in this set: **the platform doesn't change model
behaviour, it changes how models are served** — so the eval question is *"did serving change what the
model produces?"*

| Tier | What's measured | Gate |
|---|---|---|
| **Output equivalence** | New version/quantization vs baseline on a golden set | **Blocks on any quality regression** |
| **Quantization impact** | int4 vs fp16 output quality, especially at long context | Blocks if degradation exceeds tolerance |
| **Prefix cache correctness** | Cached-prefix outputs vs uncached, byte-identical | **Blocks on any mismatch** — this is a correctness invariant |
| Speculative decoding | Output identical to non-speculative; acceptance rate | Blocks on any output difference |
| Throughput | tok/s per node at fixed batch composition | Alerts on > 15% regression |
| Latency | TTFT/TPOT percentiles | Blocks on > 20% regression |

**Prefix-cache correctness deserves its own gate.** [E8](03_lld.md#36-edge-cases--correctness) is a
silent-corruption bug: reusing a block whose preceding tokens differ produces fluent, wrong output with
no error. A byte-equality test between cached and uncached paths is the only thing that catches it.

**Speculative decoding must be output-identical, not just fast.** Correctly implemented, the draft
model only *proposes* tokens that the target model verifies, so output is unchanged. If a
speculative-decoding change alters output at all, the implementation is wrong — which makes this an
unusually crisp test.

### Prompt injection

**Largely not this platform's problem, and saying so is the correct scoping answer.** This layer is
transport — it doesn't interpret content, hold tools, or take actions. Injection defence belongs to the
consumers: [02](../02_customer_support_agent/04_production_and_interview.md#41-ai-specific-concerns)
(policy engine), [03](../03_multi_agent_system/04_production_and_interview.md#41-ai-specific-concerns)
(per-role allow-lists), [10](../00_requirements_all_systems.md#10-enterprise-ai-agent-platform).

Two things that *are* in scope:

| Concern | Control |
|---|---|
| **Cross-tenant prefix-cache leakage** | Cache keys include `tenant_id`. Otherwise tenant B's request could match a block containing tenant A's prompt — **a data leak dressed as a cache hit** |
| Batch isolation | Requests share a forward pass but never share attention context; verified by test |

**The prefix-cache tenancy issue is the real risk here**, and it's the same shape as
[01](../01_production_rag_system/03_lld.md#the-permission-leak-through-cache-problem)'s
permission-leak-through-cache: a performance optimization that becomes a data-leak vector when the key
omits an identity dimension.

### Observability

Per request: tokens, TTFT, TPOT, queue time, **KV peak**, preemption count, prefix-cache hit, model
version served, fallback flag.

| Signal | Why it exists |
|---|---|
| **KV occupancy %** | The scarce resource. Sustained > 90% means admission is about to start deferring |
| **`est_output_tokens` vs actual** | Calibrates the admission estimator — over-estimating idles the GPU, under-estimating causes preemption thrashing |
| **Preemption rate** | Rising means the estimator is mis-tuned or the traffic mix shifted |
| Queue depth + wait | The autoscaling signal; the only measure of unmet demand |
| Prefix-cache hit rate | Directly drives TTFT |
| **Fallback rate** | Capacity shortfall — and the reason a team's quality changed |
| GPU utilization | The economic threshold |

**Recording the estimate alongside the actual is the non-obvious one**, and without it the admission
estimator can't be tuned — you'd see preemption thrashing with no way to tell whether the cause was bad
estimates or genuinely bursty traffic.

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Metrics | Alert |
|---|---|---|
| **KV** | Occupancy % per pool; blocks free; admission defer rate | Occupancy > 90% for 5 min · defer rate > 10% |
| **Queue** | Depth, wait p95, deadline-exceeded rate | Wait p95 > 200 ms · any 504s |
| Latency | TTFT/TPOT p50/p95/p99 per model | TTFT p95 breach · TPOT p95 > 25 ms |
| Throughput | Output tok/s per node; batch size distribution | > 15% below baseline |
| **Utilization** | GPU util %; **cost per 1M tokens** | Util < 50% sustained (**the economics break**) |
| Preemption | Rate; per-request counts; estimator error | Rate > 5% of requests |
| **Fallback** | Rate by alias; which tier absorbed it | Any sustained fallback |
| Models | Version per alias; canary %; load failures | Any load failure · canary error-rate delta |
| Tenants | Top KV consumers; 429s by limit type | One tenant > 40% of pool KV |

**Cost per 1M tokens on the dashboard, next to utilization**, is deliberate. It's the number that
determines whether the platform should continue to exist, and burying it in a monthly finance review
means nobody notices utilization decay until the bill arrives.

### Triage order

1. **KV occupancy.** Near-full explains queueing, deferrals, preemption, and latency at once. Start here.
2. **Queue depth vs GPU util.** Deep queue + high util ⇒ genuinely out of capacity. Deep queue + *low*
   util ⇒ admission control or the scheduler is the problem, not hardware.
3. **Preemption rate.** High ⇒ check estimator error (`est` vs actual). Usually a traffic-mix shift.
4. **Context-length distribution.** A shift toward long prompts collapses concurrency ~8× with no other
   symptom ([§1.5](01_requirements.md#the-concurrency-ceiling)).
5. **Per-tenant KV.** One tenant dominating is [F2](02_hld.md#25-failure-modes--blast-radius).
6. **Fallback rate.** Non-zero means capacity shortfall — and explains "the model got worse" reports.
7. **Model version + canary state.** Rules out a bad rollout.
8. **Only then** node health and hardware.

**Step 2 is the diagnostic that saves the most time.** Deep queue with low GPU utilization is
counter-intuitive and points squarely at admission control being too conservative — adding hardware
would not help and would make the economics worse.

### Rollback

| Change | Rollback | Speed |
|---|---|---|
| **Model version** | Repoint the alias from `alias_history` | **Instant** — no caller changes |
| Quantization config | Repoint to the previous version | Instant, if that pool still exists |
| Scheduler/batcher config | Config push | Seconds; applies to new iterations |
| Admission tuning (safety margin, estimator) | Config push | Seconds |
| Prefix cache | Feature flag off | Instant — **use this first if output looks corrupted** |
| Pool topology | Re-drain and rebuild | Minutes |

**Alias-based rollback is the payoff of the registry design.** Without aliases, rolling back a model
means 30 teams changing a version string. With them, it's one write.

**Turning off the prefix cache is the correct first move on any suspicion of corrupted output** — it's
the only component that can silently produce wrong tokens ([E8](03_lld.md#36-edge-cases--correctness)),
and disabling it costs TTFT rather than correctness.

---

## 4.3 Common mistakes

> **Mistake:** Sizing GPUs by model weights alone.
> **Why it's wrong:** **KV cache is the constraint.** A 70B fits in 35 GB at int4 — and one 32k request
> needs 10.5 GB on top.
> **Do instead:** size for weights **plus** projected KV at your real context distribution ([§1.5](01_requirements.md#15-the-memory-arithmetic-that-sizes-everything)).

> **Mistake:** Autoscaling on CPU utilization.
> **Why it's wrong:** GPU inference leaves CPU idle while the GPU saturates — you scale late on load and
> early on idle.
> **Do instead:** queue depth and queue wait ([§2.2](02_hld.md#autoscaling-and-routing)).

> **Mistake:** Rate limiting on requests per minute only.
> **Why it's wrong:** ten 32k-context requests can consume the whole KV budget while respecting an RPM
> limit.
> **Do instead:** TPM **and** RPM, plus a per-tenant `max_context` ([E15](03_lld.md#36-edge-cases--correctness)).

> **Mistake:** Static batching.
> **Why it's wrong:** the batch runs at the pace of its longest sequence while finished slots idle —
> roughly 5× throughput lost.
> **Do instead:** continuous batching ([§2.2](02_hld.md#batching--the-throughput-decision)).

> **Mistake:** Fixed max-batch-size as the admission rule.
> **Why it's wrong:** works until someone sends long contexts, then it OOMs — and an OOM kills **every**
> in-flight request on that GPU.
> **Do instead:** KV-aware admission on projected footprint ([§3.3](03_lld.md#admission-control)).

> **Mistake:** Rejecting requests that don't fit right now.
> **Why it's wrong:** KV frees continuously; you reject requests you could serve 200 ms later.
> **Do instead:** distinguish `terminal` from `kv_pressure` — reject the first, queue the second.

> **Mistake:** Unchunked prefill.
> **Why it's wrong:** one 32k prompt stalls every in-flight decode, spiking TPOT for all users.
> **Do instead:** chunk prefill against a per-iteration token budget.

> **Mistake:** Swapping KV to host memory on preemption.
> **Why it's wrong:** PCIe bandwidth makes the swap slower than recomputing the prefill.
> **Do instead:** recompute-based preemption with priority escalation to prevent starvation.

> **Mistake:** Leaving KV allocated after a client disconnects.
> **Why it's wrong:** a disconnected client holds the scarce resource that queued requests need.
> **Do instead:** detect disconnect and free blocks in the same iteration ([F11](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** Prefix cache keyed without `tenant_id`.
> **Why it's wrong:** tenant B matches a block containing tenant A's prompt — **a data leak dressed as a
> cache hit.**
> **Do instead:** include tenant identity in the key ([§4.1](#prompt-injection)).

> **Mistake:** Silent model fallback.
> **Why it's wrong:** teams debug quality regressions that were really routing events.
> **Do instead:** `X-Model-Version` and `X-Fallback` on every response ([§3.2](03_lld.md#32-api-contracts)).

> **Mistake:** Callers pinning model versions directly.
> **Why it's wrong:** every retirement becomes a multi-team migration.
> **Do instead:** aliases the platform repoints after evaluation.

---

## 4.4 Interview follow-ups

### "How many concurrent requests can one H100 serve?"

There's no single number, and that's the substance of the answer — it's a function of context length. A
70B at int4 leaves about 45 GB for KV; at ~327 KB per token that's roughly 4 concurrent requests at
full 32k context, ~34 at realistic 4k contexts, or ~280 at 512 tokens. Anyone quoting a fixed
concurrency figure has implicitly assumed a context distribution. This is exactly why admission control
must be KV-aware and why rate limiting needs TPM rather than just RPM.

### "Why is KV cache the constraint rather than model weights?"

Weights are a fixed, one-time cost — 35 GB at int4 for a 70B, loaded once. KV cache is *per request* and
*grows with every generated token*, so it's the variable consumer competing for what's left. On an 80 GB
card that's 35 GB fixed and ~45 GB divided among concurrent requests. And GQA is load-bearing here: with
full multi-head attention the per-token KV would be roughly 8× larger, making a single 32k request need
~84 GB — unservable on one GPU. Modern models use grouped-query attention specifically to make long
contexts affordable.

### "Why not autoscale on GPU utilization?"

Because a well-batched inference server runs at ~100% GPU utilization *by design* — that's the goal.
Utilization therefore hits its ceiling long before the system is overloaded, so it can't distinguish
"efficiently busy" from "requests are piling up." Queue depth and queue wait measure demand that isn't
being served, which is what you actually want to scale on. CPU is worse still: GPU inference leaves CPU
mostly idle, so CPU-based scaling reacts late to load and early to idleness.

### "Walk me through what happens when the GPU runs out of KV mid-generation."

The scheduler tries to allocate a new block for the growing sequence and fails. Rather than OOM — which
would kill every sequence sharing that GPU — it selects the lowest-priority preemptable sequence, frees
its blocks, and requeues it for re-prefill. The victim's `preempted_count` increments, and past a
threshold its priority escalates so it can't be starved indefinitely. Preemption is recompute-based
rather than swapping KV to host memory, because PCIe bandwidth makes the swap slower than just
recomputing the prefill. If there's no victim available, the request fails with a 503 — the honest
outcome when there's genuinely nothing to yield.

### "Is self-hosting cheaper than using an API?"

For an 8B model at the utilization we assumed, no — it's about 10× more expensive: roughly $5.92 per
million output tokens versus $0.60 for a hosted small-tier API. Even at 85% utilization with reserved
pricing it's ~$1.47, still worse. Self-hosting wins in two situations: when you're replacing
**frontier**-tier API usage, where $6–8 versus $15 is a real 2× saving at scale; or when the driver isn't
cost at all — data residency, privacy, latency floors, avoiding provider deprecation. My
recommendation would be to resolve that question before writing code, because if the answer is "to save
money on our 8B workload," the arithmetic says don't build it.

### "How do you do a zero-downtime model update?"

Blue/green at the pool level with alias indirection. Load the new version into a fresh pool, wait for a
readiness probe that confirms both the model *and* the KV allocator are initialized, then canary a small
percentage by repointing the alias. Watch TTFT, TPOT, error rate, and the eval metrics; ramp to 100%;
then *drain* the old pool rather than terminating it — it stops admitting but finishes in-flight
streams, so nobody's connection is cut. Rollback at any point is repointing the alias from
`alias_history`, which requires no caller changes. The one caveat: rollback is only available while the
old pool still exists, so there's a real cost/safety trade in how long you keep it drained-but-alive.

### "What's the most dangerous bug in this system?"

Prefix-cache corruption. It looks like a pure optimization, but attention is causal, so a cached KV block
is only valid if *every* preceding token matches too. Reuse a block whose prefix differs and you get
attention over the wrong context — producing fluent, confident, wrong output with no error anywhere. The
controls are requiring a contiguous match from token 0, pinning blocks for in-flight sequences, and a CI
gate asserting byte-equality between cached and uncached paths. It's also why turning the prefix cache
off is the first move whenever output looks corrupted.

### "One tenant is degrading everyone else. What's happening and what do you do?"

Almost certainly long contexts rather than request volume. One tenant sending 32k-context requests
consumes KV roughly 8× faster per request than the 4k average, so they can starve the pool while
comfortably respecting an RPM limit. Three layers of defence, because no single one is sufficient: a TPM
limit (token volume is what maps to the scarce resource), a per-tenant KV block quota, and a per-tenant
`max_context` cap. The cap is the blunt one but it's the only thing that stops a *single* request from
being enormous.

### "What breaks first at 10×?"

GPU procurement, not software. 1,280 H100s is a supply-chain problem on a vendor's timeline, not a budget
line item. The architectural response is to treat hosted APIs as a **standing overflow tier** rather than
an emergency fallback — which means the design must already handle "some traffic served externally" as a
normal condition, including its data-residency implications. That's a meaningful constraint if residency
was the reason for self-hosting in the first place.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **KV cache** | Cached Key/Value tensors per layer, per token, so attention isn't recomputed | **The constraint on concurrency** — per-request and grows with length |
| **Paged KV** | KV allocated in fixed-size blocks on demand | Short requests release early; avoids stranding worst-case reservations |
| **GQA** | Grouped-Query Attention — several query heads share one KV head | Cuts KV per token ~8×; what makes long contexts affordable |
| **Prefill** | Processing the entire prompt to produce the first token | Compute-bound, parallel; dominates **TTFT** |
| **Decode** | Generating tokens one at a time | **Memory-bandwidth-bound**, sequential; dominates **TPOT** |
| **TTFT** | Time To First Token | Perceived responsiveness; prefill-dominated |
| **TPOT** | Time Per Output Token | Sustained reading speed; < 25 ms ⇒ ≥ 40 tok/s |
| **Continuous batching** | Sequences join/leave the batch mid-flight | **~5× throughput** vs static — eliminates idle slots |
| **Static batching** | Fixed batch runs until all sequences finish | Simple; wastes most of the GPU on variable-length output |
| **Chunked prefill** | Splitting a long prompt across iterations | Stops one 32k prompt spiking TPOT for everyone |
| **Admission control** | Deciding whether a request's projected KV fits | Prevents OOM, which would kill **all** in-flight requests |
| **`terminal` vs `kv_pressure`** | Never-fits vs doesn't-fit-yet | Reject the first; **queue** the second |
| **Preemption** | Evicting a sequence's KV to free capacity | Recompute beats PCIe swap; needs priority escalation to avoid starvation |
| **Prefix cache** | Reusing KV blocks for identical prompt prefixes | ≥ 30% TTFT win — and a **silent-corruption risk** if the match isn't contiguous |
| **Speculative decoding** | A draft model proposes tokens the target verifies | Faster TPOT; **must be output-identical** |
| **Quantization (int4/int8)** | Lower-precision weights | Not just cost — **it's what frees the KV budget for batching** |
| **Queue depth** | Requests waiting for admission | The **only** valid autoscaling signal here |
| **TPM / RPM** | Tokens- and requests-per-minute limits | TPM maps to the scarce resource; RPM alone is insufficient |
| **Model alias** | Stable name (`prod-fast`) resolving to a pinned version | Insulates callers from retirements; enables instant rollback |
| **Drain** | Stop admitting, finish in-flight | Delivers zero-dropped-request updates |
| **GPU utilization ≥ 60%** | Average GPU busy fraction | An **economic threshold** — below it, self-hosting loses to APIs |
| **Prefill/decode disaggregation** | Separate pools per phase | The 100× move; removes the compute-vs-bandwidth compromise |

---

**Files:** [README](README.md) · [Requirements](01_requirements.md) · [HLD](02_hld.md) · [LLD](03_lld.md) · **Production & interview** (this file)
