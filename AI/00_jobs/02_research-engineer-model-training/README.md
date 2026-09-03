# 02 · Research Engineer — Model Training & Post-Training

- **Type:** Full-time · frontier labs & AI-native scale-ups
- **In one line:** The engineer half of research — turn research ideas into working training runs: data, pipelines, RLHF/RLVR loops, evals.
- **Where (examples):** OpenAI, Anthropic, Google DeepMind, Meta, xAI, Mistral, Cohere, Reka, Databricks (Mosaic), Together AI, Hugging Face.

← back to [AI Jobs hub](../README.md)

🧪 **[Try the sample project for this role](project.md)**

---

## 🎯 What the work is
- Build and run pre-training / post-training pipelines (SFT, RLHF, DPO, RL-with-verifiable-rewards).
- Own training data pipelines, reward models, and the eval loop that steers a run.
- Debug loss curves, throughput, and reward hacking; ship the model that results.

## 🧰 Core skills
- Strong PyTorch + distributed training; solid grasp of the RL/alignment stack.
- Data engineering for training corpora; experiment discipline.
- Comfort reading research and translating it into robust code.

## 📈 Market note
A high-leverage, non-PhD path into frontier labs — labs hire far more research *engineers* than scientists. **RLVR + agentic post-training** is the hot sub-area (2025→), which is exactly why the RL-environments vendor market exploded.

## 📚 Path in this repo
- [`AI/02_fine-tuning-and-alignment`](../../02_fine-tuning-and-alignment/README.md) — SFT/RLHF/DPO (core).
- [`DL/04_reinforcement-learning`](../../../DL/04_reinforcement-learning/README.md) — reward design, reward hacking.
- [`AI/10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) — the environments you'd train against ([RLVR, Lesson 2](../../10_rl-environments-and-infra/02-rl-environments-for-agents.md)).
- [`Shared/01_lora-qlora`](../../../Shared/01_lora-qlora/README.md) — efficient fine-tuning.


**System design for this role:** [`AI/29_model-training-system-design/02_post_training_pipeline`](../../29_model-training-system-design/02_post_training_pipeline/README.md) — the SFT→DPO→RLVR platform — data decontamination, GRPO, verifier sandboxing, reward-hack detection. Full Requirements → HLD → LLD, with runnable code.

## 🎒 How to stand out
- Run a full SFT→DPO loop on an open model; show the eval delta; write it up.

## 🔁 Adjacent roles
- [AI Research Scientist](../01_ai-research-scientist/README.md) · [ML Systems & Training Infra](../03_ml-systems-and-training-infra/README.md) · [RL Environments & Infra](../08_rl-environments-and-infra-engineer/README.md)
