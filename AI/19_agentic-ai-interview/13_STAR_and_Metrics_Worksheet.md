# 13 — STAR Stories & Metrics Worksheet

> The one file only **you** can complete. Everything else in this guide is reusable; this is where your real projects, numbers, and decisions go. Fill the `____` blanks, then rehearse out loud. Once filled, hand it back and I'll draft polished, spoken versions.
>
> **Rule:** every story ends in a **number**. "Improved performance" is invisible; "cut p95 from 4.2s → 1.1s" wins loops.

---

## Part 1 — Your Metrics Bank (fill once, reuse everywhere)

These plug into [11c Q61](11c_Answers_Systems_and_Design.md) and many answers. Pull real figures from dashboards/PRs/docs — approximate honestly if exact numbers are gone ("~40%, from memory").

### Latency / performance
- System: `____________________`
- Metric optimized (TTFT / p95 / p99 / throughput): `____________`
- **Before → After:** `________` → `________`
- How (the levers): `________________________________________`
- At what scale (QPS / users / docs): `____________`

### Cost / AWS
- What you reduced (GPU / inference / storage / total AWS): `____________`
- **Before → After** (or % saved): `________` → `________`  (`____% ↓`)
- How: `________________________________________`
- Over what period / at what volume: `____________`

### Scale / throughput
- Peak QPS / req-per-day handled: `____________`
- Data volume (docs / events / GB): `____________`
- Kafka: topics / partitions / consumer groups: `____________`
- Uptime / availability achieved: `____________`

### AI quality
- Task + metric (accuracy / F1 / groundedness / hallucination rate): `____________`
- **Before → After:** `________` → `________`
- Eval method (golden set size, LLM-judge, human): `____________`
- Users / adoption / business impact: `____________`

### Team / leadership
- Engineers mentored / led: `____`
- Teams that adopted your standard/tool/SDK: `____`
- Architecture reviews led: `____`

---

## Part 2 — STAR Stories (target 8–10)

For each: **S**ituation (context + scale), **T**ask (your specific ownership), **A**ction (the *decisions* and trade-offs you made — this is the Principal signal), **R**esult (numbers). Keep each to ~2–3 min spoken.

> ✍️ Tip: write **Action** as decisions, not activities. "I chose LangGraph over AutoGen because auditability > autonomy for regulated data" beats "I used LangGraph."

### Story 1 — Production agentic / multi-agent system  → maps to Q1, Q104
- **S:** `________________________________________`  Scale: `____________`
- **T:** `________________________________________`
- **A (decisions + trade-offs):**
  1. `________________________________________`
  2. `________________________________________`
  3. `________________________________________`
- **R (numbers):** `________________________________________`
- **What broke / what you'd do differently:** `____________________`

### Story 2 — Reliability / eval / caught hallucinations  → Q35, Q36, Q49
- **S:** `____________________`  **T:** `____________________`
- **A:** `________________________________________`
- **R:** `________ (error rate ↓ / incidents prevented / groundedness ↑)`

### Story 3 — Latency / cost win  → Q61, Q68
- **S:** `____________________`  **T:** `____________________`
- **A (levers):** `________________________________________`
- **R:** `latency ____ → ____ , cost ____% ↓ at ____ scale`

### Story 4 — Distributed systems at scale (Kafka/Redis)  → Q60, Q63
- **S:** `____________________`  **T:** `____________________`
- **A:** `________________________________________`
- **R:** `____________________`

### Story 5 — Technical multiplier / mentoring  → Q106, Q111
- **S:** `____________________`
- **A (what you built/standardized that others adopted):** `____________`
- **R:** `____ engineers leveled up / ____ teams adopted / time saved ____`

### Story 6 — Architecture review / influence without authority  → Q108, Q113, Q117
- **S:** `____________________` (a direction you changed without owning the team)
- **A (how: doc / prototype / data / coalition):** `____________________`
- **R:** `____________________`

### Story 7 — Build vs buy decision  → Q107
- **Decision:** built / bought `____________________`
- **Why (factors: TCO, differentiation, compliance, reversibility):** `________`
- **R:** `cost/time saved ____ , outcome ____`

### Story 8 — Failure / decision you got wrong  → Q105
- **S:** `____________________`
- **What you chose & why it was wrong:** `____________________`
- **How you caught + fixed it:** `____________________`
- **How you decide differently now:** `____________________`

### Story 9 — Ambiguity / 0→1  → Q115
- **S (no clear spec):** `____________________`
- **A (how you reduced uncertainty + shipped):** `____________________`
- **R:** `____________________`

### Story 10 — Conflict / saying no  → Q110, Q118
- **S:** `____________________`
- **A (how you navigated, kept the relationship):** `____________________`
- **R:** `____________________`

---

## Part 3 — Positioning Statements (write in your words)

### One-paragraph pitch (from [01](01_Company_and_Role_Strategy.md) — personalize it)
> `________________________________________________________________`
> `________________________________________________________________`

### "Why this company / why this role?" (Q102)
- What genuinely draws you (scale / 0→1 / CTO partnership / regulated-AI hard problems): `____________`
- Tie to your trajectory: `____________________`

### "Why leave your current role?" (Q103)
- Forward-looking reason (never trash current employer): `____________________`

### First-90-days plan (Q109) — 3 bullets in your voice
- Days 0–30 (learn): `____________________`
- Days 30–60 (prove — the exemplar you'd ship): `____________________`
- Days 60–90 (scale — standards/SDK/mentoring): `____________________`

---

## Part 4 — Gap Answers (rehearse these honestly)

### Java/Spring Boot (their core is Java; you're Python/Node/TS)
> `________________________________________________________________`
_(Suggested spine: "My AI services are Python; I read and review Java comfortably and integrate cleanly across the boundary. The JD explicitly values polyglot Python for AI services — that's exactly my lane, and I've partnered with JVM teams before at [____].")_

### Fine-tuning at scale (if your hands-on is more RAG/prompt than LoRA)
> `________________________________________________________________`
_(Suggested spine: "I own the fine-tune-vs-RAG decision and have run LoRA experiments; in production the winning call was usually RAG + prompt because [____]. I'm strongest on the decision framework and eval; large-scale training runs are where I'd partner with applied science.")_

### Principal-scope (if title has been Senior/Lead)
> `________________________________________________________________`
_(Point to blast-radius stories: Story 5, 6, 7 above.)_

---

## ✅ Done when
- [ ] Every metric blank in Part 1 has a real (or honestly-approximate) number.
- [ ] At least 8 STAR stories drafted, each ending in a number.
- [ ] Pitch + "why this company" + "first 90 days" written in your own voice.
- [ ] Gap answers rehearsed out loud without hesitation.

> When these blanks are filled, send it back — I'll turn each into a tight, spoken-length answer and slot the numbers into [11c](11c_Answers_Systems_and_Design.md) and [11d](11d_Answers_Coding_Leadership_Domain.md).
