# 05 — Fine-Tuning & Alignment

> JD: "Architect fine-tuning (LoRA/QLoRA) and alignment workflows tailored to highly regulated financial domain tasks." Be precise about what you've *actually* shipped vs. what you understand conceptually — Principals get caught overclaiming here.

---

## 🧭 The decision tree (lead with this — it's the Principal answer)

**"Fine-tune last."** Order of interventions by cost/effort:

1. **Prompt engineering** — cheapest, fastest, most iterable. Exhaust first.
2. **RAG** — for knowledge, freshness, citations, and reducing hallucination. Solves most "the model doesn't know X."
3. **Few-shot / in-context** — steer format & behavior without training.
4. **Fine-tuning** — when you need consistent *format/style/behavior*, latency (smaller specialized model beats large general one), domain tone, or to bake in patterns that are expensive to prompt every time.
5. **Pre-training / continued pre-training** — almost never justified; huge cost.

**Rule of thumb to say:** *"RAG changes what the model knows; fine-tuning changes how it behaves. If the failure is 'wrong facts,' I reach for retrieval. If it's 'right facts, wrong form/consistency/tone,' I consider fine-tuning. Usually the answer is both — fine-tune for behavior, RAG for knowledge."*

---

## 🔧 LoRA / QLoRA (know the mechanics)

- **Full fine-tuning:** update all weights. Expensive (memory, compute), risk of **catastrophic forgetting**, per-task model copies.
- **LoRA (Low-Rank Adaptation):** freeze base weights, inject small trainable low-rank matrices (A·B) into attention/linear layers. Train ~0.1–1% of params. Small adapters (MBs), swappable per task, cheap.
- **QLoRA:** LoRA on top of a **4-bit quantized** base model (NF4 quant, double quantization, paged optimizers). Lets you fine-tune large models on a **single GPU**. Trade-off: slight quality/precision hit, more than offset by accessibility.
- **Key knobs:** rank `r` (capacity vs overfit), `alpha` (scaling), target modules (which layers get adapters), dropout, learning rate.
- **Serving:** multiple LoRA adapters on one base model (adapter hot-swap / multi-LoRA serving, e.g., vLLM/S-LoRA) → cost-efficient multi-tenant fine-tuning. Good "scale" answer.

---

## 🎯 Alignment (regulated-domain flavor)

- **SFT (supervised fine-tuning)** — instruction/response pairs; the workhorse for domain behavior.
- **Preference alignment:** **RLHF** (reward model + PPO) vs **DPO** (direct preference optimization — simpler, no separate reward model, popular default now). Mention **RLAIF** (AI feedback) and **KTO** as alternatives.
- **In a regulated domain, "alignment" =** making the model reliably follow policy: cite sources, refuse out-of-scope, never give unlicensed financial advice, respect data-handling rules, produce auditable structured output. Often achievable via SFT on curated policy-compliant examples + guardrails, *without* full RLHF.
- **Constitutional / policy-conditioned approaches** — encode compliance rules explicitly.

---

## 🗂️ Data — the actual hard part (your dataset-generation strength shines here)

- **Data quality > algorithm.** A clean, representative, correctly-labeled dataset beats a fancier method.
- **Sourcing:** curated production traffic (with consent/compliance), SME-labeled examples, **synthetic generation** (use a strong model to generate + a verifier/human to filter). You've done dataset generation — tell that story.
- **De-dup, decontaminate (no eval leakage), balance, PII-scrub** — especially with financial data.
- **Splits:** train/val/test with a held-out regression/eval set that never touches training.
- **Compliance:** provenance/lineage of training data, consent, data residency, right-to-be-forgotten implications. This is a *real* fintech concern — mention it.

---

## 📏 Evaluating a fine-tune

- Compare against base model + RAG baseline on the **golden set** (see [04](04_LLMOps_Eval_Guardrails.md)).
- Watch for **catastrophic forgetting** (test general capabilities, not just the target task) and **overfitting** to training style.
- Task metrics + safety/guardrail metrics + latency/cost. Ship only if it beats the cheaper baseline meaningfully.

---

## 🎙️ Likely questions + scaffolds

- **"When would you fine-tune vs RAG vs prompt?"** → the decision tree above. Lead with "fine-tune last," give the knowledge-vs-behavior heuristic.
- **"Explain LoRA/QLoRA and when you'd pick each."** → mechanics above; LoRA when you have GPU headroom, QLoRA when memory-constrained or fine-tuning large models cheaply; both for swappable multi-task adapters.
- **"How would you fine-tune for a regulated financial task?"** → curated + synthetic-then-verified data, PII-scrubbed with provenance, SFT for behavior + policy compliance, DPO if you have preference data, evaluate for forgetting + safety, guardrails still wrap it, full data/version lineage for audit.
- **"How do you serve many fine-tuned variants cost-efficiently?"** → multi-LoRA serving on a shared base (adapter hot-swap), model gateway routing, quantized serving; avoid N full model copies.
- **"Would you fine-tune a frontier model or a small open one?"** → depends: open small model (Llama/Mistral/Qwen class) via LoRA when you need control, cost, latency, data residency, or on-prem; hosted/frontier + RAG + prompt when speed-to-value and quality dominate and data policy allows. Tie to build-vs-buy ([09](09_Leadership_and_Behavioral.md)).

> **Honesty note:** If your hands-on has been mostly RAG + prompt + orchestration and less production LoRA training, say exactly that: *"I've architected the fine-tune vs RAG decision and run LoRA experiments; at [company] the winning call was usually RAG + prompt because [reason]. I'm strong on the decision framework and the eval; large-scale training runs are where I'd lean on/partner with an applied-science function."* Principals are trusted for judgment, not for pretending. Overclaiming here is the fastest way to lose credibility.
