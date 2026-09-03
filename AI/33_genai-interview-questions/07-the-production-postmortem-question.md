# 07 · The production post-mortem question, and closing tips

> ← [`06-agentic-ai-and-mcp.md`](06-agentic-ai-and-mcp.md) · **Index:** [`README.md`](README.md)

---

## Q30 — Tell me about a GenAI product you built that failed in production

The final question of the set, and the presenter treats it as the most important one to actually prepare a real answer for — not a hypothetical, an honest one.

### The structure to answer in

```
1. CONTEXT       — what were you building, and why
2. WHAT WENT WRONG   — be specific: hallucination? cost? latency? user complaints?
3. HOW YOU DIAGNOSED IT
4. THE FIX
5. THE LESSON LEARNED — stated honestly
```

The presenter's guidance: don't lead by saying you never had a project fail. Say you built a PoC / project, deployed it, and **real issues showed up in production** — most commonly at the RAG/context level or the cost level (the model starts hallucinating, or the response quality degrades under real traffic in ways the demo never showed). Then walk through how you diagnosed it (citations? reranking? context handling?) and what you changed.

### The worked template answer given, verbatim in structure

> **"We built a RAG chatbot for HR queries. After launch, satisfaction was only 40%. On investigation, we found our chunks were too small — 200 tokens — so the AI was missing context spanning multiple chunks. We increased chunk size to 800 tokens with 100-token overlap. Satisfaction jumped to 85%."**

That's the shape of a strong answer: **a specific number before the fix, a specific mechanism identified, a specific change made, a specific number after.** Not "we improved it" — the before/after numbers and the named root cause are what make it credible.

**Standing advice, given as a rule rather than a suggestion for this question specifically:**

> **"Always prepare one real failure story before any senior-level interview. The higher the level you're interviewing for, the more certain it is that a failure story will come up — have the real one ready, with how you diagnosed and fixed it."**

---

## The recurring shapes across all 30 questions

Reading the whole set together, four structural habits repeat constantly enough to be worth naming as a checklist of their own — useful to run through before *any* GenAI interview, regardless of which specific question comes up:

| Habit | Where it showed up |
|---|---|
| **Never pick a side on a "which is better" question — name the factors instead** | Q1 (RAG vs fine-tune), Q2 (model choice), Q25 (offline vs online eval), Q26 (agent vs LLM call) |
| **Answer in points, with named tools, not a paragraph** | Q4 (billion-doc search), every architecture-shaped question |
| **When debugging, check the earliest stage in the pipeline first, not the model** | Q3 (RAG debugging: "80% of bugs are at retrieval, not the LLM"), Q12 (six-months-later failure) |
| **Have one real, specific, numbered failure story ready** | Q3, Q12, Q30 explicitly; usable as evidence in Q21/Q24 too |

---

## What the presenter explicitly did *not* cover in depth

Said outright, worth being honest about rather than inventing: several answers point to a fuller written breakdown ("in my documentation," "in my 5-part agentic series") that isn't part of *this* video's own spoken content. Where that happened — the deeper mechanics of infinite-loop prevention (Q27) and some of the cost-formula detail in Q5 — the notes above capture exactly what was said on camera and no more. For the fuller mechanics, the cross-references in [`README.md`](README.md) point to where this repo covers those topics in depth.

---

> ← [`06-agentic-ai-and-mcp.md`](06-agentic-ai-and-mcp.md) · **Index:** [`README.md`](README.md)
