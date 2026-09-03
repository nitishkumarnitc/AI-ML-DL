# 12. Text Splitters in LangChain  (Video 11)

> 📺 [Watch on YouTube](https://www.youtube.com/playlist?list=PLKnIA16_RmvaTbihpo4MtzVm4XOQa0ER0) · ⏱️ ~59 min · CampusX — Generative AI using LangChain
>
> 🔎 **RAG building block #2.** A complete, worked version already exists in the RAG series — see **[detailed notes → `rag/03_text-splitters.md`](../12_rag/03_text-splitters.md)**. This page is the LangChain-course summary + pointers.

---

## 🎯 What You'll Learn
- Why you split documents into **chunks** before embedding (context limits, embedding quality, compute).
- The four splitting strategies and when to use each.
- What `chunk_size` and `chunk_overlap` control.

---

## 📖 Overview / Why It Matters
Step 2 of the RAG indexing pipeline (`Load → **Split** → Embed → Store → Retrieve`). You almost never embed a whole document as one blob:
1. **Context limits** — models/embedders have a max input size.
2. **Embedding quality** — one vector represents a small, focused chunk far better than a giant mixed one.
3. **Efficiency** — small independent chunks are cheaper and parallelizable.

---

## 🧠 Key Concepts

### The four strategies
| Strategy | Class | Splits on | Notes |
|---|---|---|---|
| Length-based | `CharacterTextSplitter` | raw character/token count | fast, but cuts mid-word/sentence |
| **Text-structure** (default) | `RecursiveCharacterTextSplitter` | `["\n\n","\n"," ",""]` in order | recursively falls back, then merges — **the go-to** |
| Document-structure | `RecursiveCharacterTextSplitter.from_language(...)` | code/Markdown/HTML units | class/def/heading boundaries |
| Semantic | `SemanticChunker` (`langchain_experimental`) | embedding-similarity drops | meaning-aware, experimental |

### `chunk_size` & `chunk_overlap`
- **`chunk_size`** — max size of a chunk.
- **`chunk_overlap`** — how much of the previous chunk's tail is repeated at the start of the next, so context isn't orphaned at a cut. Rule of thumb: **10–20% of `chunk_size`**.

---

## 💻 Code Examples

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# From raw text
chunks = splitter.split_text(long_text)

# From loaded Documents (metadata is preserved on each chunk)
from langchain_community.document_loaders import PyPDFLoader
docs = PyPDFLoader("book.pdf").load()
chunks = splitter.split_documents(docs)   # list[Document]
```

```python
# Splitting source code along class/function boundaries
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
py_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON, chunk_size=300, chunk_overlap=0
)
```

---

## ⚠️ Gotchas & Tips
- `RecursiveCharacterTextSplitter` is the sensible default for prose — it avoids cutting mid-word by falling back through paragraph → sentence → word → char.
- Too-small chunks lose context; too-large chunks dilute embeddings and blow past limits. Tune per corpus.
- `SemanticChunker` needs embedding calls (slower/costs money) and is still experimental — don't reach for it first.
- Use `split_documents()` (not `split_text()`) when you started from loaders, to keep metadata.

---

## 🧠 Key Takeaways
- Splitting = step 2 of RAG; do it for context limits, embedding quality, and efficiency.
- Four strategies; **`RecursiveCharacterTextSplitter` is the default**.
- `chunk_overlap ≈ 10–20% of chunk_size` preserves context across cuts.
- 👉 Full worked examples (with the `chunk_size=10/25/50` trace): [`rag/03_text-splitters.md`](../12_rag/03_text-splitters.md).

---

## ❓ Revision Questions
1. Give three reasons to split before embedding.
2. Which splitter is the default for prose and why does it rarely cut mid-word?
3. What does `chunk_overlap` do, and what's a good starting ratio?
4. When would `RecursiveCharacterTextSplitter.from_language()` beat the plain splitter?
5. Why is `SemanticChunker` not the default choice today?
