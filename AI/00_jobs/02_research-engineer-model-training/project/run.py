"""
Sample project — Research Engineer, Model Training & Post-Training
A minimal end-to-end SFT -> DPO loop on a hand-rolled tiny char-level LM, with
the actual metric real DPO pipelines report: preference win-rate (does the
policy assign higher probability to the chosen response than the rejected
one?), measured before SFT, after SFT, and after DPO -- not just eyeballed
generations.

No internet/model download needed -- this is a scaled-down stand-in for the
real HF `transformers`/`trl` workflow described in project.md, implementing
the actual SFT and DPO loss math so the mechanics are real, not simulated.

Run:  python run.py
      python run.py --dpo-epochs 150 --beta 0.3     (tune the DPO run)
      python run.py --save-checkpoint dpo_model.pt   (persist the trained model)
Dependencies:
  - torch (pip install torch) -- tensors, autograd, nn.TransformerEncoderLayer, F.log_softmax
  - statistics (stdlib) -- mean() for the before/after comparisons
  - argparse (stdlib) -- CLI config
"""
import argparse
import statistics as st

import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# 1. Preference data: teach "answer concisely with bullet points" over "ramble"
#    10 pairs across a shared small vocabulary so the model generalizes a
#    *style*, not just memorizes 5 specific answers.
# ---------------------------------------------------------------------------
PAIRS = [
    ("what is a stack?", "- lifo order\n- push/pop\n- o(1) ops",
     "well a stack is a very interesting data structure that a lot of people use and it basically means..."),
    ("what is a queue?", "- fifo order\n- enqueue/dequeue\n- o(1) ops",
     "so queues are honestly a pretty cool concept and there is a lot to say about how they..."),
    ("what is recursion?", "- fn calls itself\n- needs base case\n- uses call stack",
     "recursion is this thing where basically a function ends up calling itself over and over which is kind of wild..."),
    ("what is a hash map?", "- key/value store\n- o(1) lookup\n- uses buckets",
     "a hash map is honestly one of the most useful things in programming and there is just so much history..."),
    ("what is a linked list?", "- nodes + pointers\n- o(1) insert\n- o(n) search",
     "linked lists are a classic topic that basically every computer science course spends way too long on..."),
    ("what is a graph?", "- nodes + edges\n- directed or undirected\n- bfs/dfs traversal",
     "graphs are honestly such a huge topic and there is really so much depth to how you can represent them..."),
    ("what is a binary tree?", "- nodes with 2 children\n- log(n) height if balanced\n- inorder/pre/post traversal",
     "binary trees come up constantly and honestly there is a whole family of variants worth discussing at length..."),
    ("what is memoization?", "- caches fn results\n- avoids recompute\n- speeds up recursion",
     "memoization is this technique that people love to talk about and there is a lot of nuance to when it helps..."),
    ("what is a heap?", "- priority ordering\n- o(log n) insert/pop\n- array-backed tree",
     "heaps are a pretty deep topic honestly and there are so many variants like min-heap and max-heap worth exploring..."),
    ("what is a trie?", "- prefix tree\n- fast prefix lookup\n- used in autocomplete",
     "tries are this really interesting structure that come up in a surprising number of places if you think about it..."),
]
PROMPT_PREFIX = "Q: "
RESP_SEP = "\nA: "

full_texts = []
for p, chosen, rejected in PAIRS:
    full_texts.append(PROMPT_PREFIX + p + RESP_SEP + chosen)
    full_texts.append(PROMPT_PREFIX + p + RESP_SEP + rejected)

chars = sorted(set("".join(full_texts)) | {" "})
stoi = {c: i for i, c in enumerate(chars)}
VOCAB = len(chars)


def encode(s: str) -> torch.Tensor:
    return torch.tensor([stoi[c] for c in s], dtype=torch.long)


# ---------------------------------------------------------------------------
# 2. Tiny model
# ---------------------------------------------------------------------------
class TinyLM(nn.Module):
    def __init__(self, vocab_size, n_embd=32, n_head=4, n_layer=2, max_len=256):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(max_len, n_embd)
        layer = nn.TransformerEncoderLayer(n_embd, n_head, dim_feedforward=96, batch_first=True)
        self.blocks = nn.TransformerEncoder(layer, num_layers=n_layer)
        self.head = nn.Linear(n_embd, vocab_size)

    def forward(self, x):
        t = x.shape[1]
        pos = torch.arange(t, device=x.device)
        mask = nn.Transformer.generate_square_subsequent_mask(t)
        h = self.tok_emb(x) + self.pos_emb(pos)
        h = self.blocks(h, mask=mask, is_causal=True)
        return self.head(h)


def sequence_logprob(model, prompt: str, response: str) -> torch.Tensor:
    """log P(response | prompt) under `model`, summed over response tokens.
    This raw sum is what the DPO loss itself uses (matching the standard
    DPO formulation) -- but it's biased toward SHORTER responses, since
    summing more (negative) per-token log-probs makes long responses look
    worse regardless of quality. See `preference_win_rate` below."""
    full = prompt + response
    ids = encode(full).unsqueeze(0)
    logits = model(ids)[0]  # (T, vocab)
    prompt_len = len(encode(prompt))
    logprobs = F.log_softmax(logits, dim=-1)
    total = torch.tensor(0.0)
    for t in range(prompt_len, len(ids[0]) - 1):
        next_tok = ids[0, t + 1]
        total = total + logprobs[t, next_tok]
    return total


def sequence_logprob_per_token(model, prompt: str, response: str) -> torch.Tensor:
    """Length-normalized log-prob (mean per-token, not sum) -- the metric
    practitioners actually use to compare responses of different lengths
    without the length bias `sequence_logprob` has."""
    n_tokens = max(len(response), 1)
    return sequence_logprob(model, prompt, response) / n_tokens


# ---------------------------------------------------------------------------
# 3. SFT stage: warm up on the "chosen" (concise) style only
# ---------------------------------------------------------------------------
def sft_train(model, epochs=60, lr=3e-3):
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    for epoch in range(epochs):
        total_loss = 0.0
        for p, chosen, _ in PAIRS:
            full = PROMPT_PREFIX + p + RESP_SEP + chosen
            ids = encode(full).unsqueeze(0)
            logits = model(ids)[:, :-1]
            targets = ids[:, 1:]
            loss = F.cross_entropy(logits.reshape(-1, VOCAB), targets.reshape(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
        if epoch % 20 == 0:
            print(f"  SFT epoch {epoch}: loss={total_loss / len(PAIRS):.3f}")


# ---------------------------------------------------------------------------
# 4. DPO stage: directly optimize the preference
# ---------------------------------------------------------------------------
def dpo_train(policy, ref, epochs=80, lr=1e-3, beta=0.5):
    opt = torch.optim.AdamW(policy.parameters(), lr=lr)
    ref.eval()
    for p in ref.parameters():
        p.requires_grad = False

    for epoch in range(epochs):
        total_loss = 0.0
        for prompt_text, chosen, rejected in PAIRS:
            prompt = PROMPT_PREFIX + prompt_text + RESP_SEP
            logp_c_pi = sequence_logprob(policy, prompt, chosen)
            logp_r_pi = sequence_logprob(policy, prompt, rejected)
            with torch.no_grad():
                logp_c_ref = sequence_logprob(ref, prompt, chosen)
                logp_r_ref = sequence_logprob(ref, prompt, rejected)

            logits = beta * ((logp_c_pi - logp_c_ref) - (logp_r_pi - logp_r_ref))
            loss = -F.logsigmoid(logits)

            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
        if epoch % 20 == 0:
            print(f"  DPO epoch {epoch}: loss={total_loss / len(PAIRS):.4f}")


# ---------------------------------------------------------------------------
# 5. Preference win-rate: the actual DPO eval metric (not just length)
# ---------------------------------------------------------------------------
@torch.no_grad()
def preference_win_rate(model, normalized: bool = True) -> float:
    """Fraction of pairs where the model assigns chosen a higher (length-
    normalized) log-prob than rejected -- this is what a real DPO pipeline
    reports as 'preference accuracy'. Set normalized=False to see the raw,
    length-biased version for comparison."""
    score_fn = sequence_logprob_per_token if normalized else sequence_logprob
    wins = 0
    for prompt_text, chosen, rejected in PAIRS:
        prompt = PROMPT_PREFIX + prompt_text + RESP_SEP
        if score_fn(model, prompt, chosen) > score_fn(model, prompt, rejected):
            wins += 1
    return wins / len(PAIRS)


# ---------------------------------------------------------------------------
# 6. Generation on a held-out prompt (not in the training pairs)
# ---------------------------------------------------------------------------
@torch.no_grad()
def generate(model, prompt: str, max_new_tokens=60, temperature=0.7) -> str:
    ids = encode(prompt).unsqueeze(0)
    for _ in range(max_new_tokens):
        logits = model(ids)[0, -1]
        probs = F.softmax(logits / temperature, dim=-1)
        next_id = torch.multinomial(probs, 1)
        ids = torch.cat([ids, next_id.unsqueeze(0)], dim=1)
        if chars[next_id.item()] == "\n" and ids.shape[1] > len(encode(prompt)) + 10:
            break
    out = "".join(chars[i] for i in ids[0].tolist())
    return out[len(prompt):]


def main():
    parser = argparse.ArgumentParser(description="Tiny SFT -> DPO pipeline")
    parser.add_argument("--sft-epochs", type=int, default=60)
    parser.add_argument("--dpo-epochs", type=int, default=80)
    parser.add_argument("--beta", type=float, default=0.5, help="DPO temperature (default: 0.5)")
    parser.add_argument("--save-checkpoint", default=None, help="path to save the final DPO model")
    args = parser.parse_args()

    torch.manual_seed(0)
    print(f"vocab size: {VOCAB} chars, {len(PAIRS)} preference pairs\n")

    base = TinyLM(VOCAB)

    print("=== Stage 1: SFT on chosen (concise) style ===")
    sft_model = TinyLM(VOCAB)
    sft_model.load_state_dict(base.state_dict())
    sft_train(sft_model, epochs=args.sft_epochs)

    print("\n=== Stage 2: DPO on chosen vs rejected pairs ===")
    dpo_model = TinyLM(VOCAB)
    dpo_model.load_state_dict(sft_model.state_dict())
    ref_model = TinyLM(VOCAB)
    ref_model.load_state_dict(sft_model.state_dict())
    dpo_train(dpo_model, ref_model, epochs=args.dpo_epochs, beta=args.beta)

    if args.save_checkpoint:
        torch.save(dpo_model.state_dict(), args.save_checkpoint)
        print(f"\nsaved DPO checkpoint to {args.save_checkpoint}")

    print("\n=== Eval 1: preference win-rate (the real DPO metric) ===")
    print(f"{'stage':<20}{'raw win-rate':>14}{'length-normalized win-rate':>28}")
    for name, model in [("base (untrained)", base), ("sft", sft_model), ("dpo", dpo_model)]:
        raw_rate = preference_win_rate(model, normalized=False)
        norm_rate = preference_win_rate(model, normalized=True)
        print(f"{name:<20}{raw_rate:14.0%}{norm_rate:28.0%}")
    print("Notice the RAW win-rate is ~100% even for the untrained base model -- that's a length-\n"
          "bias artifact, not a real signal: the chosen answers are shorter, and summing fewer\n"
          "(negative) per-token log-probs always looks 'better' regardless of quality. The\n"
          "length-normalized column is the metric that actually separates the stages, and it's\n"
          "exactly the fix real DPO/RLHF practitioners reach for when raw sequence log-prob gives\n"
          "a misleadingly flat or biased number.")

    print("\n=== Eval 2: held-out prompt, response length before vs after ===")
    held_out = "what is a binary search tree?"
    prompt = PROMPT_PREFIX + held_out + RESP_SEP
    lengths = {"base (untrained)": [], "sft": [], "dpo": []}
    for _ in range(5):
        lengths["base (untrained)"].append(len(generate(base, prompt)))
        lengths["sft"].append(len(generate(sft_model, prompt)))
        lengths["dpo"].append(len(generate(dpo_model, prompt)))

    print(f"{'stage':<20}{'mean response length (chars)':>30}")
    for name, lens in lengths.items():
        print(f"{name:<20}{st.mean(lens):30.1f}")
    print("\n(lower length after SFT/DPO = it learned the concise-bullet style; "
          "run again with more epochs/pairs for a cleaner signal -- this is a toy scale.)")


if __name__ == "__main__":
    main()
