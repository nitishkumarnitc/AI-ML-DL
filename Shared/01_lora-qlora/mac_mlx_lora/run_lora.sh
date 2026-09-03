#!/usr/bin/env bash
# LoRA / QLoRA fine-tuning natively on Apple Silicon via mlx-lm.
# The base model below is already 4-bit quantized ("-4bit"), so training LoRA
# adapters on top of it is the direct Mac-native equivalent of QLoRA.
#
# Usage:
#   python prepare_data.py     # run this first, from this directory, to create ./data
#   bash run_lora.sh
set -euo pipefail

# Swap for mlx-community/Qwen2.5-1.5B-Instruct-4bit for a much faster run on a smaller Mac.
MODEL="mlx-community/Mistral-7B-Instruct-v0.2-4bit"
DATA_DIR="data"
ADAPTER_DIR="adapters"
FUSED_DIR="fused-model"
TEST_PROMPT="In one paragraph, explain what a low-rank matrix decomposition is and why it is useful."

if [ ! -f "${DATA_DIR}/train.jsonl" ]; then
  echo "No ${DATA_DIR}/train.jsonl found -- run 'python prepare_data.py' first." >&2
  exit 1
fi

echo "=== BEFORE fine-tuning ==="
python3 -m mlx_lm.generate \
  --model "${MODEL}" \
  --max-tokens 150 \
  --prompt "${TEST_PROMPT}"

echo
echo "=== Training LoRA adapter ==="
python3 -m mlx_lm.lora \
  --model "${MODEL}" \
  --train \
  --data "${DATA_DIR}" \
  --adapter-path "${ADAPTER_DIR}" \
  --batch-size 1 \
  --num-layers 8 \
  --iters 200 \
  --grad-checkpoint

echo
echo "=== AFTER fine-tuning (adapter applied) ==="
python3 -m mlx_lm.generate \
  --model "${MODEL}" \
  --adapter-path "${ADAPTER_DIR}" \
  --max-tokens 150 \
  --prompt "${TEST_PROMPT}"

echo
echo "=== Fusing the adapter into a standalone model (optional, for deployment) ==="
python3 -m mlx_lm.fuse \
  --model "${MODEL}" \
  --adapter-path "${ADAPTER_DIR}" \
  --save-path "${FUSED_DIR}"

echo
echo "Done. Adapter saved to ./${ADAPTER_DIR}, fused standalone model saved to ./${FUSED_DIR}"
