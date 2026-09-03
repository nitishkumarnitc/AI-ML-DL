#!/usr/bin/env python3
"""
Distributed Training Platform - runnable core.

The tool a training-infra engineer actually writes before requesting a cluster:

  1. Params + FLOPs      the arithmetic, VALIDATED against a real nn.Module
                                                        (03_lld.md §3.3.1)
  2. Memory model        the 16N rule + activation arithmetic, with activation
                         bytes MEASURED via saved_tensors_hooks and real
                         recompute timing                (00_concepts.md §3)
  3. Parallelism planner enumerate (TP,PP,DP,micro_bs,m,recompute), reject with
                         reasons, rank survivors         (03_lld.md §3.3.1)
  4. MFU budget          six multiplicative factors, the required-MFU inversion,
                         and the double-count trap       (03_lld.md §3.3.2)
  5. Fault economics     checkpoint cadence, retention, and the $5,400 timeout
                                                        (01_requirements.md §1.6.4-5)

    pip install torch
    python run.py                      # ~3 s on CPU
    python run.py --gpus 1024 --days 20
    python run.py --model 8b
    python run.py --no-measure         # skip the torch parts, pure arithmetic, <1 s
    python run.py --csv plans.csv
    python run.py --help

Every number is computed here. Change --gpus or --days and watch which plans
stop being feasible.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from dataclasses import dataclass, field

BAR = "=" * 78

# ---- Hardware assumptions (00_requirements_all_systems.md §A) ---------------
PEAK_BF16 = 989e12          # H100 SXM BF16 DENSE. Not the 1979 sparse figure.
PEAK_FP8 = 1979e12
BW_NVLINK = 400e9           # EFFECTIVE ring bus. Spec is 900 GB/s bidirectional.
BW_IB = 50e9                # InfiniBand NDR 400 Gb/s
NVLINK_DOMAIN = 8           # H100 node. THE number that shapes the whole design.
HBM_GB = 80.0
GPU_HOUR_USD = 3.00
OBJ_GB_MONTH_USD = 0.023
BW_OBJ_PER_NODE = 2e9
MTBF_GPU_H = 50_000

KERNEL_EFF = 0.62           # the largest and least certain MFU factor (A4)


def hdr(t: str) -> None:
    print(f"\n{BAR}\n{t}\n{BAR}")


@dataclass
class ModelCfg:
    name: str
    n_layers: int
    d_model: int
    n_q_heads: int
    n_kv_heads: int
    head_dim: int
    d_ff: int
    vocab: int
    seq: int

    def __post_init__(self):
        assert self.n_q_heads % self.n_kv_heads == 0, "GQA: q heads must divide by kv heads"
        assert self.n_q_heads * self.head_dim == self.d_model, "d_model must equal n_q*head_dim"


MODELS = {
    "70b": ModelCfg("70B dense", 80, 8192, 64, 8, 128, 28672, 128256, 4096),
    "8b": ModelCfg("8B dense", 32, 4096, 32, 8, 128, 14336, 128256, 4096),
    "1b": ModelCfg("1B dense", 16, 2048, 16, 8, 128, 5632, 128256, 4096),
}


# ============================================================================
# PART 1 - parameters and FLOPs, validated against a real module
# ============================================================================


def param_count(c: ModelCfg) -> dict:
    attn = (c.d_model * c.n_q_heads * c.head_dim              # Wq
            + 2 * c.d_model * c.n_kv_heads * c.head_dim       # Wk, Wv
            + c.n_q_heads * c.head_dim * c.d_model)           # Wo
    mlp = 3 * c.d_model * c.d_ff                              # SwiGLU: gate, up, down
    emb = 2 * c.vocab * c.d_model                             # input + output
    return dict(attn_per_layer=attn, mlp_per_layer=mlp, per_layer=attn + mlp,
                embeddings=emb, total=(attn + mlp) * c.n_layers + emb)


def part1_params(c: ModelCfg, measure: bool) -> dict:
    hdr(f"PART 1 - PARAMETERS AND FLOPs ({c.name})")
    p = param_count(c)
    print(f"  L={c.n_layers} h={c.d_model} q/kv heads={c.n_q_heads}/{c.n_kv_heads} "
          f"d_h={c.head_dim} d_ff={c.d_ff} V={c.vocab:,} s={c.seq}\n")
    print(f"  {'attention per layer':>26} {p['attn_per_layer']/1e6:>10.1f} M")
    print(f"  {'MLP (SwiGLU) per layer':>26} {p['mlp_per_layer']/1e6:>10.1f} M   "
          f"<- {p['mlp_per_layer']/p['per_layer']:.0%} of a layer")
    print(f"  {'per layer':>26} {p['per_layer']/1e6:>10.1f} M")
    print(f"  {'x n_layers':>26} {p['per_layer']*c.n_layers/1e9:>10.2f} B")
    print(f"  {'embeddings (in+out)':>26} {p['embeddings']/1e9:>10.2f} B")
    print(f"  {'TOTAL N':>26} {p['total']/1e9:>10.2f} B")
    approx = 12 * c.n_layers * c.d_model ** 2
    print(f"\n  the 12*L*h^2 shortcut gives {approx/1e9:.2f} B "
          f"({approx/p['total']-1:+.1%}) -- fine for FLOPs, NOT for memory")
    print(f"  MLP is {p['mlp_per_layer']*c.n_layers/p['total']:.0%} of all parameters:")
    print("    -> where FP8 pays off most, AND where 59% of activation memory lives")

    if measure:
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            print("\n  [validation skipped: no torch]")
        else:
            # Build a SCALED-DOWN model with the same structure and check the formula
            # against a real parameter count. Validates the formula, not a guess.
            small = ModelCfg("validation", 2, 256, 4, 2, 64, 896, 1024, 128)

            class Layer(nn.Module):
                def __init__(s, m):
                    super().__init__()
                    s.wq = nn.Linear(m.d_model, m.n_q_heads * m.head_dim, bias=False)
                    s.wk = nn.Linear(m.d_model, m.n_kv_heads * m.head_dim, bias=False)
                    s.wv = nn.Linear(m.d_model, m.n_kv_heads * m.head_dim, bias=False)
                    s.wo = nn.Linear(m.n_q_heads * m.head_dim, m.d_model, bias=False)
                    s.gate = nn.Linear(m.d_model, m.d_ff, bias=False)
                    s.up = nn.Linear(m.d_model, m.d_ff, bias=False)
                    s.down = nn.Linear(m.d_ff, m.d_model, bias=False)

            mods = nn.ModuleList([Layer(small) for _ in range(small.n_layers)])
            emb_in = nn.Embedding(small.vocab, small.d_model)
            emb_out = nn.Linear(small.d_model, small.vocab, bias=False)
            real = sum(t.numel() for t in mods.parameters()) \
                + sum(t.numel() for t in emb_in.parameters()) \
                + sum(t.numel() for t in emb_out.parameters())
            pred = param_count(small)["total"]
            print(f"\n  FORMULA VALIDATION on a scaled-down real nn.Module:")
            print(f"    predicted {pred:,}   actual {real:,}   "
                  f"{'MATCH' if pred == real else 'MISMATCH'}")

    print(f"\n  FLOPs: C = 6*N*D    (fwd 2N + bwd 4N per token)")
    for D, label in ((20 * p["total"], "Chinchilla-optimal (D=20N)"), (1.4e12, "D=1.4T")):
        print(f"    {label:<28} D={D/1e12:>6.2f}T  ->  C = {6*p['total']*D:.3e} FLOPs")
    return p


# ============================================================================
# PART 2 - memory: the 16N rule, activations, and a REAL measurement
# ============================================================================


@dataclass
class Mem:
    state_gb: float
    act_gb: float
    workspace_gb: float
    @property
    def total_gb(self) -> float:
        return self.state_gb + self.act_gb + self.workspace_gb


def activation_bytes_per_layer(c: ModelCfg, micro_bs: int, policy: str) -> dict:
    """BF16, FlashAttention (no s^2 term). 00_concepts §3.2.

    Split into two classes, because TP and SP shard them differently:
      REPLICATED-unless-SP : the LayerNorm/dropout-region tensors (layer input,
                             LN1 out, LN2 out). TP leaves these on every rank;
                             sequence parallelism is what shards them.
      SHARDED-by-TP        : everything inside the parallelised GEMMs.
    """
    s_, b, h = c.seq, micro_bs, c.d_model
    t = s_ * b * h * 2                                  # one s x b x h BF16 tensor
    rep = 3 * t                                          # layer input, LN1 out, LN2 out
    shard_around = 3 * t                                 # attn out, Wo out, down out
    qkv = s_ * b * (c.n_q_heads + 2 * c.n_kv_heads) * c.head_dim * 2
    swiglu = 3 * s_ * b * c.d_ff * 2                     # gate, up, product

    table = {
        "none":      (rep, shard_around + qkv + swiglu),
        "selective": (rep, shard_around + qkv),          # drop the SwiGLU intermediates
        "full":      (t, 0),                             # layer input ONLY
    }
    rep_p, shard_p = table[policy]
    total = rep_p + shard_p
    all_total = rep + shard_around + qkv + swiglu
    return dict(around=rep + shard_around, qkv=qkv, swiglu=swiglu,
                total_none=all_total,
                total_selective=rep + shard_around + qkv,
                total_full=t,
                swiglu_share=swiglu / all_total,
                chosen=total, chosen_rep=rep_p, chosen_shard=shard_p)


def memory_model(c: ModelCfg, N: int, tp: int, pp: int, micro_bs: int,
                 policy: str, sequence_parallel: bool, workspace_gb: float = 6.0) -> Mem:
    state_gb = 16 * N / (tp * pp) / 1e9
    a = activation_bytes_per_layer(c, micro_bs, policy)
    rep = a["chosen_rep"] / tp if sequence_parallel else a["chosen_rep"]
    per_layer = a["chosen_shard"] / tp + rep
    layers_per_stage = c.n_layers / pp
    # 1F1B keeps up to pp micro-batches in flight in the earliest stage; with full
    # recompute only the boundary inputs are held, so far fewer.
    in_flight = 2 if policy == "full" else pp
    act_gb = per_layer * layers_per_stage * in_flight / 1e9
    return Mem(state_gb, act_gb, workspace_gb)


def part2_memory(c: ModelCfg, N: int, measure: bool) -> None:
    hdr("PART 2 - MEMORY: the two numbers that decide the design")
    print(f"  (a) the 16N rule -- model + optimizer state (BF16 + Adam)")
    for item, b in (("fp32 master weights", 4), ("Adam m (fp32)", 4), ("Adam v (fp32)", 4),
                    ("BF16 weights", 2), ("BF16 gradients", 2)):
        print(f"      {item:>22} {b:>3} bytes/param")
    print(f"      {'TOTAL':>22} {16:>3} bytes/param  ->  {16*N/1e9:>7.0f} GB "
          f"= {16*N/1e9/HBM_GB:.1f} x H100-80GB")
    print(f"      => plain DDP is IMPOSSIBLE. Sharding is the precondition.\n")

    print(f"  (b) activations -- ONE micro-batch, seq {c.seq}, BF16, FlashAttention")
    a = activation_bytes_per_layer(c, 1, "none")
    print(f"      {'around the layer (6 tensors)':>32} {a['around']/1e6:>8.1f} MB")
    print(f"      {'Q/K/V':>32} {a['qkv']/1e6:>8.1f} MB")
    print(f"      {'SwiGLU gate+up+product':>32} {a['swiglu']/1e6:>8.1f} MB   "
          f"<- {a['swiglu_share']:.0%} of the total")
    print(f"      {'per layer':>32} {a['total_none']/1e6:>8.1f} MB")
    print(f"      {f'x {c.n_layers} layers':>32} {a['total_none']*c.n_layers/1e9:>8.1f} GB")
    if a["total_none"] * c.n_layers / 1e9 > HBM_GB:
        m88 = memory_model(c, N, 8, 8, 1, "none", True)
        print(f"      => on ONE un-sharded GPU this does NOT fit in {HBM_GB:.0f} GB even")
        print(f"         with ZERO weights loaded.\n")
        print(f"      BUT: TP shards most of it and PP splits the layers. At TP=8/PP=8/SP")
        print(f"      the same activations land at {m88.act_gb:.1f} GB/GPU")
        print(f"      (see part 3). So recompute is NOT what makes the run possible here --")
        print(f"      it is the LEVER that buys micro_bs > 1 (kernel efficiency) or a")
        print(f"      longer sequence. That distinction matters: the 95 GB figure is the")
        print(f"      reason you must shard, not the reason you must recompute.\n")
    print(f"      {'policy':>12} {'per layer':>12} {'un-sharded':>12} "
          f"{'TP8/PP8/SP':>12} {'extra compute':>14}")
    for pol, key, extra in (("none", "total_none", "0%"), ("selective", "total_selective", "~+8%"),
                            ("full", "total_full", "~+33%")):
        mm = memory_model(c, N, 8, 8, 1, pol, True)
        print(f"      {pol:>12} {a[key]/1e6:>9.1f} MB {a[key]*c.n_layers/1e9:>9.2f} GB "
              f"{mm.act_gb:>9.2f} GB {extra:>14}")

    rep = 3 * c.seq * 1 * c.d_model * 2 * c.n_layers
    print(f"\n  (c) sequence parallelism -- the free win")
    print(f"      LN/dropout regions TP leaves REPLICATED: {rep/1e9:.1f} GB on every TP rank")
    print(f"      with SP (sharded over TP={NVLINK_DOMAIN}):  {rep/1e9/NVLINK_DOMAIN:.1f} GB")
    print(f"      => {rep/1e9*(1-1/NVLINK_DOMAIN):.1f} GB/GPU recovered at ZERO collective cost")

    if not measure:
        return
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        print("\n  [measurement skipped: no torch]")
        return

    # ---- MEASURE activation bytes with saved_tensors_hooks ------------------
    print(f"\n  (d) MEASURED activation bytes vs the analytic model")
    print("      A real transformer layer, real forward pass; every tensor saved for")
    print("      backward is intercepted and its bytes summed (deduped by storage).")

    small = ModelCfg("measured", 1, 512, 8, 2, 64, 1792, 1024, 256)

    class RealLayer(nn.Module):
        def __init__(s, m):
            super().__init__()
            s.ln1 = nn.LayerNorm(m.d_model)
            s.wq = nn.Linear(m.d_model, m.n_q_heads * m.head_dim, bias=False)
            s.wk = nn.Linear(m.d_model, m.n_kv_heads * m.head_dim, bias=False)
            s.wv = nn.Linear(m.d_model, m.n_kv_heads * m.head_dim, bias=False)
            s.wo = nn.Linear(m.n_q_heads * m.head_dim, m.d_model, bias=False)
            s.ln2 = nn.LayerNorm(m.d_model)
            s.gate = nn.Linear(m.d_model, m.d_ff, bias=False)
            s.up = nn.Linear(m.d_model, m.d_ff, bias=False)
            s.down = nn.Linear(m.d_ff, m.d_model, bias=False)
            s.cfg = m

        def forward(s, x):
            m = s.cfg
            hh = s.ln1(x)
            q = s.wq(hh).view(x.shape[0], x.shape[1], m.n_q_heads, m.head_dim).transpose(1, 2)
            k = s.wk(hh).view(x.shape[0], x.shape[1], m.n_kv_heads, m.head_dim).transpose(1, 2)
            v = s.wv(hh).view(x.shape[0], x.shape[1], m.n_kv_heads, m.head_dim).transpose(1, 2)
            k = k.repeat_interleave(m.n_q_heads // m.n_kv_heads, dim=1)
            v = v.repeat_interleave(m.n_q_heads // m.n_kv_heads, dim=1)
            # scaled_dot_product_attention uses a memory-efficient kernel: no s x s matrix
            att = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
            att = att.transpose(1, 2).reshape(x.shape[0], x.shape[1], m.d_model)
            x = x + s.wo(att)
            hh = s.ln2(x)
            return x + s.down(torch.nn.functional.silu(s.gate(hh)) * s.up(hh))

    layer = RealLayer(small)
    x = torch.randn(1, small.seq, small.d_model, requires_grad=True)

    seen, total_bytes = set(), 0

    def pack(t):
        nonlocal total_bytes
        try:
            key = (t.untyped_storage().data_ptr(), t.untyped_storage().nbytes())
        except Exception:
            key = (id(t), t.nbytes)
        if key not in seen:
            seen.add(key)
            total_bytes += key[1]
        return t

    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        out = layer(x)
        out.sum().backward()

    pred = activation_bytes_per_layer(small, 1, "none")["total_none"]
    # The measurement is fp32 (CPU default); the analytic model assumes BF16.
    print(f"      measured saved-for-backward bytes : {total_bytes/1e6:>8.2f} MB (fp32)")
    print(f"      analytic model, same config       : {pred/1e6:>8.2f} MB (BF16)")
    print(f"      analytic scaled to fp32 (x2)      : {2*pred/1e6:>8.2f} MB")
    print(f"      ratio measured/analytic-fp32      : {total_bytes/(2*pred):>8.2f}x")
    print("      The analytic model is a LOWER BOUND: it counts the tensors a hand-written")
    print("      fused implementation must keep. A stock nn.Linear/LayerNorm stack also")
    print("      saves normalisation statistics and some intermediates a fused kernel")
    print("      would not. That gap IS the value of fused kernels -- and it is why the")
    print("      design carries a >=6 GB safety margin instead of trusting the formula.")

    # ---- MEASURE the real cost of recompute --------------------------------
    from torch.utils.checkpoint import checkpoint

    def timed(fn, n=12):
        for _ in range(3):
            fn()
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - t0) / n

    stack = nn.ModuleList([RealLayer(small) for _ in range(4)])

    def plain():
        h = torch.randn(1, small.seq, small.d_model, requires_grad=True)
        for L in stack:
            h = L(h)
        h.sum().backward()

    def recomputed():
        h = torch.randn(1, small.seq, small.d_model, requires_grad=True)
        for L in stack:
            h = checkpoint(L, h, use_reentrant=False)
        h.sum().backward()

    t_plain, t_rc = timed(plain), timed(recomputed)
    print(f"\n      MEASURED recompute cost (4 real layers, fwd+bwd):")
    print(f"        no recompute   {t_plain*1e3:>7.2f} ms/iter")
    print(f"        full recompute {t_rc*1e3:>7.2f} ms/iter   -> {t_rc/t_plain-1:+.1%}")
    print(f"        (the design budgets ~+33% for FULL recompute; CPU ratios differ from")
    print(f"         GPU, but the SIGN and rough magnitude are what the budget needs)")


# ============================================================================
# PART 3 - the parallelism planner
# ============================================================================


@dataclass
class Plan:
    tp: int
    pp: int
    dp: int
    micro_bs: int
    m: int
    recompute: str
    fp8: bool
    mem: Mem
    step_s: float
    mfu: float
    bubble: float
    tp_comm_frac: float
    global_batch: int
    days: float
    meets: bool
    headroom_pts: float
    notes: list = field(default_factory=list)


def divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


def tp_comm_fraction(c: ModelCfg, N: int, tp: int, pp: int, micro_bs: int,
                     inter_node: bool, mfu: float | None = None) -> dict:
    """00_concepts §5.3.

    Reports THREE numbers, because they are different and confusing them is the
    same double-count trap as part 4:

      comm_ms      raw TP all-reduce time per micro-step per GPU
      compute_ms   pure MATMUL time (peak x KERNEL_EFF). comm/compute answers
                   "does communication dominate arithmetic?" -- the design question.
      wall_ms      per-micro-step WALL time at the achieved MFU. comm/wall is
                   smaller because MFU already contains the comm penalty, so
                   dividing by it is partly circular.
    """
    layers = c.n_layers / pp
    flops = 6 * (layers / c.n_layers * N) * c.seq * micro_bs / max(1, tp)
    compute_ms = flops / (PEAK_BF16 * KERNEL_EFF) * 1e3
    wall_ms = flops / (PEAK_BF16 * mfu) * 1e3 if mfu else None
    if tp == 1:
        return dict(comm_ms=0.0, compute_ms=compute_ms, wall_ms=wall_ms,
                    frac_compute=0.0, frac_wall=0.0)
    payload = c.seq * micro_bs * c.d_model * 2
    bus = 2 * (tp - 1) / tp * payload                     # ring all-reduce bus volume
    bw = BW_IB if inter_node else BW_NVLINK
    comm_ms = bus / bw * 4 * layers * 1e3                 # 4 all-reduces per layer
    return dict(comm_ms=comm_ms, compute_ms=compute_ms, wall_ms=wall_ms,
                frac_compute=comm_ms / compute_ms,
                frac_wall=(comm_ms / wall_ms) if wall_ms else None)


MFU_FACTORS = [
    ("kernel_efficiency", KERNEL_EFF, "matmul efficiency on real shapes incl. FlashAttention"),
    ("tp_comm_residual", 0.92, "TP all-reduce not hidden behind compute"),
    ("pp_bubble", 0.95, "interleaved 1F1B, m=128, v=2"),
    ("dp_comm_residual", 0.97, "reduce-scatter/all-gather overlapped with backward"),
    ("non_matmul", 0.92, "LayerNorm, softmax, elementwise, optimizer step"),
    ("stalls_stragglers", 0.95, "data stalls and straggler jitter"),
]


def budgeted_mfu() -> float:
    mfu = 1.0
    for _, f, _ in MFU_FACTORS:
        mfu *= f
    return mfu


def enumerate_plans(c: ModelCfg, N: int, world: int, tokens: float, days_slo: float,
                    *, margin_gb=6.0, gb_max=8 << 20, v_stages=2, top_k=5):
    C = 6 * N * tokens
    mfu_req = C / (world * PEAK_BF16 * days_slo * 86400)
    feasible, rejected = [], {}

    def reject(key, detail):
        rejected.setdefault(key, detail)

    for tp in divisors(world):
        if tp > NVLINK_DOMAIN:
            i = tp_comm_fraction(c, N, tp, 8, 1, False)
            o = tp_comm_fraction(c, N, tp, 8, 1, True)
            reject(("tp_exceeds_nvlink_domain", tp),
                   f"TP={tp} spans {tp/NVLINK_DOMAIN:.0f} nodes; TP comm would be "
                   f"{o['frac_compute']:.0%} of compute vs {i['frac_compute']:.0%} "
                   f"intra-node ({o['comm_ms']:.1f} ms vs {i['comm_ms']:.1f} ms "
                   f"against {i['compute_ms']:.1f} ms of matmul)")
            continue
        for pp in divisors(world // tp):
            dp = world // (tp * pp)
            # A stage must hold a whole number of layers.
            if c.n_layers % pp != 0:
                reject(("pp_layer_split", pp),
                       f"PP={pp} does not divide {c.n_layers} layers "
                       f"({c.n_layers/pp:.2f} layers/stage)")
                continue
            # DP=1 breaks two of this design's OWN requirements:
            #   FR-13 cross-DP-replica gradient-norm comparison (SDC screening)
            #   FR-14 elastic DP (nothing to fall back to on a node loss)
            if dp < 2:
                reject(("dp_too_narrow", tp, pp),
                       f"TP{tp}/PP{pp} leaves DP={dp}: FR-13 cross-replica SDC "
                       f"comparison and FR-14 elastic recovery both need DP >= 2")
                continue
            for micro_bs in (1, 2, 4, 8):
                for mult in (1, 2, 4, 8, 16):
                    m = mult * pp
                    if m < pp:
                        continue
                    gb = dp * m * micro_bs * c.seq
                    if gb > gb_max:
                        reject(("global_batch", tp, pp, dp, m, micro_bs),
                               f"TP{tp}/PP{pp}/DP{dp} m={m} mbs={micro_bs}: "
                               f"{gb/1e6:.1f}M tokens/step exceeds the cap -- raising the "
                               f"global batch CHANGES THE OPTIMIZATION")
                        continue
                    bubble = (pp - 1) / (v_stages * m) if pp > 1 else 0.0
                    if bubble > 0.08:
                        reject(("bubble", pp, m),
                               f"PP={pp} m={m}: {bubble:.1%} bubble; m >= 4*pp recommended")
                        continue
                    for pol in ("selective", "full", "none"):
                        mem = memory_model(c, N, tp, pp, micro_bs, pol,
                                           sequence_parallel=(tp > 1),
                                           workspace_gb=margin_gb)
                        if mem.total_gb > HBM_GB - margin_gb:
                            reject(("memory", tp, pp, micro_bs, pol),
                                   f"TP{tp}/PP{pp} mbs={micro_bs} {pol}: "
                                   f"{mem.total_gb:.1f} GB > {HBM_GB-margin_gb:.1f} GB "
                                   f"(state {mem.state_gb:.1f} + act {mem.act_gb:.1f})")
                            continue
                        cm = tp_comm_fraction(c, N, tp, pp, micro_bs, False)
                        frac = cm["frac_compute"]
                        extra = {"none": 1.0, "selective": 1.08, "full": 1.33}[pol]
                        mfu = budgeted_mfu() / extra
                        if pp > 1:
                            mfu *= (1 - bubble) / 0.95            # replace the budgeted bubble
                        for fp8 in (False, True):
                            eff_mfu = mfu * (1.33 if fp8 else 1.0)
                            days = C / (world * PEAK_BF16 * eff_mfu) / 86400
                            step_s = C / (world * PEAK_BF16 * eff_mfu) / (tokens / gb)
                            notes = []
                            if micro_bs == 1 and mem.total_gb < HBM_GB - margin_gb - 15:
                                notes.append("micro_bs could rise -- the cheapest MFU lever")
                            if dp <= 4:
                                notes.append(
                                    f"DP={dp} leaves only {dp-1} spare replica(s) for "
                                    f"elastic recovery -- thin operational headroom")
                            if pp >= 16:
                                notes.append(
                                    f"PP={pp} means {c.n_layers//pp} layers/stage; a single "
                                    f"stage fault stalls the whole pipeline")
                            if fp8:
                                notes.append("FP8 needs the FR-12 validation-loss gate")
                            feasible.append(Plan(tp, pp, dp, micro_bs, m, pol, fp8, mem,
                                                 step_s, eff_mfu, bubble, frac, gb, days,
                                                 days <= days_slo,
                                                 (eff_mfu - mfu_req) * 100, notes))
    # Rank by days, but treat plans within 3% as tied and prefer MEMORY HEADROOM --
    # spare HBM is what lets you raise micro_bs later, which is the free MFU lever.
    def key(p):
        return (not p.meets, round(p.days / 1.03), p.mem.total_gb)
    feasible.sort(key=key)
    return dict(C=C, mfu_required=mfu_req,
                plans=[p for p in feasible if not p.fp8],
                plans_fp8=[p for p in feasible if p.fp8],
                rejected=rejected)


def part3_planner(c: ModelCfg, N: int, world: int, tokens: float, days_slo: float) -> dict:
    hdr(f"PART 3 - PARALLELISM PLANNER ({world} GPUs, {days_slo:.0f}-day SLO)")
    res = enumerate_plans(c, N, world, tokens, days_slo)
    print(f"  C = 6ND = {res['C']:.3e} FLOPs")
    print(f"  MFU REQUIRED for the {days_slo:.0f}-day SLO = "
          f"{res['mfu_required']:.1%}   <-- the deadline is an MFU requirement")
    print(f"  MFU BUDGETED (six factors, part 4)          = {budgeted_mfu():.1%}")
    hp = (budgeted_mfu() - res["mfu_required"]) * 100
    print(f"  headroom = {hp:+.1f} points"
          f"{'   <-- THIN' if 0 < hp < 2 else ('   <-- DOES NOT CLOSE' if hp <= 0 else '')}")

    def table(plans, label):
        print(f"\n  {label}")
        if not plans:
            print("    (none feasible)")
            return
        print(f"  {'#':>2} {'TP':>3} {'PP':>3} {'DP':>4} {'mbs':>4} {'m':>5} {'recomp':>10} "
              f"{'GB/gpu':>7} {'MFU':>6} {'bub':>6} {'TPcomm':>7} {'days':>6} {'batch':>8}")
        for i, p in enumerate(plans[:6], 1):
            flag = "" if p.meets else "  MISSES"
            print(f"  {i:>2} {p.tp:>3} {p.pp:>3} {p.dp:>4} {p.micro_bs:>4} {p.m:>5} "
                  f"{p.recompute:>10} {p.mem.total_gb:>7.1f} {p.mfu:>6.1%} "
                  f"{p.bubble:>6.1%} {p.tp_comm_frac:>7.1%} {p.days:>6.1f} "
                  f"{p.global_batch/1e6:>7.2f}M{flag}")

    table(res["plans"], "BF16 plans (ranked by days, ties broken on memory headroom):")
    table(res["plans_fp8"], "FP8-on-MLP plans -- REQUIRE the FR-12 validation-loss gate:")

    if len(res["plans"]) > 1:
        top = res["plans"][:6]
        spread = max(q.days for q in top) / min(q.days for q in top) - 1
        print(f"\n  NOTE: these six plans span only {spread:.1%} in days but "
              f"{min(q.mem.total_gb for q in top):.0f}-"
              f"{max(q.mem.total_gb for q in top):.0f} GB/GPU and "
              f"DP={min(q.dp for q in top)}-{max(q.dp for q in top)}.")
        print("  So the choice among them is NOT about throughput -- it is about")
        print("  operational headroom: spare HBM (to raise micro_bs later) and spare DP")
        print("  replicas (for elastic recovery and cross-replica SDC screening).")
        print("  The design doc picks TP8/PP8/DP8 for that reason, not for its step time.")

    if res["plans"]:
        b = res["plans"][0]
        cm = tp_comm_fraction(c, N, b.tp, b.pp, b.micro_bs, False, mfu=b.mfu)
        cmo = tp_comm_fraction(c, N, b.tp, b.pp, b.micro_bs, True, mfu=b.mfu)
        print(f"\n  best BF16 plan: TP{b.tp}/PP{b.pp}/DP{b.dp}, mbs={b.micro_bs}, m={b.m}, "
              f"{b.recompute} recompute, SP={b.tp>1}")
        print(f"    memory: state {b.mem.state_gb:.1f} + activations {b.mem.act_gb:.1f} "
              f"+ workspace {b.mem.workspace_gb:.1f} = {b.mem.total_gb:.1f} GB / {HBM_GB:.0f}")
        print(f"    TP comm per micro-step: {cm['comm_ms']:.1f} ms")
        print(f"      vs pure matmul time {cm['compute_ms']:.1f} ms -> "
              f"{cm['frac_compute']:.1%} OF COMPUTE   <- the design question")
        print(f"      vs wall time        {cm['wall_ms']:.1f} ms -> "
              f"{cm['frac_wall']:.1%} of wall time (MFU already contains the penalty)")
        print(f"    same plan with TP crossing a node boundary: {cmo['comm_ms']:.1f} ms "
              f"= {cmo['frac_compute']:.0%} of compute")
        print(f"      => comm EXCEEDS arithmetic; it cannot be hidden. This is the "
              f"{cmo['comm_ms']/cm['comm_ms']:.0f}x cliff at the NVLink boundary.")
        print(f"    bubble {b.bubble:.1%} · global batch {b.global_batch/1e6:.2f}M tokens "
              f"· {b.days:.1f} days")
        for n in b.notes:
            print(f"    note: {n}")

    print(f"\n  REJECTED, with reasons (this is the useful half):")
    order = {"tp_exceeds_nvlink_domain": 0, "memory": 1, "bubble": 2, "global_batch": 3}
    shown = sorted(res["rejected"].items(), key=lambda kv: order.get(kv[0][0], 9))
    seen_kind = set()
    for key, detail in shown:
        if key[0] in seen_kind and len([k for k in seen_kind if k == key[0]]) >= 1:
            continue
        seen_kind.add(key[0])
        print(f"    [{key[0]}] {detail}")
    print(f"    ({len(res['rejected'])} distinct rejections total; one example per kind shown)")
    return res


# ============================================================================
# PART 4 - the MFU budget and the double-count trap
# ============================================================================


def part4_mfu(c: ModelCfg, N: int, world: int, tokens: float, days_slo: float,
              plan: Plan | None) -> None:
    hdr("PART 4 - THE MFU BUDGET (03_lld §3.3.2)")
    print("  MFU is MULTIPLICATIVE: every inefficiency is a factor, not a subtraction.\n")
    print(f"  {'factor':>22} {'x':>6} {'running':>9}   what it is")
    mfu = 1.0
    print(f"  {'peak BF16 dense':>22} {'--':>6} {1.0:>8.1%}   "
          f"{PEAK_BF16/1e12:.0f} TFLOP/s (NOT the 1979 sparse figure)")
    for name, f, desc in MFU_FACTORS:
        mfu *= f
        print(f"  {name:>22} {f:>6.2f} {mfu:>8.1%}   {desc}")
    C = 6 * N * tokens
    req = C / (world * PEAK_BF16 * days_slo * 86400)
    print(f"\n  BUDGETED MFU              = {mfu:.1%}")
    print(f"  REQUIRED for {days_slo:.0f} days   = {req:.1%}")
    print(f"  headroom                  = {(mfu-req)*100:+.1f} points")
    if 0 < (mfu - req) * 100 < 2:
        print("  => THIN. Any single factor 2% worse than budgeted misses the deadline.")
        print("     That is why FP8 is treated as the PLANNED MARGIN, not an optimization.")

    print(f"\n  days to train at various MFU (the last row is FP8's EFFECTIVE rate")
    print(f"  measured against the BF16 peak -- not a real BF16 MFU):")
    for m in (0.35, 0.38, 0.40, 0.43, mfu, mfu * 1.33):
        d = C / (world * PEAK_BF16 * m) / 86400
        tag = ""
        if abs(m - mfu) < 1e-9:
            tag = "  <- budgeted"
        elif abs(m - mfu * 1.33) < 1e-9:
            tag = "  <- FP8 effective (vs BF16 peak; needs the FR-12 gate)"
        elif 0.38 <= m <= 0.43:
            tag = "  <- published-practice range"
        print(f"    MFU {m:>6.1%}  ->  {d:>5.1f} days  "
              f"{'OK ' if d <= days_slo else 'MISS'}{tag}")

    print(f"\n  THE DOUBLE-COUNT TRAP (00_concepts §6.1):")
    if plan:
        cm = tp_comm_fraction(c, N, plan.tp, plan.pp, plan.micro_bs, False, mfu=plan.mfu)
        micro_s = cm["wall_ms"] / 1e3
        step_ok = plan.m * micro_s
        step_bad = step_ok * (1 + plan.bubble)
        steps = tokens / plan.global_batch
        print(f"    (a) FLOP model:  C/(G*PEAK*MFU)              = "
              f"{C/(world*PEAK_BF16*plan.mfu)/86400:>5.2f} days")
        print(f"    (b) step model:  {plan.m} x {micro_s*1e3:.1f} ms x {steps:,.0f} steps "
              f"= {steps*step_ok/86400:>5.2f} days   agrees")
        print(f"    (c) step model x (1+bubble) AS WELL          = "
              f"{steps*step_bad/86400:>5.2f} days   WRONG "
              f"({steps*step_bad/(steps*step_ok)-1:+.1%})")
        print("    MFU already contains the bubble and the comm residual. The error is")
        print("    small enough to look plausible, which is what makes it dangerous.")

    print(f"\n  What the budget is FOR -- diagnosing a shortfall:")
    measured = {"kernel_efficiency": 0.58, "tp_comm_residual": 0.91, "pp_bubble": 0.95,
                "dp_comm_residual": 0.96, "non_matmul": 0.91, "stalls_stragglers": 0.84}
    rows = [(n, b, measured[n], measured[n] / b, d) for n, b, d in MFU_FACTORS]
    rows.sort(key=lambda r: r[3])
    got = 1.0
    for _, _, mv, _, _ in rows:
        got *= mv
    print(f"    (example) measured MFU {got:.1%} vs budgeted {mfu:.1%}")
    print(f"    {'factor':>22} {'budget':>8} {'measured':>9} {'ratio':>7}")
    for n, b, mv, r, d in rows:
        mark = "  <- PROFILE THIS FIRST" if r == rows[0][3] else ""
        print(f"    {n:>22} {b:>8.2f} {mv:>9.2f} {r:>7.2f}{mark}")
    print("    'MFU is 38%' is not actionable. 'stalls_stragglers is 0.88x its budget' is.")


# ============================================================================
# PART 5 - checkpoint and fault economics
# ============================================================================


def part5_faults(N: int, world: int, days: float, cadence_min: float = 30.0) -> None:
    hdr(f"PART 5 - CHECKPOINT AND FAULT ECONOMICS ({days:.1f}-day projected run)")
    ck_gb = 16 * N / 1e9
    nodes = max(1, world // NVLINK_DOMAIN)
    print(f"  checkpoint size = 16N = {ck_gb:,.0f} GB\n")
    sync_s = ck_gb / (nodes * BW_OBJ_PER_NODE / 1e9)
    async_s = (ck_gb / world) / 20.0
    print(f"  {'strategy':>34} {'blocking':>10} {'overhead @ %.0f min':>20}" % cadence_min)
    for label, secs in (("sharded SYNCHRONOUS", sync_s), ("sharded ASYNC (D2H then upload)", async_s)):
        print(f"  {label:>34} {secs:>9.2f}s {secs/(cadence_min*60):>19.3%}")
    print(f"  => async is {sync_s/async_s:.0f}x better, for the cost of a background thread")

    n_ck = int(days * 24 * 60 / cadence_min)
    keep_all_pb = n_ck * ck_gb / 1e6
    keep_all_usd = n_ck * ck_gb * OBJ_GB_MONTH_USD
    compute_usd = world * days * 24 * GPU_HOUR_USD
    kept = 3 + int(days) + 2
    print(f"\n  retention over {days:.0f} days at a {cadence_min:.0f}-min cadence:")
    print(f"    keep EVERYTHING: {n_ck:,} ckpts = {keep_all_pb:.2f} PB = "
          f"${keep_all_usd/1e3:.1f}k/month")
    print(f"      that is {keep_all_usd/compute_usd:.1%} OF THE ENTIRE COMPUTE BUDGET "
          f"(${compute_usd/1e6:.2f}M), in storage")
    print(f"    policy (3 recent + 1/day + 2 milestones): {kept} ckpts = "
          f"{kept*ck_gb/1e3:.1f} TB = ${kept*ck_gb*OBJ_GB_MONTH_USD:,.0f}/month")
    print("    => retention is a DESIGN REQUIREMENT (FR-9), not housekeeping")

    cluster_mtbf = MTBF_GPU_H / world
    run_h = days * 24
    n_fail = run_h / cluster_mtbf
    print(f"\n  faults (per-GPU MTBF assumption {MTBF_GPU_H:,} h):")
    print(f"    cluster MTBF = {MTBF_GPU_H:,}/{world} = {cluster_mtbf:.1f} h "
          f"= {cluster_mtbf/24:.1f} days")
    print(f"    expected interruptions over a {run_h:.0f} h run = {n_fail:.1f}")
    print(f"\n  {'detection mechanism':>36} {'min/fail':>9} {'h lost':>8} {'% run':>7} {'$ idle':>10}")
    costs = {}
    for label, det in (("NCCL default watchdog (~30 min)", 30), ("60-s heartbeat health check", 1)):
        per = det + 3 + 1 + cadence_min / 2
        lost = n_fail * per / 60
        usd = lost * world * GPU_HOUR_USD
        costs[label] = usd
        print(f"  {label:>36} {per:>9.0f} {lost:>8.1f} {lost/run_h:>7.2%} ${usd:>9,.0f}")
    d = max(costs.values()) - min(costs.values())
    print(f"\n  => ~${d:,.0f} per flagship run, from ONE config value, at zero")
    print("     engineering cost. Almost everyone leaves it at the default.")
    print("     And keep the heartbeat IN ADDITION to the watchdog: an NCCL hang")
    print("     may never time out at all, and then the heartbeat is the only signal.")


# ============================================================================


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Distributed training platform - planner, memory model, MFU budget, "
                    "fault economics.")
    ap.add_argument("--model", choices=sorted(MODELS), default="70b")
    ap.add_argument("--gpus", type=int, default=512)
    ap.add_argument("--tokens", type=float, default=1.4e12)
    ap.add_argument("--days", type=float, default=30.0, help="deadline SLO in days")
    ap.add_argument("--cadence-min", type=float, default=30.0, help="checkpoint cadence")
    ap.add_argument("--no-measure", action="store_true",
                    help="skip the torch measurements (pure arithmetic)")
    ap.add_argument("--csv", metavar="PATH", help="write all feasible plans to CSV")
    args = ap.parse_args()

    c = MODELS[args.model]
    print(BAR)
    print("DISTRIBUTED TRAINING PLATFORM - runnable core")
    print("  AI/29_model-training-system-design/03_distributed_training_platform")
    print(BAR)
    print(f"  model={c.name}  gpus={args.gpus}  tokens={args.tokens/1e12:.2f}T  "
          f"deadline={args.days:.0f}d")

    t0 = time.perf_counter()
    measure = not args.no_measure
    p = part1_params(c, measure)
    N = p["total"]
    part2_memory(c, N, measure)
    res = part3_planner(c, N, args.gpus, args.tokens, args.days)
    part4_mfu(c, N, args.gpus, args.tokens, args.days,
              res["plans"][0] if res["plans"] else None)
    # Fault economics use the PROJECTED duration, not the SLO -- a run that finishes
    # in 29.5 days is exposed to 29.5 days of fault risk, not 30.
    proj_days = res["plans"][0].days if res["plans"] else args.days
    part5_faults(N, args.gpus, proj_days, args.cadence_min)

    hdr("SUMMARY")
    print(f"  N = {N/1e9:.2f} B · C = {6*N*args.tokens:.3e} FLOPs")
    print(f"  16N state = {16*N/1e9:,.0f} GB = {16*N/1e9/HBM_GB:.1f} x H100")
    a = activation_bytes_per_layer(c, 1, "none")
    print(f"  activations (1 micro-batch, no recompute) = "
          f"{a['total_none']*c.n_layers/1e9:.1f} GB  "
          f"(SwiGLU = {a['swiglu_share']:.0%})")
    print(f"  MFU required {res['mfu_required']:.1%} · budgeted {budgeted_mfu():.1%} · "
          f"headroom {(budgeted_mfu()-res['mfu_required'])*100:+.1f} pts")
    if res["plans"]:
        b = res["plans"][0]
        print(f"  best BF16 plan: TP{b.tp}/PP{b.pp}/DP{b.dp} mbs={b.micro_bs} m={b.m} "
              f"{b.recompute} -> {b.days:.1f} days, {b.mem.total_gb:.1f} GB/GPU"
              f"{'' if b.meets else '  (MISSES the deadline)'}")
    if res["plans_fp8"]:
        f = res["plans_fp8"][0]
        print(f"  best FP8 plan : TP{f.tp}/PP{f.pp}/DP{f.dp} mbs={f.micro_bs} m={f.m} "
              f"{f.recompute} -> {f.days:.1f} days  (needs the FR-12 loss gate)")
    if not res["plans"] and not res["plans_fp8"]:
        print("  NO FEASIBLE PLAN -- see the rejections in part 3")
    print(f"  cost: {args.gpus*args.days*24:,.0f} GPU-hr = "
          f"${args.gpus*args.days*24*GPU_HOUR_USD/1e6:.2f}M on-demand")
    print(f"\n  wall clock: {time.perf_counter()-t0:.1f} s")
    print("\n  Try:  python run.py --gpus 256   (watch the deadline stop closing)")
    print("        python run.py --model 8b --gpus 64")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["tp", "pp", "dp", "micro_bs", "m", "recompute", "fp8",
                        "state_gb", "act_gb", "total_gb", "mfu", "bubble",
                        "tp_comm_frac", "global_batch_tokens", "days", "meets_deadline"])
            for pl in res["plans"] + res["plans_fp8"]:
                w.writerow([pl.tp, pl.pp, pl.dp, pl.micro_bs, pl.m, pl.recompute, pl.fp8,
                            f"{pl.mem.state_gb:.2f}", f"{pl.mem.act_gb:.2f}",
                            f"{pl.mem.total_gb:.2f}", f"{pl.mfu:.4f}", f"{pl.bubble:.4f}",
                            f"{pl.tp_comm_frac:.4f}", pl.global_batch, f"{pl.days:.2f}",
                            pl.meets])
            print(f"  wrote {args.csv} "
              f"({len(res['plans']) + len(res['plans_fp8'])} plans)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
