# 09 · Sample project — AI Platform / MLOps & Inference Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `pip install torch && python project/run.py` (~15-30s) -- for 3 model sizes, runs a real INT8 dynamic-quantization benchmark with memory footprint + cost table, AND a concurrent load test (multiple simulated clients) reporting throughput + p50/p95 latency. See [`project/`](project/) for the full source.

## 🎯 What you'll build
Serve a small open model and produce a **cost/latency benchmark** across batch sizes and a quantization setting — the "is this shippable at expected traffic and cost" analysis this role owns.

## 🧠 Why this mirrors the real job
- "Deploy and scale inference... optimize latency/throughput/cost: batching, KV-cache, quantization" → you'll vary batch size and quantization and measure both axes.
- "Model serving internals; cost engineering" → the deliverable is a $/1K-tokens number, not just "it's fast."

## 🧰 Prerequisites
- Python, `transformers`, `accelerate`, `bitsandbytes` (for 8-bit quantization); a GPU helps but CPU works for the exercise at reduced scale.
- A small model, e.g. `Qwen/Qwen2.5-0.5B-Instruct` or `gpt2`.
- ~4–5 hours.

## 🧰 Tools, libraries & skills used here
- **`torch.ao.quantization.quantize_dynamic`** — real INT8 post-training dynamic quantization applied to `nn.Linear` layers, including picking a working backend (`qnnpack`/`fbgemm`) for your CPU, a genuine platform-engineering wrinkle you'll hit on real hardware too.
- **Batch-size sweeps and latency/throughput benchmarking** — the core loop of capacity planning: more batching raises throughput up to a point, then flattens or reverses as you hit hardware limits.
- **Cost modeling**: converting a measured `ms/step` into a `$/1K requests` figure against an assumed hourly compute cost — the actual artifact an MLOps engineer hands to a PM or finance stakeholder.
- **What a real serving stack adds on top**: **vLLM** or **TensorRT-LLM** (production LLM serving with continuous batching + PagedAttention/KV-cache management), **ONNX Runtime** or **Hugging Face Optimum** for cross-hardware export, **bitsandbytes** for 4-/8-bit LLM quantization specifically, and autoscaling/observability (Kubernetes HPA, Prometheus/Grafana) to keep cost and latency in bounds under real traffic.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| torch | pip install torch | `nn.Linear` model, `torch.ao.quantization.quantize_dynamic` (real INT8 quantization), backend engine selection (`qnnpack`/`fbgemm`) |
| time (stdlib) | built in | batch-size benchmarking |
| warnings (stdlib) | built in | silencing noisy deprecation warnings from the quantization API |

## 🪜 Step-by-step

### 1. Baseline: single-request latency
```python
import torch, time
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-0.5B-Instruct"
tok = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def generate_batch(prompts, model, max_new_tokens=50):
    inputs = tok(prompts, return_tensors="pt", padding=True)
    t0 = time.perf_counter()
    out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    dt = time.perf_counter() - t0
    n_new_tokens = out.shape[1] - inputs["input_ids"].shape[1]
    return dt, n_new_tokens * len(prompts)

prompt = "Explain the concept of caching in one paragraph."
dt, tokens = generate_batch([prompt], model)
print(f"batch=1: {dt:.2f}s, {tokens/dt:.1f} tok/s")
```

### 2. Batch-size sweep
```python
for batch_size in [1, 4, 8, 16]:
    prompts = [prompt] * batch_size
    dt, tokens = generate_batch(prompts, model)
    print(f"batch={batch_size}: {dt:.2f}s total, {tokens/dt:.1f} tok/s throughput")
```
Expect throughput (tokens/sec) to rise with batch size up to a point, then flatten as you hit compute/memory limits — that inflection point is the real finding, not any single number.

### 3. Add 8-bit quantization and re-run the sweep
```python
model_8bit = AutoModelForCausalLM.from_pretrained(model_name, load_in_8bit=True, device_map="auto")
for batch_size in [1, 4, 8, 16]:
    prompts = [prompt] * batch_size
    dt, tokens = generate_batch(prompts, model_8bit)
    print(f"[8bit] batch={batch_size}: {dt:.2f}s total, {tokens/dt:.1f} tok/s throughput")
```

### 4. Turn throughput into a cost estimate
```python
gpu_cost_per_hour = 0.50  # pick a real on-demand small-GPU price to anchor this

def cost_per_1k_tokens(tokens_per_sec, cost_per_hour):
    tokens_per_hour = tokens_per_sec * 3600
    return (cost_per_hour / tokens_per_hour) * 1000

print(cost_per_1k_tokens(tokens_per_sec=120, cost_per_hour=gpu_cost_per_hour))
```

### 5. Tabulate and recommend
| Config | batch=1 tok/s | batch=16 tok/s | est. $/1K tokens @ batch=16 |
|---|---|---|---|
| fp32/fp16 baseline | | | |
| 8-bit quantized | | | |

Recommend a batch size + quantization setting for a hypothetical "1000 requests/hour" load, and say why — latency-per-request tradeoff vs throughput/cost.

## ✅ Deliverable
The benchmark table + cost calculation + a one-paragraph recommendation for a target load, explicitly trading off latency vs cost.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`04_llm-serving-and-inference-optimization`](../../04_llm-serving-and-inference-optimization/README.md) — vLLM, KV-cache, real production batching · [`Shared/02_mlops`](../../../Shared/02_mlops/README.md) · [`10_rl-environments-and-infra` Lesson 7](../../10_rl-environments-and-infra/07-the-environment-platform-and-infra.md).
