# 11. Document Loaders in LangChain  (Video 10)

> 📺 [Watch on YouTube](https://www.youtube.com/playlist?list=PLKnIA16_RmvaTbihpo4MtzVm4XOQa0ER0) · ⏱️ ~57 min · CampusX — Generative AI using LangChain
>
> 🔎 **This is the first of the RAG building blocks.** A complete, worked version of these notes already lives in the RAG series — see **[detailed notes → `rag/02_document-loaders.md`](../12_rag/02_document-loaders.md)**. This page is the LangChain-course summary + pointers.

---

## 🎯 What You'll Learn
- What a **Document Loader** is and why it's step 1 of every RAG pipeline.
- The `Document` object (`page_content` + `metadata`) — the unit that flows through the whole pipeline.
- The common loaders: `TextLoader`, `PyPDFLoader`, `WebBaseLoader`, `CSVLoader`, `DirectoryLoader`.
- `.load()` (eager) vs `.lazy_load()` (streaming) and when each matters.

---

## 📖 Overview / Why It Matters
RAG lets an LLM answer questions over *your* data (PDFs, web pages, CSVs, a folder of docs). Before the model can use that data, you must **load it into a standard shape**. That's the job of Document Loaders — the first stage of the indexing pipeline:

```
Load → Split → Embed → Store → Retrieve
(here)  (12)     (13)    (13)     (14)
```

Every loader returns a list of **`Document`** objects, each with:
- `page_content` — the raw text.
- `metadata` — a dict (source path, page number, URL, row index…), invaluable for citations and filtering later.

---

## 🧠 Key Concepts

### The `Document` object
The universal currency of LangChain data pipelines. Loaders produce them, splitters transform them, vector stores index them. Keeping everything as `Document`s (not bare strings) means metadata survives all the way to retrieval, so you can cite the source page/URL of an answer.

### Common loaders
| Loader | Source | Package |
|---|---|---|
| `TextLoader` | `.txt` files | `langchain_community.document_loaders` |
| `PyPDFLoader` | PDFs (one `Document` per page) | `langchain_community.document_loaders` |
| `WebBaseLoader` | web page(s) via URL | `langchain_community.document_loaders` |
| `CSVLoader` | CSV rows (one `Document` per row) | `langchain_community.document_loaders` |
| `DirectoryLoader` | a folder, with a `glob` pattern | `langchain_community.document_loaders` |

### `load()` vs `lazy_load()`
- `.load()` reads everything into memory at once — simple, fine for small sources.
- `.lazy_load()` yields `Document`s one at a time — use it for large corpora so you don't blow up memory.

---

## 💻 Code Examples

```python
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, WebBaseLoader, CSVLoader, DirectoryLoader,
)

# Text
docs = TextLoader("notes.txt", encoding="utf-8").load()

# PDF — one Document per page
docs = PyPDFLoader("dl_curriculum.pdf").load()
print(len(docs), docs[0].metadata)   # e.g. 12 {'source': 'dl_curriculum.pdf', 'page': 0}

# Web page
docs = WebBaseLoader("https://example.com/article").load()

# CSV — one Document per row
docs = CSVLoader("data.csv").load()

# A whole directory of PDFs, streamed
loader = DirectoryLoader("./corpus", glob="**/*.pdf", loader_cls=PyPDFLoader)
for doc in loader.lazy_load():
    process(doc)
```

---

## ⚠️ Gotchas & Tips
- `PyPDFLoader` needs `pypdf` installed; scanned/image PDFs need OCR (won't extract text otherwise).
- `WebBaseLoader` grabs raw page text (needs `beautifulsoup4`) — it won't run JavaScript; for JS-heavy pages use a browser-based loader.
- Preserve `metadata` — it's what lets you show "answer from page 7 of X" later.
- Loaders live in `langchain_community` (community integrations), not `langchain_core`.

---

## 🧠 Key Takeaways
- Document Loaders are **step 1** of RAG: turn any source into a list of `Document` objects.
- A `Document` = `page_content` + `metadata`; metadata carries through to retrieval for citations/filtering.
- Pick the loader by source type; `DirectoryLoader` batches a folder.
- Prefer `lazy_load()` for large corpora.
- 👉 Full walkthrough with more loaders and examples: [`rag/02_document-loaders.md`](../12_rag/02_document-loaders.md).

---

## ❓ Revision Questions
1. What two fields does a `Document` object always have, and why does metadata matter downstream?
2. Which loader would you use for a folder of 500 PDFs, and how would you avoid loading them all into memory at once?
3. How many `Document`s does `PyPDFLoader` typically produce for a 10-page PDF? What about `CSVLoader` for a 100-row file?
4. Why do loaders live in `langchain_community` rather than `langchain_core`?
5. What's the next pipeline step after loading, and why can't you usually skip it?
