# 04 — Production & interview: Research Experiment Platform

> ← [03_lld.md](03_lld.md) · [system README](README.md) · [00_concepts.md](00_concepts.md)

**Three-sentence compression:** The AI-specific concern list for a *training-side* system is a
different list from the serving-side one, and saying which rows don't apply is part of the answer. The
operational centre of gravity is the **quarterly FDR calibration audit** — the only mechanism that
tells you whether the platform is producing rigor or laundering noise. The mistake I see most: treating
this as an experiment *tracker*, which is a UI problem, rather than an experiment *gate*, which is a
correctness problem.

---

## 4.1 AI-specific concerns

The [skill's](../../../.claude/skills/ai-system-design/SKILL.md) concern table is written for
inference-serving systems. **Roughly half of it does not apply here, and pretending otherwise would be
padding.** Below: the rows that do apply, translated to the training side, then an explicit list of the
rows that don't and why.

### Applies — translated to the training side

| Concern | What this design specifies |
|---|---|
| **Compute cost** (the training analogue of token cost) | Arithmetic in [§1.6](01_requirements.md): $10.11/run, $36.8k/quarter under the two-tier policy vs $60.1k naive. Levers, in order: **dedup** (FR-8, zero-cost hits), **tiered δ** (FR-10, the structural fix), **pairing** (4.8× at ρ=0.8), **screening at small scale**. Cost attribution per ablation/owner within 1 h (FR-13) |
| **Turnaround budget** | [§1.5](01_requirements.md) sums to 83 min against a 2.5 h SLO. The volatile term is *queue wait*, owned by design 03 — mitigated with a reserved partition, not by assuming queueing is free |
| **Eval / regression gating** | This system **is** the gate. Its CI-equivalent is: no `supported` verdict without achieved power ≥ 0.80 and BH correction. The quarterly calibration audit (§4.2) is the regression test *on the gate itself* |
| **"Hallucination"** — translated: **false discovery** | The exact analogue. A `supported` verdict for an effect that isn't real is this system's hallucination. Controlled by BH (FDR ≤ 0.05), the `inconclusive` verdict, alpha-spending on interim looks, and confirmation-tier re-testing with fresh seeds |
| **Non-determinism** | `deterministic` flag recorded per run; seed tuple stored as **three separate columns** so pairing can hold them equal; container **digest** pinned because kernel selection changes numerics. Bit-exact `replay` (FR-12) is a P1 requirement, not a nice-to-have |
| **Drift** | Two kinds, both real: (a) **σ drift** — seed variance changes as the model family evolves, so `variance_estimates` is time-windowed and flagged `stale` past 90 days; (b) **environment drift** — a base-image rebuild changes numerics, detectable because `image_digest` is a first-class provenance column |
| **Observability** | Every verdict stores its `engine_version`, exact `run_ids`, observed σ, achieved power, and correction method. Per-run: WAL depth, ingest lag, NaN detector, heartbeat. The one dashboard that matters is **realized FDR**, not GPU utilization |
| **Prompt injection** — translated: **untrusted config/code execution** | A submitted config is *data*: it is schema-validated, and the resolver does **not** support arbitrary code evaluation (no `eval`, no `!!python/object` YAML tags). Runs execute researcher-authored code, so isolation is per-tenant namespace + no credentials in the training container beyond a scoped artifact-store token. This is a real concern here, just not the LLM-prompt version of it |
| **Cold start / capacity** | Reserved ablation partition (~104 GPUs) + preemptible overflow. Autoscale on **queue depth of authorized specs**, never on CPU — same reasoning as [`27/04`](../../27_ai-platform-system-design/04_llm_inference_platform/README.md), for the same reason |
| **PII / data governance** | Training corpora may contain PII; the platform stores **manifest hashes, never content**. Decontamination status is a manifest property (§3.1.1) and gates submission with a `422` |

### Does not apply — and why

| Serving-side concern | Why it's absent here |
|---|---|
| **TTFT / streaming latency** | There is no stream and no user waiting on tokens. The latency analogue is *turnaround*, which is measured in minutes and bounded by GPU queueing, not by decode speed |
| **Prompt caching / semantic caching** | No prompts. The structural analogue is **run dedup** (FR-8), which is genuinely the same idea — cache on exact input identity — and is covered above |
| **Model routing / provider fallback** | No inference providers in the path. The analogue would be GPU-type fallback (H100 → A100), and it is deliberately **rejected**: mixing GPU SKUs within an ablation changes numerics and breaks pairing. Better to queue than to run an arm on different silicon |
| **Guardrails (toxicity, output schema)** | The system's outputs are numbers and verdicts, not generated text |
| **Groundedness / citation enforcement** | No generation. The nearest analogue — "every claim traces to evidence" — is exactly what the five `NOT NULL` provenance columns implement |
| **Prompt/version management** | Replaced by **config content-hashing + code SHA + image digest**, which is a strictly stronger form of the same discipline |

> **Saying "this row doesn't apply, and here is the training-side analogue" is worth more in a design
> review than filling it in.** A candidate who discusses prompt injection in a design with no prompts
> has pattern-matched a checklist instead of reasoning about the system.

---

## 4.2 Operations and runbook

### 4.2.1 Dashboards, in priority order

| Dashboard | Panels | Alert on |
|---|---|---|
| **1. Rigor (the one that matters)** | Realized FDR (quarterly, trailing); % of verdicts `inconclusive`; % of ablations with a power override; σ/ρ estimate age and sample count per cell | Realized FDR > 0.10; override rate > 20% of ablations |
| **2. Turnaround** | p50/p95 hypothesis→verdict, split by stage (queue vs execution vs verdict); queue depth in the ablation partition | p95 > 2.5 h for 2 consecutive hours |
| **3. Telemetry health** | Agent WAL depth p99; ingest lag p95; ingest error rate by code; runs with stale heartbeat | WAL depth p99 > 10k points; ingest lag p95 > 30 s |
| **4. Spend** | GPU-hours by ablation/owner/day; dedup hit rate; % spend in screen vs confirm tier; unattributed cluster hours | Ablation > 120% of declared budget; **any** unattributed hours (means bypass) |
| **5. Data integrity** | Runs by `code_dirty`; manifests by `decontam_passed`; `metric_value_conflict` count | Any `metric_value_conflict`; dirty-run share > 10% |

**Deliberately not dashboard #1: GPU utilization.** A fully utilized cluster running underpowered
ablations is the failure this platform exists to prevent. Utilization is dashboard #6.

### 4.2.2 The quarterly FDR calibration audit

This is the platform's own regression test, and it is the runbook item most designs omit.

```
Quarterly, for every `supported` verdict issued 1-2 quarters ago:
  1. Find whether a confirmation-tier ablation, or the flagship run, subsequently tested it.
  2. Classify: confirmed / contradicted / never-followed-up.
  3. Realized FDR ≈ contradicted / (confirmed + contradicted).
  4. Report by engine_version, by tier, and by whether a power override was used.

Interpretation:
  realized FDR <= 0.05   -> the gate is calibrated
  0.05 < FDR <= 0.10     -> investigate: usually interim-look abuse or sigma staleness
  FDR > 0.10             -> the gate is NOT working. Most likely causes, in order:
                              (a) sigma underestimated (census stale) -> re-run the census
                              (b) overrides being used routinely      -> tighten the social cost
                              (c) promotion reusing screening seeds   -> §3.6 edge case 3
  never-followed-up > 60% -> the lab is not acting on verdicts; the platform is decorative
```

### 4.2.3 On-call triage order

1. **Are runs dying?** Check scheduler + node health first. Runs dying is the only thing that costs money by the minute.
2. **Is ingest backing up?** Check WAL depth. Rising WAL is safe (by design) but tells you the control plane is unhealthy.
3. **Is the control plane down?** Confirm the degraded mode is actually degrading correctly — runs continuing, metrics buffering. If runs *are* dying because of a control-plane outage, that is a **P0 design regression**, not an incident to ride out.
4. **Are verdicts wrong?** Slowest and most damaging. Check `engine_version` changes and σ estimate age before suspecting the statistics.

### 4.2.4 Rollback

| Change | Rollback |
|---|---|
| Verdict-engine version | Verdicts are immutable and version-stamped. Roll back the deployment; **do not** mutate past verdicts. Recompute creates new verdicts linked as superseding |
| Power-calculator change | Same, plus: re-run the calibration audit for affected ablations before trusting the new numbers |
| Schema migration | Provenance columns are `NOT NULL`; any migration that would make one nullable is rejected in review, because it silently permits unjoinable results |
| Base container image | Old digest stays valid forever; in-flight ablations pin their digest and are unaffected. **A base-image bump must never be applied to a running ablation** |

---

## 4.3 Common mistakes

| Mistake | Why it's wrong | Do instead |
|---|---|---|
| **Building an experiment tracker** | A tracker records what happened. It cannot stop an underpowered ablation, cannot enforce pairing, and cannot refuse to call a low-power null result "not supported." The valuable part is the **gate**, and no tracker has one | Design the authorization path first (HLD §2.1 path ①). The dashboard is the last 10% |
| **Defaulting σ instead of measuring it** | `n` scales as σ². A defaulted σ makes every power number fiction, and the fiction is unfalsifiable | Variance census: 8 identical runs per cell, ~$81. FR-3 makes measurement a P0 |
| **Reporting `not_supported` at low power** | Converts "we couldn't see it" into "it doesn't work." Kills real ideas, invisibly, forever | Three-outcome verdict; `inconclusive` whenever achieved power < 0.80 |
| **Computing power from *planned* n** | Runs die. Planned power is what you hoped for; achieved power is what you got | Compute from observed σ and the runs that actually completed (§3.3.3 step 4) |
| **Per-arm p-values in a sweep** | 20 arms at α=0.05 yields a "winner" 64% of the time under the null | BH across arms, plus a fresh-seed confirmation run for the winner |
| **Letting researchers peek and stop early** | Ten naive looks inflates α from 0.05 to ~0.20 | Fixed horizon at pre-registration; O'Brien–Fleming boundary for interim looks; `looks_used` monotonic and persisted |
| **Reusing screening runs in the confirmation** | The confirmation is then conditioned on the selection event; its p-value is meaningless | Fresh seed range, enforced at the API (§3.6 edge case 3) |
| **Hashing the config *file*** | Two files with different defaults can train identically, and identical files can resolve differently | Hash the fully-**resolved** tree |
| **Pinning the container by tag** | Tags move; a rebuilt tag changes cuBLAS kernels, which changes numerics by a margin comparable to the effects being measured | Pin the **digest** |
| **Making the tracker a hard dependency of the training loop** | A control-plane deploy kills a 30-day run — once. Then the lab disables telemetry permanently | Agent WAL + idempotent ingest; degraded mode is "results stale," never "runs die" |
| **Indexing metrics by wall-clock time** | Workers skew; comparing two runs by timestamp compares scheduling, not training | Index by optimizer **step**; timestamps are metadata |
| **Kafka + Spark + a data lake for 6,000 points/s** | Over-built by ~2 orders of magnitude, and it *loses the transactional join* between metric and provenance — the one thing that makes a number defensible | One Postgres/Timescale. Say plainly that the volume is small and the join is the product |
| **Adding GPU-SKU fallback to reduce queue time** | Mixing H100 and A100 within an ablation changes numerics and destroys pairing | Queue. Better to wait than to compare arms across silicon |
| **Treating the ladder as a notebook** | The extrapolation's *confidence interval* is where the flagship decision lives, and a notebook loses it | First-class `ladder` entity with a persisted fit + bootstrap CI + an OOM-beyond-rung warning |

---

## 4.4 Interview follow-ups

**Q: "This sounds like Weights & Biases. Why build it?"**
W&B is an excellent tracker and this design would happily use it for the metric tier. But the product
here is the **gate and the verdict**: refusing an underpowered ablation, constructing paired arms by
construction, applying BH across arms, returning `inconclusive` rather than `not_supported`, and
auditing realized FDR quarterly. None of that is a tracker feature. I would buy the UI and build the
gate — and I would put the gate *in front of the scheduler*, which is a place a SaaS tool cannot sit.

**Q: "Researchers will hate the power gate. What happens?"**
They will bypass it, and that is the top risk in [§1.7](01_requirements.md) rather than an
afterthought. Three mitigations, in order of importance: (1) **pre-registration must cost under two
minutes** — σ and ρ are auto-filled, so the researcher supplies δ and the ablated keys and nothing
else; (2) the override is **self-serve**, not a permission request, but the reason is recorded and
shown on every result — social cost, not a gate; (3) the 409 leads with `detectable_delta`, so the
message is "n=3 is blind below 0.019 nats and you're looking for 0.01" rather than "denied." The gate
that gets used beats the gate that is correct.

**Q: "How do you know σ = 0.02?"**
I don't — it's assumption A1 and it's the single most load-bearing number in the design. It is also
cheap to measure: 8 identical runs is 27 GPU-hours, about $81. That is why FR-3 makes measuring it a
P0 requirement and why the API returns `409 no_variance_estimate` rather than falling back to a
default. **A power calculation on a defaulted σ is worse than no power calculation**, because it looks
quantitative.

**Q: "Why paired t-test and not Bayesian?"**
Mostly organizational. A Bayesian posterior gives a more natural answer ("87% probability B is
better") and handles the sequential-peeking problem more gracefully. I rejected it as the *default*
because it requires the lab to specify and defend priors, and a mis-specified prior is a silent failure
in a system whose whole purpose is to eliminate silent failures. I would offer it alongside the
frequentist verdict once σ/ρ history is rich enough to justify empirical priors — that's the
`revisit-when` in [§2.2](02_hld.md).

**Q: "What if the ablation doesn't transfer to the flagship scale?"**
That's the honest limitation and I would not claim otherwise. Two things help: the scaling ladder
(FR-9) tells you whether the effect *survives* two orders of magnitude, which is strictly more
information than one small ablation; and every promoted result records whether it held at the next
rung, which over a year gives the lab its own empirical transfer prior. Nobody can answer it up front,
and the platform's job is to accumulate the answer rather than assert it.

**Q: "Your verdict SLO is 5 seconds. Why does that matter?"**
Because a verdict that takes 30 seconds gets cached, and a cached verdict gets read after new runs have
landed — so the number on screen and the number in the database disagree. The 5 s budget is what lets
the verdict be computed **fresh on every read**, which is why `runs.final_metric` is denormalized
(§3.1.3): the verdict path reads 256 doubles, never a metric series.

**Q: "What breaks at 10× and what would you change?"**
Metric-ingest write amplification at ~60k points/s — not volume; 180 GB/quarter is still small. I'd
batch at 30 s in the agent and add a write-through aggregation tier so the verdict path stops touching
raw series. What I would **not** do is add Kafka: it buys ingest headroom and costs the transactional
join, which is the product. The second thing to break is the reserved partition, and the right answer
there is to **tier the SLO** (screening stays at 1 h, confirmation moves to 6 h) rather than buy GPUs
to defend a single number.

**Q: "One failure mode you'd volunteer?"**
Control-plane outage. Most experiment platforms make the tracker a hard dependency of the training
loop, so a tracker deploy kills a 30-day run. Here the run agent writes to a local WAL first and the
ingest API is idempotent on `(run_id, step, metric_key)`, so a Postgres failover costs a stale
dashboard. The degraded mode is explicitly *"runs continue, results stale, no new submissions"* — and
I'd add that if runs ever *do* die from a control-plane outage, I'd treat it as a P0 design regression
rather than an incident, because a lab only needs to be burned once before it turns telemetry off.

**Q: "Where does this system end and the training platform begin?"**
Hard boundary: this platform emits **signed job specs** and consumes **metrics + terminal status**. It
never places a process on a GPU. [Design 03](../03_distributed_training_platform/README.md) owns
placement, parallelism, checkpointing and fault tolerance. The two meet at the signature check — which
is also the enforcement boundary, so the split is load-bearing rather than organizational tidiness.

---

## 4.5 Glossary

| Term | Meaning | Where it bites in this design |
|---|---|---|
| **Ablation** | Change one component, measure the effect | The atomic unit of work; the pre-registration is per-ablation |
| **Arm** | One variant within an ablation | BH corrects across an ablation's arms |
| **Achieved power** | Power computed from *observed* σ and *completed* n | Gates the verdict before significance does (§3.3.3) |
| **Alpha (α)** | P(false positive); conventionally 0.05 | Spent permanently by interim looks |
| **Alpha spending** | Allocating α across planned interim looks | O'Brien–Fleming boundary makes early stopping legal |
| **BH / Benjamini–Hochberg** | FDR-controlling multiple-comparison correction | The default correction; less power-destroying than Bonferroni |
| **Bit-exact replay** | Reproducing a run's numerics from its provenance tuple | FR-12; requires image digest + deterministic kernels |
| **Chinchilla-optimal** | `D ≈ 20N` tokens for a compute budget | Sizes every ladder rung |
| **Config hash** | sha256 of the canonical **resolved** config | The join key; enables dedup and pair verification |
| **Content-addressed** | Identified by hash of contents, not by name/path | Configs, checkpoints, data manifests |
| **Decontamination** | Removing eval-set overlap from training data | A manifest property; `422` at submission if absent |
| **Delta (δ)** | The effect size you want to detect | Tiered: 0.02 for screening, 0.01 for confirmation |
| **Detectable delta** | Smallest effect n runs can see: `σ√(15.70/n)` | The number the 409 leads with |
| **FDR** | False discovery rate — fraction of "significant" results that are wrong | The platform's one correctness NFR (≤ 0.05) |
| **Image digest** | `sha256:...` immutable container identity | Pinned instead of a tag, because kernels change numerics |
| **Inconclusive** | Third verdict outcome: power too low to conclude | Prevents low-power nulls being read as refutations |
| **MFU** | Model FLOPs Utilization | Used only for sizing here; it's design 03's currency |
| **Nat** | Natural-log unit of loss; `perplexity = exp(loss)` | The unit of δ and σ |
| **Paired design** | Arms share seed tuple, data order, eval batches | 4.8× fewer runs at ρ=0.8 |
| **Power** | P(detecting a real effect); conventionally 0.80 | The gate's threshold |
| **Pre-registration** | Declaring hypothesis/arms/horizon/metric before running | Immutable once the first run starts |
| **Provenance tuple** | (config, code, image, data, seeds) | Five `NOT NULL` columns; dedup identity |
| **Rho (ρ)** | Paired-arm correlation | Determines pairing's benefit; pairing refused below 0.5 |
| **Scaling law** | `L(N,D) = E + A/N^α + B/D^β` | Fitted on the ladder; extrapolated with a bootstrap CI |
| **Screening / confirmation tier** | Cheap δ=0.02 gate, then expensive δ=0.01 test | The structural cost fix (§1.6.2) |
| **Sigma (σ)** | Std-dev of the metric across seeds at fixed config | The most load-bearing assumption; measured, not defaulted |
| **Variance census** | 8 identical runs to measure σ and ρ | ~$81/cell; the highest-leverage spend in the design |
| **WAL** | Write-ahead log (here: the run agent's local buffer) | What makes a control-plane outage survivable |

---

← [03_lld.md](03_lld.md) · [system README](README.md) ·
→ [02 Post-training pipeline](../02_post_training_pipeline/README.md)
