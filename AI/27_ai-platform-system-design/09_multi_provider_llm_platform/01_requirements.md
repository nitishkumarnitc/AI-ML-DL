# 01 · Requirements — Multi-Provider LLM Platform (Gateway)

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
>
> Shared front-matter: [`../00_requirements_all_systems.md#9-multi-provider-llm-platform`](../00_requirements_all_systems.md#9-multi-provider-llm-platform)

---

## 1.1 Problem & users

### What breaks today

Thirty internal applications each call LLM providers directly. Every one of them has independently
reinvented the same four things — and each copy is subtly different:

| What each app rebuilt | How it actually behaves in practice |
|---|---|
| Retry logic | Some retry 429s without backoff, amplifying provider overload into an outage |
| Timeout handling | Values range from 5 s to none; the ones with none hold connections through provider incidents |
| Provider SDK integration | Pinned to whatever version shipped that quarter; upgrades are per-app projects |
| Cost tracking | Six apps track nothing. Finance sees one invoice and cannot attribute it |

The consequences compound in ways that aren't obvious from the list:

- **A model deprecation is a 30-app migration.** Providers give ~6 months' notice; coordinating 30 teams
  inside that window is a quarter of engineering time that produces no features.
- **No app has better availability than its provider**, and no app can. A provider incident is an
  application incident, every time.
- **Prompt changes ship without review** because they live inside application code, where nobody reviews
  them as the behavioural changes they are.
- **Nobody can answer "what are we spending on AI, by team?"** — which means nobody can optimize it.

### Users and jobs

| User | Job to be done | What they judge the platform on |
|---|---|---|
| **Application engineer** (primary) | Call an LLM without learning four SDKs | One endpoint, one auth model, no added latency |
| **Platform engineer** | Change routing/models without 30 redeploys | Config propagation, safe rollback |
| **Finance** | Attribute spend to team/app/feature | Reconciliation against the actual invoice |
| **Security** | Control egress and custody of provider keys | Apps never hold keys; PII never leaves policy bounds |
| **Engineering leadership** | Reduce AI spend without slowing teams | Measured savings, not projections |

### The defining constraint

> **Availability must be *higher* than any single provider's — and adding a component to the request path
> normally makes availability worse, not better.**

This is the whole design in one sentence, and it contains its own contradiction. A gateway is a new hop; the
naive expectation is that total availability equals gateway availability × provider availability, which is
*lower* than the provider alone. The platform only earns its place if fallback across providers buys back
more than the gateway costs — and that turns on two things the arithmetic in [§1.5](#15-the-availability-arithmetic--the-central-claim)
makes explicit:

1. **The gateway's own availability sets the ceiling.** No amount of provider redundancy helps if the
   gateway itself is down.
2. **Fallback only helps to the extent provider failures are independent** — and vendor diversity is not
   the same thing as infrastructure diversity.

Three further constraints shape everything else:

- **A gateway that adds latency gets bypassed.** p95 overhead must stay under 30 ms, and
  [§1.6](#16-the-latency-budget--zero-margin-by-construction) shows the stated budget lands at *exactly*
  30 ms, which is not a budget so much as a coincidence.
- **The gateway is a transport and policy layer, not an intelligence layer.** Every feature that adds
  reasoning to the request path spends the latency budget.
- **Logging is the infrastructure cost, and it must never block a request.** At 173M requests/day, request
  and response bodies are ~692 GB/day. That is the platform's real bill —
  [§1.7](#17-capacity--cost--the-costs-are-not-where-you-expect).

---

## 1.2 Functional requirements

### Unified surface

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | **P0** | One request/response shape across OpenAI, Anthropic, Gemini, Bedrock | An app switches provider by changing one config value, no code change |
| **FR-2** | **P0** | Streaming passthrough with no added buffering | First chunk forwarded within 10 ms of receipt; no chunk coalescing |
| FR-3 | P0 | **Provider passthrough escape hatch** | An app can send a provider-native payload and bypass translation, keeping auth, logging, and budget enforcement |
| FR-12 | P1 | Model alias pinning — `prod-fast` resolves to a specific version | Deprecation is a config change at the gateway, not 30 app migrations |

**FR-3 is not a concession — it is what makes FR-1 adoptable.** A unified API is by construction a
lowest-common-denominator API, and the teams using provider-specific features (structured outputs, prompt
caching, computer use, provider-side tools) are usually the most sophisticated ones. Without an escape
hatch they route around the gateway entirely, and the platform loses exactly the traffic whose cost and
egress matter most. **The escape hatch keeps policy enforcement even when it gives up translation** — that
asymmetry is the point.

### Reliability

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-4** | **P0** | **Fallback chain on provider failure**, configurable order | Failover adds < 500 ms; retried request is not double-charged |
| **FR-5** | **P0** | Circuit breaker per provider + per model, with health probes | Opens on error-rate threshold; half-open probes recover automatically |
| **FR-6** | **P0** | **Per-app fallback policy, including "do not fall back"** | An app can declare cross-provider substitution unacceptable and receive an error instead |
| FR-7 | P0 | Idempotency keys on non-streaming requests | A retried request never produces two side effects or two charges |

**FR-6 exists because silent substitution is a correctness hazard**, and it is the most common thing
gateway designs get wrong. An app whose prompt is tuned for one model — few-shot formatting, JSON-mode
behaviour, refusal boundaries — may get materially worse output from the fallback while receiving a 200 OK.
For an app that classifies support tickets, degraded output beats an error. For an app that generates
customer-facing legal text, an error beats silently different output. **Only the app knows which**, so the
policy belongs to the app, not to the gateway's defaults.

### Governance

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-8** | **P0** | Per-tenant rate limits and **hard budget caps** | Requests rejected with 429 + `Retry-After` at the cap; no overspend |
| **FR-9** | **P0** | **Per-request cost attribution** by team / app / feature | Reconciles with the provider invoice within 2% |
| **FR-10** | **P0** | Central key custody in a vault; apps never hold provider keys | Rotation is a platform operation with zero app changes |
| **FR-11** | **P0** | Full request/response logging with configurable PII redaction | Zero raw PII in third-party payloads where policy forbids it |

**FR-9's "within 2%" is harder than it reads, and it is not achievable by summing local token counts.**
Provider billing includes things a gateway cannot see from the response alone: cached-input tokens priced
differently, batch discounts, reasoning tokens billed but not always itemized, per-provider rounding, and
mid-month price changes. **The design must reconcile against invoices rather than trust its own arithmetic**
— which makes attribution a monthly closing process, not a metric. See [§3.5](03_lld.md#35-state-machines).

### Optimization

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-13 | P1 | Cost/latency/quality-aware routing policy | ≥ 30% cost reduction vs. all-frontier routing |
| FR-14 | P1 | **Exact response cache** | ≥ 25% hit rate on eligible traffic; hit path < 20 ms total |
| FR-15 | P1 | **Semantic response cache** | Near-duplicate hits at ≥ 0.95 similarity, **without breaching the 30 ms budget** |
| FR-16 | P1 | Versioned prompt registry with canary + rollback | A prompt change is reviewable, attributable, and revertible in < 60 s |
| FR-17 | P2 | Shadow traffic to a candidate model | Mirrored requests never affect the live response or the caller's budget |

**FR-15 is in direct conflict with the latency NFR, and the conflict is instructive.** Semantic caching
requires embedding the incoming request. A hosted embedding call is 20–40 ms — **more than the entire
gateway budget** — so the naive implementation of FR-15 makes the platform violate its own core NFR on
*every request*, including the ~75% that miss. The resolution is an in-process quantized embedding model
(~3–5 ms CPU) over a small per-tenant hot index; details in [§2.2](02_hld.md#22-component-choices).

---

## 1.3 Non-functional requirements

### Latency — the requirement that decides adoption

| NFR | Target | Why this number |
|---|---|---|
| **Gateway overhead** | **p95 < 30 ms** | Below provider jitter, so the gateway is invisible in app-level metrics |
| Streaming per-chunk overhead | < 10 ms | Chunk delay is perceived directly as typing speed |
| Cache-hit total latency | < 20 ms | A hit must be *obviously* faster than a call, or nobody enables it |
| Failover added latency | < 500 ms | One provider timeout's worth of delay, not two |

**"p95 < 30 ms" is chosen relative to provider variance, not to a UX threshold.** Frontier providers vary
by hundreds of milliseconds request to request; overhead under 30 ms disappears into that noise, and an app
team comparing before/after sees no regression. At 100 ms it becomes visible, someone plots it, and the
bypass conversation starts.

### Availability

| NFR | Target | Why |
|---|---|---|
| **End-to-end availability** | **99.99%** (≈ 4.3 min/month) | The entire value proposition — higher than any single provider |
| **Gateway process availability** | **≥ 99.995%** | Derived, not chosen: it is the ceiling on the above ([§1.5](#15-the-availability-arithmetic--the-central-claim)) |
| Control-plane availability | 99.9% | Config changes can wait; requests cannot |
| Logging availability | 99.9%, **async** | Log loss is acceptable; blocking a request to log it is not |

**The gateway-availability target is derived, and stating it as derived matters.** 99.995% for a component
in the synchronous request path rules out several ordinary architectural choices — a single region, a
synchronous dependency on Redis, in-place deploys — and those exclusions come from arithmetic rather than
preference.

### Scale, cost, isolation

| NFR | Target | Notes |
|---|---|---|
| Throughput | 2,000 RPS aggregate | 30 apps; planning figure sized for peak |
| Config propagation | < 60 s | Routing and prompt changes without redeploy |
| Cost attribution accuracy | Within 2% of invoices | Monthly reconciliation, not live arithmetic |
| Tenant isolation | One tenant's burst cannot starve another | Per-tenant concurrency ceilings, not just RPS limits |
| Log retention | Metadata 100% / 13 months · bodies sampled | [§1.7](#17-capacity--cost--the-costs-are-not-where-you-expect) |

---

## 1.4 Non-goals

| Non-goal | Why | Where it lives instead |
|---|---|---|
| **Hosting or serving models** | Entirely different problem — GPUs, KV cache, batching | [04 — Inference platform](../04_llm_inference_platform/README.md) |
| **Agent orchestration** | The gateway is transport + policy. Adding planning puts reasoning in the request path | [03](../03_multi_agent_system/README.md), [10](../10_enterprise_agent_platform/README.md) |
| **Guaranteeing semantic equivalence across providers** | **Impossible, and claiming it causes real incidents** — see below | Per-app fallback policy ([FR-6](#reliability)) |
| RAG / retrieval | A different system that *calls* the gateway | [01 — RAG](../01_production_rag_system/README.md) |
| Fine-tuning management | v1 scope discipline | Later |
| Being the eval platform | Shadow traffic (FR-17) produces comparisons; judging them is elsewhere | [07 — Eval platform](../07_llm_evaluation_platform/README.md) |
| Prompt *authoring* tooling | Registry stores and versions prompts; it doesn't write them | — |

> **The semantic-equivalence non-goal is the most important one to say out loud.** A unified API creates a
> powerful false impression: that `model` is a free parameter. It is not. Identical inputs to two providers
> produce different formatting, different JSON reliability, different refusal boundaries, and different
> tool-calling behaviour. The gateway normalizes the *envelope*, never the *behaviour* — and every design
> decision downstream ([FR-6](#reliability), shadow traffic, canary prompts) exists because of that gap.

---

## 1.5 The availability arithmetic — the central claim

This section exists because "99.99%, higher than any single provider" is the platform's headline claim, and
it survives contact with arithmetic only under conditions worth naming.

### Step 1 — What a single provider actually delivers

```
Observed frontier-provider availability (public status histories, incident-inclusive):
  ~99.5% – 99.9%  →  plan on 99.7%

99.7% unavailability = 0.003  ≈  2.2 hours/month
```

**An app on one provider cannot promise better than ~99.7%,** and no amount of retry logic changes that:
retries help with transient errors, not with a provider being down.

### Step 2 — What two providers buy, assuming independence

```
Two providers, failures INDEPENDENT:
  P(both down) = 0.003 × 0.003 = 9 × 10⁻⁶   →   99.9991%

Three providers:  2.7 × 10⁻⁸               →   99.999997%
```

This is the number gateway pitches quote, and **it is the number that does not survive step 4.**

### Step 3 — The gateway is a serial component, so it caps everything

```
A_total = A_gateway × A_fallback_set

Target A_total = 99.99%  =  0.9999
Best case A_fallback_set ≈ 0.999991

⇒  A_gateway ≥ 0.9999 / 0.999991  ≈  0.999909   →   ~99.991%
```

Add operational margin and the gateway needs **≥ 99.995%** — about **2.2 minutes of downtime per month,
inclusive of deploys and config pushes.**

> **This is the finding that shapes the architecture.** 2.2 min/month rules out: single-region deployment,
> a synchronous hard dependency on Redis, in-place deploys, and any control-plane failure that can take the
> data plane with it. Each of those exclusions is a design constraint derived from one division.

### Step 4 — Correlation, which is where the pitch breaks

Provider failures are **not** independent. Shared infrastructure, shared upstream capacity, and
simultaneous demand spikes correlate them:

```
Let c = fraction of provider incidents that are correlated across providers.

Effective unavailability ≈ c·p  +  (1−c)·p²      where p = 0.003

c = 0    →  9.0 × 10⁻⁶   →  99.9991%     (the pitch)
c = 0.05 →  1.6 × 10⁻⁴   →  99.984%      ⚠️ below target
c = 0.20 →  6.0 × 10⁻⁴   →  99.94%       ⚠️ well below target
```

**At just 5% correlation the fallback set alone misses 99.99%,** before the gateway's own downtime is even
multiplied in.

The practical failure is concrete and common: **Azure-hosted OpenAI and Bedrock-hosted Anthropic in the
same cloud region are not two independent providers.** They are two vendors on one failure domain. A
regional networking incident takes both, the circuit breakers open on both, and the fallback chain has
nowhere to go.

### What the design must therefore do

| Requirement forced by the arithmetic | Consequence |
|---|---|
| **Diversify infrastructure, not just vendors** | At least one provider on a *different cloud*, reached over a different network path |
| **Gateway multi-region active-active, fully stateless** | No single-region failure domain; any instance can serve any request |
| **Every gateway dependency must fail *open*** | Redis unavailable ⇒ serve with degraded rate limiting, never reject |
| **Deploys must not consume the budget** | Blue/green or rolling with connection draining; 2.2 min/month is ~1 bad deploy |
| **Control plane separate from data plane** | Config-push failure must not affect in-flight requests |
| **Publish the honest number** | 99.99% *conditional on* provider independence; state the assumption ([A4](#assumptions)) |

> **The claim to make in an interview is the conditional one.** "99.99%, achieved by multi-provider
> fallback" is a claim that collapses under one question about correlated failure. "99.99% provided at least
> two providers sit on independent infrastructure and the gateway holds 99.995% — and here's the sensitivity
> to correlation" is a claim that holds.

---

## 1.6 The latency budget — zero margin by construction

The budget as stated in the shared requirements sums to **exactly 30 ms against a 30 ms target**:

| Stage | Budget |
|---|---|
| TLS + auth (JWT verify, cached JWKS) | 5 ms |
| Rate-limit + budget check (Redis) | 6 ms |
| Routing policy evaluation | 3 ms |
| Cache lookup | 8 ms |
| Request translation to provider schema | 3 ms |
| Response translation + async log enqueue | 5 ms |
| **Total** | **30 ms** |

> ⚠️ **A budget that lands exactly on its target has no margin, and a p95 with no margin is a p99 breach
> waiting for a GC pause.** Worse, the 8 ms cache-lookup line silently assumes exact-match caching only —
> [FR-15](#optimization)'s semantic cache needs an embedding, and a hosted embedding call at 20–40 ms
> exceeds the whole budget by itself.

### Two independent problems

**Problem A — no margin.** Every line is already optimistic: 6 ms assumes two Redis round trips inside one
datacentre with no contention; 8 ms assumes a cache lookup that never misses into a second tier.

**Problem B — semantic caching doesn't fit.** Embedding the request is unavoidable for FR-15, and the
obvious implementation blows the budget on *every* request, hits and misses alike.

### The path that closes it

```
Baseline (stated)                                              30 ms   ⚠️ at target, no margin

−  Single Redis round trip: rate-limit + budget + concurrency
   in ONE Lua script                                    6 → 3  (−3 ms)
−  In-process JWT verify with locally cached JWKS,
   no network on the hot path                           5 → 2  (−3 ms)
−  Cache eligibility check BEFORE lookup: streaming,
   temperature > 0, and tool-calling requests skip the
   cache entirely (~65% of traffic)                     8 → 3  (−5 ms, weighted)
−  Routing policy compiled to a decision table at
   config-push time, not evaluated per request          3 → 1  (−2 ms)
                                                       ─────────────────
Common path                                                  ≈ 17 ms   ✅ ~13 ms margin

Cache-eligible path (in-process int8 MiniLM embed ~4 ms
   + local ANN over the tenant hot index ~3 ms)               ≈ 24 ms   ✅ within budget
Cache HIT: provider call skipped entirely                     ≈ 19 ms total
   vs. ~900 ms+ for a provider call                          ~47× faster
```

**The eligibility-check-before-lookup ordering is the load-bearing move**, and it is a scheduling decision
rather than an optimization. Streaming, non-zero temperature, and tool-calling requests are not cacheable at
all, so paying lookup cost on them is pure waste. Checking eligibility first — three field comparisons,
under 0.1 ms — removes cache cost from the majority of traffic and is what creates room for the semantic
path on the traffic that can actually use it.

**The compiled-routing-table point generalizes.** Anything that can be computed at config-push time must not
be computed per request. With 173M requests/day, 2 ms of per-request policy evaluation is ~96 CPU-hours/day
spent re-deriving an answer that changes a few times a week.

---

## 1.7 Capacity & cost — the costs are not where you expect

### Volume

```
2,000 RPS aggregate × 86,400 s  ≈  173M requests/day  ≈  5.2B/month
```

### Gateway compute is noise

```
~2 ms CPU per request × 173M  =  346k CPU-s/day  ≈  96 CPU-hours/day
   at ~$0.04/CPU-hour  ≈  $4/day  ≈  $120/month

With multi-region active-active and headroom for peak: ~$3k/month all-in.
```

**Against $500k/month of token spend, gateway compute rounds to zero.** Any argument for the platform based
on compute efficiency is arguing about 0.6% of the bill.

### Logging is the real infrastructure cost

```
173M requests/day × ~4 KB (request + response bodies + metadata)  =  692 GB/day

Hot,   7 days uncompressed:          4.8 TB
Warm, 30 days, ~4:1 compression:     ~5 TB
                                    ───────
                             ≈ $1,500/month storage + ingest
```

**Full-body retention for 13 months would be ~270 TB and dominate the platform's cost**, which forces a
split that also happens to be the right one for the users:

| Tier | What it holds | Retention | Why |
|---|---|---|---|
| **Metadata** — 100% of requests | tenant, app, model, tokens, cost, latency, status, provider, cache outcome | **13 months** | ~200 bytes/request ⇒ ~35 GB/day. **This is what finance and capacity planning need**, and it's cheap |
| **Bodies** — sampled | full request + response text | **7–30 days** | 100% for errors, ~1% of successes, 100% for flagged tenants |

> **The asymmetry is the design.** Metadata is small and answers every recurring question — spend by team,
> latency by model, cache hit rate, error rates. Bodies are 20× larger and only needed for debugging a
> specific incident, which is a *recent* activity. **Sampling bodies while keeping metadata complete gives
> up almost nothing and removes the platform's largest cost line.**

**Errors are sampled at 100% deliberately.** A 0.1% error rate means error bodies are 0.1% of volume — free
— and they are the only bodies anyone reliably asks for.

### The value side, which is the actual justification

```
Assume $500k/month org-wide token spend (A1).

Routing:  ~30% of traffic moved from frontier to small tier      ⇒ −30%
Caching:  ~25% hit rate on the ~35% of eligible traffic          ⇒ −9%
Overlap and interaction, discounted conservatively               ⇒ −40% net

Savings  ≈  $200k/month
Cost     ≈  $3k infra + $1.5k logging + ~3 engineers (~$75k fully loaded)
         ≈  $80k/month
Net      ≈  +$120k/month, ~2.5× return
         — before counting availability and migration insulation
```

### The number that doesn't reconcile, and what it implies

```
$500k/month ÷ 5.2B requests/month  ≈  $0.0001 per request
```

At small-tier pricing (~$0.30/M input, ~$1.20/M output) that is roughly **300–500 tokens per request,
averaged across everything.** So the stated numbers together describe a fleet dominated by
classification, extraction, and embedding-adjacent calls — **not long-form chat.**

That matters because it changes where the savings come from:

| If the mix is… | Then… |
|---|---|
| **Small requests, high RPS** (as stated) | Caching is strong (short prompts repeat); per-request *overhead* is the dominant design concern — 30 ms on a 200 ms call is 15% |
| **Chat-heavy, lower RPS** | Requests drop to ~10–20M/day, per-request cost rises ~10×, **routing becomes the dominant lever** and logging volume falls by 90% |

**Both are plausible readings of "30 apps," and they produce different priorities**, so the design targets
the stated figure (which sizes infrastructure conservatively) while noting that the *optimization emphasis*
should be re-derived once the real traffic mix is measured. This is [Q4](#open-questions).

---

## 1.8 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | ~$500k/month org-wide token spend | Medium | **Below ~$50k/month the platform isn't worth the engineering.** At $50k, 40% savings is $20k/month against ~$80k of cost — a losing trade. Build a shared library instead of a service |
| **A2** | 25% cache-hit rate on eligible traffic | Low | Savings drop from 40% to ~30%; routing carries the case alone. Measurable in a week with a shadow cache |
| **A3** | Apps tolerate a lowest-common-denominator API | Medium | Mitigated by design via passthrough ([FR-3](#unified-surface)) rather than left to chance |
| **A4** | **At least two providers on genuinely independent infrastructure** | **Low** | **The 99.99% claim fails** — [§1.5 step 4](#step-4--correlation-which-is-where-the-pitch-breaks). At 20% correlation the ceiling is ~99.94%. This is the assumption to verify first |
| A5 | ~35% of traffic is cache-eligible (temp 0, non-streaming, no tools) | Low | Directly scales A2's contribution; the eligibility check makes it measurable from day one |
| A6 | Providers expose token counts in responses | High | Otherwise cost attribution requires local tokenization per provider — feasible but a per-provider maintenance burden |
| A7 | 30 apps, ~2k RPS peak | Medium | See [§1.7](#the-number-that-doesnt-reconcile-and-what-it-implies) — the mix matters more than the count |

**A4 is the one that decides whether the headline claim is true**, and it is answerable in an afternoon by
listing each provider's hosting region and network path. **A1 is the one that decides whether to build at
all** — and the honest version of that check is that a gateway is worth building when token spend is large
enough that 40% of it exceeds a small team's cost. Below that line, this design is over-engineering.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | **Is cross-provider fallback acceptable per app?** | Decides whether [FR-6](#reliability)'s default is *fall back* or *fail*. Getting it wrong means either avoidable outages or silent quality changes in customer-facing output | Each app team |
| **Q2** | **Data-residency constraints per provider/region?** | Constrains the routing table, and can make the independent-infrastructure requirement (A4) unsatisfiable in some regions | Legal / Security |
| **Q3** | Who owns the prompt registry's review gate? | An unreviewed registry is application code with extra steps. Unowned ⇒ prompt changes ship unreviewed anyway | Platform + app teams |
| **Q4** | **What is the actual traffic mix?** | Determines whether caching or routing is the primary lever ([§1.7](#the-number-that-doesnt-reconcile-and-what-it-implies)) | Measurable in week 1 |
| Q5 | Hard budget caps: reject, or degrade to a cheaper model? | Rejecting is predictable; degrading is kinder but changes behaviour silently | Finance + app teams |
| Q6 | Is the gateway mandatory or opt-in? | Opt-in gets adoption but leaves cost blind spots; mandatory needs the escape hatch to be genuinely good | Engineering leadership |

**Q1 is the question whose wrong answer causes an incident.** A default of *fall back* turns provider
outages into invisible quality changes; a default of *fail* turns them into visible outages. There is no
safe global default, which is why it's a per-app declaration — and why the platform should refuse to pick
one on teams' behalf.

**Q6 determines whether the cost numbers in [§1.7](#the-value-side-which-is-the-actual-justification) are
real.** 40% savings on 60% of traffic is 24%, and the apps that opt out are usually the largest spenders,
because they're the ones with the most tuning invested in a specific provider.

---

**Next:** [02_hld.md →](02_hld.md) — architecture, the fallback and circuit-breaker design, routing, caching, failure modes, and the scale plan.
