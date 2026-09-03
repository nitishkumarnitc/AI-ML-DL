# 5. Retrievers in LangChain

> 📺 [Watch on YouTube](https://www.youtube.com/watch?v=pJdMxwXBsk0&list=PLKnIA16_Rmva0dRLWEHLznSHKbFD_RJfX) · ⏱️ ~51 min · CampusX — Generative AI using LangChain

## 🎯 What You'll Learn

- What a retriever is and how it differs from a vector store
- The two ways to categorize retrievers in LangChain: by **data source** and by **search strategy**
- How the `WikipediaRetriever` and `VectorStoreRetriever` work
- Why plain similarity search isn't always enough, and how **MMR**, **MultiQueryRetriever**, and **ContextualCompressionRetriever** each fix a specific weakness
- How to build and invoke each of these retrievers in code
- Why retrievers matter so much once you start building (and improving) RAG systems

## 📖 Overview

This is the fourth and final "core RAG component" video in the series, after Document Loaders, Text Splitters, and Vector Stores. Once retrievers are covered, the series moves on to building actual RAG applications.

**Definition:** A retriever is a component in LangChain that fetches relevant documents from a data source in response to a user's query.

Think of it as a simple function:

```
Input:  user query (string)
Output: a list of Document objects (the relevant ones)
```

Internally, the retriever goes into a data source — which could be a vector store, a REST API, a website, anything — scans/searches it, decides which documents are most relevant to the given query, and returns them. It behaves like a small search engine sitting in front of your data.

Three things to internalize about retrievers in LangChain:

1. **There is no single "the retriever."** LangChain ships with 20-30+ retriever implementations, each suited to different data sources or search needs.
2. **Every retriever is a Runnable** — exactly like models and prompts. That means every retriever exposes `.invoke(query)`, can be composed with the pipe operator (`|`), and can be dropped straight into an LCEL chain. This is what makes retrievers so easy to plug into RAG pipelines later.
3. **Retrievers can be categorized in two orthogonal ways:**
   - **By data source** — what underlying store/service the retriever searches (Wikipedia, a vector store, arXiv, etc.)
   - **By search strategy** — what algorithm/mechanism the retriever uses to decide relevance (plain similarity, MMR, multi-query expansion, compression, etc.)

## 🔑 Retriever Types

### 1. Wikipedia Retriever *(data-source-based)*

Queries the Wikipedia API directly to fetch content relevant to a query.

- **How it works:** You give it a query (e.g., "Albert Einstein"), it sends that query to the Wikipedia API, and it retrieves the most relevant articles.
- **Important nuance:** matching here is **keyword-based**, not semantic — the API decides relevance by how many keywords in the query match an article, not by embedding similarity.
- **Is it a document loader?** A natural doubt: since it just "loads" Wikipedia articles, isn't this a document loader in disguise? No — a document loader would dump *all* content indiscriminately. This component performs an internal search/ranking step to decide which articles are relevant to the query before returning them, which is why it qualifies as a retriever (there's a form of "intelligence"/selection logic involved).
- Returns results as standard LangChain `Document` objects (with `page_content` and `metadata`).
- Part of `langchain-community` (community-contributed).

### 2. Vector Store Retriever *(data-source-based)*

The most common type of retriever — wraps a vector store and lets you search/fetch documents based on **semantic similarity** using embeddings.

**How it works, step by step:**
1. Documents are stored in a vector store (Chroma, FAISS, Weaviate, etc.).
2. Each document is converted into a dense vector using an embedding model.
3. A user query arrives and is converted into a vector using the same embedding model.
4. The query vector is compared against all document vectors (semantic search).
5. The top-k most similar documents are fetched and returned.

Created directly from a vector store via `.as_retriever(...)`.

**Why not just call `vectorstore.similarity_search()` directly?** Both approaches return identical results for a plain similarity search — so what's the point of wrapping it in a retriever? Two reasons:
- The retriever object is a **Runnable**, so it can be plugged straight into chains (`similarity_search()` cannot).
- More importantly, `.as_retriever()` lets you swap the underlying **search strategy** (e.g., MMR instead of plain similarity) without changing how you call it. `vectorstore.similarity_search()` only ever performs one fixed strategy. This flexibility is the real payoff, and it's what powers the advanced retrievers below.

*(The video also briefly mentions an **Archive/arXiv Retriever**, which scans arXiv for relevant research papers, as another example of a data-source-based retriever.)*

### 3. MMR — Maximal Marginal Relevance *(search-strategy-based)*

**The problem it solves:** Plain similarity search can return *redundant* results. Example: 5 stored documents about climate change — two say almost the same thing ("glaciers melting in the Arctic"), while others cover deforestation, wildfires, and coastal flooding. A query like "What are the adverse effects of climate change?" run through plain similarity search might return the two near-duplicate glacier documents plus one more — wasting two of your three "slots" on repeated information instead of giving diverse perspectives.

**Core philosophy:** Pick results that are not only relevant to the query but also **different from each other**.

**How it works:**
1. Pick the single most relevant document first.
2. For each subsequent pick, choose a document that is still relevant to the query **but as dissimilar as possible from the documents already selected**.
3. Repeat until k documents are selected.

This balances **relevance** against **diversity**, reducing redundancy while keeping quality high.

**Key parameter — `lambda_mult`:** ranges from `0` to `1`.
- `lambda_mult = 1` → behaves exactly like plain similarity search (no diversity weighting).
- `lambda_mult = 0` → maximizes diversity (may sacrifice some relevance).
- In practice, pick a value between 0 and 1 depending on how much diversity you want.

### 4. MultiQueryRetriever *(search-strategy-based)*

**The problem it solves:** Ambiguous or broad user queries. Example: "How can I stay healthy?" could mean "What should I eat?", "How often should I exercise?", or "How do I manage stress?" — each of these has different relevant documents. A single ambiguous query fed into a plain retriever often returns confused, lower-quality results because the retriever may latch onto surface-level keyword overlaps (e.g., a query mentioning "energy" and "balance" accidentally matching an unrelated document about "solar energy systems balancing electricity demand").

**Core philosophy:** Resolve the ambiguity by generating multiple reformulated versions of the query, rather than relying on just one.

**How it works:**
1. The (possibly ambiguous) user query is sent to an LLM.
2. The LLM generates several diverse-but-related variations of the query (e.g., from "How can I stay healthy?" it might generate "What are the best foods to maintain good health?", "How often should I exercise to stay fit?", "What lifestyle habits improve mental and physical wellness?", etc.).
3. Each of these variant queries is run through a base retriever (typically a similarity-search retriever) against the same document store.
4. All the results are merged, duplicates are removed, and the top-k results are returned to the user.

**Demonstrated effect:** With a deliberately ambiguous query ("How to improve energy levels and maintain balance"), the plain similarity retriever got confused and pulled in an irrelevant document about a "solar system" (matching on the words "energy" and "balance"). The `MultiQueryRetriever`, by contrast, generated several health/nutrition-focused query variants and returned only health-and-nutrition documents — no irrelevant solar system result.

### 5. ContextualCompressionRetriever *(search-strategy-based)*

**The problem it solves:** A single stored chunk/document can contain multiple, unrelated topics glued together — for example, a chunk that talks about the Grand Canyon, then photosynthesis, then tourist visits, all in one paragraph. This commonly happens with long source documents where a text splitter doesn't cleanly separate topics (a split can land in the middle of a paragraph, mixing the end of one idea with the start of another). If a user asks "What is photosynthesis?", a normal retriever correctly identifies that this chunk is relevant — but returns the *entire* chunk, including the irrelevant Grand Canyon and tourism sentences. That pollutes the LLM's context and can hurt answer quality and user experience.

**Core philosophy:** Improve retrieval quality by *compressing* each retrieved document down to only the parts relevant to the query, discarding the rest.

**How it works — two components:**
1. **Base retriever** — a normal retriever (e.g., similarity search) that fetches candidate documents (D1, D2, ...) as usual.
2. **Compressor** — typically an LLM (e.g., via `LLMChainExtractor`) that receives each retrieved document together with the original query, and is prompted to trim the document down to just the query-relevant portion, discarding everything else. The output is a new, shorter version of each document (D1', D2', ...) containing only relevant content.

**When to use it:**
- Your documents are long and may contain mixed/multiple topics.
- You want to reduce the context length sent to the LLM.
- You want to improve the answer accuracy of your RAG pipeline by removing noise from retrieved context.

**Demonstrated effect:** Given a chunk mixing Grand Canyon facts and a photosynthesis sentence, querying "What is photosynthesis?" returned only the single relevant sentence about photosynthesis — the Grand Canyon and other unrelated sentences were dropped entirely.

### Other retrievers mentioned (not covered in depth)

The video name-drops several more retrievers available in LangChain and points viewers to the official documentation for details:

- **Parent Document Retriever** — retrieves small child chunks for search, but returns the larger parent document/chunk for context.
- **Time-Weighted Vector Retriever** — factors in recency, favoring newer documents.
- **Self-Query Retriever** — uses an LLM to turn a natural-language query into structured filters against document metadata.
- **Ensemble Retriever** — combines results from multiple retrievers.
- **Multi-Retriever** setups — routing/combining across several retrievers.

LangChain has 20-30+ retrievers in total; only the most broadly useful ones were covered here.

## 💻 Code Examples

> All examples assume `documents` is a list of pre-built `langchain_core.documents.Document` objects, and that an embedding model / LLM (e.g., OpenAI) is configured.

### Wikipedia Retriever

```python
from langchain_community.retrievers import WikipediaRetriever

# top_k_results = how many articles to return, lang = result language (default "en")
retriever = WikipediaRetriever(top_k_results=2, lang="en")

query = "the geopolitical history of india and pakistan from the perspective of a chinese"
docs = retriever.invoke(query)

for doc in docs:
    print(doc.page_content)
    print("-" * 50)
```

### Vector Store Retriever (basic similarity search)

```python
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

documents = [
    Document(page_content="LangChain is used to build LLM based applications."),
    Document(page_content="LangChain provides abstractions to make working with LLMs easy."),
    Document(page_content="Chroma is a vector database optimized for LLM based applications."),
    Document(page_content="Embeddings are vector representations of text used for semantic search."),
]

embedding_model = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embedding=embedding_model)

# Create a retriever from the vector store — top 2 results
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

query = "What is Chroma used for?"
results = retriever.invoke(query)

for doc in results:
    print(doc.page_content)

# Equivalent (but non-Runnable, single-strategy) direct call:
# results = vectorstore.similarity_search(query, k=2)
```

### MMR Retriever (diverse, non-redundant results)

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

vectorstore = FAISS.from_documents(documents, embedding=OpenAIEmbeddings())

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 3, "lambda_mult": 0.5}  # 1 = pure relevance, 0 = max diversity
)

query = "What is LangChain?"
results = retriever.invoke(query)

for doc in results:
    print(doc.page_content)
```

### MultiQueryRetriever (resolving ambiguous queries)

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers.multi_query import MultiQueryRetriever

vectorstore = FAISS.from_documents(documents, embedding=OpenAIEmbeddings())

# Base retriever that MultiQueryRetriever will run each generated query against
similarity_retriever = vectorstore.as_retriever(
    search_type="similarity", search_kwargs={"k": 5}
)

multiquery_retriever = MultiQueryRetriever.from_llm(
    retriever=similarity_retriever,
    llm=ChatOpenAI(model="gpt-3.5-turbo"),  # LLM used to generate query variations
)

query = "How to improve energy levels and maintain balance?"
results = multiquery_retriever.invoke(query)

for doc in results:
    print(doc.page_content)
```

### ContextualCompressionRetriever (trimming irrelevant content per document)

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor

vectorstore = FAISS.from_documents(documents, embedding=OpenAIEmbeddings())

base_retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

llm = ChatOpenAI(model="gpt-4o-mini")
compressor = LLMChainExtractor.from_llm(llm)

compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever,
)

query = "What is photosynthesis?"
results = compression_retriever.invoke(query)

for doc in results:
    print(doc.page_content)
```

## 📊 Retriever Comparison

| Retriever | Category | Problem It Solves | When to Use |
|---|---|---|---|
| **Wikipedia Retriever** | Data source | Fetching relevant, ranked content straight from Wikipedia without manually loading articles | Quick factual/background lookups sourced from Wikipedia |
| **Vector Store Retriever** | Data source | Basic semantic search over your own embedded documents | Default choice for most RAG pipelines; foundation for the advanced retrievers below |
| **Archive/arXiv Retriever** | Data source | Fetching relevant research papers for a query | Research/academic use cases |
| **MMR Retriever** | Search strategy | Top-k results being near-duplicates of each other (redundancy) | You need diverse perspectives/coverage, not just the single best match repeated |
| **MultiQueryRetriever** | Search strategy | Ambiguous, broad, or multi-intent user queries hurting retrieval quality | User queries are short, vague, or could be interpreted multiple ways |
| **ContextualCompressionRetriever** | Search strategy | Retrieved chunks contain mixed/irrelevant content alongside the relevant part | Long or poorly-split documents; need to shrink LLM context / cut noise / improve answer accuracy |

## 🧠 Key Takeaways

- A retriever is a Runnable that takes a query and returns a list of relevant `Document` objects — think of it as a search engine in front of a data source.
- LangChain has many retrievers (20-30+), not just one; they differ by **data source** (Wikipedia, vector store, arXiv, ...) and/or **search strategy** (similarity, MMR, multi-query, compression, ...).
- Because every retriever is a Runnable, it can be invoked with `.invoke()` and dropped directly into LCEL chains — this is central to how RAG pipelines are built later in the series.
- `VectorStoreRetriever` (`.as_retriever()`) does the same thing as `vectorstore.similarity_search()` at its most basic setting, but it unlocks pluggable, more advanced search strategies (like MMR) — which direct vector-store calls cannot do.
- **MMR** trades a bit of relevance for diversity by penalizing documents too similar to ones already picked; tune this with `lambda_mult` (0 = max diversity, 1 = pure relevance).
- **MultiQueryRetriever** uses an LLM to expand one ambiguous query into several clearer variants, retrieves for each, then merges/deduplicates — reducing the chance of an off-topic result caused by keyword confusion.
- **ContextualCompressionRetriever** uses an LLM (a "compressor," e.g. `LLMChainExtractor`) to trim each retrieved document down to just the query-relevant sentences, which is especially useful when text splitting produces chunks with mixed topics.
- Retrievers are one of the primary levers for improving a RAG system: when a basic RAG pipeline underperforms, swapping in a more advanced retriever (MMR, MultiQuery, Contextual Compression, or others like Parent Document / Self-Query / Ensemble retrievers) is a common fix.
- This was the fourth and final RAG core component covered (after Document Loaders, Text Splitters, and Vector Stores) — the series moves on to building full RAG applications next.

## ❓ Revision Questions

1. In your own words, what is a retriever, and what are its input and output?
2. Why is `WikipediaRetriever` classified as a retriever and not a document loader, even though it "loads" Wikipedia content?
3. What are the two independent ways to categorize LangChain retrievers, and give one example of each?
4. What concrete advantage does `vectorstore.as_retriever()` give you over calling `vectorstore.similarity_search()` directly, given that both can return identical results for a basic query?
5. Describe the redundancy problem that MMR is designed to fix, and explain how its selection process avoids it.
6. What does the `lambda_mult` parameter control in an MMR retriever, and what happens at its two extremes (0 and 1)?
7. Walk through what happens, step by step, when an ambiguous query is passed to a `MultiQueryRetriever`.
8. Why might a normal similarity-search retriever return an irrelevant document for an ambiguous query, and how does `MultiQueryRetriever` avoid that failure mode?
9. Explain how a single document chunk can end up covering multiple unrelated topics, and why this matters for retrieval quality.
10. What are the two components inside a `ContextualCompressionRetriever`, and what role does each play?
11. Name at least two other LangChain retrievers mentioned in the video (beyond the five covered in depth) and what each is generally used for.
12. Why do so many different retrievers exist in LangChain, from a RAG-system-improvement perspective?
