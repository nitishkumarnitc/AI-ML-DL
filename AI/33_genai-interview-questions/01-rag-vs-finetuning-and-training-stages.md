# 01 · RAG vs fine-tuning, and the three training stages

> **Index:** [`README.md`](README.md) · **Next:** [`02-model-selection-and-system-architecture.md`](02-model-selection-and-system-architecture.md) →

---

## Q1 — When would you choose fine-tuning over RAG, and when RAG over fine-tuning?

**The trap:** picking a side. The presenter is explicit — never tell the interviewer "RAG is better" or "fine-tuning is better." Say it depends on the use case, then walk the factors.

### What each actually is

| | Fine-tuning | RAG |
|---|---|---|
| Mechanism | Changes the model's **weights** | Weights are **never touched** |
| What it needs | A domain-specific dataset, trained into the model | A document store, retrieved at query time |
| Cost | Training cost, upfront | Retrieval cost, ongoing, generally lower |

> **The two one-line explanations the presenter gives, worth keeping verbatim:**
> *"RAG is like giving the AI a textbook to read each time. Fine-tuning is like sending the AI to school to permanently learn the skill."* Use the textbook for facts that change; use the school for skills that stay.

### When to choose RAG

- Your data **changes often**, and you need the answer to reflect the latest version
- You need to **show sources / proper citation** for where an answer came from
- You have **private documentation the model doesn't already know**

### When to choose fine-tuning

- You need a **specific style or format** every time — the answer cannot vary in structure (RAG doesn't guarantee this; the same query can come back formatted differently)
- **Latency matters more than freshness** — fine-tuning bakes the behaviour in, so there's no retrieval step slowing you down
- You have on the order of **1,000+ examples of clean input→output pairs**, each output in a consistent structured format

### The worked example (verbatim from the video)

> A law firm wants a legal-assistant chatbot that must stay updated with new legal cases (cases change constantly → **use RAG**), but the firm *also* wants the AI to always answer in **formal legal language with a specific structure** (→ **fine-tuning**). The honest answer is **both together** — RAG for the changing case data, fine-tuning for the fixed output format and tone.

That's the actual answer shape to give in an interview: not "RAG" or "fine-tuning," but a combination justified by two different requirements pulling in different directions.

---

## Q7 — What's the difference between pre-training, fine-tuning, and instruction-tuning?

Interviewers use this to catch candidates who conflate the three. Keep them distinct.

| Stage | What happens | The presenter's analogy |
|---|---|---|
| **Pre-training** | The model learns from a massive general corpus (trillions of tokens of web text). This is where the base weights are formed. Extremely expensive — only large labs do this. | *"Like teaching a baby AI to read by showing it billions of web pages."* Or: sending a kid to school for years to learn everything general. |
| **Instruction-tuning** | *After* pre-training, the model is taught to follow instructions and answer helpfully/politely — to actually respond to a user's query the way a user expects, rather than just predicting the next token. | Teaching the (now-literate) child to follow rules and answer politely. |
| **Fine-tuning** | Teaching the model **one specific skill for one specific business** — e.g. a medical-AI or customer-support variant. | Sending the child for a specific course or specialisation — e.g. a space-specialisation program. |

### The worked example

> Meta pre-trains Llama on ~15 trillion tokens of internet text. It's then **instruction-tuned** to produce "Llama Instruct." A hospital then **fine-tunes** that instruction-tuned model on its own ~15,000 examples of medical text to get a domain-specific medical assistant.

### The interview framing

> "Always distinguish these three clearly. Confused candidates get the stages mixed up and lose points for it. Explain each one, then compare them — don't answer them as if they're the same question."

---

> **Index:** [`README.md`](README.md) · **Next:** [`02-model-selection-and-system-architecture.md`](02-model-selection-and-system-architecture.md) →
