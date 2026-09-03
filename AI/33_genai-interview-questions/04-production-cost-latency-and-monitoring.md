# 04 · Production cost, latency, and monitoring

> ← [`03-debugging-rag-and-evaluating-it.md`](03-debugging-rag-and-evaluating-it.md) · **Index:** [`README.md`](README.md) · **Next:** [`05-security-compliance-and-safety.md`](05-security-compliance-and-safety.md) →

---

## Q8 — How would you design a GenAI app to be robust/scalable in general?

The presenter calls this a common **repeat question** with a short, standard answer: **model routing, aggressive caching, and rate limiting**. (Each of these is expanded in the questions below — the presenter deliberately doesn't re-explain them here and points to the fuller answers.)

---

## Q9 — Your LLM API bill hits ₹50 lakh (~$60K) per month. How would you cut it down?

Framed as an increasingly common real scenario as companies scale LLM usage (the presenter notes this is showing up constantly in production teams now, referencing tools like GitHub Copilot's credit-limit model as a real-world parallel).

### The cost levers, in order

**1. Model routing.** ~70% of real queries don't need your most expensive model. Route simple/factual queries to a cheaper model; reserve the frontier model for genuinely hard queries.

**2. Prompt caching.** Cache the **system prompt / stable prefix** rather than re-sending it on every call. (Anthropic and OpenAI both support prefix caching — the presenter notes this can cut 30–90% of the *repeated* prefix cost.) You don't need to re-hit the full prompt every single time.

**3. Use shorter prompts.**

**4. Self-host an open-source LLM** for the high-volume, simple-query slice of traffic instead of paying per-token for a frontier model on every call.

**5. Cache frequent/repeated queries** outright, so identical or near-identical questions don't hit the model at all.

### The worked example

> A sales company had a **₹50 lakh/month** OpenAI bill. After auditing, they found **60% of queries were simple factual lookups** going to GPT-4 unnecessarily. They switched that slice to **GPT-4o-mini**, keeping the expensive model only for the harder 40%. Same overall service, dramatically lower bill — because the higher-tier model was being used for queries that never needed it.

**Interview framing:** "always remember — higher model use for simple queries is the classic waste. Route by difficulty."

---

## Q10 — Your chatbot needs to respond in under 500 milliseconds. How do you achieve this?

This is a latency question, and the presenter's rule: **latency = streaming + smaller model + caching**, always mentioned together.

| Lever | What it does |
|---|---|
| **Streaming** | First token should appear in ~100–200ms. Don't make the user wait for the full response — stream tokens as they generate |
| **Use a smaller model on the hot path** | Haiku-class / GPT-mini-class models for the latency-critical path |
| **Prompt caching** | Keep the system prompt / retrieval index pre-computed rather than rebuilt per request |
| **Reduce max tokens** | If the question is small, don't let the model generate a huge answer — cap response length so token count (and thus generation time) stays low |
| **Speculative decoding** | A small model predicts tokens; a larger model verifies. Since most predictions are accepted, you get large-model quality at closer to small-model speed |

> **The analogy:** *"Like making instant food — pre-cut the vegetables (pre-computed embeddings), pre-heat (prompt caching), serve in smaller portions (smaller models), and start serving as soon as the first item is ready (streaming) — the customer feels served instantly."*

The presenter also points to the real UX pattern in tools like GitHub Copilot: it shows incremental "thinking" text rather than a blank wait — the user perceives responsiveness even while the full answer is still generating.

---

## Q11 — How do you monitor GenAI in production?

Five categories of things to monitor, using something like Azure App Insights (or equivalently LangSmith, Langfuse, Arize Phoenix — named later in the transcript) as the logging/observability layer.

| Category | What's tracked |
|---|---|
| **Quality metrics** | Faithfulness, relevance, hallucination rate, confidence — "the final eval layer" |
| **Performance** | Latency, whether tokens are streaming on time |
| **Cost** | Ongoing cost per call/session |
| **User feedback** | Thumbs up / thumbs down signals collected directly in the product |
| **System health** | API errors, rate-limit hits, general availability |

> **The analogy:** *"Like running a hospital — you measure recovery rate, wait times, bills, patient satisfaction. Without monitoring, anyone can exploit a problem and you'd never know."*

**Interview tip:** name real tools — LangSmith, Langfuse, Arize Phoenix — and mention that these platforms let you **set alerts for any metric dropping more than 10%**.

---

## Q12 — Your GenAI app worked great, then six months later it started failing. What's the issue?

A diagnosis question. The presenter's checklist of the most likely causes, roughly in order of likelihood:

1. **The underlying provider model was upgraded** silently (OpenAI/Anthropic push a model update; your prompt's assumptions no longer hold exactly)
2. **Data drift** — the underlying data your RAG retrieves from has changed shape over time
3. **Vector-DB population drift** — bad or noisy documents got added to the index over time, degrading retrieval quality
4. **Prompt drift** — someone on the team made a small edit to the prompt that broke an edge case (removed a guard the original prompt had)
5. **Dependency updates** — a library/framework version bump (e.g. a LangChain version bump) changed behaviour under the hood

**Interview framing:** work through these as a checklist — model update? data drift? document noise? prompt edit? dependency bump? — rather than guessing at one cause.

---

## Q13 — How would you do A/B testing on a prompt in production?

Steps:

**1. Define your success metric first** — e.g. user satisfaction, task completion rate.

**2. Set up a feature flag** to route ~50% of traffic to prompt A, ~50% to prompt B.

**3. Log everything** — input, output, and the metric, for every request.

**4. Run for at least ~1,000 samples/variant** for statistical significance. Use **LLM-as-judge** for automatic scoring at scale, plus **human review on a sample** to sanity-check the automatic scores.

**5. Pick the winner** based on the combined signal, then roll it out to everyone.

### The worked example

> An e-commerce company tested two product-description prompts: one that just wrote a description, another that explicitly wrote **"three benefits, ending with a call to action."** After 500 test prompts, the structured version **increased click-through rate by 23%**. That result was enough to roll the new prompt out to all traffic.

---

> ← [`03-debugging-rag-and-evaluating-it.md`](03-debugging-rag-and-evaluating-it.md) · **Index:** [`README.md`](README.md) · **Next:** [`05-security-compliance-and-safety.md`](05-security-compliance-and-safety.md) →
