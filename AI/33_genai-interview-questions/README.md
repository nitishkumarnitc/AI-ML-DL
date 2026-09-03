# 33 — 30 GenAI Interview Questions (Real, Asked at FAANG-adjacent Companies)

> Source: [AmanAI Lab — "30 GenAI Interview Questions ASKED at FAANG in 2026"](https://www.youtube.com/watch?v=spg2na6stmc) (63 min). Notes built from the real spoken transcript — every question, answer, and worked example below comes from the video, cleaned up and organised, not invented.

---

## What this actually is

Not a "theory" list. The presenter is explicit throughout: these are **real-time questions** — asked in real interviews — and the emphasis is on *how to structure the answer* as much as the answer itself. Three habits recur across all 30:

1. **Never give a one-sided answer to a "which is better" question.** RAG vs fine-tuning, GPT-5 vs Claude vs Llama — the correct move every time is to name the deciding *factors* and say "it depends on the use case," then actually walk through the factors. Committing to one side is the trap the interviewer sets.
2. **Answer in points, not paragraphs**, and name specific tools (Pinecone, Qdrant, Redis, LangGraph, Cohere Rerank) rather than speaking generically. Specificity is read as seniority.
3. **Always have one real failure story ready.** Several questions (debugging RAG, the "worked for 6 months then broke," the production post-mortem) are graded on whether you can narrate a genuine failure and fix, not a hypothetical.

---

## Files

| File | Covers | Video's own question numbers |
|---|---|---|
| [`01-rag-vs-finetuning-and-training-stages.md`](01-rag-vs-finetuning-and-training-stages.md) | RAG vs fine-tuning decision factors; pre-training vs fine-tuning vs instruction-tuning | Q1, Q7 |
| [`02-model-selection-and-system-architecture.md`](02-model-selection-and-system-architecture.md) | Choosing between frontier/open models; billion-document search architecture; multi-hop retrieval; when prompting stops being enough | Q2, Q4, Q5, Q6 |
| [`03-debugging-rag-and-evaluating-it.md`](03-debugging-rag-and-evaluating-it.md) | Debugging a RAG system giving wrong answers in production; the 3-level RAG eval framework; hallucination detection; regression suites; offline vs online eval | Q3, Q21, Q22, Q24, Q25 |
| [`04-production-cost-latency-and-monitoring.md`](04-production-cost-latency-and-monitoring.md) | Cutting a ₹50L/month LLM bill; sub-500ms latency; production monitoring; diagnosing "it worked for 6 months then broke"; A/B testing prompts | Q8, Q9, Q10, Q11, Q12, Q13 |
| [`05-security-compliance-and-safety.md`](05-security-compliance-and-safety.md) | HIPAA-compliant GenAI; preventing data leaks; RBAC in RAG; PII in training data; prompt-injection defence; compliance auditing; data residency; handling a viral offensive-response incident | Q14–Q20, Q23 |
| [`06-agentic-ai-and-mcp.md`](06-agentic-ai-and-mcp.md) | When to build an agent vs a simple LLM call; preventing infinite agent loops; what MCP actually is and why it exists; agentic AI in one worked example | Q26, Q27, Q28, Q29 |
| [`07-the-production-postmortem-question.md`](07-the-production-postmortem-question.md) | The closing question — narrating a GenAI product that failed in production — plus the presenter's cross-cutting interview tips | Q30 |

---

## The cross-cutting interview tip, stated once so it isn't repeated 30 times

> **"Never tell the interviewer 'RAG is better' or 'fine-tuning is better.' If you say that, they will give you a use case that breaks your answer. Always say: it depends on the use case, and here are the factors."**

This applies to nearly every comparison question in the set (RAG vs fine-tuning, GPT-5 vs Claude vs Llama, offline vs online eval, agent vs simple LLM call). The presenter names this explicitly as *the* trap interviewers set, and structures nearly every answer around naming factors rather than picking a side.

---

## Where this connects in the rest of the repo

| This video's topic | Deeper treatment already in this repo |
|---|---|
| RAG vs fine-tuning, chunking, reranking | [`../12_rag/`](../12_rag/README.md) |
| Fine-tuning mechanics (LoRA/QLoRA) | [`../02_fine-tuning-and-alignment/`](../02_fine-tuning-and-alignment/README.md) |
| Evaluation (RAG triad, hallucination detection, G-Eval, regression suites) | [`../16_evals/`](../16_evals/README.md) |
| Prompt injection, jailbreak detection, output filtering | [`../03_llm-security-and-guardrails/`](../03_llm-security-and-guardrails/README.md) |
| Agentic loops, infinite-loop prevention, multi-agent design | [`../05_multi-agent-frameworks/`](../05_multi-agent-frameworks/README.md) · [`../13_langgraph/`](../13_langgraph/README.md) |
| MCP in depth | [`../15_mcp/`](../15_mcp/README.md) |
| Cost/latency arithmetic done properly, at system-design depth | [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md) |
| A full mock-interview loop with model answers | [`../19_agentic-ai-interview/`](../19_agentic-ai-interview/README.md) |

This folder is the fast, question-and-answer version. Use it to rehearse the *shape* of an answer in under two minutes each; use the linked folders when you need the underlying mechanism cold.
