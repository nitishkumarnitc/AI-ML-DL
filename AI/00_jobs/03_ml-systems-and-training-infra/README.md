# 03 · ML Systems & Training-Infrastructure Engineer

- **Type:** Full-time
- **In one line:** Make giant training runs go fast and not fall over — distributed training, GPUs/CUDA, networking, throughput.
- **Where (examples):** NVIDIA, OpenAI, Anthropic, Google, Meta (PyTorch), xAI, Databricks, Together AI, CoreWeave, Modal, Lambda, Cerebras.

← back to [AI Jobs hub](../README.md)

🧪 **[Try the sample project for this role](project.md)**

---

## 🎯 What the work is
- Scale training across thousands of GPUs: parallelism (data/tensor/pipeline/FSDP), collectives, checkpointing.
- Squeeze throughput: kernels/CUDA/Triton, memory, communication overlap, fault tolerance.
- Build the training platform other engineers run experiments on.

## 🧰 Core skills
- Systems + performance engineering; CUDA/Triton a big plus; PyTorch internals.
- Distributed systems, networking, storage; profiling and debugging at scale.

## 📈 Market note
Brutally supply-constrained. Kernel/performance specialists are in especially short supply. Demand tracks the GPU build-out.

## 📚 Path in this repo
- [`DL/02_pytorch`](../../../DL/02_pytorch/README.md) — framework internals.
- [`AI/04_llm-serving-and-inference-optimization`](../../04_llm-serving-and-inference-optimization/README.md) — KV-cache, batching, quantization (shares the perf mindset).
- [`Shared/02_mlops`](../../../Shared/02_mlops/README.md) — ops/reliability.


**System design for this role:** [`AI/29_model-training-system-design/03_distributed_training_platform`](../../29_model-training-system-design/03_distributed_training_platform/README.md) — 70B on 512 GPUs in 30 days — parallelism plan, MFU budget, checkpointing, fault tolerance. Full Requirements → HLD → LLD, with runnable code.

## 🎒 How to stand out
- Optimize a real training/inference kernel; show a measured speedup and explain why.

## 🔁 Adjacent roles
- [Research Engineer](../02_research-engineer-model-training/README.md) · [AI Platform / MLOps & Inference](../09_ai-platform-mlops-inference-engineer/README.md)
