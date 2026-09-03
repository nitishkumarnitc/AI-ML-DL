# 00 — Concepts primer: what you need to know before reading this design

> **Read this first if you have not run a post-training loop.** Everything here is a prerequisite,
> taught from scratch. If you already know what β does in DPO and why GRPO drops the critic, skip to
> [`01_requirements.md`](01_requirements.md).
>
> ← [system README](README.md) · → [01_requirements.md](01_requirements.md)

---

## The three-sentence version

1. **Pre-training** teaches a model what text looks like; **post-training** teaches it what *good*
   output looks like — and it is three different techniques (SFT, preference optimization, RL with
   verifiable rewards) applied in sequence, each with a different failure mode.
2. The systems shape is counter-intuitive: the expensive part is not the gradient step, it is
   **generating the model's own outputs to learn from** — which needs a completely different memory
   layout from training.
3. The dominant failure is **reward hacking**: the model finds a way to score well that isn't what you
   meant, and it looks exactly like progress on your dashboard.

---

## 1. The three stages, and what each one can and cannot do

| Stage | What it needs | What it teaches | Cannot do |
|---|---|---|---|
| **SFT** (supervised fine-tuning) | `(prompt, good_response)` pairs | Format, style, instruction-following. "This is what an answer looks like" | Cannot teach *preference between two plausible answers* — it only ever sees the good one |
| **Preference optimization** (DPO, and relatives) | `(prompt, chosen, rejected)` triples | Relative quality. "This answer is better than that one" | Cannot explore. It only learns from responses **you** supplied, not from its own |
| **RLVR** (RL with verifiable rewards) | `(prompt, verifier)` — a *program* that scores an output | Correctness on checkable tasks: code that passes tests, math with a right answer | Cannot help where correctness isn't mechanically checkable |

**Why the order matters.** DPO on a base model that cannot yet produce a well-formatted answer wastes
its signal on formatting. RLVR on a model that cannot produce parseable code gets reward 0 on
everything and learns nothing — a **zero-gradient cold start**, and it is the most common way a first
RLVR run fails.

---

## 2. SFT: the part that looks easy and isn't

SFT is ordinary next-token cross-entropy loss, computed **only on the response tokens** (the prompt is
context, not a target):

```python
loss = cross_entropy(logits[prompt_len:], response_tokens)   # mask the prompt out
```

Getting the masking wrong trains the model to *generate prompts*, which is a real bug with a
subtle symptom: outputs that drift into asking questions instead of answering them.

**The hard part of SFT is the data, and it has exactly two failure modes:**

| Failure | What it does | Fix |
|---|---|---|
| **Duplication** | Near-duplicate examples get effectively upweighted; the model memorizes a phrasing | MinHash/LSH near-dedup at Jaccard ≈ 0.8 |
| **Contamination** | Eval-set text is in the training data ⇒ every downstream benchmark number is a lie | n-gram overlap check against **all** eval suites before training |

**Contamination is the one that matters most and costs the least to prevent.** With a Bloom filter over
13-grams of every eval suite, checking a 600M-token corpus is ~10 CPU-minutes. Skipping it invalidates
every number the rest of the pipeline produces — including the reward-hacking detector, which is the
one thing you cannot afford to have compromised.

### Why 13-grams?

Short n-grams (3–5) collide constantly in natural language and flag everything; long ones (30+) miss
paraphrased or reformatted contamination. 13 tokens is long enough to be effectively unique to a
document and short enough to survive light reformatting. It's a convention, not a theorem — but pick a
number and state it, because "we checked for overlap" without an n is not a check.

---

## 3. DPO: what β actually controls

**The idea.** RLHF classically trains a *reward model* on preferences, then optimizes the policy
against it with RL. DPO's insight is that for the specific KL-regularized objective RLHF uses, you can
skip the reward model — the optimal policy has a closed form, and you can optimize preferences
directly.

**The loss.** For a preference triple `(x, y_w, y_l)` (prompt, winner, loser):

```
Δ = [log π_θ(y_w|x) − log π_ref(y_w|x)] − [log π_θ(y_l|x) − log π_ref(y_l|x)]

L_DPO = −log σ(β · Δ)
```

Read it in pieces:
- `log π_θ(y|x)` — the summed log-probability the policy assigns to that response.
- **Subtracting `log π_ref`** measures how much the policy has moved *relative to the reference*, not its absolute confidence. This is what keeps DPO anchored.
- `Δ` is therefore "how much more has the policy moved toward the winner than toward the loser."
- `−log σ(β·Δ)` is a logistic loss: push `Δ` positive.

**What β does.** β scales how hard you push before the loss saturates.

| `β·Δ` | Loss | Meaning |
|---|---|---|
| 0 | 0.693 | Policy has no preference. This is where every run starts |
| 1 | 0.313 | Learning |
| 2 | 0.127 | Nearly saturated |
| **3** | **0.049** | **Saturated — no gradient left** |
| 8 | 0.0003 | Numerically dead |

**Low β** (0.01–0.1) = weak pull, the policy stays near the reference, safe but slow.
**High β** (0.5+) = strong pull, fast movement and a real risk of degeneration.

### The failure you will actually see: DPO loss collapse

If the loss falls below ~0.05 within the first 10–20% of steps, the model has found a **trivial
separator** — usually length, formatting, or a single token that appears in every `chosen` and no
`rejected`. From the table, loss < 0.05 means `β·Δ > 2.94`; there is no gradient left, and the
remaining 80% of the run does nothing.

**The diagnostic that distinguishes real learning from collapse:**

| Signal | Real learning | Collapse |
|---|---|---|
| DPO loss | falls to ~0.3–0.5 over the run | < 0.1 within 20% of steps |
| Implicit-reward accuracy | rises to 0.7–0.9 | 1.00 almost immediately |
| Mean response length | roughly stable | moves > 25% |
| Held-out preference win-rate | rises with training loss | flat or falling |

**Length is the usual culprit**, because summed log-probability is length-dependent: a longer response
has lower total log-probability, so a policy can win preferences by systematically shortening (or
lengthening) rather than improving. That is why length-normalized win-rate is a required metric and
not an optional one.

---

## 4. RLVR, PPO and GRPO — and why the critic is a systems decision

**RLVR** replaces a learned reward model with a **program**: run the generated code against unit
tests, check the math answer against ground truth, validate JSON against a schema. Reward is 0/1 (or
partial credit) and, crucially, **cannot be gamed by fooling a neural reward model** — only by gaming
the verifier itself, which is a much narrower attack surface.

### The loop

```
for step in range(N):
    prompts  = sample(dataset, B)                       # B prompts
    rollouts = policy.generate(prompts, k samples each) # ← the expensive part
    rewards  = [verifier(p, r) for p, r in rollouts]    # ← CPU, GPUs idle
    advantages = normalize(rewards)                     # how "good" relative to what?
    policy.update(rollouts, advantages)                 # ← the gradient step
```

### Where the baseline comes from — PPO vs GRPO

An advantage needs a baseline: *good compared to what?*

**PPO** trains a second network, a **critic** (value function), to predict expected reward per state.
Accurate, and it costs you a whole extra model **with its own optimizer state**.

**GRPO** removes the critic. It generates `k` samples for the *same* prompt and uses the group as its
own baseline:

```
A_i = (r_i − mean(r_1..r_k)) / std(r_1..r_k)
```

**Why this is a systems decision, not just an algorithmic one.** On one 8×H100 node with an 8B policy
(full arithmetic in [`01_requirements.md §1.6`](01_requirements.md)):

| | Memory used per GPU | Free for KV cache | Max concurrent rollouts |
|---|---|---|---|
| **GRPO** (policy + reference) | 24 GB | 56 GB → 448 GB total | **2,967** |
| **PPO** (policy + reference + **critic** + reward model) | 42 GB | 38 GB → 304 GB total | **2,013** |

**The critic's optimizer state (16 bytes/param, another 16 GB/GPU) pushes the achievable rollout batch
below the 2,048 the design needs.** GRPO isn't just cheaper — on this hardware, at this group size, PPO
*doesn't fit*. That is the kind of trade you will be asked to defend.

### Why `k` (group size) matters

The GRPO baseline is a mean over `k` samples, so its noise falls as `1/√k`. Small `k` (2–4) gives a
noisy advantage; large `k` costs generation time linearly. `k = 8` is a common compromise. If **all
`k` samples get the same reward**, `std = 0` and the advantage is undefined — that group contributes
nothing. This is common early (everything fails) and late (everything passes), and handling it is an
edge case, not a footnote.

---

## 5. KL divergence: the leash

Every method above includes a term keeping the policy near its reference:

```
KL(π_θ ‖ π_ref) = Σ π_θ(y|x) · log[π_θ(y|x) / π_ref(y|x)]
```

In practice a per-token estimate summed over the response. It is the **leash**:

- **KL too low** → the policy barely moved; you spent GPU-hours on nothing.
- **KL too high** → the policy has left the reference's distribution. Outputs start to degenerate, and any learned reward model is now being asked about inputs it never saw during training — so its scores become meaningless *precisely when they look best*.

**KL is the single most useful diagnostic in post-training**, because it is the one number that
distinguishes "learning" from "drifting off the map." A rising reward with a rising KL and a falling
held-out score is the signature of reward hacking.

---

## 6. Reward hacking — the failure that looks like success

The model optimizes what you *measured*, not what you *meant*.

| Hack | What the model found | Detection |
|---|---|---|
| **Length exploitation** | Longer (or shorter) answers score better regardless of content | Mean response length vs. score; **length-normalized** win-rate |
| **Verifier gaming** | Code that passes the tests without solving the problem — reading expected outputs, catching all exceptions, `sys.exit(0)`, writing to the test file | A **held-out verifier implemented independently** |
| **Reward-model exploitation** | Text in a region where the learned RM is wrongly confident | KL to reference; RM score vs. human/held-out score |
| **Refusal collapse** | Refusing is safer than answering, so refuse more | Refusal rate as a tracked metric with a ceiling |
| **Format mimicry** | Copying the surface form of good answers (headers, hedging, citations) without the substance | Held-out task accuracy, not preference score |

### The detection arithmetic that decides your design

Reward hacking shows up as a **gap** between the training verifier's pass rate and a held-out
verifier's. To see a gap you need enough held-out samples for it to clear the noise. For two
proportions near 0.5, the standard error of the difference is `√(2 × 0.25/n)`:

| Held-out samples | SE of the gap | Smallest gap visible (2 SE) |
|---|---|---|
| 100 | 0.071 | **14.1 points** |
| 400 | 0.035 | 7.1 points |
| **1,500** | **0.018** | **3.7 points** |
| 2,223 | 0.015 | 3.0 points |
| 5,000 | 0.010 | 2.0 points |

**Reward hacking announces itself as a 2–5 point divergence long before it becomes a 15-point one.**
With 100 held-out prompts you cannot see it until it is catastrophic. **~1,500 is the floor for useful
detection** (a 3.7-point gap), and that number is a *requirement*, not a tuning choice.

**The part that is easy to get wrong:** the table above assumes both sides have `n` samples. They
don't. The *held-out* side has 1,500, but the *training* pass rate at a given step rests on far fewer
— a few hundred rollouts — so its SE (≈0.036 at n=192) is nearly 3× the held-out side's (0.013). **The
combined SE is dominated by the training side, which means buying held-out prompts past ~1,500 barely
tightens the interval.** The fix is to compute the gap over a *rolling window* of steps so both sides
have comparable sample counts. This is the kind of error that survives a design review and dies the
moment you write the code.

### Why the held-out verifier must be independently implemented

If both verifiers share code, they share bugs — and a model that games the shared bug passes both.
"Held out" must mean *a different implementation of the same specification*, not the same function on
different data.

---

## 7. Why generation is the systems problem

Training and generation want opposite things from a GPU:

| | Training step | Generation (decode) |
|---|---|---|
| Bottleneck | **Compute** (large matmuls) | **Memory bandwidth** (read all weights per token) |
| Batch shape | Few long sequences, full attention | Many sequences, one token at a time |
| Memory hogs | Optimizer state (16 B/param), activations | **KV cache** (128 KB/token for an 8B model) |
| Ideal engine | FSDP/DDP trainer | Continuous-batching inference server (paged KV) |

So a post-training platform runs **two engines over one set of weights**, and every step it must move
updated weights from trainer to generator. How you do that is the design's central decision:

```
8B policy = 16 GB in BF16.
  in-memory broadcast over NVLink   : 0.04 s
  in-memory broadcast over InfiniBand: 0.32 s
  write checkpoint to object store, reload in the inference engine,
    rebuild CUDA graphs             : ~56 s   ← against an ~89 s step
```

**The checkpoint round-trip is a 63% tax on every step.** It is also the obvious first implementation,
which is why the design names it as the rejected alternative rather than assuming nobody would do it.

---

## 8. Vocabulary

| Term | Meaning |
|---|---|
| **SFT** | Supervised fine-tuning — cross-entropy on `(prompt, good response)`, prompt masked |
| **DPO** | Direct Preference Optimization — preference learning without a reward model |
| **β (beta)** | DPO's strength knob; how hard to push before the logistic loss saturates |
| **Reference model** | Frozen copy of the pre-DPO/pre-RL policy; the anchor for KL and for DPO's log-ratios |
| **Implicit reward** | `β·log[π_θ(y|x)/π_ref(y|x)]` — DPO's induced reward, useful as a diagnostic |
| **RLHF** | RL from Human Feedback — train a reward model on preferences, then optimize with RL |
| **RLVR** | RL with Verifiable Rewards — reward comes from a *program*, not a learned model |
| **PPO** | Proximal Policy Optimization — clipped policy gradient with a learned critic |
| **GRPO** | Group Relative Policy Optimization — no critic; the group mean is the baseline |
| **Critic / value model** | Network predicting expected reward; PPO needs it, GRPO doesn't |
| **Rollout** | One generated response sampled from the policy |
| **Group size `k`** | Rollouts per prompt in GRPO; baseline noise falls as `1/√k` |
| **Advantage** | How much better a rollout was than the baseline |
| **KL divergence** | Distance from the reference policy — the leash |
| **Verifier** | Program that scores a rollout (unit tests, answer check, schema validation) |
| **Reward hacking** | Scoring well without doing the intended thing |
| **Length normalization** | Dividing by token count so length can't win on its own |
| **Decontamination** | Removing eval-set overlap from training data |
| **MinHash / LSH** | Near-duplicate detection by hashed shingle signatures |
| **On-policy / off-policy** | Whether rollouts came from the *current* weights or older ones |
| **Staleness** | How many updates old the weights that produced a rollout are |
| **KV cache** | Cached keys/values so decode doesn't re-read history; the memory that caps concurrency |
| **Zero-gradient cold start** | Every rollout scores 0, so nothing is learned — the classic first-RLVR-run failure |

---

← [system README](README.md) · → [01_requirements.md](01_requirements.md) ·
[shared assumptions](../00_requirements_all_systems.md)
