# 12 — Study Plan

> Two-week plan (assuming ~2 hrs/weekday, more on weekends) + a 48-hour crash version. Adjust to your actual timeline. Everything is **active recall + out-loud rehearsal**, not passive reading.

---

## 🗓️ Two-Week Plan

### Week 1 — Depth (build the technical case)

**Day 1 — Framing & self-audit**
- Read [01](01_Company_and_Role_Strategy.md) + [README](README.md). Research the specific company (products, recent news, funding, leadership). Verify their stats.
- Write your one-paragraph pitch + 3 proof pillars ([01](01_Company_and_Role_Strategy.md)). Say it out loud 5×.
- List every claim in the recruiter email → note which story you'll tell for each.

**Day 2 — Agentic AI** → [02](02_Agentic_AI_and_Orchestration.md)
- Study the file. Draw the agent stack + 3 multi-agent patterns from memory.
- Answer mock Qs 1–18 out loud. Nail LangGraph-vs-AutoGen and "when NOT to use agents."

**Day 3 — RAG & Retrieval** → [03](03_RAG_and_Retrieval.md)
- Study. Draw the RAG pipeline from memory. Explain hybrid search + RRF + reranking + GraphRAG out loud.
- Mock Qs 19–34. Rehearse the "10M loan docs" design.

**Day 4 — LLMOps / Eval / Guardrails** → [04](04_LLMOps_Eval_Guardrails.md)
- Study. This is your edge — go deep. Prep the eval-framework + hallucination-control + guardrails answers cold.
- Mock Qs 35–50. Rehearse "how do you build trust with regulators."

**Day 5 — Fine-tuning + Distributed Systems** → [05](05_FineTuning_and_Alignment.md), [06](06_Distributed_Systems_Backend.md)
- Fine-tune decision tree + LoRA/QLoRA mechanics (Qs 51–59). Be honest about hands-on depth.
- Kafka/Redis/inference/AWS (Qs 60–75). **Write down your real latency/cost numbers.**

**Weekend 1 — System Design intensive** → [07](07_System_Design_HLD_LLD.md)
- Study the framework + reference architecture. Memorize the platform skeleton diagram.
- Fully whiteboard 3 case studies out loud (agentic platform, doc-intelligence agent, eval platform).
- Do 1 timed 45-min mock design (Qs 76–88) — record yourself, critique.

### Week 2 — Breadth, polish, rehearsal

**Day 8 — Coding** → [08](08_Coding_and_DSA.md)
- Write the applied snippets from memory: rate limiter, LRU, retry/backoff, async-bounded LLM calls, agent loop.
- 3–4 medium DSA (hashmap, heap/top-k, graph/toposort).

**Day 9 — Coding cont.**
- 1 timed 45-min live-coding mock, out loud. Practice narrating decisions + complexity.
- Redo any weak applied problem.

**Day 10 — Leadership & Behavioral** → [09](09_Leadership_and_Behavioral.md)
- Write all 8–10 STAR stories (with numbers). Map each to themes.
- Rehearse Qs 102–118 out loud. Nail "why this company," "technical multiplier," "build vs buy," "first 90 days."

**Day 11 — Domain + Questions-to-ask** → [10](10_Questions_to_Ask_and_Redflags.md)
- Fintech/regulated-AI framing (Qs 119–122). Prep your questions per interviewer.
- Comp/leveling prep. Decide your numbers + walk-away point.

**Day 12 — Full mock loop**
- Simulate: 1 design + 1 agentic deep-dive + 1 behavioral, back to back, out loud (ideally with a peer/mentor).
- Note gaps.

**Weekend 2 — Fill gaps + polish**
- Re-drill the "20 you must nail" ([11](11_Mock_Questions_Bank.md)).
- Re-whiteboard your weakest design case.
- Re-tell your weakest 3 STAR stories until crisp.

**Day before**
- Light review only (README + [01](01_Company_and_Role_Strategy.md) + your pitch + the 20 must-nail). Skim diagrams. Sleep. No cramming.

---

## ⚡ 48-Hour Crash Version

**Day 1 (AM):** [01](01_Company_and_Role_Strategy.md) framing + write pitch/pillars + company research. [11](11_Mock_Questions_Bank.md) — read the "20 must-nail."
**Day 1 (PM):** [02](02_Agentic_AI_and_Orchestration.md) + [03](03_RAG_and_Retrieval.md) + [04](04_LLMOps_Eval_Guardrails.md) — study + answer the ⭐ questions out loud.
**Day 2 (AM):** [07](07_System_Design_HLD_LLD.md) — memorize the framework + platform diagram; whiteboard 2 cases. Skim [06](06_Distributed_Systems_Backend.md) + write your latency/cost numbers.
**Day 2 (PM):** [09](09_Leadership_and_Behavioral.md) — write top 6 STAR stories + "why this company" + "first 90 days" + "build vs buy." Prep [10](10_Questions_to_Ask_and_Redflags.md) questions. Rehearse the 20 must-nail once more.

---

## ✅ Readiness checklist (tick before the loop)

- [ ] Can deliver the one-paragraph pitch smoothly.
- [ ] 8–10 STAR stories written, each with numbers, each mapped to a theme.
- [ ] Can draw the agentic platform architecture from memory.
- [ ] LangGraph vs AutoGen, hybrid search, eval framework, hallucination control — answerable cold.
- [ ] Real latency + cost + scale numbers memorized.
- [ ] Fine-tuning depth: honest, precise scope of what you've shipped.
- [ ] 2–3 system-design cases whiteboarded out loud.
- [ ] Applied coding snippets writable from memory.
- [ ] "Why this company," "first 90 days," "technical multiplier," "build vs buy" — crisp.
- [ ] 3–4 sharp questions per interviewer type prepared.
- [ ] Comp expectations + walk-away point decided.
- [ ] Verified current company facts (don't quote stale numbers).

---

## 🎯 The three things that win this loop
1. **Judgment over trivia** — always name the trade-off, decide, justify, say what you'd measure.
2. **The fintech lens** — auditability, guardrails, human-in-loop, cost-of-being-wrong on every answer.
3. **Multiplier evidence** — show impact measured in *other engineers*, not just your own output.
