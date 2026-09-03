# Video 27 — Advanced RAG: Corrective RAG (CRAG)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `41XDn81nR5c`
> **Watch:** https://www.youtube.com/watch?v=41XDn81nR5c

## 🎯 Overview
This video introduces **Corrective RAG (CRAG / C-RAG)**, a variant of RAG that stops the LLM from blindly trusting retrieved documents. It first shows — with a live demo — how traditional RAG fails when retrieval returns irrelevant chunks, then explains CRAG's fix: a **retrieval evaluator** that grades documents and routes into three cases (correct / incorrect / ambiguous), using **knowledge refinement** and **web search** to correct bad retrieval. The whole paper architecture is then built in LangGraph, step by step from a first-principles traditional-RAG base.

## 🧠 Key Concepts

### Traditional RAG recap
A query is embedded (embedding model → query vector), semantically searched against a **vector database** of your private documents (**retrieval**), the retrieved docs + query + a prompt are sent to the LLM (**augmentation**), and the LLM answers from those docs (**generation**). RAG = **retrieval + augmentation + generation**.

### The problem CRAG solves
The LLM is told to answer **only** from the retrieved docs, so it **blindly trusts** them. If retrieval returns the *wrong* docs, the answer is wrong. Example: ask *"What is an LLM?"* against a DB containing only ML books — semantic search still returns *something* (e.g. Random Forest chunks), and the LLM is forced to answer from irrelevant context. In a business setting (e.g. a leave-policy question whose document doesn't exist) this can produce confident **hallucinations** with dangerous consequences.

The demo used three classic ML/DL books. *"Bias–variance tradeoff"* worked (relevant chunks retrieved → accurate answer). *"What is a transformer in deep learning"* still produced a fluent answer **even though none of the four retrieved chunks mention transformers** — the answer came from the LLM's **parametric knowledge**, which is exactly where hidden hallucination risk lives.

### CRAG's core idea — the retrieval evaluator
After retrieval, CRAG does **not** send docs straight to the LLM. It inserts a **retrieval evaluator** that inspects the query and each document and decides relevance. Three cases:
- **Correct** (docs relevant) → refine the docs, then generate as usual (internal knowledge).
- **Incorrect** (docs not relevant) → go to an **external knowledge source** (web search) and answer from that.
- **Ambiguous** (partially relevant) → do **both**: keep the good docs *and* web-search for the rest, merge, then generate.

This mirrors the 2024 CRAG paper: query `x` → retrieve `d1, d2` → evaluator grades them → refine into *internal knowledge*, and/or web-search into *external knowledge* → generate.

### Build strategy — first principles
Rather than dropping the whole architecture at once, complexity is added iteratively to a plain traditional-RAG base:
1. Knowledge Refinement, 2. Retrieval Evaluation, 3. Web Search (incorrect case), 4. Query Rewrite, 5. Ambiguous case + simplification.

## 🔧 Code / Implementation

### Traditional RAG base
```python
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from typing import TypedDict, List
from langchain_core.documents import Document

# 1. load 3 ML/DL books -> ~2000 Document objects
docs = load_three_books()

# 2. split; also replace weird PDF chars to avoid unicode errors
splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
chunks = splitter.split_documents(docs)            # -> 6000+ chunks

# 3. embed + store in FAISS
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})   # top-4

llm = ChatOpenAI()

class RAGState(TypedDict):
    question: str
    docs: List[Document]
    answer: str

def retrieve(state: RAGState):
    return {"docs": retriever.invoke(state["question"])}

def generate(state: RAGState):
    context = "\n\n".join(d.page_content for d in state["docs"])
    prompt = (f"Answer ONLY from the context. If not in context, say you don't know.\n"
              f"Question: {state['question']}\nContext: {context}")
    return {"answer": llm.invoke(prompt).content}
# graph: retrieve -> generate   (blindly trusts docs)
```

### Iteration 1 — Knowledge Refinement (decompose → filter → recompose)
A retrieved chunk often mixes relevant text with junk (because 900-char chunking splits blindly). Refinement fixes this in three steps: **decomposition** (split the doc into sentence-level *strips*), **filtration** (grade each strip's relevance and drop irrelevant ones), **recomposition** (merge kept strips into a refined context). *(The paper fine-tuned a 770M-parameter T5-large for filtration; since that checkpoint isn't public, we use an OpenAI LLM.)*
```python
class RAGState(TypedDict):
    question: str
    docs: List[Document]
    strips: List[str]
    kept_strips: List[str]
    refined_context: str
    answer: str

def decompose_to_sentences(text: str) -> List[str]:
    # split a document into sentence-level strips (~1–2 sentences each)
    ...

# strict relevance filter -> structured true/false per strip
filter_prompt = (
    "You are a strict relevance filter. Return keep=true ONLY if the sentence directly "
    "helps answer the question. Use only the sentence. Output JSON only."
)
filter_chain = build_structured_chain(filter_prompt, llm)   # returns {keep: bool}

def refine(state: RAGState):
    context = "\n\n".join(d.page_content for d in state["docs"])
    strips = decompose_to_sentences(context)
    kept = [s for s in strips if filter_chain.invoke({"q": state["question"], "s": s}).keep]
    return {"strips": strips, "kept_strips": kept, "refined_context": " ".join(kept)}
# graph: retrieve -> refine -> generate
```

### Iteration 2 — Retrieval Evaluation (correct / incorrect / ambiguous)
An LLM scores **each** retrieved doc 0–1 for relevance to the query. With **lower = 0.3** and **upper = 0.7**:
- **correct** — at least one doc scores **> upper (0.7)**.
- **incorrect** — **no** doc scores **> lower (0.3)**.
- **ambiguous** — anything else.

Important: only docs with **score > lower (0.3)** (`good_docs`) are used for generation — even a doc scoring 0.2 in a "correct" batch is dropped.
```python
UPPER, LOWER = 0.7, 0.3

class EvalResult(BaseModel):     # structured output per document
    score: float
    reason: str

eval_prompt = (
    "You are a strict retrieval evaluator for RAG. You are given one retrieved chunk and a "
    "question. Return a relevance score between 0 and 1 (1 = chunk alone is sufficient to "
    "answer fully, 0 = irrelevant). Be conservative with high scores. Also return a short "
    "reason. Output JSON only."
)
evaluator = build_structured_chain(eval_prompt, llm)   # -> {score, reason}

def evaluate(state):
    scores, reasons, good_docs = [], [], []
    for d in state["docs"]:
        r = evaluator.invoke({"question": state["question"], "chunk": d.page_content})
        scores.append(r.score); reasons.append(r.reason)
        if r.score > LOWER:
            good_docs.append(d)                        # used for generation

    if any(s > UPPER for s in scores):
        return {"good_docs": good_docs, "verdict": "correct",   "reason": "at least one chunk > 0.7"}
    if not good_docs:                                  # no doc above lower threshold
        return {"good_docs": [], "verdict": "incorrect", "reason": "no chunk was sufficient"}
    return {"good_docs": good_docs, "verdict": "ambiguous", "reason": "mixed signals"}

def route_after_evaluation(state):
    return {"correct": "refine", "incorrect": "web_search", "ambiguous": "ambiguous"}[state["verdict"]]
```
State also gains `good_docs`, `verdict`, `reason`. Initially only the **correct** path fully generates; incorrect/ambiguous just print. Refinement is changed to build its context from **good_docs** only.

### Iteration 3 — Web Search for the incorrect case
When the verdict is **incorrect**, don't stop — search the web with **Tavily**, then **refine** those web docs (identical refine step) and **generate**. Refine and generate nodes are **reused**, not rewritten.
```python
# state gains: web_docs: List[Document]

def web_search(state):
    results = tavily.invoke(state["question"])
    web_docs = [Document(page_content=r["content"], metadata={"title": r["title"], "url": r["url"]})
                for r in results]
    return {"web_docs": web_docs}

# refine now chooses its source by verdict:
def refine(state):
    source = state["good_docs"] if state["verdict"] == "correct" else state["web_docs"]
    context = "\n\n".join(d.page_content for d in source)
    ...   # decompose -> filter -> recompose (same as before)
```

### Iteration 4 — Query Rewrite before web search
A vague user query (e.g. *"LLMs and recent developments"*) gives poor search results. Rewrite it into a keyword-rich, scoped, search-engine-friendly query first.
```python
class Query(BaseModel):
    query: str

rewrite_prompt = (
    "You are a web search query composer. Keep it short. If a question implies recency, add "
    "constraints like 'last 30 days'. Do NOT answer the question. Return JSON with a single query."
)
rewrite_chain = build_structured_chain(rewrite_prompt, llm)

def rewrite_query(state):                       # state gains web_query
    return {"web_query": rewrite_chain.invoke({"question": state["question"]}).query}
# web_search now uses state["web_query"] instead of the original question.
```
Example: *"recent AI news"* → rewritten to *"recent AI news last 30 days"*. The instructor notes it helps in only some cases, but the paper stresses it, so it's included.

### Final — Ambiguous case + simplification via state
For **ambiguous**, keep the good docs **and** web-search, merge everything into one context, then generate. Instead of a third branch, the graph is simplified to **two routes** by exploiting LangGraph state:
```python
def route_after_evaluation(state):
    # correct -> refine directly; incorrect OR ambiguous -> rewrite_query
    return "refine" if state["verdict"] == "correct" else "rewrite_query"

def refine(state):
    if state["verdict"] == "correct":
        source = state["good_docs"]
    elif state["verdict"] == "incorrect":
        source = state["web_docs"]
    else:  # ambiguous -> use BOTH retrieved good docs and web docs
        source = state["good_docs"] + state["web_docs"]
    context = "\n\n".join(d.page_content for d in source)
    ...   # decompose -> filter -> recompose
```
Flow by verdict:
- **correct** → refine(good_docs) → generate (internal knowledge only)
- **incorrect** → rewrite_query → web_search → refine(web_docs) → generate (external knowledge only)
- **ambiguous** → rewrite_query → web_search → refine(good_docs + web_docs) → generate (both)

This is the full paper architecture built from scratch.

## 🪜 Step-by-Step Walkthrough
1. Build traditional RAG: load → split (900/150) → FAISS → retriever(k=4) → `retrieve` → `generate`.
2. Add **knowledge refinement** (decompose → filter → recompose) between retrieve and generate.
3. Add a **retrieval evaluator** scoring each doc 0–1; classify **correct / incorrect / ambiguous** with upper 0.7 / lower 0.3; keep only `good_docs` (>0.3) for generation.
4. Add **web search (Tavily)** for the incorrect path; reuse refine + generate.
5. Add **query rewrite** before web search.
6. Fold the **ambiguous** case in (good_docs + web_docs) and simplify to two routes using state.

## ⚠️ Gotchas & Tips
- Traditional RAG **blindly trusts** retrieved docs — the root cause of hallucinations when retrieval is bad.
- **Chunking splits blindly** at a character count, so a chunk can mix relevant and irrelevant sentences — hence refinement.
- The paper's filter/evaluator used a **fine-tuned T5-large (770M)** (cheaper and better for the task); the video substitutes an OpenAI LLM only because that checkpoint isn't public.
- Two thresholds drive routing: **upper (0.7)** decides "correct", **lower (0.3)** decides which docs survive **and** whether the batch is "incorrect".
- Only **good_docs (score > 0.3)** are ever used for generation — drop weak docs even within a "correct" batch.
- **Rewrite queries** for the web to get richer results; add recency constraints when implied.
- Use **LangGraph state** to collapse the ambiguous branch — fewer nodes, less duplicated code.

## 📌 Key Takeaways
- **CRAG** adds a **retrieval evaluator** so the system never blindly trusts retrieved documents.
- Retrieval is graded into **correct / incorrect / ambiguous**, each handled differently.
- **Knowledge refinement** = decompose into strips → filter by relevance → recompose, improving generation quality.
- **Correct** → internal knowledge; **incorrect** → web search (external); **ambiguous** → both merged.
- Thresholds: **> 0.7** ⇒ correct; **no doc > 0.3** ⇒ incorrect; else ambiguous; **only docs > 0.3** feed generation.
- **Query rewriting** before web search yields better external results.
- Built first-principles on plain RAG, staying close to the 2024 CRAG paper (LLM substituted for the fine-tuned T5).
