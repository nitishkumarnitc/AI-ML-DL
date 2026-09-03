# 02 · Sample project — Research Engineer, Model Training & Post-Training

← back to [job description](README.md) · [jobs hub](../README.md)

🏗️ **Then design the platform version:** [Post-Training Pipeline](../../29_model-training-system-design/02_post_training_pipeline/README.md) — full Requirements → HLD → LLD for the system a lab would actually run this on ([folder index](../../29_model-training-system-design/README.md)).

> ▶ **Run the real code:** `pip install torch && python project/run.py` (~10s) -- runs the real SFT->DPO loop on a tiny hand-rolled LM (now 10 preference pairs) and prints both a raw AND length-normalized preference win-rate plus response length before/after. `--dpo-epochs`, `--beta`, and `--save-checkpoint` are all real CLI options. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A full **SFT → DPO** post-training loop on a small open model, with a before/after eval showing the DPO step actually moved behavior in the intended direction.

## 🧠 Why this mirrors the real job
- "Build and run pre-training/post-training pipelines" → you'll run both stages back to back on the same base model.
- "Own training data pipelines, reward models, and the eval loop that steers a run" → you write the preference pairs and the eval that judges the result.
- "Debug loss curves... and reward hacking" → you'll watch for the DPO loss collapsing to zero (a real failure mode) and check the model didn't just learn to be short/evasive to win preferences.

## 🧰 Prerequisites
- Python, PyTorch, `transformers`, `trl`, `datasets` (`pip install transformers trl datasets accelerate`).
- A small base model you can run on CPU or a modest GPU — e.g. `Qwen/Qwen2.5-0.5B-Instruct` or `gpt2`.
- ~4–6 hours.

## 🧰 Tools, libraries & skills used here
- **PyTorch** — the model, the optimizer (`AdamW`), and the manually-implemented DPO loss (`log-sigmoid` of a log-probability-ratio difference) so the math is visible instead of hidden inside a library call.
- **Custom log-probability scoring** (`sequence_logprob`) — computing `log P(response | prompt)` by summing token log-softmaxes is exactly what `trl`'s `DPOTrainer` does internally; seeing it written out demystifies what "the reference model" and "the policy model" actually mean.
- **What a real pipeline swaps in**: Hugging Face `transformers` (real pretrained models), `datasets` (data loading), `trl`'s `SFTTrainer`/`DPOTrainer` (production-grade SFT/DPO/PPO loops), `accelerate` or DeepSpeed (multi-GPU), `peft`/LoRA (parameter-efficient fine-tuning so you don't retrain the whole model), and Weights & Biases for tracking loss curves across runs.
- **Core skill**: reading a loss curve and recognizing failure modes (e.g. DPO loss collapsing to ~0 too fast, which you'll actually see when you run this) instead of just trusting that "training happened."

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| torch | pip install torch | tensors, autograd, `nn.TransformerEncoderLayer`, log-softmax for the hand-rolled DPO loss |
| statistics (stdlib) | built in | averaging response lengths across generations for the before/after comparison |

## 🪜 Step-by-step

### 1. Pick one behavior to shift
Something checkable, not vibes-based. Example: "prefer concise answers over rambling ones" or "always answer in bullet points."

### 2. Write ~30 preference pairs
```python
# preferences.jsonl — one line per example
# {"prompt": "...", "chosen": "...", "rejected": "..."}
import json
pairs = [
    {
        "prompt": "Explain what a hash map is.",
        "chosen": "- Key-value store.\n- O(1) average lookup.\n- Backed by an array of buckets.",
        "rejected": "Well, a hash map is a really interesting data structure that has been used for decades in computer science, and to understand it fully we should first talk about arrays..."
    },
    # ... ~30 total, same chosen/rejected pattern for your chosen behavior
]
with open("preferences.jsonl", "w") as f:
    for p in pairs:
        f.write(json.dumps(p) + "\n")
```

### 3. SFT stage — warm up the model on the "chosen" style
```python
from datasets import load_dataset
from trl import SFTTrainer, SFTConfig

ds = load_dataset("json", data_files="preferences.jsonl", split="train")
ds = ds.map(lambda x: {"text": f"### Prompt: {x['prompt']}\n### Response: {x['chosen']}"})

trainer = SFTTrainer(
    model="Qwen/Qwen2.5-0.5B-Instruct",
    train_dataset=ds,
    args=SFTConfig(output_dir="sft-out", num_train_epochs=2, per_device_train_batch_size=4),
)
trainer.train()
trainer.save_model("sft-out")
```

### 4. DPO stage — teach the preference directly
```python
from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("sft-out")
ref_model = AutoModelForCausalLM.from_pretrained("sft-out")
tok = AutoTokenizer.from_pretrained("sft-out")

dpo_trainer = DPOTrainer(
    model=model, ref_model=ref_model,
    args=DPOConfig(output_dir="dpo-out", per_device_train_batch_size=2, num_train_epochs=1),
    train_dataset=ds,  # trl's DPOTrainer expects prompt/chosen/rejected columns
    tokenizer=tok,
)
dpo_trainer.train()
```
Watch the loss curve — if it crashes to near-zero in a handful of steps, your pairs are probably too easy/short; that's the "reward hacking"-adjacent failure to notice, not ignore.

### 5. Eval: did it actually change behavior?
```python
held_out_prompts = ["Explain what recursion is.", "What is a binary search tree?"]

def generate(model_path, prompt):
    m = AutoModelForCausalLM.from_pretrained(model_path)
    t = AutoTokenizer.from_pretrained(model_path)
    ids = t(prompt, return_tensors="pt")
    out = m.generate(**ids, max_new_tokens=120)
    return t.decode(out[0], skip_special_tokens=True)

for p in held_out_prompts:
    print("BEFORE (base):", generate("Qwen/Qwen2.5-0.5B-Instruct", p)[:200])
    print("AFTER  (DPO): ", generate("dpo-out", p)[:200])
```
Score both outputs against your target behavior (bullet points? length under N words?) with a simple rule-based or LLM-as-judge check — don't eyeball it.

## ✅ Deliverable
- `preferences.jsonl`, the SFT and DPO training logs, and a short table: held-out prompt → base output → DPO output → did it match the target behavior (yes/no).
- One paragraph on any reward-hacking-like symptom you saw and how you'd fix it (more diverse pairs? a length penalty?).

## ⏱️ Time box
A weekend.

## 🏗️ Scale this to a real lab — the system design

This project is one SFT→DPO loop on a tiny model. A lab runs ~20 post-training experiments a week and
the shape of the system is set by something this project can't reveal: **generation, not gradients,
dominates.** [`29/02 · Post-Training Pipeline`](../../29_model-training-system-design/02_post_training_pipeline/README.md)
is the full Requirements → HLD → LLD, including the RLVR stage this project stops short of.

**The step budget that reframes the problem** (8B policy, 8×H100, GRPO with 256 prompts × k=8):

```
policy update      35.8 s   40.0%   GPU busy
generation: decode 20.5 s   22.9%   GPU busy (memory-bandwidth-bound, NOT compute)
verify             16.0 s   17.9%   GPUs COMPLETELY IDLE  <- sandboxed test execution is CPU work
reference logprobs 11.9 s   13.3%
generation: prefill 5.3 s    5.9%
weight sync         0.3 s    0.3%
```

**The gradient step is a minority of the cost**, and 18% of every step has no GPU work at all. Two
consequences the toy version hides: you need **two engines over one set of weights** (a trainer and an
inference engine want opposite memory layouts), and syncing between them via a checkpoint round-trip
costs **~56 s against an 89 s step — a 63% tax**, mostly the inference engine's CUDA-graph rebuild.
In-memory broadcast is 0.04 s.

| What this project does | What the pipeline adds | Why |
|---|---|---|
| Uses whatever text is at hand | **Decontamination**: 13-gram Bloom filter vs **every** eval suite, enforced by a DB trigger | ~10 CPU-minutes and 72 MB. Skipping it doesn't just inflate a benchmark — it **disables the reward-hack detector**, whose primary signal is a held-out pass rate |
| Watch for the DPO loss collapsing | **Collapse detector with a sample size**: EMA(loss) < 0.10 *and* accuracy > 0.99 over a **≥256-pair window** | Raw `accuracy > 0.99` on a batch of 8 fires ~27% of the time at 85% *true* accuracy — it aborts healthy runs. Thresholds on proportions need an `n` |
| Stops after DPO | **RLVR/GRPO stage** with program-based rewards | A verifier is a program; its attack surface is the program. A learned reward model's is every out-of-distribution region of its input space, and it fails silently and confidently |
| — | **GRPO over PPO — decided by a memory table** | The requirement is 2,048 concurrent rollouts (309 GB of KV cache). GRPO leaves 2,967; PPO's critic adds 16 GB/GPU of *optimizer state* → **2,013, below the requirement.** PPO doesn't fit |
| Eyeball whether behaviour changed | **Held-out verifier, ≥1,500 prompts, independently *implemented*** | Shared code shares bugs — a model gaming the shared bug passes both graders. Enforced by a CI import-graph check |
| "Check it didn't just get shorter" | **Four-signal detector**: verifier gap (with a CI), length drift, KL excursion, refusal rise | Each alone has a benign explanation; the conjunction doesn't. The gap fires only when its CI *excludes* the threshold, because a detector that cries wolf gets switched off |
| — | **Network-isolated sandbox** with three independent bounds | The code being executed was written by a model **being gradient-optimized to maximize the score that code produces.** That is a search process pointed at your sandbox |

**The detection arithmetic to internalize:** at 100 held-out prompts, 2 SE of the gap is **14.1
points**; reward hacking announces itself at 2–5. And the sharper point, which only showed up when the
demo was written: the gap's noise is **dominated by the *training* side** (~192 rollouts/step), so more
held-out prompts past ~1,500 barely help — you window the gap over 8 steps instead.

**Run the pipeline's core:**

```bash
python ../../29_model-training-system-design/02_post_training_pipeline/project/run.py
```

A real GRPO loop over three response strategies **discovers a verifier exploit on its own** — training
pass rate climbs 0.65 → 0.97 while an independently-implemented held-out verifier goes 0.25 → 0.03. On
a reward-only dashboard that is a great run.

## 🔁 Where to go deeper
[`AI/02_fine-tuning-and-alignment`](../../02_fine-tuning-and-alignment/README.md) — the SFT/RLHF/DPO theory · [`DL/04_reinforcement-learning`](../../../DL/04_reinforcement-learning/README.md) — reward design, reward hacking · [`AI/10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) — the RLVR environments this feeds into.

**Design-level:** [`29/02_post_training_pipeline`](../../29_model-training-system-design/02_post_training_pipeline/README.md) — the platform version of this project, with quantified NFRs, rejected alternatives, failure modes and runnable code.
