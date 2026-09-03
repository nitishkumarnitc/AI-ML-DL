# 04 · Production & Interview — Multi-Provider LLM Platform

> **Phase 4 of 4** · [← LLD](03_lld.md) · [Back to README](README.md)

---

## 4.1 AI-specific production concerns

### The gateway sees provider drift that no individual app can

This is the platform's most underrated capability, and it exists purely because of its position. A provider
updating the model behind its own alias changes behaviour for every caller — same endpoint, same latency,
200 OK, different output. **An individual app cannot distinguish that from its own prompt change.** The
gateway, holding every app's traffic against pinned concrete versions, can.

The mechanism is cheap: keep a small fixed probe set per model, run it a few times a day, and track output
distribution — length, refusal rate, JSON-parse success, embedding centroid drift. None of that is judgment;
it's all cheap statistics on shape. When it moves and our pinned version didn't change, the provider changed
something.

> **This turns [F13](02_hld.md#25-failure-modes--blast-radius) from undetectable into monitored, and it is
> an argument for centralization that has nothing to do with cost.** Thirty apps each seeing 3% of the
> traffic cannot find this signal. One gateway seeing 100% can.

### Cost attribution is a monthly closing process, not a metric

The 2% target ([FR-9](01_requirements.md#governance)) is missed by every design that computes cost locally
and stops. The reasons are unglamorous and additive:

| Source of drift | Effect |
|---|---|
| Cached-input tokens priced at a fraction | Overstates cost if counted as fresh input |
| Batch/committed-use discounts | Applied at the invoice, invisible per request |
| Reasoning tokens billed but variably reported | Understates cost |
| Per-provider rounding and minimum billing units | Small, systematic |
| Mid-month price changes | Whole-month skew if the rate card isn't versioned |

**The design response is the `disputed` state in
[§3.5](03_lld.md#cost-attribution-lifecycle)**: store our computation and the reconciled figure separately,
alert when the delta exceeds 2%, and treat the delta as the accuracy metric. **Attribution accuracy is a
monitored value with an owner, not an assumption** — and a rate card that isn't versioned by effective date
will silently reintroduce the drift every time pricing changes.

### The routing quality signal has to come from somewhere else

Routing decides cost/quality trade-offs, but the gateway cannot judge quality — that requires the eval
platform ([07](../07_llm_evaluation_platform/README.md)). The honest division:

| The gateway does | The gateway does not |
|---|---|
| Route on declared task class, prompt length, provider health | Predict output quality |
| Mirror traffic to a candidate model (FR-17) | Decide which output was better |
| Record which model served which request | Own the quality bar |

**Shadow traffic produces the pairs; the eval platform judges them; the routing table encodes the verdict.**
A gateway that tries to close that loop internally has become an eval platform with a latency budget it
cannot meet.

### Prompt registry centralization has a failure mode centralization created

Moving prompts out of application code is a clear win — until a single registry change affects several apps
at once. Prompt sharing is the specific hazard: two apps converge on one `invoice-extract` prompt, one team
tunes it for their case, and the other team's output changes with no commit in their repo.

The controls that matter: **canary by percentage before `active`**, `reviewed_by` required for promotion,
and — most importantly — **per-prompt ownership with an explicit list of consuming apps.** A prompt used by
more than one app needs both owners' sign-off, or it should be forked. **Shared prompts are shared
production dependencies**, and the registry should make that visible rather than convenient.

### PII redaction must happen at egress, and the ordering is a compliance control

Redacting at log write yields clean logs and has already transmitted raw PII to a third party. **The
redaction boundary is the outbound provider call** ([E17](03_lld.md#36-edge-cases--correctness)).

Two consequences that are easy to miss:

1. **Redaction changes model input, so it changes output quality.** A design that redacts names in a
   customer-service prompt will get worse responses. That trade-off is the tenant's to make via
   `pii_redaction`, and it should be measured, not assumed harmless.
2. **Redaction sits in the 30 ms budget.** Regex-based detectors are ~1 ms; an ML-based PII classifier is
   20 ms+ and does not fit. **The strict-policy tier gets a slower path, explicitly**, rather than the whole
   platform paying for it.

---

## 4.2 Runbook

### Dashboards

**The SLO panel — gateway overhead separated from provider time:**

```
lat_gateway_ms         p50 / p95 / p99            ← THE NFR (target p95 < 30 ms)
lat_provider_ms        p50 / p95 / p99 by provider × model
lat_gateway_ms by stage: auth · governance · cache · routing · translation
```

**Availability, which is the value proposition:**

```
availability_end_to_end      (rolling 30 d, target 99.99%)
availability_gateway         (target 99.995% — the derived ceiling)
breaker_state                per provider × model, as a state timeline
SIMULTANEOUS_OPEN_COUNT      ← the A4 test. Anything ≥ 2 is the headline finding failing
failover_rate                and added latency p95
governance_degraded_rate     (fail-open events — governance is advisory while > 0)
```

**Cost:**

```
$/day by tenant / app / feature
$/day by model × provider
cost_usd vs cost_reconciled delta            ← the 2% NFR
cache_hit_rate  split exact / semantic / ineligible
routing_mix     % frontier vs small tier      ← the 30% savings claim
savings_vs_all_frontier  (counterfactual)
```

**Cache safety — no error signal exists, so the distribution is the monitor:**

```
cache_similarity histogram on hits           ← mass just above 0.95 = tuned too loose
CROSS_TENANT_CACHE_HIT count                 ← must be exactly 0, always
```

**Log pipeline:**

```
log_queue_depth · log_drop_rate · body_sample_rate_effective
bytes/day  (the real infrastructure cost line)
```

### Alerts

| Alert | Threshold | First action |
|---|---|---|
| **`SIMULTANEOUS_OPEN_COUNT` ≥ 2** | **Immediate page** | **The A4 assumption is failing.** Check whether the open providers share a cloud/region. This is the platform's core claim breaking |
| **Gateway p95 overhead** | > 30 ms for 5 min | Read the **per-stage** panel. Usual causes: Redis latency, cache eligibility misclassification |
| **Gateway availability** | < 99.995% (30 d) | Deploy history first — deploys are the most common consumer of a 2.2 min/month budget |
| **`CROSS_TENANT_CACHE_HIT` > 0** | **Immediate page** | **Data leak.** Disable the semantic cache org-wide, then find the key-construction bug |
| **`cost_usd` vs reconciled** | delta > 2% | Check for a new pricing tier, unversioned rate card, or unmodelled token type |
| Single breaker open | > 5 min | Normal operations; verify failover is working and the app policies allow it |
| **`governance_degraded_rate` > 0** | Any sustained | Redis health. **Budget caps are advisory while this is non-zero** — say so in the incident channel |
| Log drop rate | > 1% for 15 min | Log-store health. **Do not "fix" it by making writes synchronous** |
| Cache similarity distribution shift | mass moving toward the threshold | Raise the threshold; sample hits for human review |
| Routing mix shift | frontier share up > 10 pts | Usually an app re-declaring task class ([E21](03_lld.md#36-edge-cases--correctness)) |
| Provider TPM/RPM headroom | < 20% | Contract capacity conversation, before it becomes an incident |

**The `governance_degraded_rate` alert has an unusual required action: announce it.** During a fail-open
window, budget caps are not enforced exactly. Finance and the affected teams need to know that, because the
month's numbers will reflect it — and a silent degradation of a *governance* control is how a platform loses
the trust it was built to create.

### Incident playbooks

**"Two providers are down at once."**

1. This is [F4](02_hld.md#25-failure-modes--blast-radius). Confirm the third provider is serving.
2. Check whether the failed providers share a cloud region or network path.
3. **If they do, the incident is a finding, not just an outage:** [A4](01_requirements.md#assumptions) is
   false and the 99.99% claim needs restating. That belongs in the postmortem as a headline, not a footnote.
4. Verify `FALLBACK_DISALLOWED` volume — apps with `none`/`same_provider_only` are fully down and their
   owners need telling.
5. Remediation is architectural: relocate a provider to independent infrastructure. **Not more retries.**

**"Gateway overhead breached 30 ms."**

1. Per-stage panel. In practice it's almost always one of three things:
   - **Redis latency** — check governance p95; a cross-AZ Redis read is 6 ms instead of 3 ms.
   - **Cache eligibility misclassification** — if eligible-traffic share jumped, requests that should skip
     the cache are paying 7 ms of embed + ANN.
   - **A new synchronous call added to the hot path.** Diff the request pipeline against the last release.
2. Immediate mitigation: disable the semantic cache tier. Costs hit rate, restores ~7 ms instantly.
3. The structural fix is the discipline itself: **nothing enters the request path without a budget line.**

**"A team says output quality changed and their code didn't."**

1. Query `request_log` for `alias` vs `model_resolved` over the window — did the alias get repointed?
2. Check `failover_from`: were they silently served by a fallback provider?
3. Check `prompt_version`: did a shared prompt change under them?
4. Check the provider drift probes: did the provider change the model behind our pinned version?

> **This playbook is the platform's best argument in one query.** Before centralization, that question was
> unanswerable — a team spent a day bisecting their own prompt. After, it's four lookups in a table that
> already exists. **`alias` and `model_resolved` being separate columns is what makes step 1 possible.**

**"Cost attribution is off."**

1. Segment the delta by provider and model — it's almost always one provider and one token type.
2. Check for cached-input pricing, batch discounts, or a new token category (reasoning, tool-use).
3. Verify the rate card's effective date against the invoice period.
4. Correct the estimator and **backfill `cost_reconciled`**, leaving `cost_usd` untouched — the delta is the
   audit trail.

**"A tenant is starving others."**

1. Check per-tenant **concurrency**, not RPS ([E16](03_lld.md#36-edge-cases--correctness)) — long streams
   hold connections while looking harmless on an RPS chart.
2. Lower their `concurrency_limit`; it takes effect within the config-propagation window.
3. If the pool is genuinely saturated, add capacity — but the ceiling is the fix, not the capacity.

---

## 4.3 Common mistakes

| # | Mistake | Why it's wrong | What to do instead |
|---|---|---|---|
| 1 | **Claiming 99.99% from multi-provider fallback without qualification** | Ignores the gateway's serial position and provider correlation. At 5% correlation the fallback set alone misses the target | State the conditional claim with the sensitivity ([§1.5](01_requirements.md#15-the-availability-arithmetic--the-central-claim)) |
| 2 | **Treating vendor diversity as infrastructure diversity** | Two vendors in one cloud region are one failure domain | At least one provider on a different cloud and network path |
| 3 | **Silent cross-provider fallback by default** | Substituted models produce different output with a 200 OK | Per-app policy, defaulting to the **safer, less available** option |
| 4 | **Failing over mid-stream** | Delivered tokens can't be unsent; the answer changes mid-sentence | Fail with `tokens_delivered`; let the app decide |
| 5 | **Synchronous logging** | Makes the log store a 99.995% dependency | Async, bounded queue, drop-on-full |
| 6 | **Unbounded log queue** | Log-store outage becomes a gateway OOM | Bounded with drop-on-full |
| 7 | **Fail-closed on Redis** | One Redis blip spends the month's availability budget | Fail open with local approximate limits, and **say what that gives up** |
| 8 | **Global (cross-tenant) cache** | Better hit rate, and a data leak | Tenant in the key, plus an assertion on read |
| 9 | **Hosted embedding call for semantic caching** | 20–40 ms exceeds the entire gateway budget | In-process quantized model, or drop the feature |
| 10 | **Cache lookup before the eligibility check** | Pays lookup cost on ~65% of traffic that can never hit | Check eligibility first — three comparisons |
| 11 | **Per-request config lookup** | 2 ms × 173M/day recomputing a weekly-changing table | Compile at push time, hold last-known-good |
| 12 | **Summing local token counts for attribution** | Misses cached-input pricing, discounts, reasoning tokens. Cannot hit 2% | Reconcile to invoices; store both figures |
| 13 | **Retry until success** | Amplifies provider degradation into an outage | One jittered retry, then breaker |
| 14 | **Per-provider breakers** | Discards healthy models when one tier degrades | Per provider × model |
| 15 | **RPS limits as tenant isolation** | Long streams starve the pool at low RPS | Concurrency ceilings |
| 16 | **Redacting PII at log write** | Raw PII already left for a third party | Redact at egress |
| 17 | **Justifying the platform on compute efficiency** | Gateway compute is ~0.6% of the bill | Justify on cost control, availability, and migration insulation |
| 18 | **An LLM-based router** | Costs more latency than the whole budget and more money than it saves | Declarative rules compiled to a table |
| 19 | **No passthrough escape hatch** | Sophisticated teams bypass the gateway, taking the biggest spend with them | Passthrough that keeps auth, budget, and logging |
| 20 | **Promising semantic equivalence across providers** | Impossible, and it causes real incidents | Non-goal, stated explicitly and early |

**Mistake 1 is the one that separates a rehearsed answer from a real one.** "99.99% via multi-provider
fallback" is the pitch, and it dies to a single follow-up about correlated failure. Presenting the
arithmetic *including* the correlation sensitivity is the whole reason to have done the arithmetic.

**Mistake 17 is the framing error that sinks gateway proposals.** Compute is $3k/month against $500k of
token spend. A proposal arguing efficiency is arguing about a rounding error; the case is cost *control*
(~$200k/month), availability, and not spending a quarter on the next deprecation.

---

## 4.4 Interview follow-ups

**"How can adding a hop increase availability?"**
> Only by buying back more than it costs, and the arithmetic has to be shown. The gateway is serial, so
> total availability is gateway × fallback-set — which means the gateway itself needs ~99.995%, about
> 2.2 minutes a month including deploys. That derived number is what forces stateless multi-region
> active-active, fail-open dependencies, and blue/green deploys. Then fallback across providers takes the
> provider term from 99.7% to nearly five nines — *if* failures are independent.

**"And if they're not independent?"**
> Then the claim fails, and it fails fast. At 5% correlation the fallback set alone lands at 99.984%; at 20%
> it's 99.94%. The concrete version of the problem is that Azure-hosted OpenAI and Bedrock-hosted Anthropic
> in the same region are two vendors on one failure domain — a regional networking incident opens both
> breakers. So the requirement isn't "multiple providers," it's **multiple infrastructures**, and the
> detection is specific: simultaneous breaker opens across providers pages, because that event *is* the
> assumption being falsified.

**"Your latency budget sums to exactly 30 ms. Isn't that fine?"**
> No — a p95 with zero margin is a p99 breach waiting for a GC pause, and the stated budget also assumes
> exact-match caching only. Semantic caching needs an embedding, and a hosted embedding call is 20–40 ms,
> more than the whole budget. Four changes get the common path to ~17 ms: one atomic Redis call instead of
> three round trips, in-process JWT verification, compiled routing tables, and — the big one — checking
> cache *eligibility* before doing the lookup, which removes cache cost from the ~65% of traffic that can
> never hit.

**"Would you fall back across providers by default?"**
> No, and this is the decision I'd defend hardest. Silent substitution means an app tuned for one model gets
> materially different output with a 200 OK. For ticket classification that's the right trade; for
> customer-facing legal text an error is far better. Only the app knows, so it's a per-app policy with four
> values — including `cross_provider_same_tier`, because most teams' real position is "another frontier
> model yes, a downgrade no," which a boolean can't express. **The default is the safer, less available
> one.**

**"What happens if you fail over mid-stream?"**
> You don't. Once a token has reached the client the request is no longer idempotent from the user's point
> of view, whatever the API says. Restarting on another provider produces output that changes voice, repeats
> itself, or contradicts what the user already read — worse than an error, because they might not notice. So
> we fail with a `tokens_delivered` count and let the app decide.

**"Where does the money actually go?"**
> Not compute. Gateway compute is ~$120/month of CPU, ~$3k all-in with multi-region headroom, against $500k
> of token spend. The real infrastructure cost is **logging** — 692 GB/day of bodies — which is why metadata
> is kept at 100% for 13 months and bodies are sampled at ~1% for 7–30 days. Metadata is 200 bytes and
> answers every recurring question; bodies are 20× larger and only wanted for recent debugging. **The real
> cost, though, is engineering time**, and the justification is $200k/month of cost control plus
> availability plus not spending a quarter on the next deprecation.

**"How do you hit 2% cost-attribution accuracy?"**
> Not by arithmetic. Cached-input tokens are priced differently, batch discounts appear at the invoice,
> reasoning tokens are billed inconsistently, and rate cards change mid-month. So I store our computed cost
> and the reconciled figure in separate columns, alert when the delta exceeds 2%, and treat the delta as the
> metric. **Attribution is a monthly closing process with an owner**, not a number the gateway asserts.

**"What can this platform see that the 30 apps couldn't?"**
> Provider drift. When a provider changes the model behind its own alias, every app sees different output
> with a 200 OK and no way to distinguish it from their own change. The gateway holds 100% of traffic
> against pinned versions, so cheap distributional probes — length, refusal rate, JSON-parse success —
> detect it. It's an argument for centralization that has nothing to do with cost, and it's the one I'd lead
> with to a skeptical staff engineer.

**"When would you *not* build this?"**
> Below roughly $50k/month of token spend. At that level 40% savings is $20k against ~$80k of platform cost
> — a losing trade — and the right answer is a shared client library that standardizes retries and cost
> logging without adding a hop or an availability dependency. **The gateway becomes correct when 40% of
> token spend exceeds a small team's fully loaded cost.**

**"What breaks first at 10×?"**
> Logging, at 6.9 TB/day of bodies — sampling stops being an optimization and becomes mandatory. But the
> more interesting change is that **routing changes purpose**: at 20k RPS a single provider's contracted
> throughput can't absorb the traffic, so spreading across providers goes from a 30% cost lever to the only
> way to serve at all. Which makes [F4](02_hld.md#25-failure-modes--blast-radius) worse — losing a provider
> is then a capacity shortfall, not a failover, because the others are already at their ceilings.

**"How does this relate to the inference platform?"**
> They're the buy and build sides of the same problem, and at ~100× they merge. [04](../04_llm_inference_platform/README.md)
> found self-hosting ~10× worse at moderate utilization — but that verdict was utilization-dependent. At
> 200k RPS the small tier runs GPUs near saturation, self-hosting becomes correct for that tier, and the
> gateway becomes the router between internal serving and external providers. **Same gateway, one more
> backend.**

---

## 4.5 Glossary

| Term | Meaning |
|---|---|
| **Alias** | A stable name (`prod-fast`) resolved at the gateway to a concrete provider model version. Makes deprecation a config change |
| **Circuit breaker** | Per provider × model state machine that stops sending traffic to a failing target and probes for recovery |
| **Correlated failure** | Provider incidents that co-occur due to shared infrastructure. The assumption the 99.99% claim depends on being small |
| **Data plane / control plane** | Request path vs. configuration path. Separate failure domains by design |
| **Fail open** | On dependency failure, serve with degraded enforcement rather than reject. Trades governance precision for availability |
| **Fallback chain** | Ordered list of (provider, model) candidates for an alias, gated by per-app policy |
| **Half-open** | Breaker state admitting a few probe requests; any failure returns it to open |
| **Idempotency key** | Client-supplied token making a retry safe. Paired with an `uncertain` state for timeouts |
| **Passthrough** | Provider-native request bypassing translation while keeping auth, budget, and logging |
| **Provider drift** | A provider changing model behaviour behind its own alias — no error signal, detectable only from aggregate traffic |
| **Reserve / settle** | Estimate cost at admission, correct it on response. What makes a hard budget cap hold under concurrency |
| **Semantic cache** | Embedding-similarity cache for near-duplicate requests. Viable only with an in-process embedder |
| **Shadow traffic** | Mirrored requests to a candidate model, never affecting the live response |
| **Sliding window** | Rate-limit algorithm counting requests in a moving interval. Chosen over token bucket for explainability |
| **TPM / RPM** | Tokens- and requests-per-minute limits in provider contracts. Become capacity constraints at scale |

---

## Where this sits in the set

| | |
|---|---|
| **Hardest constraint** | Availability *above* any single provider, from a component that is serially in the path |
| **Cost profile** | Compute is noise; **logging is the infrastructure cost**; engineering time is the real cost |
| **Buy-side counterpart of** | [04 — Inference platform](../04_llm_inference_platform/README.md) — they merge at ~100× |
| **Feeds** | [10 — Enterprise agent platform](../10_enterprise_agent_platform/README.md), which uses this as its model-access layer |
| **Shared pattern** | Tenant-in-cache-key, from [01 — RAG](../01_production_rag_system/README.md). Same leak, different system |

**Next:** [10 — Enterprise AI agent platform →](../10_enterprise_agent_platform/README.md) — the capstone, composing 01, 03, 07, and this one.

[← Back to README](README.md) · [← LLD](03_lld.md) · [All systems](../README.md)
