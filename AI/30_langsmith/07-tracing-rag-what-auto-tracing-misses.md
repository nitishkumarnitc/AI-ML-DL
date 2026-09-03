# 07 · Tracing RAG — and the Two Problems It Exposes

> ← [`06-tags-metadata-and-run-names.md`](06-tags-metadata-and-run-names.md) · **Next:** [`08-the-traceable-decorator.md`](08-the-traceable-decorator.md) →

---

## Why RAG is the case that most needs tracing

RAG sounds trivial when you describe it: send the LLM the question *plus* some relevant context from your own documents, so it can answer about data it was never trained on.

Theoretically simple. In production, the most common complaint about a RAG chatbot is that **the answer quality just isn't good** — and the reason that complaint is so hard to act on is that there are two independent failure points:

| Failure | What happened | Where to look |
|---|---|---|
| **Retriever error** | The query went out, the wrong chunks came back. Question was about notice period; the retriever returned company history | Retrieved documents |
| **Generator error** | The right chunks came back, and the LLM hallucinated anyway | The assembled prompt + the completion |

In production you have the question and the bad answer. Nothing between. So you cannot tell which box failed — and the fixes are unrelated (lesson 01, Story C).

LangSmith closes the gap by recording, for every query: the question as the retriever saw it, **the actual documents retrieved**, the **fully assembled prompt** (question + context), and the LLM's completion. Which failed becomes a matter of *looking*, not guessing.

---

## The application

`03_rag_v1.py`. Corpus: *An Introduction to Statistical Learning* as a PDF — **441 pages**.

```python
# 03_rag_v1.py
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["LANGSMITH_PROJECT"] = "RAG Chatbot"

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda

PDF_PATH = "islr.pdf"

# ---- step 1: load ----
docs = PyPDFLoader(PDF_PATH).load()               # 441 pages -> 441 Documents

# ---- step 2: chunk ----
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
chunks = splitter.split_documents(docs)

# ---- step 3: embed + retriever ----
vector_store = FAISS.from_documents(chunks, OpenAIEmbeddings(model="text-embedding-3-small"))
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

# ---- the chain ----
prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer ONLY from the provided context. "
               "If the context is insufficient, say you don't know."),
    ("human", "Question: {question}\n\nContext:\n{context}"),
])
model  = ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

parallel = RunnableParallel({
    "context":  retriever | RunnableLambda(format_docs),
    "question": RunnablePassthrough(),
})

chain = parallel | prompt | model | parser

while True:
    q = input("\nAsk: ")
    if not q:
        break
    print(chain.invoke(q))
```

### The chain shape, since it's the part people trip on

```
        question (a plain string)
              │
      ┌───────┴────────┐            RunnableParallel
      │                │
 RunnablePassthrough   retriever ──► format_docs
      │                                  │
   question                           context
      └───────┬──────────────────────────┘
              ▼
      {"question": …, "context": …}
              │
           prompt ──► model ──► parser ──► answer
```

`RunnableParallel` runs both branches on the *same* input and merges their outputs into a dict. The passthrough branch hands the question along untouched; the retriever branch fetches documents and `format_docs` joins their text into one block. The prompt template then has both variables it needs.

### Run it

```
Ask: Who is the author of this book?
→ Gareth James, Daniela Witten, Trevor Hastie and Robert Tibshirani.

Ask: What is the full form of GLM?
→ Generalized Linear Model.
```

---

## The trace

```
RunnableSequence                                    ← trace root
├── RunnableParallel
│   ├── RunnablePassthrough    in: "Who is the author…"   out: same string
│   └── RunnableSequence
│       ├── VectorStoreRetriever   in: query   out: 4 Documents  ★
│       └── RunnableLambda         in: 4 Documents   out: one joined string
├── ChatPromptTemplate         in: {question, context}   out: the full prompt  ★
├── ChatOpenAI                 in: messages   out: completion   + tokens + cost
└── StrOutputParser            in: AIMessage   out: str
```

The two starred runs are the diagnosis:

- **`VectorStoreRetriever` output** — the actual chunks. Wrong topic? Retriever error. Only one chunk when the question needed three? Retriever error.
- **`ChatPromptTemplate` output** — the exact string the model saw. Context present and on-topic but the answer contradicts it? Generator error.

Story C is now a thirty-second investigation. That is the whole reason RAG and tracing belong together.

---

## Problem 1 — most of the application is invisible

Scroll the trace and look for the PDF load. It isn't there. Neither is chunking. Neither is embedding.

Three of the app's most important operations — and the *slowest* — are absent:

```
❌ PyPDFLoader.load()                         not traced
❌ splitter.split_documents(docs)             not traced
❌ FAISS.from_documents(...)                  not traced
✅ everything from parallel | prompt | … on   traced
```

### Why

> **LangSmith auto-traces LangChain runnables — things executed through the runnable interface (`.invoke()`, `.stream()`, `.batch()`).** Nothing else.

Loading, splitting and embedding here are ordinary Python function calls made at module level. No runnable, no callback, no trace. The tracer isn't ignoring them; it never hears about them.

### Why it matters

You wanted to know: how long did the PDF take to load? How long did chunking take? How long did embedding take, and with which model? All unavailable. **The application is partially observed, and the unobserved part is the expensive part.**

Fixed in lesson 08.

---

## Problem 2 — a logic bug that tracing makes obvious

Ask a question. It takes a long time. Ask another. It takes a long time again — the video measures roughly **202 seconds** per query.

Look at the script's structure and the reason is plain: loading, chunking and embedding are **at module level**. Every process start re-does all three. 441 pages re-parsed, re-chunked, and every chunk re-embedded through a paid API — before a single question is answered.

```
run 1:  load(441 pages) → chunk → embed ALL chunks → answer     ~202 s
run 2:  load(441 pages) → chunk → embed ALL chunks → answer     ~202 s   ← identical work
run 3:  …
```

What should happen:

```
first run ever:  load → chunk → embed → PERSIST the index → answer
every run after: LOAD the index → answer                              ~2 s
```

Embeddings are a **pure function of (documents, chunking parameters, embedding model)**. None of those changed. Recomputing them is waste twice over — wall-clock *and* an embedding-API bill on every process start.

Fixed in lesson 10.

> **Note the meta-point, which is the actual lesson here.** Problem 2 is a design flaw that has nothing to do with observability. It was found by *looking at latency numbers you would not otherwise have had*. Observability's second job — after debugging — is making badly-shaped systems visible to their own authors. The video's author wrote this code and found the flaw by tracing it.

---

## ⭐ Beyond the video — the retriever fields worth checking first

*Added: a checklist for reading a RAG trace, since "look at the retrieved documents" is advice you can follow more or less well.*

When a RAG answer is wrong, walk the retriever run in this order:

| # | Check | Diagnosis if it's off |
|---|---|---|
| 1 | **How many documents came back?** | Fewer than `k` → the store has less than you think, or a filter over-matched. `k=1` when the question needs synthesis → the `k=1` bug from Story C |
| 2 | **Are they on-topic at all?** | No → embedding/query mismatch. Try hybrid search, or check the query was not mangled before the retriever saw it |
| 3 | **On-topic but the wrong granularity?** | Chunk boundaries cut the answer in half. Raise `chunk_size` or `chunk_overlap` |
| 4 | **Right document, wrong section?** | Classic overlap problem — the answer straddles a boundary |
| 5 | **Correct chunks present, answer still wrong?** | **Generator** error. Now go to the prompt run |
| 6 | **In the prompt run: is the context actually in the string?** | Empty or `{context}` literal → template variable bug. Extremely common, instantly visible, invisible without tracing |
| 7 | **Context there, grounding instruction weak?** | The lenient-prompt failure. Strengthen to "answer only from context; if insufficient, say you don't know" and consider demanding citations |

Check 6 deserves emphasis. A silent template-variable mismatch — you wrote `{context}` in the template but the dict key is `contexts` — produces a prompt where the context is missing or literal. The app doesn't crash. The LLM answers from parametric memory and sounds confident. Without the assembled prompt in front of you, this bug can survive for weeks.

---

## Recap

- RAG has **two independent failure points** with unrelated fixes; without intermediates you cannot tell which fired.
- Tracing records the **retrieved documents** and the **assembled prompt** — the two fields that split the diagnosis.
- **Problem 1:** LangSmith auto-traces **only LangChain runnables**. Plain Python (load, chunk, embed) is invisible → lesson 08.
- **Problem 2:** re-embedding the whole corpus on every process start, ~202 s per query → lesson 10.
- Observability's second job is showing authors the flaws in their own designs.
- Read a bad RAG trace in a fixed order: document count → topicality → granularity → prompt assembly → grounding strength.

---

## Self-check

1. Why does `RunnableParallel` show up as a run with children rather than as one flat step?
2. The retriever returned four on-topic chunks and the answer still contradicts them. Which run do you open next, and what exactly are you looking for in it?
3. State the rule for what LangSmith auto-traces in one sentence.
4. Problem 2 is not an observability problem. So why is it in a lesson about tracing?

---

**Next:** [`08-the-traceable-decorator.md`](08-the-traceable-decorator.md) →
