"""
Sample project — AI / ML Research Scientist
Two miniature ablation studies on a tiny character-level transformer:

  Experiment A: does LR warmup change final-loss variance?
  Experiment B: learned positional embeddings vs. fixed sinusoidal ones?

Each experiment trains N seeds per variant, reports mean/stdev, and prints a
verdict on whether the effect is bigger than seed-to-seed noise. Results are
written to a CSV so you can plot them properly later, and a crude ASCII bar
chart is printed so you get an at-a-glance read without leaving the terminal.

This is the actual research loop at any scale: state a hypothesis, vary ONE
thing, run multiple seeds, and check the effect against the noise floor
before believing it. Everything else (bigger model, more variants, real
hyperparameter sweeps) is the same loop repeated.

Run:  python run.py
      python run.py --seeds 8 --steps 500       (more seeds/steps -> less noisy, slower)
      python run.py --experiment warmup          (run just one experiment)
Dependencies:
  - torch (pip install torch) -- tensors, autograd, nn.TransformerEncoderLayer, AdamW
  - statistics (stdlib) -- mean/pstdev for the seed-noise comparison
  - argparse, csv (stdlib) -- CLI config and results export
"""
import argparse
import csv
import math
import statistics as st

import torch
import torch.nn as nn
import torch.nn.functional as F

TEXT = ("the quick brown fox jumps over the lazy dog. " * 40 +
        "to be or not to be, that is the question. " * 40 +
        "all that glitters is not gold, and not all who wander are lost. " * 40 +
        "a journey of a thousand miles begins with a single step. " * 40)

chars = sorted(set(TEXT))
stoi = {c: i for i, c in enumerate(chars)}
data = torch.tensor([stoi[c] for c in TEXT], dtype=torch.long)

BLOCK_SIZE, BATCH_SIZE = 48, 32


def get_batch():
    ix = torch.randint(len(data) - BLOCK_SIZE - 1, (BATCH_SIZE,))
    x = torch.stack([data[i:i + BLOCK_SIZE] for i in ix])
    y = torch.stack([data[i + 1:i + BLOCK_SIZE + 1] for i in ix])
    return x, y


def sinusoidal_positions(block_size: int, n_embd: int) -> torch.Tensor:
    """Fixed (non-learned) positional encoding, as in the original Transformer paper."""
    pos = torch.arange(block_size).unsqueeze(1).float()
    div = torch.exp(torch.arange(0, n_embd, 2).float() * (-math.log(10000.0) / n_embd))
    pe = torch.zeros(block_size, n_embd)
    pe[:, 0::2] = torch.sin(pos * div)
    pe[:, 1::2] = torch.cos(pos * div)
    return pe


class TinyLM(nn.Module):
    def __init__(self, vocab_size, n_embd=48, n_head=4, n_layer=2, pos_encoding="learned"):
        super().__init__()
        self.pos_encoding = pos_encoding
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        if pos_encoding == "learned":
            self.pos_emb = nn.Embedding(BLOCK_SIZE, n_embd)
        else:
            self.register_buffer("pos_emb_fixed", sinusoidal_positions(BLOCK_SIZE, n_embd))
        layer = nn.TransformerEncoderLayer(n_embd, n_head, dim_feedforward=128, batch_first=True)
        self.blocks = nn.TransformerEncoder(layer, num_layers=n_layer)
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, x):
        b, t = x.shape
        mask = nn.Transformer.generate_square_subsequent_mask(t)
        if self.pos_encoding == "learned":
            pos = torch.arange(t, device=x.device)
            h = self.tok_emb(x) + self.pos_emb(pos)
        else:
            h = self.tok_emb(x) + self.pos_emb_fixed[:t]
        h = self.blocks(h, mask=mask, is_causal=True)
        return self.head(h)


def train_run(seed: int, steps: int, warmup_steps: int = 0, lr: float = 3e-3,
              pos_encoding: str = "learned") -> float:
    torch.manual_seed(seed)
    model = TinyLM(len(chars), pos_encoding=pos_encoding)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    last_loss = None
    for step in range(steps):
        cur_lr = lr * min(1.0, (step + 1) / max(warmup_steps, 1))
        for g in opt.param_groups:
            g["lr"] = cur_lr
        x, y = get_batch()
        logits = model(x)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
        opt.zero_grad()
        loss.backward()
        opt.step()
        last_loss = loss.item()
    return last_loss


def ascii_bar(value: float, max_value: float, width: int = 30) -> str:
    n = int((value / max_value) * width) if max_value else 0
    return "#" * max(n, 0)


def run_ablation(name: str, variants: dict, seeds: int, steps: int, csv_writer=None):
    print(f"\n=== {name} ===")
    results = {}
    for variant_name, train_kwargs in variants.items():
        losses = []
        for seed in range(seeds):
            loss = train_run(seed, steps, **train_kwargs)
            losses.append(loss)
            if csv_writer:
                csv_writer.writerow([name, variant_name, seed, loss])
        results[variant_name] = losses
        print(f"  {variant_name}: seed losses = {[round(v, 3) for v in losses]}")

    print(f"\n  {'variant':<18}{'mean':>8}{'stdev':>8}   chart")
    max_mean = max(st.mean(v) for v in results.values())
    for variant_name, losses in results.items():
        mean, stdev = st.mean(losses), st.pstdev(losses)
        print(f"  {variant_name:<18}{mean:8.3f}{stdev:8.3f}   {ascii_bar(mean, max_mean)}")

    means = {k: st.mean(v) for k, v in results.items()}
    gap = max(means.values()) - min(means.values())
    noise = max(st.pstdev(v) for v in results.values())
    verdict = "SUPPORTED" if gap > noise else "INCONCLUSIVE (gap smaller than seed noise)"
    print(f"\n  gap between best/worst variant: {gap:.3f} | max within-variant stdev: {noise:.3f}")
    print(f"  Verdict: {verdict}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Tiny transformer ablation studies")
    parser.add_argument("--seeds", type=int, default=5, help="seeds per variant (default: 5)")
    parser.add_argument("--steps", type=int, default=300, help="training steps per run (default: 300)")
    parser.add_argument("--experiment", choices=["warmup", "positional", "both"], default="both")
    parser.add_argument("--csv", default="ablation_results.csv", help="output CSV path")
    args = parser.parse_args()

    print(f"corpus size: {len(TEXT)} chars, vocab: {len(chars)} unique chars")
    print(f"config: seeds={args.seeds}, steps={args.steps}, experiment={args.experiment}")

    with open(args.csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["experiment", "variant", "seed", "final_loss"])

        if args.experiment in ("warmup", "both"):
            run_ablation(
                "Experiment A: LR warmup (0 steps vs 50 steps)",
                {"warmup_0": {"warmup_steps": 0}, "warmup_50": {"warmup_steps": 50}},
                args.seeds, args.steps, writer,
            )

        if args.experiment in ("positional", "both"):
            run_ablation(
                "Experiment B: learned vs sinusoidal positional encoding",
                {"learned_pos": {"pos_encoding": "learned"},
                 "sinusoidal_pos": {"pos_encoding": "sinusoidal"}},
                args.seeds, args.steps, writer,
            )

    print(f"\nFull per-seed results written to {args.csv} -- open it in a spreadsheet or "
          f"pandas to plot the distributions properly instead of trusting the ASCII bars.")


if __name__ == "__main__":
    main()
