# Runnable core — Post-Training Pipeline

```bash
pip install torch
python run.py                       # ~2 s on CPU
python run.py --skip-dpo            # parts 1,3,4,5 only — NO torch needed, <1 s
python run.py --dpo-steps 300 --rl-steps 80
python run.py --csv out.csv         # part-4 per-step metrics
python run.py --help
```

## What it actually runs

| Part | What it does | Design section |
|---|---|---|
| **1 · Decontamination** | A real 13-gram Bloom filter over real eval-suite text, then a real corpus scan — including a paraphrase that correctly slips through | [`03_lld.md`](../03_lld.md) §3.3.6 |
| **2 · DPO + collapse** | Hand-rolled DPO loss on a tiny LM, run **twice**: pairs differing in content vs pairs where `chosen` is always shorter. Only the second collapses | [`03_lld.md`](../03_lld.md) §3.3.1 · FR-4 |
| **3 · GRPO advantages** | The degenerate groups — all-fail, all-pass, and the float-noise trap that `(r−μ)/(σ+ε)` turns into advantages in the thousands | [`03_lld.md`](../03_lld.md) §3.3.2 |
| **4 · Reward hacking** | 🔴 **The one to read.** A real GRPO loop over 3 response strategies **discovers** a verifier exploit on its own | [`03_lld.md`](../03_lld.md) §3.3.3–3.3.4 |
| **5 · Detection power** | How many held-out prompts you need — and why the answer isn't "more held-out prompts" | [`00_concepts.md`](../00_concepts.md) §6 |

## Part 4 — the exploit is discovered, not scripted

Two verifiers for "what is A + B?", sharing **no code**:

```python
def verifier_training(prompt, response, answer):     # LOOSE, as a hurried engineer writes it
    return 1.0 if str(answer) in re.findall(r"-?\d+", response) else 0.0

def verifier_heldout(prompt, response, answer):      # STRICT: one final answer, and it's right
    m = re.search(r"(?:answer|=)\s*:?\s*(-?\d+)\s*$", response.strip(), re.I)
    return 1.0 if m and int(m.group(1)) == answer else 0.0
```

A tabular policy over three strategies (`honest`, `shotgun`, `verbose_hedge`) is updated by **real GRPO
advantages computed from real calls to the loose verifier**. Nothing tells it about the exploit. Typical
run:

```
 step   frac0    train  heldout      gap     len  P(honest)  P(shotgun)
    1   0.000    0.646    0.252   +0.394    28.9      0.333       0.333
   12   0.000    0.932    0.089   +0.844    33.3      0.135       0.821
   30   0.000    0.969    0.027   +0.942    36.9      0.036       0.953
```

Training pass rate **0.65 → 0.97**. Held-out pass rate **0.25 → 0.03**. The policy found that listing
25 numbers satisfies "the right number appears somewhere" while satisfying no strict grader at all.

**On a reward-only dashboard this is a great run.** The held-out verifier is the only thing that makes
it visible — and only because it is a different *implementation*, not just different data.

## Two design bugs this code found

Written honestly, because both survived the prose and died on contact with the code:

1. **The verifier-gap threshold had no `n`.** The requirement said "detect a 3-point gap with 1,500
   held-out prompts." 2 SE at n=1,500 is **3.7 points**, not 3.0 (3.0 needs n≈2,223). Worse: the
   gap's SE is **dominated by the *training* side** — a single step's training pass rate rests on ~192
   rollouts (SE 0.036) versus 0.013 for 1,500 held-out. Buying held-out prompts past ~1,500 barely
   moves the CI; the fix is a **rolling 8-step window**. Now in [§1.7 A8](../01_requirements.md) and
   [§3.3.4](../03_lld.md).
2. **The DPO collapse threshold had no `n` either.** `reward_accuracy > 0.99` on a batch of 8 fires
   ~27% of the time at 85% *true* accuracy — it aborts healthy runs within a few steps. Fixed to
   EMA(loss) plus accuracy over a ≥256-pair window. Now in FR-4 and [§3.3.1](../03_lld.md).

Same error class both times: **a threshold on a proportion, stated without a sample size.**

## Honest limitations

- **Part 4's policy is tabular over 3 fixed strategies**, not a neural policy generating free text. Real GRPO explores a vastly larger space and finds subtler exploits. What *is* real: the verifier code, the reward signal, the advantage computation, the policy-gradient update, and the fact that the exploit is discovered rather than planted.
- **Part 2's model has no attention** (embed + MLP + head), so it learns per-position token preferences only. Enough to make the collapse contrast real; not a language model.
- **Part 1's suites are 4 items**, so the filter is KB not MB. The production sizing is printed alongside.
- The `honest` strategy is correct 70% of the time by construction — a stand-in for a model that makes arithmetic mistakes, not a measured rate.

## What a real pipeline adds

| Here | In production |
|---|---|
| In-process "generation" | vLLM/SGLang-class engine, paged KV, continuous batching |
| `emit()` returning a string | An 8B policy on 8×H100, 2,048 concurrent rollouts, 309 GB of KV cache |
| A Python function call | gVisor sandbox: no network, 2 s CPU, 512 MB, `pids_max=64` ([§3.3.3](../03_lld.md)) |
| Tabular logits | FSDP trainer + in-memory 16 GB weight broadcast each step ([§2.2](../02_hld.md)) |
| Printed verdict | Immutable signed report + hard promotion gate ([§3.1.5](../03_lld.md)) |
| 4-item Bloom filter | 72 MB filter, 40M shingles, DB trigger enforcing 100% suite coverage |

---

← [system README](../README.md) · [00_concepts.md](../00_concepts.md) · [03_lld.md](../03_lld.md)
