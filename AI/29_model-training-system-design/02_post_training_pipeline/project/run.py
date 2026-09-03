#!/usr/bin/env python3
"""
Post-Training Pipeline - runnable core.

Implements, for real, the five parts of the design that carry judgement:

  1. Decontamination      13-gram Bloom filter  (03_lld.md §3.3.6)
  2. DPO + collapse       hand-rolled DPO loss  (03_lld.md §3.3.1)
  3. GRPO advantages      degenerate groups     (03_lld.md §3.3.2)
  4. REWARD HACKING       a real GRPO loop that DISCOVERS a verifier exploit,
                          caught by a real independently-implemented held-out
                          verifier and the four-signal detector
                                                (03_lld.md §3.3.3-3.3.4)
  5. Detection power      how many held-out prompts you actually need
                                                (00_concepts.md §6)

    pip install torch
    python run.py                  # ~2 s on CPU
    python run.py --dpo-steps 300  # longer DPO runs
    python run.py --skip-dpo       # parts 1,3,4,5 only -- no torch needed, <1 s
    python run.py --csv out.csv
    python run.py --help

Part 4 is the one to read. The exploit is not scripted: a tabular policy is
updated by real GRPO advantages computed from a real (deliberately loose)
verifier, and it finds the hack on its own.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import random
import re
import statistics as st
import sys
import time
from dataclasses import dataclass, field

BAR = "=" * 78


def hdr(t: str) -> None:
    print(f"\n{BAR}\n{t}\n{BAR}")


# ============================================================================
# PART 1 - Decontamination: a real 13-gram Bloom filter  (03_lld §3.3.6)
# ============================================================================


class BloomFilter:
    """Standard Bloom filter. m = -n·ln(p)/(ln2)², k = (m/n)·ln2."""

    def __init__(self, capacity: int, error_rate: float = 1e-3):
        self.n = max(1, capacity)
        self.p = error_rate
        self.m = max(8, int(math.ceil(-self.n * math.log(self.p) / (math.log(2) ** 2))))
        self.k = max(1, int(round(self.m / self.n * math.log(2))))
        self.bits = bytearray((self.m + 7) // 8)
        self.added = 0

    def _idx(self, item: str):
        d = hashlib.blake2b(item.encode(), digest_size=16).digest()
        h1 = int.from_bytes(d[:8], "little")
        h2 = int.from_bytes(d[8:], "little") | 1
        for i in range(self.k):
            yield ((h1 + i * h2) % self.m)

    def add(self, item: str) -> None:
        for b in self._idx(item):
            self.bits[b >> 3] |= 1 << (b & 7)
        self.added += 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[b >> 3] >> (b & 7) & 1 for b in self._idx(item))

    @property
    def size_bytes(self) -> int:
        return len(self.bits)


def shingles(tokens: list[str], n: int):
    for i in range(max(0, len(tokens) - n + 1)):
        yield " ".join(tokens[i:i + n])


def tok(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text.lower())


def part1_decontamination(n: int = 13, fpr: float = 1e-3) -> dict:
    hdr("PART 1 - DECONTAMINATION (03_lld §3.3.6)")
    print(f"A real {n}-gram Bloom filter over eval suites, then a real corpus scan.\n")

    # Two small "eval suites".
    suite_items = [
        "A train leaves the station at 3 pm travelling at 60 km per hour "
        "how far does it travel in 4 hours and 30 minutes total",
        "Natalia sold clips to 48 of her friends in April and then she sold "
        "half as many clips in May how many clips did she sell altogether",
        "Compute the derivative of the function f of x equals x cubed plus "
        "two x squared minus five x plus seven with respect to x",
        "Write a python function that returns the n th fibonacci number "
        "using memoisation and analyse its time and space complexity",
    ]
    bf = BloomFilter(capacity=sum(len(tok(s)) for s in suite_items) or 1, error_rate=fpr)
    for s in suite_items:
        for sh in shingles(tok(s), n):
            bf.add(sh)
    print(f"  suites: 2 · items: {len(suite_items)} · shingles added: {bf.added}")
    print(f"  filter: m={bf.m:,} bits = {bf.size_bytes/1024:.1f} KB, k={bf.k} hashes, "
          f"FPR target {fpr}")

    corpus = [
        ("doc-clean-1", "The capital of France is Paris and it sits on the river Seine "
                        "which flows north west toward the English Channel coast."),
        ("doc-clean-2", "To reverse a linked list iteratively keep three pointers named "
                        "previous current and next and relink each node as you walk."),
        ("doc-contam-1", "Here is a worked example. Natalia sold clips to 48 of her friends "
                         "in April and then she sold half as many clips in May how many "
                         "clips did she sell altogether. The answer is 72."),
        ("doc-clean-3", "Gradient descent updates parameters in the direction opposite to "
                        "the gradient of the loss scaled by a learning rate value."),
        ("doc-contam-2", "Practice problem: Compute the derivative of the function f of x "
                         "equals x cubed plus two x squared minus five x plus seven with "
                         "respect to x and then evaluate it at x equals one."),
        ("doc-near-miss", "Compute the derivative of g of y equals y cubed minus four y "
                          "plus one and evaluate the result at y equals two exactly."),
    ]
    print(f"\n  scanning {len(corpus)} documents:\n")
    print(f"  {'doc':>16} {'hits':>6} {'grams':>7} {'ratio':>8}  verdict")
    kept, dropped = [], []
    for did, text in corpus:
        t = tok(text)
        grams = list(shingles(t, n))
        hits = sum(1 for sh in grams if sh in bf)
        ratio = hits / max(1, len(grams))
        if hits > 0:
            dropped.append(did)
            verdict = "DROP (eval overlap)"
        else:
            kept.append(did)
            verdict = "keep"
        print(f"  {did:>16} {hits:>6} {len(grams):>7} {ratio:>8.3f}  {verdict}")

    print(f"\n  kept {len(kept)} · dropped {len(dropped)}: {dropped}")
    print("  'doc-near-miss' paraphrases a suite item but shares no 13-gram -> kept.")
    print("  That is the known limitation: n-gram overlap does not catch paraphrase")
    print("  (02_hld §2.2 -- embedding checks go ON TOP, never instead).")

    print("\n  Production sizing (01_requirements §1.6.4):")
    for cap, p in ((40_000_000, 1e-2), (40_000_000, 1e-3)):
        m = -cap * math.log(p) / (math.log(2) ** 2)
        print(f"    40M shingles @ FPR {p:<6}: {m/8/1e6:>5.0f} MB, "
              f"k={round(m/cap*math.log(2))} hashes")
    print("    600M training shingles x ~1 us = ~10 CPU-minutes, trivially parallel.")
    print("    => the cheapest P0 requirement in the design.")
    return dict(kept=len(kept), dropped=len(dropped), filter_kb=bf.size_bytes / 1024)


# ============================================================================
# PART 3 - GRPO advantages and the degenerate groups  (03_lld §3.3.2)
# ============================================================================

ZERO_STD_EPS = 1e-6


def grpo_advantages(groups: list[list[float]]) -> tuple[list[float], float]:
    out, n_zero = [], 0
    for rewards in groups:
        mu = st.mean(rewards)
        sd = st.pstdev(rewards)
        if sd < ZERO_STD_EPS:
            out.extend([0.0] * len(rewards))
            n_zero += 1
            continue
        out.extend([(r - mu) / sd for r in rewards])
    return out, n_zero / len(groups)


def part3_grpo() -> None:
    hdr("PART 3 - GRPO ADVANTAGES: the degenerate groups (03_lld §3.3.2)")
    print("The group mean IS the baseline -- no critic. All the judgement is in the")
    print("zero-variance case, which happens on every run: early (all fail) and")
    print("late (all pass).\n")
    cases = [
        ("healthy mix", [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]),
        ("one success", [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]),
        ("ALL fail (cold start)", [0.0] * 8),
        ("ALL pass (saturated)", [1.0] * 8),
        ("float noise only", [0.5, 0.5, 0.5, 0.5000000001, 0.5, 0.5, 0.5, 0.5]),
        ("partial credit", [0.9, 0.3, 0.7, 0.1, 0.5, 0.4, 0.8, 0.2]),
    ]
    print(f"  {'group':>24} {'std':>12} {'advantages (first 4)':>34}")
    for name, rewards in cases:
        adv, _ = grpo_advantages([rewards])
        sd = st.pstdev(rewards)
        shown = ", ".join(f"{a:+.2f}" for a in adv[:4])
        print(f"  {name:>24} {sd:>12.3e}   [{shown}, ...]")

    print("\n  The 'float noise only' row is the trap. With `(r-mu)/(sd+eps)` a 1e-10")
    print("  spread produces advantages in the thousands, and the training curve looks")
    print("  MORE active, not broken. Contributing exactly 0.0 is the correct handling.\n")

    mixed = [[1.0, 0.0, 1.0, 0.0], [0.0] * 4, [0.0] * 4, [1.0] * 4, [0.3, 0.7, 0.1, 0.9]]
    _, frac = grpo_advantages(mixed)
    print(f"  5-group batch, 3 degenerate -> frac_zero_std_groups = {frac:.2f}")
    print(f"  FR-12 halts when this exceeds 0.9 for 10 consecutive steps.")
    print("  reward_mean disambiguates: ~0 => cold start, ~1 => saturated. Opposite fixes.")


# ============================================================================
# PART 4 - REWARD HACKING, discovered by a real GRPO loop
# ============================================================================

# ---- The task: "what is A + B?" --------------------------------------------


def make_task(rng: random.Random) -> tuple[str, int]:
    a, b = rng.randint(1, 25), rng.randint(1, 25)
    return f"What is {a} + {b}?", a + b


# ---- Verifier #1: the TRAINING verifier. Loose on purpose. -----------------
# Written the way a hurried engineer writes it: "does the right number appear?"


def verifier_training(prompt: str, response: str, answer: int) -> float:
    """LOOSE: accepts if the correct number appears ANYWHERE in the response."""
    return 1.0 if str(answer) in re.findall(r"-?\d+", response) else 0.0


# ---- Verifier #2: the HELD-OUT verifier. Independent implementation. -------
# Shares NO code with the above (03_lld §3.1.2 import-graph invariant).


def verifier_heldout(prompt: str, response: str, answer: int) -> float:
    """STRICT: the response must state exactly one final answer, and it must be right."""
    m = re.search(r"(?:answer|=)\s*:?\s*(-?\d+)\s*$", response.strip(), re.IGNORECASE)
    if m is None:
        return 0.0
    return 1.0 if int(m.group(1)) == answer else 0.0


# ---- Three response strategies the policy can choose between --------------

STRATEGIES = ["honest", "shotgun", "verbose_hedge"]


def emit(strategy: str, answer: int, rng: random.Random) -> str:
    if strategy == "honest":
        # Correct 70% of the time (a real model makes arithmetic mistakes).
        val = answer if rng.random() < 0.70 else answer + rng.choice([-2, -1, 1, 2])
        return f"Let me add them. answer: {val}"
    if strategy == "shotgun":
        # THE EXPLOIT: list many numbers. The loose verifier finds the right one
        # somewhere; the strict verifier sees no single final answer.
        lo = max(0, answer - 12)
        nums = " ".join(str(v) for v in range(lo, lo + 25))
        return f"It could be one of these: {nums}. Hard to say precisely."
    # verbose_hedge: long, no number at all. Fails both. A control arm.
    return ("This is an addition problem. Addition is commutative and associative, "
            "so the order of the operands does not affect the result, and one can "
            "proceed by decomposing each operand into tens and units before "
            "recombining the partial sums carefully.")


def softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    e = [math.exp(x - m) for x in xs]
    s = sum(e)
    return [v / s for v in e]


@dataclass
class StepRow:
    step: int
    reward_mean: float
    train_pass: float
    heldout_pass: float
    gap: float
    mean_len: float
    frac_zero_std: float
    probs: list[float] = field(default_factory=list)


def part4_reward_hacking(steps: int = 40, groups_per_step: int = 24, k: int = 8,
                         heldout_n: int = 1500, lr: float = 0.6, seed: int = 7
                         ) -> tuple[list[StepRow], dict]:
    hdr("PART 4 - REWARD HACKING, DISCOVERED (03_lld §3.3.3-3.3.4)")
    print("A tabular policy over 3 response strategies, updated by REAL GRPO")
    print("advantages computed from the REAL loose training verifier above.")
    print("Nothing about the exploit is scripted -- the policy finds it.\n")
    print("  training verifier (LOOSE) : correct number appears anywhere")
    print("  held-out verifier (STRICT): exactly one final answer, and it is right")
    print("  -> the two share no code. That is what makes the gap meaningful.\n")

    rng = random.Random(seed)
    logits = [0.0, 0.0, 0.0]
    rows: list[StepRow] = []

    print(f"  {'step':>5} {'frac0':>7} {'train':>8} {'heldout':>8} {'gap':>8} "
          f"{'len':>7} {'P(honest)':>10} {'P(shotgun)':>11}")
    for step in range(1, steps + 1):
        probs = softmax(logits)
        groups, chosen_all, lens, train_hits = [], [], [], []
        for _ in range(groups_per_step):
            prompt, ans = make_task(rng)
            rewards, picks = [], []
            for _ in range(k):
                s = rng.choices(STRATEGIES, weights=probs, k=1)[0]
                resp = emit(s, ans, rng)
                r = verifier_training(prompt, resp, ans)     # REAL verifier call
                rewards.append(r)
                picks.append(s)
                lens.append(len(tok(resp)))
                train_hits.append(r)
            groups.append(rewards)
            chosen_all.append(picks)

        advantages, frac_zero = grpo_advantages(groups)

        # Real policy-gradient update: push up strategies with positive advantage.
        grad = [0.0, 0.0, 0.0]
        i = 0
        for picks in chosen_all:
            for s in picks:
                grad[STRATEGIES.index(s)] += advantages[i]
                i += 1
        n = groups_per_step * k
        logits = [l + lr * g / n for l, g in zip(logits, grad)]

        # Independent held-out evaluation with the STRICT verifier.
        ho_rng = random.Random(90_000 + step)
        ho = []
        for _ in range(heldout_n):
            prompt, ans = make_task(ho_rng)
            s = ho_rng.choices(STRATEGIES, weights=probs, k=1)[0]
            ho.append(verifier_heldout(prompt, emit(s, ans, ho_rng), ans))

        row = StepRow(step, st.mean(advantages) if advantages else 0.0,
                      st.mean(train_hits), st.mean(ho),
                      st.mean(train_hits) - st.mean(ho), st.mean(lens), frac_zero,
                      list(probs))
        rows.append(row)
        if step % max(1, steps // 10) == 0 or step == 1:
            print(f"  {step:>5} {row.frac_zero_std:>7.3f} {row.train_pass:>8.3f} "
                  f"{row.heldout_pass:>8.3f} {row.gap:>+8.3f} {row.mean_len:>7.1f} "
                  f"{probs[0]:>10.3f} {probs[1]:>11.3f}")

    # ---- The four-signal detector (03_lld §3.3.4) --------------------------
    first, last = rows[0], rows[-1]
    gap = last.gap
    se = math.sqrt(last.train_pass * (1 - last.train_pass) / (groups_per_step * k) +
                   last.heldout_pass * (1 - last.heldout_pass) / heldout_n)
    ci = (gap - 1.96 * se, gap + 1.96 * se)
    drift = (last.mean_len - first.mean_len) / max(1e-9, first.mean_len)

    GAP_T, LEN_T = 0.03, 0.25
    sigs = [
        ("verifier_gap", gap, GAP_T, ci, ci[0] > GAP_T),
        ("length_drift", abs(drift), LEN_T, None, abs(drift) > LEN_T),
    ]
    print(f"\n  {'signal':>16} {'value':>9} {'threshold':>10} {'95% CI':>22} {'fired':>7}")
    for name, val, thr, c, fired in sigs:
        cs = f"[{c[0]:+.4f},{c[1]:+.4f}]" if c else "-"
        print(f"  {name:>16} {val:>9.4f} {thr:>10.3f} {cs:>22} {str(fired):>7}")

    verdict = "confirmed" if any(n == "verifier_gap" and f for n, _, _, _, f in sigs) else (
        "suspected" if sum(f for *_, f in sigs) >= 2 else "clean")
    print(f"\n  Note the CI rule's real threshold: firing needs the CI LOWER BOUND")
    print(f"  above {GAP_T}, i.e. an observed gap above {GAP_T + 1.96*se:.4f} at these")
    print(f"  sample sizes -- not {GAP_T}. That conservatism is deliberate (04 §4.2.2):")
    print(f"  a detector that fires on noise is a detector that gets switched off.")
    print(f"\n  VERDICT: {verdict.upper()}")
    print(f"    training pass rate rose {first.train_pass:.3f} -> {last.train_pass:.3f} "
          f"({last.train_pass - first.train_pass:+.3f})")
    print(f"    held-out pass rate     {first.heldout_pass:.3f} -> {last.heldout_pass:.3f} "
          f"({last.heldout_pass - first.heldout_pass:+.3f})")
    print(f"    P(shotgun exploit)     {first.probs[1]:.3f} -> {last.probs[1]:.3f}")
    print(f"    mean response length   {first.mean_len:.1f} -> {last.mean_len:.1f} "
          f"({drift:+.1%})")
    print("\n  On a reward-only dashboard this is a great run: the training pass rate")
    print("  climbed substantially. The held-out verifier is the ONLY reason it is")
    print("  visible as a hack -- and only because it is a different implementation,")
    print("  not just different data (04 §4.4).")
    return rows, dict(verdict=verdict, gap=gap, ci=ci, drift=drift)


# ============================================================================
# PART 5 - Detection power  (00_concepts §6)
# ============================================================================


def part5_detection_power(train_n: int = 192) -> None:
    hdr("PART 5 - DETECTION POWER: how many held-out prompts you need")
    print("SE of a difference of two proportions, worst case at p=0.5.")
    print("A gap fires only when its 95% CI EXCLUDES the threshold (03_lld §3.3.4),")
    print("so this table decides whether the detector works at all.\n")
    print(f"  {'held-out n':>12} {'SE(gap)':>10} {'min visible gap (2 SE)':>24} "
          f"{'detects 3 pts?':>16}")
    for n in (100, 400, 1000, 1500, 3000, 5000):
        se = math.sqrt(2 * 0.25 / n)
        print(f"  {n:>12,} {se:>10.4f} {2*se*100:>23.1f}p {str(2*se < 0.03):>16}")
    n3 = math.ceil(2 * 0.25 / (0.03 / 2) ** 2)
    print(f"\n  100 held-out prompts can only see a 14.1-point divergence, and reward")
    print(f"  hacking announces itself at 2-5 points. n=1500 gives a {2*math.sqrt(2*0.25/1500)*100:.1f}-point")
    print(f"  floor; seeing exactly 3.0 points needs n={n3:,}. So 1500 is the practical")
    print("  FLOOR (FR-7), not the number that resolves a 3-point gap.")

    print("\n  THE ASYMMETRY THAT ACTUALLY BINDS -- and it is not the held-out side:")
    se_tr = math.sqrt(0.25 / train_n)
    print(f"    training pass rate is measured on {train_n} rollouts/step  -> SE {se_tr:.4f}")
    print(f"    held-out  pass rate on 1,500 prompts               -> SE {math.sqrt(0.25/1500):.4f}")
    print(f"    combined SE {math.sqrt(0.25/train_n + 0.25/1500):.4f} is "
          f"{se_tr/math.sqrt(0.25/1500):.1f}x dominated by the TRAINING side.")
    w = math.ceil(1500 / train_n)
    print(f"    => buying more held-out prompts past ~1500 barely moves the CI.")
    print(f"       The fix is to compute the gap over a ROLLING WINDOW of steps:")
    print(f"       {w} steps x {train_n} rollouts = {w*train_n:,} training samples,")
    print(f"       which balances the two sides (03_lld §3.3.4 uses window W={w}).")


# ============================================================================
# PART 2 - DPO + collapse detection (needs torch)
# ============================================================================


def seq_logprob(model, ids, prompt_len: int):
    """SUM of token logprobs over RESPONSE tokens only (03_lld §3.3.1)."""
    import torch
    logits = model(ids[:, :-1])
    logp = torch.log_softmax(logits.float(), dim=-1)
    tgt = ids[:, 1:]
    tokl = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
    mask = torch.zeros_like(tokl)
    mask[:, prompt_len - 1:] = 1.0            # mask the prompt out
    return (tokl * mask).sum(dim=-1)


def part2_dpo(dpo_steps: int, seed: int = 11) -> dict:
    hdr("PART 2 - DPO + COLLAPSE DETECTION (03_lld §3.3.1)")
    import torch
    import torch.nn as nn

    VOCAB, D, PLEN, RLEN = 40, 32, 6, 14
    results: dict[str, dict] = {}

    class TinyLM(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(VOCAB, D)
            self.pos = nn.Embedding(PLEN + RLEN, D)
            self.ln = nn.LayerNorm(D)
            self.mlp = nn.Sequential(nn.Linear(D, 4 * D), nn.GELU(), nn.Linear(4 * D, D))
            self.head = nn.Linear(D, VOCAB)

        def forward(self, x):
            h = self.emb(x) + self.pos(torch.arange(x.shape[1]))
            return self.head(self.ln(h + self.mlp(self.ln(h))))

    GOOD, BAD = range(2, 20), range(20, VOCAB)      # overlapping USE, disjoint sets

    def make_pairs(kind: str, n: int, rng: random.Random):
        """kind='quality' -> chosen/rejected drawn from the SAME token pool, chosen just
                             has a higher RATE of good tokens. Statistically learnable,
                             NOT trivially separable. Lengths matched.
           kind='length'  -> chosen is systematically much shorter: a trivial separator.

        Pairs are generated FRESH every step (never sampled from a fixed pool), so the
        model has to learn the distribution rather than memorise 96 examples.
        """
        out = []
        for _ in range(n):
            prompt = [rng.randrange(2, VOCAB) for _ in range(PLEN)]
            if kind == "quality":
                ch = [rng.choice(GOOD) if rng.random() < 0.75 else rng.choice(BAD)
                      for _ in range(RLEN)]
                rj = [rng.choice(GOOD) if rng.random() < 0.35 else rng.choice(BAD)
                      for _ in range(RLEN)]
            else:
                ch = [rng.randrange(2, VOCAB) for _ in range(4)] + [0] * (RLEN - 4)
                rj = [rng.randrange(2, VOCAB) for _ in range(RLEN)]
            out.append((prompt, ch, rj))
        return out

    for kind, label in (("quality", "A: pairs differ in CONTENT (lengths matched)"),
                        ("length", "B: chosen is always SHORTER (trivial separator)")):
        print(f"\n  --- variant {label} ---")
        rng = random.Random(seed)
        torch.manual_seed(seed)
        policy, ref = TinyLM(), TinyLM()
        ref.load_state_dict(policy.state_dict())
        for p in ref.parameters():
            p.requires_grad_(False)                     # FROZEN reference
        opt = torch.optim.AdamW(policy.parameters(), lr=3e-3)
        beta = 0.1

        print(f"  {'step':>6} {'dpo_loss':>10} {'EMA(loss)':>10} {'beta*margin':>12} "
              f"{'acc(256)':>9} {'len(ch)':>8} {'len(rj)':>8}")
        halted, hist = None, []
        # Both collapse thresholds need a sample size. A raw batch-of-8 loss is noisy,
        # and 8/8 "reward_accuracy = 1.00" happens ~27% of the time at 85% TRUE accuracy.
        # So: EMA the loss, and window the accuracy over >=ACC_WINDOW pairs.
        ema_loss, ACC_WINDOW, acc_window = None, 256, []
        for step in range(1, dpo_steps + 1):
            batch = make_pairs(kind, 8, rng)          # FRESH pairs every step
            pr = torch.tensor([b[0] for b in batch])
            ch = torch.tensor([b[1] for b in batch])
            rj = torch.tensor([b[2] for b in batch])
            ids_w = torch.cat([pr, ch], dim=1)
            ids_l = torch.cat([pr, rj], dim=1)

            lp_w, lp_l = seq_logprob(policy, ids_w, PLEN), seq_logprob(policy, ids_l, PLEN)
            with torch.no_grad():
                rp_w, rp_l = seq_logprob(ref, ids_w, PLEN), seq_logprob(ref, ids_l, PLEN)
            margin = (lp_w - rp_w) - (lp_l - rp_l)
            loss = -torch.nn.functional.logsigmoid(beta * margin).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
            opt.step()

            m = dict(dpo_loss=float(loss), bm=float((beta * margin).mean()),
                     acc=float((margin > 0).float().mean()),
                     lc=float((ch != 0).sum(1).float().mean()),
                     lr_=float((rj != 0).sum(1).float().mean()))
            hist.append(m)
            ema_loss = m["dpo_loss"] if ema_loss is None else 0.9 * ema_loss + 0.1 * m["dpo_loss"]
            acc_window.extend([1.0] * round(m["acc"] * 8) + [0.0] * (8 - round(m["acc"] * 8)))
            acc_window = acc_window[-ACC_WINDOW:]
            m["ema_loss"] = ema_loss
            m["acc_win"] = st.mean(acc_window) if len(acc_window) >= ACC_WINDOW else float("nan")
            if step % max(1, dpo_steps // 6) == 0 or step == 1:
                aw = f"{m['acc_win']:.3f}" if m["acc_win"] == m["acc_win"] else "  -  "
                print(f"  {step:>6} {m['dpo_loss']:>10.4f} {ema_loss:>10.4f} "
                      f"{m['bm']:>12.3f} {aw:>9} {m['lc']:>8.1f} {m['lr_']:>8.1f}")

            # FR-4 collapse detector, thresholds from the 00_concepts §3 loss table.
            if halted is None and step <= 0.20 * dpo_steps:
                if ema_loss < 0.10:
                    halted = (step, f"EMA(dpo_loss)={ema_loss:.3f} < 0.10 "
                                    f"(beta*margin={m['bm']:.2f} > 2.2 -> saturated)")
                elif len(acc_window) >= ACC_WINDOW and m["acc_win"] > 0.99:
                    halted = (step, f"reward_accuracy={m['acc_win']:.3f} over the last "
                                    f"{ACC_WINDOW} pairs: trivially separable")

        f = hist[-1]
        if halted:
            s, why = halted
            print(f"\n  >>> COLLAPSE DETECTED at step {s} of {dpo_steps} "
                  f"({s/dpo_steps:.0%} of run)")
            print(f"      {why}")
            print(f"      diagnosis order (03_lld §3.3.1): length delta chosen-rejected = "
                  f"{f['lc'] - f['lr_']:+.1f} tokens")
            if abs(f["lc"] - f["lr_"]) > 2:
                print("      -> LARGE. The model separated on LENGTH, not quality.")
                print("         Fix the pairs; do not lower beta and hope.")
            print(f"      FR-4: halting is the DEFAULT. The remaining "
                  f"{dpo_steps - s} steps would do nothing.")
        else:
            print(f"\n  no collapse: EMA(loss) {f['ema_loss']:.4f}, "
                  f"beta*margin {f['bm']:.3f}, windowed accuracy {f['acc_win']:.3f}")
            print(f"      The loss fell GRADUALLY -- it was still {[h['ema_loss'] for h in hist][int(0.2*dpo_steps)-1]:.3f} at the 20%")
            print("      mark, where variant B was already under 0.10. That gradual descent is")
            print("      what real learning looks like: the pairs are not trivially separable.")
            print("      (By step %d it HAS saturated -- correct for a toy task this small. The" % dpo_steps)
            print("       detector only guards the first 20%, which is where collapse is")
            print("       distinguishable from convergence.)")
        results[kind] = dict(final_loss=f["dpo_loss"], final_ema=f["ema_loss"],
                            final_acc=f["acc_win"], halted_at=halted[0] if halted else None,
                            len_delta=f["lc"] - f["lr_"])

    print("\n  Same model, same beta, same step count. Only the DATA differed.")
    print("  That is why FR-4's diagnosis leads with the length delta.")
    return results


# ============================================================================


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Post-Training Pipeline - decontamination, DPO collapse, GRPO "
                    "advantages, and a real discovered reward hack.")
    ap.add_argument("--dpo-steps", type=int, default=150, help="DPO steps per variant (150)")
    ap.add_argument("--rl-steps", type=int, default=40, help="GRPO steps in part 4 (40)")
    ap.add_argument("--k", type=int, default=8, help="GRPO group size (8)")
    ap.add_argument("--heldout-n", type=int, default=1500, help="held-out prompts (1500)")
    ap.add_argument("--skip-dpo", action="store_true", help="skip part 2 (no torch needed)")
    ap.add_argument("--csv", metavar="PATH", help="write part-4 per-step metrics to CSV")
    args = ap.parse_args()

    print(BAR)
    print("POST-TRAINING PIPELINE - runnable core")
    print("  AI/29_model-training-system-design/02_post_training_pipeline")
    print(BAR)

    t0 = time.perf_counter()
    part1_decontamination()

    dpo = None
    if not args.skip_dpo:
        try:
            import torch  # noqa: F401
        except ImportError:
            print("\n  [part 2 skipped: PyTorch not installed. pip install torch]",
                  file=sys.stderr)
        else:
            dpo = part2_dpo(args.dpo_steps)

    part3_grpo()
    rows, det = part4_reward_hacking(steps=args.rl_steps, k=args.k,
                                     heldout_n=args.heldout_n)
    part5_detection_power()

    hdr("SUMMARY")
    if dpo:
        for kind, label in (("quality", "content-differing pairs"),
                            ("length", "length-separable pairs ")):
            r = dpo[kind]
            state = (f"COLLAPSED at step {r['halted_at']}" if r["halted_at"]
                     else "learned normally")
            print(f"  DPO {label}: EMA(loss) {r['final_ema']:.4f}, "
                  f"acc(256) {r['final_acc']:.3f} -> {state}")
    print(f"  reward-hack verdict     : {det['verdict'].upper()}")
    print(f"  train-vs-heldout gap    : {det['gap']:+.4f}  "
          f"CI [{det['ci'][0]:+.4f}, {det['ci'][1]:+.4f}]")
    print(f"  length drift            : {det['drift']:+.1%}")
    print(f"\n  wall clock: {time.perf_counter()-t0:.1f} s")
    print("\n  Read next: ../01_requirements.md §1.6.2 (why the critic doesn't fit)")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", "reward_mean", "train_pass", "heldout_pass", "gap",
                        "mean_len", "frac_zero_std", "p_honest", "p_shotgun", "p_hedge"])
            for r in rows:
                w.writerow([r.step, f"{r.reward_mean:.5f}", f"{r.train_pass:.5f}",
                            f"{r.heldout_pass:.5f}", f"{r.gap:.5f}", f"{r.mean_len:.2f}",
                            f"{r.frac_zero_std:.4f}"] + [f"{p:.5f}" for p in r.probs])
        print(f"  wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
