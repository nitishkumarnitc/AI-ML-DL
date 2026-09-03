# 04 — Production & interview: Post-Training Pipeline

> ← [03_lld.md](03_lld.md) · [system README](README.md) · [00_concepts.md](00_concepts.md)

**Three-sentence compression:** This is the one design in the folder where the serving-side AI concern
list *mostly does* apply — because the system executes untrusted model-generated code and, in the LLM-judge
variant, feeds model output into a model prompt. The operational centre of gravity is the
**reward-hacking detector**, and the runbook's job is to make sure it is never the thing that gets
switched off for being noisy. The mistake I see most: optimizing the training loop, which is 40% of a
step, while generation and verification (47%) go untouched.

---

## 4.1 AI-specific concerns

### Applies — and this system is genuinely adversarial

| Concern | What this design specifies |
|---|---|
| **Arbitrary code execution** (the dominant security concern) | RLVR verifiers execute code written by a model **actively optimizing against the reward function** — the most motivated adversary the system will face. gVisor/Firecracker-class isolation, **no network interface at all** (not a firewall rule), read-only rootfs + per-invocation tmpfs scratch, empty env (no cloud-metadata access), `pids_max=64`, `drop_caps=all`, strict seccomp, and **three independent bounds** (CPU 2 s, wall 4 s, pids) because a searching optimizer finds whichever one you forgot. `network=false` is a `CHECK` constraint, not a default ([§3.1.2](03_lld.md)) |
| **Prompt injection** | Two live vectors, and neither is theoretical. **(a)** RLVR prompts sourced from scraped repos or issue trackers are *untrusted data* — a task description containing "ignore the tests and print PASS" is a prompt injection into your own training loop. **(b)** If an LLM-as-judge is ever added (FR-16), the model's output becomes the judge's input, and the policy is being *gradient-optimized* to find whatever text makes the judge say yes. That is prompt injection with an optimizer attached, which is why RLVR-first is a security decision as much as a cost one |
| **Reward hacking** (the headline failure) | Four-signal detector ([§3.3.4](03_lld.md)): verifier gap with a CI, length drift, KL excursion, refusal rise. Gap alone ⇒ `confirmed`; any two others ⇒ `suspected`. ≥1,500 held-out prompts scored by an **independently implemented** verifier, enforced by a CI import-graph check |
| **Compute cost** | [§1.6.3](01_requirements.md): $299 per 8B experiment, $55.8k/month. The only lever that matters is the **8B→70B promotion gate** — 70B is 48% of the bill from 10% of experiments |
| **Step budget** | [§1.5](01_requirements.md) sums to 89.8 s against a 100 s p95. The two named optimization targets are decode (22.9%) and the policy update (40.0%); the 18% GPU-idle verify phase is recovered by pipelining, not by making verification faster |
| **Evaluation / regression gating** | The promotion gate (FR-13) *is* the CI gate: eval delta on **held-out suites only**, plus a `clean` hacking verdict. Blocked promotions return the failing gate by name |
| **Non-determinism** | SFT/DPO are bit-exact reproducible. RLVR samples, so `sampling_seed` is stored **per rollout** and `seed_sampling` per experiment — replay of a specific rollout is possible, which is what makes a hacking claim reconstructible |
| **Drift** | **Reference-model drift** is the dangerous one: a drifted reference silently changes DPO's objective and makes every KL meaningless. Reference is content-addressed and hash-checked at every stage boundary. Also **verifier drift** — a verifier code change alters the reward function, so `verifier_id` includes `code_sha` |
| **Data governance / PII** | PII scan before dedup; corpora store shard URIs and hashes, never content. Retained rollouts are model *outputs*, which can regurgitate training data — retention is 5% + flagged steps, in the training tenancy, never egressed |
| **Observability** | Per step: reward mean/std, `frac_zero_std_groups`, KL mean/p95, mean response length, both pass rates, refusal rate, verifier timeout rate, GPU-idle fraction, step seconds. **The dashboard must not show reward alone** — see §4.2.1 |
| **Cold start & capacity** | GPU warm pools for the generation engine (CUDA-graph rebuild is ~40 s, which is exactly why the checkpoint-round-trip weight sync was rejected). Sandbox pool autoscales on **rollout-queue depth** |

### Does not apply

| Serving-side concern | Why absent |
|---|---|
| **TTFT / streaming latency** | Generation here is throughput work feeding a training step; no user waits on a token. The analogue is *step time*, and it is budgeted in §1.5 |
| **Model routing / provider fallback** | Only one policy exists — it is the thing being trained. There is nothing to route to |
| **Semantic / prompt caching** | The structural analogue is the **verifier-result cache** keyed `(verifier_id, response_hash)`, which is genuinely the same idea and is correct *only because* verifiers are pure functions — which is itself a consequence of FR-6's no-network rule |
| **Hallucination / groundedness / citations** | No retrieval and no user-facing generation. The analogue is the verifier gap: is the score grounded in real correctness or in a shortcut? |
| **Multi-tenancy / per-tenant isolation** | Single-tenant research platform. The isolation that matters is the *sandbox*, not the tenant |

---

## 4.2 Operations and runbook

### 4.2.1 Dashboards, in priority order

| Dashboard | Panels | Alert on |
|---|---|---|
| **1. Hacking signals** | `train_pass_rate` **and** `heldout_pass_rate` on the same axis · gap with CI · mean response length · KL mean/p95 · refusal rate | Gap CI lower bound > 0.03 (windowed over 8 steps) · length drift > 25% · KL > 12 |
| **2. Signal health** | `frac_zero_std_groups` · `reward_std` · `frac_empty` · truncation rate | `frac_zero_std_groups` > 0.9 for 10 steps (either direction) |
| **3. Step budget** | Stacked per-stage seconds (sync/prefill/decode/verify/ref/update) · `gpu_idle_frac` · staleness histogram | Step p95 > 100 s · `gpu_idle_frac` > 5% · any staleness > `max_staleness` |
| **4. Verifier fleet** | Sandbox utilization · verifier p95 · **timeout rate** · error rate · **sandbox violations** | Any sandbox violation (page immediately) · timeout rate > 2% · queue depth rising |
| **5. Data integrity** | Corpora by `usable` · suites registered vs checked · dedup/decontam removal counts | Any training start against a `usable=false` corpus (should be impossible — investigate the trigger) |
| **6. Spend** | GPU-hours by experiment/owner · 8B vs 70B split · promotion rate | 70B share > 55% of monthly spend |

**Rule stated explicitly because it is the whole point:** *never* a dashboard whose headline is
`reward_mean` alone. A climbing reward with a flat held-out rate is the signature of the failure this
system exists to catch, and a reward-only panel renders it as success.

### 4.2.2 Protecting the detector from itself

The detector's real failure mode is being switched off for crying wolf. Three deliberate defences:

```
1. The gap signal fires only when its 95% CI EXCLUDES the threshold.
   With n=100 heldout, SE=0.071 -> the CI is so wide it either never fires or fires
   constantly. The CI requirement is what makes >=1500 heldout prompts a REQUIREMENT
   rather than a recommendation.

2. One non-gap signal alone is never enough. Length moves for legitimate reasons
   (a task family that genuinely needs longer answers). Two signals together do not
   have a common benign explanation.

3. Every fired signal retains 100% of that step's rollouts. An engineer who can READ
   the transcript is an engineer who trusts the detector. A verdict with no evidence
   attached gets argued with, then ignored.
```

**Quarterly detector audit:** for every `confirmed` verdict, did a human confirm the hack from the
retained rollouts? For every `clean` experiment that was promoted, did a regression appear later?
Track both rates. A detector with > 30% unconfirmed `confirmed` verdicts is miscalibrated and will be
disabled by its users; a detector that missed a hack that surfaced downstream needs a fifth signal.

### 4.2.3 On-call triage order

1. **Sandbox violation?** Page. Kill the pool, quarantine, security review. Nothing else matters until this is resolved.
2. **Is a run burning budget with no signal?** Check `frac_zero_std_groups`. Cold start and saturation both waste 100% of the remaining spend, and both are cheap to detect and cheap to fix.
3. **Step time blown out?** Check the stacked step budget. Order of likelihood: verifier p95 rose → decode slowed (response length runaway) → weight sync fell back to checkpoint round-trip.
4. **Detector firing?** Read the retained rollouts *before* changing thresholds. Raising a threshold to silence a signal is how a lab ships a reward hack.
5. **A corpus marked usable that shouldn't be?** Investigate the trigger, not the API. The invariant is enforced in the database for a reason.

### 4.2.4 Rollback

| Change | Rollback |
|---|---|
| Verifier code | `verifier_id` includes `code_sha`, so a change is a *new verifier*. In-flight experiments keep the old one. **A verifier change mid-experiment changes the reward function** and is rejected |
| Detector version | Reports are `detector_version`-stamped. Re-running produces a new report; old ones are not mutated. Promotion checks the report's detector version against current |
| Eval suite revision | New revision = new `(suite_id, revision)`; corpora re-evaluated for usability. Previously-dropped documents are **not** restored (a corpus's hash must be stable) |
| Base container image | Pinned by digest per stage. Never applied to a running experiment |
| A promoted checkpoint later found to be hacked | `promotable=false` + `promotion_block`, then walk the lineage graph (FR-15) and mark every descendant. This is the scenario lineage exists for |

---

## 4.3 Common mistakes

| Mistake | Why it's wrong | Do instead |
|---|---|---|
| **Optimizing the training loop first** | The policy update is 40% of a step. Generation + verify is 47%, and 18% of every step has *zero GPU work* | Profile the whole step. Pipeline verify against the next generation; then attack decode (A1: currently ~15% of the weight-bound roofline) |
| **Syncing weights via a checkpoint round-trip** | ~56 s against an 89 s step — a **63% tax** — mostly the inference engine's reload and CUDA-graph rebuild, not the I/O | In-memory broadcast with the engines co-located: 0.04 s over NVLink |
| **Choosing PPO without doing the memory arithmetic** | The critic's *optimizer state* (16 B/param) drops max concurrent rollouts from 2,967 to 2,013 — **below the 2,048 requirement**. PPO doesn't fit this node at this group size | Do the §1.6.2 table before choosing an algorithm. On one node, GRPO. On two, PPO becomes viable again |
| **Dividing by `std + eps` for zero-variance groups** | Manufactures enormous advantages from float noise. A genuinely baffling bug, because the training curve looks *more* active | Contribute exactly 0 advantage and count the group in `frac_zero_std_groups` |
| **Scoring a verifier crash as reward 0** | Teaches the model that crashing the verifier is as good as failing honestly — and crashing is much easier than solving | Exclude from the group with reward `NULL`. Count timeouts separately from failures |
| **100 held-out prompts** | Detects only a 14.1-point gap. Reward hacking shows up at 2–5 points, so the detector is decorative | ≥1,500 (2 SE = 3.7 pts), fire only when the gap's CI excludes the threshold, **and window the gap over 8 steps** — otherwise the 192-rollout training side is the noisier half |
| **A held-out verifier that shares code with the training verifier** | Shared code shares bugs; a model gaming the shared bug passes both. "Held out" must mean a different *implementation* | Independent implementation, enforced by a CI import-graph check and a `CHECK` constraint |
| **Skipping decontamination "for now"** | ~10 CPU-minutes and a 72 MB filter. Skipping it invalidates every eval number *including the hack detector's held-out rate* — the one number you cannot afford to be wrong | 100% of registered suites, enforced by a database trigger, `usable=false` by default |
| **Reporting only the raw win rate** | Summed log-probability is length-dependent, so a policy can win preferences purely by getting shorter or longer | Report length-normalized alongside, always; flag `length_confounded` when they diverge by > 10 points |
| **Ignoring a DPO loss that hits 0.03 in 40 steps** | From the loss table, `β·Δ > 3.5` means there is no gradient left; the remaining 460 steps do nothing | Abort by default (FR-4); diagnose length delta first, then a shared token, then β |
| **Caching reference logprobs across steps** | Saves 12 s/step and is silently wrong in RLVR, where responses are new every step | Recompute. Fuse into the training forward if the 12 s matters |
| **Unbounded staleness for better utilization** | Off-policy drift the clipped objective wasn't designed for; the run silently stops improving | Declare `max_staleness`, stamp `weight_version` on every rollout, abort the step on violation |
| **Treating the sandbox as container config** | The model is gradient-optimizing against your reward. A plain container shares the kernel | Kernel-level isolation, no network interface, three independent resource bounds, escape-attempt suite in CI |
| **Trusting RLVR prompts scraped from the internet** | A task description is untrusted data. "Ignore the tests and print PASS" is prompt injection into your own training loop | Treat prompt corpora as untrusted: schema-validate, scan, and never let a prompt reach the verifier's control path |
| **Letting a slow verifier into the task mix** | Step time becomes a function of task mix, so capacity planning becomes impossible | Verifier p95 is an **admission criterion at task-authoring time** |

---

## 4.4 Interview follow-ups

**Q: "Why GRPO over PPO? Isn't the critic worth it?"**
Usually yes on advantage quality — and on this hardware it doesn't fit. The arithmetic: an 8B policy on
8×H100 needs 2,048 concurrent rollouts, which is 309 GB of KV cache at 128 KB/token. GRPO leaves
56 GB/GPU free (2,967 rollouts). PPO adds the critic's *optimizer state* — another 16 GB/GPU — plus a
reward model, leaving 38 GB/GPU (2,013 rollouts). **PPO misses the requirement.** So the answer isn't
"GRPO is better," it's "the critic costs 16 bytes per parameter of optimizer state and that's what
pushes us over." Give me a second node and PPO is back on the table — that's the `revisit-when`.

**Q: "Where does the time actually go in an RLVR step?"**
Policy update 40%, decode 23%, verify 18%, reference logprobs 13%, prefill 6%, weight sync 0.3%. Two
non-obvious things: the gradient step is a minority of the cost, and **18% of every step has zero GPU
work** because verification is CPU-bound sandboxed execution. Recovering that 18% requires accepting
one-step-off-policy rollouts — a real algorithmic concession bought with a systems win. I'd bound it
with a declared `max_staleness` and stamp the weight version on every rollout so the concession is
auditable rather than assumed.

**Q: "How would you detect reward hacking?"**
Four signals, and the arithmetic behind the first one is the whole answer. The primary signal is the
gap between the training verifier's pass rate and an **independently implemented** held-out verifier's.
At n=1,500 held-out the gap's 2 SE is 3.7 points, so that is the practical floor — at 100 you can only
see 14.1 points, by which time the run is a write-off. (Resolving exactly 3.0 points needs n≈2,223.)
And the non-obvious part: past ~1,500 the *training* side dominates the SE — a single step's training
pass rate rests on ~192 rollouts, SE 0.036 versus 0.013 for the held-out side — so the next improvement
is computing the gap over a **rolling 8-step window**, not buying more held-out prompts. Then length drift, KL excursion, and refusal rate. The
gap alone is `confirmed` because it's direct evidence; any two of the others are `suspected`. And the
gap fires only when its CI *excludes* the threshold, because a detector that cries wolf gets turned
off.

**Q: "Why does the held-out verifier need to be a different implementation, not just different data?"**
Because the hack I actually worry about is verifier gaming, not prompt overfitting. If both verifiers
import the same assertion helper, a model that finds the loose assertion passes both. Held-out data
catches "memorized these prompts"; held-out *implementation* catches "found the bug in your checker." I
enforce it with a CI import-graph check and a `CHECK` constraint, because it is the kind of invariant
that gets broken by a well-meaning refactor extracting shared code.

**Q: "What's the single cheapest requirement here and why is it P0?"**
Decontamination. A 72 MB Bloom filter over 13-grams of every eval suite, ~10 CPU-minutes for a 600M-token
corpus. It is P0 because everything downstream depends on it — including the held-out pass rate the
hacking detector reads. A contaminated corpus doesn't just inflate your benchmark, it **disables your
safety net**. I enforce it with a database trigger rather than an API check so it can't be bypassed by a
backfill.

**Q: "Your decontamination drops ~40k documents falsely at FPR 0.1%. Isn't that bad?"**
It's 0.008% of a 500k-doc corpus, and the asymmetry is the argument: a false drop costs a rounding error
of training data; a false *keep* invalidates every eval number and the hack detector with it. I'd pick
FPR 0.1% over 1% for the same reason — 72 MB instead of 48 MB is free, and it cuts false drops 10×.

**Q: "What breaks first at 10×?"**
The **CPU sandbox fleet**, not the GPUs. Ten concurrent experiments need ~2,560 sandboxes; the fleet
cost goes from $2.8k to $28k/month and starts rivalling a GPU line. Fix: autoscale on rollout-queue
depth, and cache verifier results by `(verifier_id, response_hash)` — which is only *correct* because
verifiers have no network and no writable shared state, so FR-6 is what makes the optimization sound. A
design that scales GPUs and leaves the verifier fleet fixed turns 18% GPU idle into 60%.

**Q: "At 10× policy size, does anything invert?"**
Yes, and it's the design's central decision. At 80B, `16N` is 1,280 GB of optimizer state — 16 GPUs
before any KV cache — so weights can no longer be time-shared between the two engines. Generation has to
disaggregate onto its own pool, and the in-memory broadcast becomes a cross-node 160 GB transfer. The
alternative I rejected at 8B becomes the right answer at 80B. That's what the `revisit-when` column is
for.

**Q: "One failure mode you'd volunteer?"**
The verifier sandbox, because the threat model is unusual: the code being executed was written by a
model that is being *gradient-optimized* to maximize the score that code produces. That's not an
accidental adversary, it's a search process with a loss function pointed at my sandbox. So: kernel-level
isolation, no network interface at all rather than a firewall rule, empty environment so there's no
cloud-metadata path, and three independent resource bounds because a search will find whichever one I
forgot. And it fails closed — a violation is a security event, not a rollout with reward 0.

---

## 4.5 Glossary

| Term | Meaning | Where it bites |
|---|---|---|
| **Advantage** | How much better a rollout was than its baseline | 0 for zero-variance groups; never `std + eps` |
| **β (beta)** | DPO's strength knob | `β·Δ > 2.2` ⇒ loss < 0.10 ⇒ collapse |
| **Cold start (zero-gradient)** | Every rollout scores 0, so nothing is learned | `frac_zero_std_groups` > 0.9 with `reward_mean` ≈ 0 |
| **Continuous batching** | Inference scheduling that admits new sequences as others finish | The generation engine's throughput mechanism |
| **Critic / value model** | Predicts expected reward; PPO needs it | Its optimizer state is what makes PPO not fit |
| **Decontamination** | Removing eval-set overlap from training data | 13-gram Bloom, 72 MB, 100% coverage, DB trigger |
| **DPO** | Direct Preference Optimization | Preference learning with no reward model |
| **DPO collapse** | Loss saturates early on a trivial separator | Abort by default; diagnose length first |
| **GRPO** | Group Relative Policy Optimization | Group mean as baseline; no critic ⇒ fits the node |
| **Group size `k`** | Rollouts per prompt | Baseline noise falls as `1/√k`; KV cost rises linearly |
| **Held-out verifier** | Independently *implemented* scorer, never trained on | ≥1,500 prompts; import-graph-disjoint |
| **Implicit reward** | `β·log[π_θ/π_ref]` | DPO's induced reward; `reward_accuracy` → 1.00 signals collapse |
| **KL divergence** | Distance from the reference policy | The leash; a rising KL with a flat held-out score is a hack |
| **KV cache** | Cached keys/values for decode | 128 KB/token; caps concurrent rollouts |
| **Length normalization** | Per-token rather than total score | Stops length winning on its own |
| **MinHash / LSH** | Near-duplicate detection via hashed shingles | 128 perms, b=16/r=8, J ≥ 0.8 |
| **Off-policy / staleness** | Rollouts produced by older weights | Bounded by `max_staleness`; stamped per rollout |
| **PPO** | Proximal Policy Optimization | Needs a critic; see the memory table |
| **Reference model** | Frozen anchor for KL and log-ratios | Content-addressed; hash-checked at stage boundaries |
| **Reward hacking** | Scoring well without doing the intended thing | The headline failure; four-signal detector |
| **RLVR** | RL with Verifiable Rewards | Reward from a program, not a network |
| **Rollout** | One sampled response | Stamped with weight version + sampling seed |
| **Sandbox violation** | Verifier code tried to escape its box | Security event, fail closed, quarantine |
| **SFT** | Supervised fine-tuning | Loss masked to response tokens only |
| **Verifier** | Program that scores a rollout | Pure function only because it has no network |
| **Verifier gap** | `train_pass_rate − heldout_pass_rate` | The primary hacking signal; needs a CI |
| **Win rate (raw / len-norm)** | Fraction of comparisons preferred | Report both; divergence ⇒ `length_confounded` |

---

← [03_lld.md](03_lld.md) · [system README](README.md) ·
→ [03 Distributed training platform](../03_distributed_training_platform/README.md)
