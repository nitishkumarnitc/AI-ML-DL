# 02 · Model selection and system architecture

> ← [`01-rag-vs-finetuning-and-training-stages.md`](01-rag-vs-finetuning-and-training-stages.md) · **Index:** [`README.md`](README.md) · **Next:** [`03-debugging-rag-and-evaluating-it.md`](03-debugging-rag-and-evaluating-it.md) →

---

## Q2 — How do you decide between GPT-5, Claude, and an open-source model like Llama?

Same trap as Q1: don't just declare a winner. The presenter's structure is **five factors**, and you pick the winner *per factor*, then combine.

| Factor | Where each tends to win |
|---|---|
| **Cost** | Llama is free to self-host, but you pay for GPU infrastructure. GPT/Claude are token-metered on the provider's cloud. Where raw cost-per-call matters most at low/no infra investment, Llama wins |
| **Privacy** | If data can't leave your servers, **open-source hosted locally** wins by default — the data never leaves your infrastructure |
| **Quality** | Claude is called out for strong writing and reasoning; GPT for code quality; Llama "good but not as good" as either |
| **Latency** | Smaller/faster variants (Haiku-class, GPT-mini-class) beat the larger open-source models on raw response speed |
| **Customization** | Only open-source lets you do **full fine-tuning** — closed models limit you to prompting/light adaptation |

> **The analogy given:** *"Choosing a car — need luxury and best quality, get Claude or GPT. Need a private vehicle, get Llama. Need a cheap daily-use car, get a mini version like Haiku or GPT-mini."*

### The worked example

> A hospital **cannot** send patient data to OpenAI due to privacy law → pick **Llama 4**, hosted on their own infrastructure, fine-tuned on medical data. A marketing agency with **no privacy constraint** that wants the best writing quality → pick **Claude 4.7**. Same question, opposite answer, because the deciding factor differs.

**Interview tip stated directly:** always mention privacy and cost first — "it shows you're thinking like an engineer, not just a developer."

---

## Q4 — How would you design a chatbot that needs to search across one billion documents?

A system-design-level question. The instinct to avoid: giving a single flat answer. The presenter's structure is an explicit **four-layer pipeline**, and the tip is to answer in points with named tools, not a paragraph.

```
1. SMART ROUTING
   Classify whether the query even needs a search at all — some questions
   can be answered without retrieval. Route via something like LangGraph,
   deciding whether to hit a search API, Postgres, or cache.

2. HYBRID SEARCH
   BM25 (keyword search) + cosine similarity / dot product (vector search),
   combined — not vector search alone.

3. RERANKING
   Apply a reranker (cross-encoder style) on the top results, because the
   correct answer is often NOT first in the initial retrieval — it might be
   ranked 9th or 10th out of the top-10 candidates before reranking.

4. CACHING
   Don't re-run retrieval for frequent/repeated queries — cache them
   (e.g. Redis).
```

> **The analogy:** *"You don't check every book in a huge library first — you decide what section to search (routing), search the catalogue (hybrid search), pick the best book (reranking), and cache frequent requests."*

**Interview tip:** name actual tools when you answer — "Pinecone or Qdrant" for the vector DB, "Cohere Rerank / mono-cross-encoder" for the reranker, "Redis" for the cache. Naming specific tools is explicitly called out as more impressive than describing the pattern generically.

---

## Q5 — When does prompt engineering stop being enough, and you need fine-tuning?

Three concrete signals given, all measurable:

| Signal | What it looks like |
|---|---|
| **Context-limit pressure** | Your prompt has grown past ~3,000 tokens just to control behaviour — you're paying (in tokens and money) for control that fine-tuning would bake in for free |
| **Output inconsistency** | Even with strong instructions, the output format is inconsistent — the model keeps "forgetting" the format no matter how firmly you word the instruction |
| **Repeated correction loops** | You find yourself continuously asking follow-up questions / corrections to get the same kind of output |

The presenter frames the rough math: if your prompt overhead alone exceeds ~2,000 tokens per call with meaningful call volume, fine-tuning tends to **pay for itself within about three months** — the training cost is recovered by the per-call token savings.

---

## Q6 — How do you handle a query that needs information from multiple documents?

This is **multi-hop retrieval**. Three approaches, in the order given:

**1. Query decomposition** — break the user's single question into sub-questions, retrieve for each sub-question independently, then combine the answers.

**2. Iterative retrieval** — retrieve once, use what you found to inform the *next* retrieval (the classic "search → read → search again" loop), then combine at the end.

**3. Graph-based retrieval** — use a knowledge graph that links entities properly; answer via the graph's nodes first, then produce the final answer from that.

### The worked example (verbatim structure)

> *"Who is the CEO of the company that bought WhatsApp?"* — you can't answer this in one search. You first have to find **who bought WhatsApp** (Meta), *then* find **the CEO of Meta**. That's query decomposition + a combine step.

### A second worked example

> A finance chatbot is asked to *"compare Q3 2024 revenue with Q3 2025 revenue."* One search won't return both numbers. **Decompose** into "Q3 2024 revenue" and "Q3 2025 revenue," retrieve each separately, then let the model compare the two retrieved numbers accurately.

---

> ← [`01-rag-vs-finetuning-and-training-stages.md`](01-rag-vs-finetuning-and-training-stages.md) · **Index:** [`README.md`](README.md) · **Next:** [`03-debugging-rag-and-evaluating-it.md`](03-debugging-rag-and-evaluating-it.md) →
