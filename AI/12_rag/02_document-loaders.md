# 2. Document Loaders in LangChain

> 📺 [Watch on YouTube](https://www.youtube.com/watch?v=bL92ALSZ2Cg&list=PLKnIA16_Rmva0dRLWEHLznSHKbFD_RJfX) · ⏱️ ~56 min · CampusX — Generative AI using LangChain

This is Video 2 of a RAG-focused stretch of the LangChain playlist. Having covered LangChain's core components (Models, Prompts, Chains) and core concepts (Runnables) in earlier videos, the series now pivots to building RAG-based applications. Every RAG application is built from four components — **Document Loaders → Text Splitters → Vector Stores → Retrievers** — and this video covers the first one: Document Loaders.

## 🎯 What You'll Learn
- What a RAG-based application is and why plain LLM chat (e.g. ChatGPT) can't answer questions about private, recent, or organization-specific data
- What a LangChain `Document` object is (`page_content` + `metadata`) and why every loader standardizes its output into this shape
- How to load plain text with `TextLoader`
- How to load PDFs page-by-page with `PyPDFLoader`, plus when to reach for `PDFPlumberLoader`, `UnstructuredPDFLoader`, `AmazonTextractPDFLoader`, or `PyMuPDFLoader` instead
- How to bulk-load every file in a folder with `DirectoryLoader` (and its `glob` pattern syntax)
- The difference between `.load()` (eager) and `.lazy_load()` (lazy/generator-based) — and when each matters
- How to scrape and query a web page with `WebBaseLoader`
- How to load tabular data row-by-row with `CSVLoader`
- Where to find the full catalog of loaders, and how to build a custom loader when none of the built-in ones fit

## 📖 Overview

### Why RAG?
Chatbots like ChatGPT answer well most of the time, but they fail in a few predictable situations:
1. **Current/recent information** — the model was trained on data up to some cutoff and doesn't know about today's news.
2. **Personal data** — it has never seen your private emails, notes, or documents.
3. **Organization-internal data** — it has never seen your company's internal documentation or codebase.

In every one of these cases, the model simply never saw the relevant data during training. **Retrieval-Augmented Generation (RAG)** fixes this by connecting the LLM to an **external knowledge base** — a database, a folder of PDFs, personal documents, anything. When a user asks something the LLM doesn't know, the system retrieves relevant information from that external knowledge base and uses it as grounding context for the LLM's answer.

> RAG is a technique that combines **information retrieval** (from a knowledge base) with **language generation** (by an LLM), where the model retrieves relevant documents and uses them as context to generate accurate, grounded responses.

**Benefits of RAG:**
- **Up-to-date answers** — the knowledge base can be refreshed independently of the model.
- **Privacy** — you don't have to upload sensitive/confidential documents to a third-party chatbot; the document stays in your own knowledge base.
- **No practical document-size limit** — a 1 GB document would blow past any model's context window if uploaded directly, but RAG splits it into small chunks and processes them incrementally instead.

### The four RAG components
Any RAG application, however complex, is generally built from four building blocks:

| # | Component | Job |
|---|-----------|-----|
| 1 | **Document Loaders** | Pull raw data from any source into a standardized format |
| 2 | **Text Splitters** | Break large documents into smaller, manageable chunks |
| 3 | **Vector Stores** | Embed chunks and store them for similarity search |
| 4 | **Retrievers** | Fetch the chunks most relevant to a given query |

This note covers component #1. (Text Splitters, Vector Stores, and Retrievers follow in later videos.)

### The `Document` object
Data for a RAG app can live anywhere — a PDF, a `.txt` file, a database, a cloud provider, a web page. LangChain needs all of that heterogeneous data to end up in one **common, standardized format** so downstream components (splitters, embedders, retrievers) don't need to care where the data originally came from. That standardized format is the `Document` object.

> **Document Loaders** are components in LangChain used to load data from various sources into a standardized format — usually `Document` objects — which can then be used for chunking, embedding, retrieval, and generation.

Every `Document` object carries exactly two things:

| Attribute | Contents |
|---|---|
| `page_content` | The actual extracted text/content |
| `metadata` | Everything *about* that content — source path/URL, creation date, last-modified date, author, page number, row index, etc. |

Whichever loader you use — `TextLoader`, `PyPDFLoader`, or any other — calling `.load()` always returns a **Python list of `Document` objects**. This is the single most important principle behind every document loader in LangChain: once you understand one loader, you understand the usage pattern for practically all of them.

All built-in loaders live in the community package:
```python
from langchain_community.document_loaders import ...
```

## 🔑 Loaders Covered

### 1. TextLoader
The simplest loader in LangChain. It picks up a plain text file and loads it into LangChain as a single `Document` object.

**Use it for:** log files, code snippets, transcripts (e.g. a YouTube video transcript) — anything that's already plain text.

```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader('cricket.txt', encoding='utf-8')
docs = loader.load()

print(type(docs))          # <class 'list'>
print(len(docs))           # 1  -> one Document for one text file
print(type(docs[0]))       # <class 'langchain_core.documents.base.Document'>
print(docs[0].page_content)
print(docs[0].metadata)
```
- `encoding` is optional — only needed if your file has special characters (e.g. UTF-8 content that isn't plain ASCII).
- A single text file always produces a list containing exactly **one** `Document`.

### 2. PyPDFLoader (and other PDF loaders)
`PyPDFLoader` reads a PDF file and converts it into `Document` objects **page by page** — a 25-page PDF becomes a list of 25 `Document` objects, each with its own `page_content` and its own `metadata` (page number, source, total pages, etc.).

Internally it uses the `pypdf` library (`pip install pypdf` is required), which makes it a great fit for **text-based PDFs** but a poor fit for **scanned images or complex layouts**.

```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader('dl-curriculum.pdf')
docs = loader.load()

print(len(docs))              # 23 -> one Document per page, for a 23-page PDF
print(docs[0].page_content)   # text of page 1
print(docs[0].metadata)       # producer, creator, creation date, title, source, total pages, page number
```

**Other PDF loaders worth knowing about** (all in `langchain_community.document_loaders`), for cases `PyPDFLoader` doesn't handle well:

| Loader | Best for |
|---|---|
| `PDFPlumberLoader` | PDFs with heavy **tabular** content — extracting table data |
| `UnstructuredPDFLoader` | Scanned PDFs / structure-aware extraction |
| `AmazonTextractPDFLoader` | Scanned/image-based PDFs (cloud OCR via AWS Textract) |
| `PyMuPDFLoader` | PDFs with complex, multi-column layouts |

You don't need to study every one of these upfront — the LangChain documentation lists the full catalog with usage examples and a dedicated tutorial for extracting tables/structure from PDFs. Learn the specific loader you need when a project actually calls for it.

### 3. DirectoryLoader
Loads **every matching file inside a folder** in one call, instead of loading files one at a time. Internally, it wraps another loader class and applies it to each file it finds.

Key parameters:
- `path` — the directory to scan
- `glob` — a pattern describing which files to pick up
- `loader_cls` — which loader class to apply to each matched file

```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader

loader = DirectoryLoader(
    path='books',
    glob='*.pdf',            # every .pdf directly inside the "books" folder
    loader_cls=PyPDFLoader
)

docs = loader.load()
print(len(docs))   # 1186 -> sum of pages across all 3 PDFs (326 + 392 + 468)
```

**Common `glob` patterns:**

| Pattern | Meaning |
|---|---|
| `**/*.txt` | All `.txt` files in this folder **and every subfolder** |
| `*.pdf` | All `.pdf` files directly inside the given folder (no subfolders) |
| `data/*.csv` | All `.csv` files inside a `data` subfolder |
| `**/*` | All files, in every subfolder, regardless of extension |

`DirectoryLoader` works with any loader class you pass as `loader_cls` — `TextLoader`, `PyPDFLoader`, `CSVLoader`, etc. — so everything else in this note composes with it directly.

### 4. Lazy Loading — `.load()` vs `.lazy_load()`
Loading three large PDFs at once with `DirectoryLoader.load()` is noticeably slow, and it holds **every single page, from every file, in memory at the same time**. That's fine for 3 PDFs; it isn't fine for 100 or 500.

Every LangChain document loader exposes **two** loading methods:

| Method | Behavior |
|---|---|
| `.load()` | **Eager loading.** Loads everything at once, returns a full `list[Document]`. Simple, but memory-heavy — use it when the number/size of documents is small and you need everything in memory at once. |
| `.lazy_load()` | **Lazy loading.** Returns a **generator** of `Document` objects. Documents are fetched **one at a time, on demand**, processed, and released — never all held in memory simultaneously. Use it for large document sets or when you need streaming processing without a large memory footprint. |

```python
loader = DirectoryLoader(path='books', glob='*.pdf', loader_cls=PyPDFLoader)

# Eager: waits until everything is loaded, then returns the full list
docs = loader.load()
for document in docs:
    print(document.metadata)

# Lazy: starts printing almost immediately — one Document in memory at a time
for document in loader.lazy_load():
    print(document.metadata)
```
With `.load()`, there's a long upfront wait while all 1,186 documents are built before anything prints. With `.lazy_load()`, output starts appearing almost immediately because each `Document` is created, used, and discarded one at a time.

### 5. WebBaseLoader
Loads and extracts text content directly from a web page, so you can ask questions about it via an LLM.

Internally it uses two libraries:
- **`requests`** — to make the HTTP request to the page
- **`BeautifulSoup`** — to parse the page's HTML and pull out the text content

**Works well with:** static pages — blogs, news articles, product pages, generally public content.
**Struggles with:** JavaScript-heavy pages where content is rendered dynamically by user interaction. For those, use `SeleniumURLLoader` instead.

```python
from langchain_community.document_loaders import WebBaseLoader

loader = WebBaseLoader('https://example.com/product-page')
docs = loader.load()

print(len(docs))            # 1 -> a single URL produces a single Document
print(docs[0].page_content)
```
- Passing a **list of URLs** instead of a single string produces one `Document` per URL.
- A natural next step is to feed `docs[0].page_content` into a prompt + LLM chain and ask questions about the page — see the Code Examples section below.
- Project idea from the video: a Chrome extension that opens alongside any webpage and lets the user chat with that page in real time, backed by an API that uses `WebBaseLoader` + an LLM behind the scenes.

### 6. CSVLoader
Loads a CSV file so that **each row becomes its own `Document` object**.

```python
from langchain_community.document_loaders import CSVLoader

loader = CSVLoader(file_path='Social_network_ads.csv')  # 5 columns, 400 rows
docs = loader.load()

print(len(docs))            # 400 -> one Document per row
print(docs[0].page_content) # "UserID: ...\nGender: ...\nAge: ...\n..." (column: value pairs)
print(docs[0].metadata)     # {'source': 'Social_network_ads.csv', 'row': 0}
```
`CSVLoader` also supports `.lazy_load()`, which is useful for large CSVs — loop through rows one at a time instead of holding the entire file in memory. This loader is especially handy for data-analysis-style projects, e.g. asking an LLM "what's the maximum value in this column?"

### 7. Other loaders & building a custom loader
LangChain's documentation organizes loaders into well-defined categories — web pages, PDFs, cloud storage (S3, Azure, Google Drive, Dropbox), social platforms, messaging services, productivity tools (e.g. Git), common file types (JSON, CSV, directories), and more, including a dedicated **YouTube transcript loader**. There are hundreds of loaders in total — don't try to study them all upfront; look one up from the docs when a specific project actually needs it.

If no existing loader fits your data source, LangChain lets you write a **custom document loader**: create a class that inherits from `BaseLoader` and implement your own `load` and `lazy_load` logic. This is in fact exactly how the large pool of community-contributed loaders came to exist — individual contributors built loaders for their own use cases and added them to `langchain_community`.

```python
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

class MyCustomLoader(BaseLoader):
    def __init__(self, source):
        self.source = source

    def lazy_load(self):
        # yield Document objects one at a time
        yield Document(page_content="...", metadata={"source": self.source})

    def load(self):
        return list(self.lazy_load())
```

## 💻 Code Examples

### Setup common to every loader
```python
from dotenv import load_dotenv
load_dotenv()
```

### TextLoader → summarization chain
Once you have `page_content`, it slots straight into any LangChain chain:
```python
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import TextLoader
from dotenv import load_dotenv

load_dotenv()

loader = TextLoader('cricket.txt', encoding='utf-8')
docs = loader.load()

model = ChatOpenAI()
prompt = PromptTemplate(
    template='Write a summary for the following poem - \n{poem}',
    input_variables=['poem']
)
parser = StrOutputParser()

chain = prompt | model | parser

print(chain.invoke({'poem': docs[0].page_content}))
```

### WebBaseLoader → question-answering over a web page
```python
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from dotenv import load_dotenv

load_dotenv()

url = 'https://example.com/product-page'
loader = WebBaseLoader(url)
docs = loader.load()

model = ChatOpenAI()
prompt = PromptTemplate(
    template='Answer the following question \n{question} \nfrom the following text \n{text}',
    input_variables=['question', 'text']
)
parser = StrOutputParser()

chain = prompt | model | parser

print(chain.invoke({
    'question': 'What is the product we are talking about?',
    'text': docs[0].page_content
}))
```

### Inspecting any loader's output (the universal pattern)
```python
docs = loader.load()        # or loader.lazy_load() for a generator

type(docs)                  # list[Document]  (or a generator, for lazy_load)
len(docs)                   # number of Document objects produced
docs[0]                     # the first Document
docs[0].page_content        # its text content
docs[0].metadata            # its metadata dict
```

## 📊 Comparison Table

| Loader | Use Case | Input | Notes |
|---|---|---|---|
| `TextLoader` | Plain text: logs, code snippets, transcripts | Path to a `.txt` file | Simplest loader; always returns exactly 1 `Document` |
| `PyPDFLoader` | Text-based PDFs | Path to a `.pdf` file | One `Document` per page; uses `pypdf`; weak on scanned/complex-layout PDFs |
| `PDFPlumberLoader` | PDFs with tables | Path to a `.pdf` file | Optimized for extracting tabular data |
| `UnstructuredPDFLoader` | Scanned PDFs, structured extraction | Path to a `.pdf` file | Structure-aware; handles non-plain-text PDFs |
| `AmazonTextractPDFLoader` | Scanned/image PDFs | Path to a `.pdf` file (via AWS Textract) | Cloud OCR-based extraction |
| `PyMuPDFLoader` | Complex, multi-column layouts | Path to a `.pdf` file | Fast, layout-aware parsing |
| `DirectoryLoader` | Bulk-loading many files from a folder | Directory path + `glob` pattern + `loader_cls` | Wraps another loader class; applies it to every matched file |
| `WebBaseLoader` | Static web pages: blogs, news, product pages | URL or list of URLs | Uses `requests` + `BeautifulSoup`; not for JS-heavy pages (use `SeleniumURLLoader`) |
| `CSVLoader` | Tabular/CSV data | Path to a `.csv` file | One `Document` per row |

## 🧠 Key Takeaways
- RAG connects an LLM to an external knowledge base so it can answer questions about data it never saw during training — solving the private-data, recent-data, and internal-documentation gaps of plain chat.
- Every RAG app is built from four components: **Document Loaders → Text Splitters → Vector Stores → Retrievers**.
- Every document loader's job is the same: pull data from *some* source and standardize it into a list of `Document` objects, each with `page_content` and `metadata`.
- `PyPDFLoader` produces one `Document` per PDF page; `CSVLoader` produces one `Document` per row; `TextLoader` and `WebBaseLoader` (for a single URL) each produce exactly one `Document`.
- `DirectoryLoader` bulk-applies any other loader class (`loader_cls`) across every file matching a `glob` pattern inside a folder.
- Every loader exposes both `.load()` (eager — everything in memory at once) and `.lazy_load()` (lazy — a generator, one `Document` at a time). Prefer lazy loading for large document sets or memory-constrained streaming.
- All built-in loaders live in `langchain_community.document_loaders`; if none fit your source, you can write a custom loader by subclassing `BaseLoader`.
- You don't need to memorize every loader that exists — learn the one you need, project by project, from the LangChain documentation.

## ❓ Revision Questions
1. Why can't a plain LLM chatbot answer questions about your personal emails or your company's internal documentation, even though it's a very capable model?
2. What two attributes does every LangChain `Document` object have, and what does each one hold?
3. What is returned when you call `.load()` on any LangChain document loader — a single `Document`, or something else?
4. If a PDF has 40 pages, how many `Document` objects will `PyPDFLoader.load()` return, and why?
5. Why is `PyPDFLoader` a poor choice for a scanned PDF, and which loaders would you reach for instead?
6. What are the three arguments you typically pass to a `DirectoryLoader`, and what does each control?
7. Write a `glob` pattern that would load every `.csv` file in a `data` folder and every one of its subfolders.
8. What is the core difference between `.load()` and `.lazy_load()`, and when would you prefer one over the other?
9. Which two Python libraries does `WebBaseLoader` use internally, and what does each one do? What loader would you use instead for a JavaScript-heavy page?
10. How many `Document` objects does `CSVLoader` produce for a CSV with 400 rows, and what goes into the `page_content` of each one?
11. If none of LangChain's built-in loaders fit your data source, how would you build your own?
