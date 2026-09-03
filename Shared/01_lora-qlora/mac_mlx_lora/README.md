# LoRA / QLoRA on Apple Silicon (MLX)

Companion to the main [module README](../README.md) and
[Local LLM Fine-tuning on Mac (M-series) Using QLoRA and MLX](https://www.classcentral.com/course/youtube-local-llm-fine-tuning-on-mac-m1-16gb-340110)
by Shaw Talebi. No CUDA GPU needed — this trains directly on your Mac's own GPU via
[MLX](https://github.com/ml-explore/mlx).

The base model used here (`mlx-community/Mistral-7B-Instruct-v0.2-4bit`) is already 4-bit
quantized, so training a LoRA adapter on top of it is the direct Mac-native equivalent of QLoRA —
same idea as the notebook in `../notebooks/`, different backend (MLX instead of
bitsandbytes/CUDA).

## Requirements
- Apple Silicon Mac (M1 or newer)
- ~8GB+ free RAM for the 7B-4bit model (use the smaller model below if tighter on memory)

```bash
pip install -r ../requirements_mlx.txt
```

## 1. Prepare the dataset
Exports the same [`mlabonne/guanaco-llama2-1k`](https://huggingface.co/datasets/mlabonne/guanaco-llama2-1k)
dataset used in the Colab notebook into the `train.jsonl` / `valid.jsonl` format `mlx_lm.lora` expects:

```bash
python prepare_data.py
```

## 2. Train, compare, and fuse
Runs baseline generation, LoRA training, post-training generation, and adapter fusing in one go:

```bash
bash run_lora.sh
```

Or run the steps individually:

```bash
# Before fine-tuning
python3 -m mlx_lm.generate --model mlx-community/Mistral-7B-Instruct-v0.2-4bit \
  --max-tokens 150 --prompt "In one paragraph, explain what a low-rank matrix decomposition is."

# Train a LoRA adapter
python3 -m mlx_lm.lora --model mlx-community/Mistral-7B-Instruct-v0.2-4bit \
  --train --data data --adapter-path adapters --batch-size 1 --num-layers 8 --iters 200

# After fine-tuning (adapter applied)
python3 -m mlx_lm.generate --model mlx-community/Mistral-7B-Instruct-v0.2-4bit \
  --adapter-path adapters --max-tokens 150 \
  --prompt "In one paragraph, explain what a low-rank matrix decomposition is."

# Fuse the adapter into a standalone model (optional, for deployment)
python3 -m mlx_lm.fuse --model mlx-community/Mistral-7B-Instruct-v0.2-4bit \
  --adapter-path adapters --save-path fused-model
```

## Tuning for your hardware
- **Tight on memory (16GB Mac):** swap `MODEL` in `run_lora.sh` for
  `mlx-community/Qwen2.5-1.5B-Instruct-4bit` — much smaller, trains in a couple of minutes.
- **`--num-layers`**: how many of the model's final layers get LoRA adapters. Lower = less
  memory/faster, higher = more capacity to adapt.
- **`--iters`**: training steps. 200 is a quick demo; increase for a more thoroughly-tuned adapter.
- **`--grad-checkpoint`**: trades compute for memory — keep it on if you hit memory pressure.

## Reference
- [MLX-LM LoRA docs](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md)
- [MLX GitHub](https://github.com/ml-explore/mlx)
