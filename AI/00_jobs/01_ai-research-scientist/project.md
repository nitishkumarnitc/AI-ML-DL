# 01 · Sample project — AI / ML Research Scientist

← back to [job description](README.md) · [jobs hub](../README.md)

🏗️ **Then design the platform version:** [Research Experiment Platform](../../29_model-training-system-design/01_research_experiment_platform/README.md) — full Requirements → HLD → LLD for the system a lab would actually run this on ([folder index](../../29_model-training-system-design/README.md)).

> ▶ **Run the real code:** `pip install torch && python project/run.py` (~1-2 min) -- runs TWO real ablation studies (LR warmup, and learned vs sinusoidal positional encoding) and prints the mean/stdev table + verdict for each, plus writes every per-seed result to a CSV. `--help` shows CLI options. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Two miniature **ablation studies**: train a tiny character-level language model under two variants of a design choice, across multiple seeds, and write a one-page research memo on what you found — the same loop as frontier research, just at toy scale. The second study (positional encoding) shows the same method applied to a different, independent question, because real research is rarely a single ablation.

## 🧠 Why this mirrors the real job
- "Turn a fuzzy research question into a measurable hypothesis and a training run" → you'll pick one concrete question ("does learning-rate warmup change final loss variance?") before writing any code.
- "Design and run large experiments; read results" → multiple seeds per variant, plotted, not eyeballed from one run.
- "Publish or ship into the next model" → the memo is the artifact; that's literally the research work product.

## 🧰 Prerequisites
- Python, PyTorch (CPU is fine — model is <1M params).
- A small text file to train on (e.g. tiny Shakespeare — any public-domain text works).
- ~2–3 hours.

## 🧰 Tools, libraries & skills used here
- **PyTorch** (`torch.nn`, `torch.optim`, autograd) — the near-universal framework for this role; you're using `nn.TransformerEncoderLayer`, embeddings, and a causal attention mask by hand instead of importing a pretrained model.
- **Statistics** (`statistics.mean`/`pstdev`) — comparing a mean effect against seed-to-seed noise is the single most-skipped step in informal ML experimentation, and the one that separates a real result from a coincidence.
- **Experiment design**: one variable changed at a time, multiple seeds, a stated hypothesis before running anything — the actual research skill, independent of scale.
- **What a real lab adds on top**: distributed training (`torch.distributed`/DeepSpeed/FSDP) instead of a single tiny model, experiment tracking (Weights & Biases, MLflow), config management (Hydra), and a job scheduler (SLURM/Kubernetes) instead of a laptop loop.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| torch | pip install torch | tensors, autograd, `nn.TransformerEncoderLayer`, `AdamW` optimizer — the model and training loop |
| statistics (stdlib) | built in | `mean`/`pstdev` to compare the two variants against seed noise |

## 🪜 Step-by-step

### 1. Pick one variable to ablate
Keep it to **one** change so results are interpretable. Good starter choices:
- Warmup steps: `0` vs `100`.
- Positional encoding: learned vs sinusoidal.
- LR: `3e-4` vs `1e-3`.

### 2. Minimal training script
```python
import torch, torch.nn as nn, urllib.request

text = open("input.txt").read()  # any small text corpus
chars = sorted(set(text))
stoi = {c: i for i, c in enumerate(chars)}
data = torch.tensor([stoi[c] for c in text], dtype=torch.long)

block_size, batch_size = 64, 32

def get_batch():
    ix = torch.randint(len(data) - block_size, (batch_size,))
    x = torch.stack([data[i:i+block_size] for i in ix])
    y = torch.stack([data[i+1:i+block_size+1] for i in ix])
    return x, y

class TinyLM(nn.Module):
    def __init__(self, vocab_size, n_embd=64, n_head=4, n_layer=2):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.Sequential(*[
            nn.TransformerEncoderLayer(n_embd, n_head, dim_feedforward=256, batch_first=True)
            for _ in range(n_layer)
        ])
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, x):
        b, t = x.shape
        pos = torch.arange(t, device=x.device)
        h = self.tok_emb(x) + self.pos_emb(pos)
        h = self.blocks(h)
        return self.head(h)

def train_run(seed, warmup_steps, lr=3e-4, steps=500):
    torch.manual_seed(seed)
    model = TinyLM(len(chars))
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    losses = []
    for step in range(steps):
        cur_lr = lr * min(1.0, (step + 1) / max(warmup_steps, 1))
        for g in opt.param_groups:
            g["lr"] = cur_lr
        x, y = get_batch()
        logits = model(x)
        loss = nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        opt.zero_grad(); loss.backward(); opt.step()
        losses.append(loss.item())
    return losses
```

### 3. Run the ablation across seeds
```python
results = {"no_warmup": [], "warmup_100": []}
for seed in range(5):
    results["no_warmup"].append(train_run(seed, warmup_steps=0)[-1])
    results["warmup_100"].append(train_run(seed, warmup_steps=100)[-1])

import statistics as st
for name, vals in results.items():
    print(name, "mean:", st.mean(vals), "stdev:", st.pstdev(vals))
```

### 4. Plot and interpret
Plot mean final loss ± stdev per variant. Ask: is the difference bigger than the seed-to-seed noise? If not, your ablation is inconclusive — that's a real, common research outcome, not a failure.

## ✅ Deliverable
A one-page memo with:
1. **Hypothesis** — what you expected and why.
2. **Method** — exact config, seeds, steps.
3. **Result** — the table/plot, mean ± stdev per variant.
4. **Conclusion** — supported, not supported, or inconclusive (say which, honestly).
5. **Next experiment** — what you'd try next given this result.

## ⏱️ Time box
Half a day, including the writeup.

## 🏗️ Scale this to a real lab — the system design

This project is one ablation, run by hand. A lab runs ~200 a quarter, and at that volume the
interesting problems are not in the training loop — they are in **whether the answers can be read at
all.** [`29/01 · Research Experiment Platform`](../../29_model-training-system-design/01_research_experiment_platform/README.md)
is the full Requirements → HLD → LLD for that system.

**Start with the finding that changes how you'd run this project:**

```
sigma  = seed-to-seed std of final val loss (~0.02 nats at 200M params)
delta  = the effect you want to detect

runs per arm for 80% power = 15.70 · sigma²/delta²
smallest effect n seeds can see = sigma · sqrt(15.70/n)

  n=3  (this project's default) ->  0.046 nats
  n=63                          ->  0.010 nats
```

**Real architectural effects are 0.005–0.02 nats.** So the 5-seed version of step 3 above cannot see
the effects it is testing for — which is exactly why the step-4 verdict is so often "inconclusive."
The fix costs nothing: **pair the arms** (same init seed, same data order, same eval batches, only the
ablated variable differs) and test the *differences*. At ρ=0.8 that turns 126 runs into 26.

| What this project does | What the platform adds | Why |
|---|---|---|
| 5 seeds because 5 felt reasonable | **Power gate**: computes required `n` from measured σ, ρ and δ, and refuses an underpowered plan | A gate in front of the scheduler, not a dashboard beside it — advisory rigor gets bypassed |
| σ assumed | **Variance census**: 8 identical runs per (family, scale), ~$81 | A power calculation on a defaulted σ is fiction that looks quantitative |
| Arms constructed by hand | **Paired arms built by construction**, with the resolved config diff verified | A stray default silently breaking pairing is a failure no human notices |
| A config dict in a script | **Five `NOT NULL` provenance columns** — resolved-config hash, code SHA, container **digest**, data manifest hash, seed tuple | A metric that isn't joinable to all five isn't evidence. Pinning by tag instead of digest lets a cuBLAS upgrade masquerade as your result |
| Eyeball the mean ± stdev | **Verdict engine**: paired-t where legal, BH across arms, **achieved** power, and `inconclusive` as a first-class outcome | A two-outcome system turns "we couldn't see it" into "it doesn't work" — a false negative laundered as a finding |
| One ablation | **Two-tier policy** (screen at δ=0.02 → confirm at δ=0.01 with fresh seeds) | Full power on everything costs $60.1k/quarter against a $60k ceiling; tiering the *effect size* is the structural fix |
| — | **Scaling-law ladder** as a first-class object with a bootstrap CI | A 7-rung ladder is **$3,391 = 0.31%** of the $1.1M flagship it de-risks |

**Two traps this project can't show you but the design covers:** a 20-arm sweep produces a "winner"
**64% of the time under the null**, and peeking at live loss curves inflates α from 0.05 to ~0.20 over
ten looks. Both are why "pre-registration" appears in a systems design document — they cannot be fixed
after the fact by better statistics.

**Run the platform's core:**

```bash
python ../../29_model-training-system-design/01_research_experiment_platform/project/run.py
```

It performs 24 real training runs, **measures** σ and ρ, then runs the actual power calculator and
verdict engine on them — including the paired-vs-unpaired CI comparison on identical data.

## 🔁 Where to go deeper
[`DL/04_reinforcement-learning`](../../../DL/04_reinforcement-learning/README.md) · [`AI/02_fine-tuning-and-alignment`](../../02_fine-tuning-and-alignment/README.md) — the same experiment-design muscle applied to RLHF/DPO instead of pretraining.

**Design-level:** [`29/01_research_experiment_platform`](../../29_model-training-system-design/01_research_experiment_platform/README.md) — the platform version of this project, with quantified NFRs, rejected alternatives, failure modes and runnable code.
