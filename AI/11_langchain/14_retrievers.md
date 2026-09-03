# 14. Retrievers in LangChain  (Video 13)

> 📺 [Watch on YouTube](https://www.youtube.com/playlist?list=PLKnIA16_RmvaTbihpo4MtzVm4XOQa0ER0) · ⏱️ ~51 min · CampusX — Generative AI using LangChain
>
> 🔎 **RAG building block #4.** Full worked version in the RAG series — see **[detailed notes → `rag/05_retrievers.md`](../12_rag/05_retrievers.md)**. This page is the LangChain-course summary + pointers.

---

## 🎯 What You'll Learn
- What a **Retriever** is and how it differs from a raw vector store.
- The main retriever types: vector-store (similarity / MMR), MultiQuery, Contextual Compression.
- Why a retriever is a `Runnable` and slots straight into chains.

---

## 📖 Overview / Why It Matters
Step 5 — the "R" in RAG (`Load → Split → Embed → Store → **Retrieve**`). A **Retriever** is a uniform, composable interface whose one job is: *given a query string, return the most relevant `Document`s*. It's a `Runnable`, so it drops directly into an LCEL chain (`retriever | prompt | model | parser`). A vector store *can* search, but the Retriever is the standard interface chains expect — and some retrievers add logic beyond plain similarity search.

---

## 🧠 Key Concepts

### Retriever ≠ vector store
A vector store does similarity search; a retriever is the **abstraction** over "get relevant docs." Some retrievers wrap a vector store; others wrap external search, wikipedia, or add re-ranking/expansion. All share `.invoke(query) -> list[Document]`.

### Key retriever types
| Retriever | What it does | Why |
|---|---|---|
| **Vector-store (similarity)** | `vs.as_retriever()` top-k cosine | the default |
| **MMR** (Maximal Marginal Relevance) | balances relevance **and diversity** | avoids k near-duplicate chunks |
| **MultiQueryRetriever** | LLM rewrites the query into several variants, unions results | beats a single phrasing of the question |
| **ContextualCompressionRetriever** | an LLM/compressor trims retrieved docs to just the relevant bits | denser, less-noisy context |

### It's a Runnable
Because retrievers implement the `Runnable` interface, you compose them like everything else (see [Runnables](09_runnables-part1.md)):
```
retriever | format_docs | prompt | model | parser
```

---

## 💻 Code Examples

```python
# 1. Plain similarity retriever from a vector store
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
docs = retriever.invoke("How does attention work?")

# 2. MMR — relevance + diversity
retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 4, "fetch_k": 20, "lambda_mult": 0.5},
)

# 3. MultiQuery — LLM expands the query into variants
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI
mq = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(), llm=ChatOpenAI(model="gpt-4o-mini")
)

# 4. Contextual compression — trim docs to the relevant parts
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
compressor = LLMChainExtractor.from_llm(ChatOpenAI(model="gpt-4o-mini"))
cc = ContextualCompressionRetriever(
    base_compressor=compressor, base_retriever=vectorstore.as_retriever()
)
```

---

## ⚠️ Gotchas & Tips
- Use **MMR** when top-k results are near-duplicates (redundant context wastes the prompt budget).
- **MultiQuery** helps when users phrase questions differently than the source text — but it costs extra LLM calls.
- **Contextual compression** improves signal-to-noise but adds latency/cost (an LLM pass per retrieval).
- Retrievers return `Document`s — remember to format them (join `page_content`) before stuffing into a prompt.

---

## 🧠 Key Takeaways
- A **Retriever** is the standard `query → relevant Documents` interface; it's a `Runnable`, so it composes in chains.
- Beyond plain similarity: **MMR** (diversity), **MultiQuery** (query expansion), **Contextual Compression** (trim noise).
- Choose based on your failure mode: duplicates → MMR, phrasing mismatch → MultiQuery, noisy chunks → compression.
- 👉 Full walkthrough: [`rag/05_retrievers.md`](../12_rag/05_retrievers.md).

---

## ❓ Revision Questions
1. How does a retriever differ from a vector store?
2. When does MMR beat plain similarity search?
3. What problem does `MultiQueryRetriever` solve, and what's its cost?
4. What does a Contextual Compression retriever do to retrieved documents, and why?
5. Why is it convenient that a retriever is a `Runnable`?
