# 4. Vector Stores in LangChain

> 📺 [Watch on YouTube](https://www.youtube.com/watch?v=k13WK0bxQP0&list=PLKnIA16_Rmva0dRLWEHLznSHKbFD_RJfX) · ⏱️ ~50 min · CampusX — Generative AI using LangChain

## 🎯 What You'll Learn

- Why keyword-matching similarity fails, and why semantic (embedding-based) similarity is needed instead
- What embeddings are and how similarity between two pieces of text is measured (cosine similarity / angular distance)
- What a vector store is, its four core features (storage, similarity search, indexing, CRUD)
- The difference between a **vector store** and a **vector database**
- How LangChain provides a common interface across vector stores (FAISS, Pinecone, Chroma, Qdrant, Weaviate, …)
- How to create, populate, search, filter, update, and delete data in a **Chroma** vector store using LangChain

## 📖 Overview

This is the third video in the RAG-components series (after Document Loaders and Text Splitters). The video builds intuition for vector stores through a movie-recommender case study, then defines what a vector store is, lists its key features, clarifies the "vector store vs vector database" naming confusion, and finally demonstrates the Chroma vector store in LangChain end to end — creating a store, adding documents, running similarity search (with and without scores), filtering by metadata, and updating/deleting documents.

**Embeddings**, briefly: a technique that uses a neural network to convert a piece of text into a numerical vector (e.g., 512 or 784 dimensions) that captures its semantic meaning. Once text is represented as vectors, "how similar are two texts" becomes a geometric question — measured with cosine similarity (or equivalently, angular distance) between the two vectors. Smaller angular distance / higher cosine similarity = more semantically similar.

**Vector store vs vector database**, briefly: a vector store gives you two things — storage of vectors, and retrieval via similarity search. A vector database is a vector store plus traditional database features (distributed architecture, durability/backup, ACID-like transactions, concurrency control, authentication/authorization). So every vector database is a vector store, but not every vector store is a full vector database.

## 🔑 Core Concepts

### Why we need vector stores — the movie recommender case study

Imagine building an IMDb-style movie catalog site. The basic architecture is straightforward: a database of movies (id, name, director, actor, genre, release date, outcome), a backend that pulls this data, and a frontend that displays it.

**First improvement — a recommender system.** When a user views a movie page (say, *Spider-Man*), show similar movies at the bottom (e.g., *Iron Man*, *Captain America*) to increase engagement and time-on-site.

**Naive approach — keyword matching.** Compare two movies (M1, M2) on structured attributes: director, actor, genre, release date proximity. If most of these match, treat the movies as similar.

This works "okay" but has two serious flaws:

1. **False positives.** *My Name Is Khan* and *Kabhi Alvida Naa Kehna* share the same director (Karan Johar), same lead actor (Shahrukh Khan), a similar release period, and an overlapping genre (drama) — so the keyword system rates them as highly similar. In reality their storylines are completely different, so this is a poor recommendation.
2. **False negatives.** *Taare Zameen Par* and *A Beautiful Mind* are thematically very similar (both center on a character struggling with a condition who is also brilliant in another way), but they share no director, actor, genre, or era — so keyword matching never flags them as similar, even though they genuinely are.

**Conclusion:** keyword matching is too simplistic. A better approach is to compare the actual **plot/story** of two movies — if plots are semantically similar, the movies are similar.

**The semantic approach:**
1. Fetch the full plot text (~2000–3000 words) for every movie (via APIs or web scraping) and add it to the database.
2. Comparing the semantic meaning of two pieces of text is normally a hard NLP problem — but deep learning solves this via **embeddings**: pass the text through a neural network that outputs a vector (e.g., 512-dim or 784-dim) encoding its meaning.
3. Convert every movie's plot into an embedding vector.
4. Plot all vectors in a high-dimensional coordinate system and compute the **angular distance / cosine similarity** between any two vectors. Small angular distance = high similarity.
5. Example: comparing M4 (*Stree*) against M1 (*3 Idiots*), M2, and M3 — if M4's angular distance to M1 is smallest, then *3 Idiots* is the most similar recommendation for *Stree*.

**Three practical challenges this introduces at scale:**

| # | Challenge | Why it's hard |
|---|---|---|
| 1 | Generating embedding vectors | Must generate embeddings for potentially millions of movies |
| 2 | Storage | Embedding vectors can't be stored in traditional relational databases (MySQL, Oracle) — those databases can't compute similarity between stored vectors |
| 3 | Fast semantic search | Comparing a query vector against, say, 1 million stored vectors one-by-one is O(n) and computationally very expensive — too slow for good user experience |

**Vector stores exist specifically to solve these three challenges.**

### What is a vector store?

> A vector store is a system designed to store and retrieve data represented as numerical vectors.

**Four key features:**

1. **Storage** — Stores vectors along with their associated metadata (e.g., movie ID, movie name). Two storage modes:
   - **In-memory** (RAM) — fast, but data is lost when the application closes. Good for small/prototype apps.
   - **On-disk** — persists across restarts. Used for enterprise-scale applications.

2. **Similarity search** — Given a query vector, retrieve the stored vectors most similar to it (this is the core semantic-search capability).

3. **Indexing** — A data structure/method that makes similarity search on high-dimensional vectors fast, avoiding a full O(n) linear scan. Example technique (clustering-based indexing):
   - Suppose there are 1,000,000 vectors, each 784-dimensional. A naive linear search compares the query against all 1,000,000 vectors — very slow.
   - Cluster the 1,000,000 vectors into, say, 10 clusters (~100,000 vectors each) using any clustering algorithm.
   - Compute a **centroid vector** for each cluster (average of all vectors in that cluster) — now there are only 10 centroid vectors.
   - For a new query vector, first compare it against just the 10 centroids to find the closest cluster (e.g., cluster C3).
   - Then search only within that cluster's ~100,000 vectors for the actual nearest match.
   - Net effect: ~100,010 comparisons instead of 1,000,000 — a large speedup while still returning a (near-)best result.
   - This is just one indexing approach. A more famous production technique is **Approximate Nearest Neighbor (ANN)** search — a research topic in its own right, not covered in depth here.

4. **CRUD operations** — Add, retrieve, update, and delete vectors, just like any other database.

**Use cases:** recommender systems, semantic search in general, RAG (covered in depth in the next video), and similarity search over images/multimedia. Anywhere an application stores/retrieves vectors, a vector store will outperform a traditional relational database, since relational databases aren't built for vector storage/retrieval or similarity computation.

### Vector store vs vector database

These terms are often used interchangeably online, which can be confusing. The distinction:

- A **vector store** is a system that gives you two things: (1) storage for vectors, and (2) retrieval via similarity/semantic search.
- A **vector database** is a vector store **plus** traditional database-like features:
  - Distributed architecture (for scaling)
  - Backup and restore / durability & persistence
  - ACID (or near-ACID) transaction guarantees
  - Concurrency control (multiple simultaneous users)
  - Authentication & authorization (security)

**Key rule of thumb:** *A vector database is effectively a vector store with extra database features.* Every vector database is a vector store, but not every vector store is a vector database (a vector store doesn't necessarily have database-like features).

- **Vector store** — typically a lightweight library/service focused purely on storing vectors and performing similarity search. May lack transactions, a rich query language (SQL-like), or role-based access control. Ideal for prototyping and smaller-scale applications. Example: **FAISS** (Facebook AI Similarity Search).
- **Vector database** — a full-fledged database system for storing and querying vectors, with the additional distributed architecture, durability, metadata handling, transaction guarantees, and auth features listed above. Used in production environments needing significant scale or handling very large datasets. Examples: **Milvus, Qdrant, Weaviate, Pinecone**.

### Chroma DB (main demo)

Chroma is a **lightweight, open-source vector database**, well suited to local development and small-to-medium-scale production needs. It sits somewhere between a pure vector store and a full vector database: it's not as heavyweight/feature-complete as something like Pinecone, but it does have some database-like features that a plain vector store lacks — giving a bit of the flavor of both.

**Chroma's data hierarchy:**

```
Tenant (a user / org / team)
 └── Database (a tenant can create multiple)
      └── Collection (like a "table" in RDBMS terms)
           └── Documents (each Document = an embedding vector + its metadata)
```

**Core operations covered in the demo** (done in Google Colab): creating a collection, adding documents, viewing stored documents, similarity search (with and without scores), metadata-based filtering, updating documents, and deleting documents.

### Other stores mentioned

- **FAISS** — Facebook's library, cited as a classic example of a lightweight "vector store" (not a full database).
- **Pinecone, Qdrant, Weaviate, Milvus** — cited as examples of full "vector databases" used in production at scale.
- LangChain ships wrapper components for all of these under a **common interface** (shared method names/signatures), so switching the underlying vector store later (e.g., FAISS → Pinecone as an app grows) requires minimal code changes.

## 💻 Code Examples

The demo installs the needed libraries in Colab, then walks through the following LangChain + Chroma workflow. (Note: the video's spoken import path corresponds to the older `langchain.vectorstores` location; the imports below use the current recommended packages — `langchain_openai` for embeddings and `langchain_chroma` for Chroma.)

```python
# 1. Install dependencies
# pip install langchain langchain-openai langchain-chroma chromadb

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# 2. Create Document objects (page_content = text, metadata = extra info)
docs = [
    Document(
        page_content="Virat Kohli is one of the most successful and consistent batsmen in IPL history.",
        metadata={"team": "Royal Challengers Bangalore"},
    ),
    Document(
        page_content="Rohit Sharma is the most successful captain in IPL history, leading Mumbai Indians to five titles.",
        metadata={"team": "Mumbai Indians"},
    ),
    Document(
        page_content="MS Dhoni, famously known as Captain Cool, has led Chennai Super Kings to multiple IPL titles.",
        metadata={"team": "Chennai Super Kings"},
    ),
    Document(
        page_content="Jasprit Bumrah is considered one of the best fast bowlers in T20 cricket.",
        metadata={"team": "Mumbai Indians"},
    ),
    Document(
        page_content="Ravindra Jadeja is a great all-rounder who can bat and bowl effectively for Chennai Super Kings.",
        metadata={"team": "Chennai Super Kings"},
    ),
]

# 3. Create the vector store
vector_store = Chroma(
    embedding_function=OpenAIEmbeddings(),
    persist_directory="my_chroma_db",   # on-disk persistence (SQLite-backed under the hood)
    collection_name="sample",
)

# 4. Add documents (each gets an auto-generated unique ID; custom IDs can be passed too)
vector_store.add_documents(docs)

# 5. View everything currently stored
vector_store.get(include=["embeddings", "documents", "metadatas"])

# 6. Similarity search — plain semantic query
vector_store.similarity_search(query="Among these, who is a bowler?", k=1)
# -> returns the Jasprit Bumrah document

vector_store.similarity_search(query="Among these, who is a bowler?", k=2)
# -> returns Jasprit Bumrah + Ravindra Jadeja (semantically linked via "all-rounder")

# 7. Similarity search with score (lower score = smaller distance = more similar)
vector_store.similarity_search_with_score(query="Among these, who is a bowler?", k=2)

# 8. Metadata filtering (query can be left empty; filter narrows by metadata field)
vector_store.similarity_search(query="", filter={"team": "Chennai Super Kings"})
# -> returns MS Dhoni + Ravindra Jadeja documents

# 9. Update an existing document by its ID
updated_doc = Document(
    page_content="Virat Kohli, the former captain of Royal Challengers Bangalore, is renowned for his aggressive leadership and consistency.",
    metadata={"team": "Royal Challengers Bangalore"},
)
vector_store.update_document(document_id="<virat-kohli-doc-id>", document=updated_doc)

# 10. Delete document(s) by ID
vector_store.delete(ids=["<virat-kohli-doc-id>"])
```

**Homework set in the video:** re-implement this exact workflow with a different vector store (FAISS or Pinecone) — since LangChain exposes the same method names across stores, the code changes should be minimal.

## 📊 Vector Store Comparison

| Aspect | Vector Store | Vector Database |
|---|---|---|
| Core job | Store vectors + similarity search | Vector store + full DB feature set |
| Distributed architecture | Not typically | Yes |
| Backup / restore, durability | Not typically | Yes |
| Transactions (ACID / near-ACID) | Not typically | Yes |
| Concurrency control (multi-user) | Not typically | Yes |
| Authentication / authorization | Not typically | Yes |
| Best for | Prototyping, small-scale apps | Production, large-scale apps |
| Examples | FAISS | Milvus, Qdrant, Weaviate, Pinecone |
| Where Chroma fits | Between the two — lightweight like a store, but with some DB-like features | |

## 🧠 Key Takeaways

- Naive keyword matching for similarity produces both false positives (same director/actor/genre but different story) and false negatives (same theme but no shared keywords) — it's an unreliable similarity signal.
- Embeddings convert text into numeric vectors that capture semantic meaning; cosine similarity / angular distance between vectors measures semantic similarity.
- A vector store must solve three problems at scale: generating embeddings for large datasets, storing vectors (relational DBs can't do similarity search), and searching efficiently (avoiding a full O(n) linear scan).
- The four defining features of a vector store are: storage (in-memory or on-disk), similarity search, indexing (e.g., clustering-based, or ANN) for fast search, and CRUD operations.
- A vector database = a vector store + traditional database features (distributed architecture, durability, transactions, concurrency control, auth). Every vector database is a vector store; not every vector store is a vector database.
- Chroma is a lightweight, open-source vector database that sits between a pure vector store and a full vector database, and is well suited to local development and small/medium production use.
- Chroma organizes data as Tenant → Database → Collection → Documents (embedding vector + metadata), roughly analogous to RDBMS's database → table → row structure.
- LangChain exposes a common interface (`from_documents`/`from_texts`, `add_documents`/`add_texts`, `similarity_search`, `similarity_search_with_score`, metadata filtering, `update_document`, `delete`) across all supported vector stores, so switching providers later requires minimal code changes.
- `similarity_search_with_score` returns a distance-like score where **lower is better** (more similar), not a similarity percentage.
- Metadata filtering lets you narrow results by structured fields (e.g., team name) independent of, or combined with, the semantic query.

## ❓ Revision Questions

1. Why does simple keyword matching fail as a similarity measure for movie recommendations? Give one example each of a false positive and a false negative from the video.
2. What is an embedding, and how does it let us compare the semantic meaning of two pieces of text numerically?
3. What does "angular distance" or "cosine similarity" tell us about two embedding vectors?
4. List and briefly explain the three challenges that arise when building a large-scale, embedding-based similarity system, and explain how a vector store addresses each one.
5. Name the four key features of a vector store.
6. Explain, with the clustering example from the video, how indexing speeds up similarity search compared to a naive linear scan.
7. What is the precise difference between a vector store and a vector database? Give one example of each.
8. Why is Chroma described as sitting "between" a vector store and a vector database?
9. Describe Chroma's data hierarchy from top to bottom (Tenant, Database, Collection, Document).
10. In LangChain + Chroma, which method would you use to: (a) create a vector store, (b) add new documents, (c) run a semantic query with a similarity score, (d) filter results by metadata, (e) update an existing document, (f) delete a document?
11. In `similarity_search_with_score`, does a lower score mean more similar or less similar? Why?
12. Why does LangChain design all its vector store wrappers around a common interface? What practical benefit does this give you if your application later needs to switch vector stores?
