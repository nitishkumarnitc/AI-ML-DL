# 🧩 Module 4: LoRA & QLoRA — Parameter-Efficient Fine-Tuning

> Fine-tune large language models on a single GPU (or an Apple Silicon Mac) by training
> small adapter matrices instead of the full model.

---

## 🎥 Curated Video Tutorials

| # | Video | Why it's here |
|---|-------|----------------|
| 1 ⭐ | [QLoRA — How to Fine-Tune an LLM on a Single GPU (w/ Python Code)](https://www.youtube.com/watch?v=XpoKB3usmKc) — Shaw Talebi | Best overall pick. Explains the 4 ingredients of QLoRA (4-bit NormalFloat, Double Quantization, Paged Optimizers, LoRA) with intuition first, math second, then walks through real code. Comes with a companion [blog post](https://towardsdatascience.com/qlora-how-to-fine-tune-an-llm-on-a-single-gpu-4e44d6b5be32/), Colab notebook, GitHub repo, and a HF dataset+model. This project follows its structure. |
| 2 | [Local LLM Fine-tuning on Mac (M-series) Using QLoRA and MLX](https://www.classcentral.com/course/youtube-local-llm-fine-tuning-on-mac-m1-16gb-340110) — Shaw Talebi | Same author, but for Apple Silicon using MLX instead of CUDA/bitsandbytes. Directly relevant if you don't have an NVIDIA GPU. Mirrored in [`mac_mlx_lora/`](mac_mlx_lora/). |
| 3 | [LoRA & QLoRA Explained Simply — Full Fine-Tuning vs PEFT](https://www.youtube.com/watch?v=cO6Ly7mIziQ) | Go here first if you want deeper math/intuition before touching code. |
| 4 | [LoRA & QLoRA Fine-tuning Explained In-Depth](https://www.youtube.com/watch?v=t1caDsMzWBk) | Alternative depth-first explanation. |
| 5 | [The Complete Guide to End-to-End LLM Fine-Tuning (LoRA, QLoRA & Full)](https://www.youtube.com/watch?v=jrf5vyOEMr8) | Widest scope — also covers full fine-tuning for comparison. |

**Recommended order:** watch #1 end-to-end, run the notebook in this folder alongside it, then skim #3/#4 for the math if you want it to really stick.

---

## 🧠 Concepts

### The problem
Full fine-tuning of a 7B-parameter model updates **all 7B weights**, which needs:
- ~28GB+ just for FP32 weights, plus optimizer states and gradients → often 4-8x the model size in VRAM
- A full copy of the model saved per fine-tuning run

### LoRA (Low-Rank Adaptation)
Instead of updating the full weight matrix `W` (shape `d × k`), LoRA freezes `W` and learns a
**low-rank update** `ΔW = B·A`, where `B` is `d × r` and `A` is `r × k`, with rank `r << d, k`
(commonly 8-64). The forward pass becomes:

```
h = W·x + (B·A)·x  =  W·x + BA·x
```

Only `A` and `B` are trained — for `d=k=4096` and `r=16`, that's `2 × 4096 × 16 ≈ 131K` params
instead of `16.7M`, roughly a **99% reduction** in trainable parameters for that layer. `W` never
moves, so you can swap adapters in and out of the same frozen base model.

### QLoRA = Quantization + LoRA
QLoRA adds four tricks on top of LoRA so the **frozen base model** itself fits in much less memory:
1. **4-bit NormalFloat (NF4)** — a data type tuned for the roughly-normal distribution of neural net weights, more accurate than plain 4-bit int at the same size.
2. **Double Quantization** — quantizes the quantization constants themselves, saving a bit more memory.
3. **Paged Optimizers** — uses NVIDIA unified memory to page optimizer states to CPU RAM on GPU OOM spikes instead of crashing.
4. **LoRA adapters** — trained in higher precision (bf16) on top of the frozen 4-bit base, with gradients backpropagated *through* the quantized weights into the adapters.

Net effect: a 7B model that needs ~28GB in FP32 can be fine-tuned on a **single consumer GPU with
~6-10GB VRAM**, at a small (usually negligible) cost to final quality vs. full fine-tuning.

### LoRA vs. QLoRA — when to use which
| | LoRA | QLoRA |
|---|---|---|
| Base model precision | FP16/BF16 | 4-bit (NF4) |
| VRAM for a 7B model | ~14-16GB | ~5-8GB |
| Training speed | Faster | ~20-30% slower (dequant overhead) |
| Use when | You have a decent GPU (e.g. A100/RTX 4090) and want max speed | You have a single consumer GPU, a free Colab T4, or a Mac and want to fit a bigger model |

### Common real-world usages
- **Domain adaptation** — adapt a general chatbot to legal, medical, or internal-company text without touching the base weights.
- **Persona / tone adapters** — one base model, many swappable "personality" adapters (formal support agent, casual assistant, a specific brand voice).
- **Instruction tuning** — turn a base (non-chat) model into an instruction-follower, which is exactly what the project below does.
- **Multi-tenant serving** — serve hundreds of customers from one loaded base model by hot-swapping a few-MB adapter per request instead of loading a full fine-tuned model per customer.
- **Style/format transfer** — e.g. training a model to always answer in a fixed JSON schema, or in a specific reply style (Shaw Talebi's original tutorial: a YouTube-comment responder).

---

## 📊 Dataset

**[`mlabonne/guanaco-llama2-1k`](https://huggingface.co/datasets/mlabonne/guanaco-llama2-1k)** —
a 1,000-example subset of the OpenAssistant **Guanaco** dataset (the same dataset used in the
original QLoRA paper), pre-formatted into Llama-2 instruction/response prompt style:

```
<s>[INST] {instruction} [/INST] {response} </s>
```

Chosen because it's small (fast to train on in a live demo — a few minutes on a free Colab T4),
public, and needs zero preprocessing for the `transformers`/`trl` path. `mac_mlx_lora/prepare_data.py`
re-exports the same dataset into the `train.jsonl` / `valid.jsonl` format MLX expects.

---

## 🚀 Basic Project: Instruction-tuning a base model with QLoRA

Fine-tune `mistralai/Mistral-7B-Instruct-v0.2` (swap for a smaller model like
`Qwen/Qwen2.5-1.5B-Instruct` or `TinyLlama/TinyLlama-1.1B-Chat-v1.0` if you want faster iteration
or don't have Colab Pro) on the Guanaco instructions above, then compare its answers before vs.
after fine-tuning.

### Path A — Google Colab / any CUDA GPU
Open [`notebooks/01_LoRA_QLoRA_Concepts_and_Project.ipynb`](notebooks/01_LoRA_QLoRA_Concepts_and_Project.ipynb) in Colab (Runtime → Change runtime type → T4 GPU) and run all cells top to bottom.

```bash
pip install -r requirements.txt
```

### Path B — Local Mac (Apple Silicon, MLX)
No CUDA needed — trains natively on the Mac's own GPU via MLX.

```bash
pip install -r requirements_mlx.txt
python mac_mlx_lora/prepare_data.py
bash mac_mlx_lora/run_lora.sh
```

See [`mac_mlx_lora/README.md`](mac_mlx_lora/README.md) for the step-by-step breakdown.

---

## 📁 Folder Structure

```
4.LoRA_QLoRA/
├── README.md                                          ← you are here
├── requirements.txt                                    (CUDA/Colab path: transformers, peft, trl, bitsandbytes)
├── requirements_mlx.txt                                (Mac path: mlx-lm)
├── notebooks/
│   └── 01_LoRA_QLoRA_Concepts_and_Project.ipynb        (concepts + full QLoRA fine-tuning walkthrough)
└── mac_mlx_lora/
    ├── README.md                                       (Mac-specific instructions)
    ├── prepare_data.py                                 (exports the dataset to MLX jsonl format)
    └── run_lora.sh                                     (train → generate → fuse, via mlx_lm CLI)
```

## 🔗 Further Reading
- [QLoRA paper — "QLoRA: Efficient Finetuning of Quantized LLMs"](https://arxiv.org/abs/2305.14314)
- [LoRA paper — "LoRA: Low-Rank Adaptation of Large Language Models"](https://arxiv.org/abs/2106.09685)
- [Hugging Face PEFT docs](https://huggingface.co/docs/peft)
- [Hugging Face TRL SFTTrainer docs](https://huggingface.co/docs/trl/sft_trainer)
- [MLX-LM LoRA docs](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
