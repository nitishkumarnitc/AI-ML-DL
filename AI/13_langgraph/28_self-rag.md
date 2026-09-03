# Video 28 — Self-RAG Tutorial — Advanced RAG

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `BbO_XaEjzaA`
> **Watch:** https://www.youtube.com/watch?v=BbO_XaEjzaA

## 🎯 Overview
This video covers **Self-RAG (Self-Reflective RAG)**, another advanced RAG technique (following the previous CRAG video). Its core idea is **self-reflection**: at every step the system judges its own actions — whether to retrieve at all, whether retrieved docs are relevant, whether the answer is grounded (no hallucination), and whether the answer is actually useful. After the theory, the full architecture is implemented in LangGraph step by step on a hypothetical company chatbot.

## 🧠 Key Concepts

### Three problems with traditional RAG
1. **Indiscriminate retrieval** — RAG retrieves *even when retrieval is unnecessary*. A kids' encyclopedia bot asked *"How many seconds are there in a minute?"* doesn't need retrieval; the LLM's parametric knowledge suffices. Forcing retrieval pulls in noisy chunks (some from a history encyclopedia), which makes the answer **less confident** ("*typically about 60 seconds, depending on context*") and **wastes compute**.
2. **Blindly trusts retrieved docs** — ask *"What causes diabetes?"*; a chunk about diabetes *effects* is semantically similar and gets retrieved, so the LLM produces a factually/logically off answer because it was forced to use that chunk.
3. **Doesn't verify its own answers** — once an answer is generated it becomes final; there's no check for hallucination or whether it truly answers the question.

### What Self-RAG is
> *Self-RAG stands for Self-Reflective RAG, where the LLM actively judges its own retrieval, evidence and answers instead of blindly trusting retrieved documents.*

Its USP is **self-reflection** — at each step the architecture questions its own actions and adjusts. It answers **four questions**:
1. **Is retrieval needed** for this query? (else answer directly from parametric knowledge)
2. **Are the retrieved documents relevant?** (grade each; keep relevant ones)
3. **Is the generated response grounded** in the retrieved docs? (hallucination check)
4. **Does the response actually answer** the user's question? (usefulness check)

### Grounding: fully / partially / no support
For question 3, every fact in the answer should come from the retrieved docs:
- **fully supported** — every fact traces to the context.
- **partially supported** — some facts are grounded, but the model **fabricated** extra facts (e.g. adding "*fatigue and headaches, especially in older patients*" not in the docs).
- **no support** — the whole answer is fabricated from parametric knowledge (a full hallucination).

### The Self-RAG architecture
```
question → decide_retrieval?
    ├─ no  → direct generate → END
    └─ yes → retrieve → relevance filter (grade each doc, keep relevant)
                ├─ none relevant → no answer found (or web search) → END
                └─ ≥1 relevant  → generate_from_context
                        → is_supported (fully / partially / no)
                            ├─ fully     → is_use
                            └─ partial/no → revise_answer → back to is_supported (loop, max retries)
                        → is_use (useful?)
                            ├─ useful     → finalize → END
                            └─ not useful → rewrite question → retrieve again (loop, max retries)
                                            → else no answer found → END
```
Two **loops** with **max-retries** break conditions prevent infinite cycles: the *revise_answer* loop (grounding) and the *rewrite question → retrieve* loop (usefulness). *(The paper used a specially fine-tuned model; this build uses OpenAI LLMs, so the core ideas match but the fine details differ.)*

The demo builds a RAG chatbot for a **hypothetical company, "Nexa AI Solutions"** (3 ChatGPT-generated docs: company profile, company policies, product & pricing), chunked at **size 600, overlap 150**.

## 🔧 Code / Implementation

### Base state and setup
```python
from typing import TypedDict, List, Literal
from pydantic import BaseModel, Field
from langchain_core.documents import Document

class SelfRAGState(TypedDict):
    question: str
    need_retrieval: bool
    docs: List[Document]
    relevant_docs: List[Document]
    context: str
    answer: str
    final_answer: str
    is_support: Literal["fully", "partially", "no"]
    evidence: List[str]
    is_use: Literal["useful", "not_useful"]
    reason: str
    retrieval_query: str
    rewrite_tries: int
# retriever + ChatOpenAI created as usual; chunk_size=600, chunk_overlap=150
```

### Step 1 — decide retrieval + direct generate + retrieve
```python
class ShouldRetrieve(BaseModel):
    should_retrieve: bool = Field(description="True if external documents are needed to answer reliably else False")

decide_llm = llm.with_structured_output(ShouldRetrieve)

DECIDE_PROMPT = (
    "You decide whether retrieval is needed. Return JSON matching the schema.\n"
    "should_retrieve = True if answering requires specific facts, citations, or info likely "
    "NOT in the model. False for general explanation, definitions, or reasoning. "
    "If unsure, choose True."
)

def decide_retrieval(state):
    decision = decide_llm.invoke([("system", DECIDE_PROMPT), ("human", state["question"])])
    return {"need_retrieval": decision.should_retrieve}

DIRECT_PROMPT = (
    "Answer the question using your general knowledge. Do NOT assume access to external "
    "documents. If unsure or the answer requires specific sources, say "
    "'I don't know based on my general knowledge.'"
)

def direct_generate(state):
    resp = llm.invoke([("system", DIRECT_PROMPT), ("human", state["question"])])
    return {"answer": resp.content}

def retrieve(state):
    # later this uses state["retrieval_query"] instead of the raw question
    return {"docs": retriever.invoke(state.get("retrieval_query", state["question"]))}

def route_retrieval(state):
    return "retrieve" if state["need_retrieval"] else "direct_generate"
```

### Step 2 — relevance filter (grade each doc)
```python
class IsRelevant(BaseModel):
    is_relevant: bool = Field(description="True if document helps answer the question else False")

relevance_llm = llm.with_structured_output(IsRelevant)

RELEVANCE_PROMPT = (
    "You are judging document relevance. Return JSON matching the schema. A document is "
    "relevant if it contains information useful for answering the question."
)

def is_relevant(state):
    relevant = []
    for doc in state["docs"]:
        r = relevance_llm.invoke([("system", RELEVANCE_PROMPT),
                                  ("human", f"Question: {state['question']}\nDocument: {doc.page_content}")])
        if r.is_relevant:
            relevant.append(doc)
    return {"relevant_docs": relevant}
```
Example: 4 docs retrieved for *"Who is the CEO of Nexa AI?"*, only the 1 truly-relevant doc kept; the semantically-close-but-irrelevant docs are filtered out (noise removed).

### Step 3 — generate from context (or bail out)
```python
GEN_PROMPT = "You are a business RAG assistant. Answer the user's question using ONLY the provided context."

def generate_from_context(state):
    context = "\n\n".join(d.page_content for d in state["relevant_docs"])
    resp = llm.invoke([("system", GEN_PROMPT),
                       ("human", f"Question: {state['question']}\nContext: {context}")])
    return {"context": context, "answer": resp.content}

def no_relevant_docs(state):          # placeholder — could be replaced by a web-search node
    return {"final_answer": "No relevant document found."}

def branch_after_relevance(state):
    return "generate_from_context" if len(state["relevant_docs"]) >= 1 else "no_relevant_docs"
```
The `no_relevant_docs` node is a deliberate **placeholder**: it can be swapped for a *rewrite query → web search → back to `is_relevant`* sub-flow to make the bot more robust (code provided in the repo but not wired into the final Self-RAG graph).

### Step 4 — is_supported (hallucination check)
```python
class Support(BaseModel):
    support: Literal["fully", "partially", "no"]
    evidence: List[str]

support_llm = llm.with_structured_output(Support)
# SUPPORT_PROMPT: check that every fact in the answer comes from the context; classify
# fully / partially / no support and extract the supporting evidence facts.

def is_supported(state):
    r = support_llm.invoke([("system", SUPPORT_PROMPT),
                            ("human", f"Question: {state['question']}\n"
                                      f"Answer: {state['answer']}\nContext: {state['context']}")])
    return {"is_support": r.support, "evidence": r.evidence}
```
Demos: *"How many employees does Nexa AI have?"* → **fully supported** (answer "85+" traces to evidence). *"Describe Nexa AI company culture"* → **partially supported** (model added extras beyond the evidence). *"Does Nexa AI have a free trial?"* (not in docs) → **no support** (model fabricated "14 days" from parametric knowledge) — and self-reflection catches it.

### Step 5 — revise_answer loop
```python
REVISE_PROMPT = ("You are a strict reviser. Rewrite the answer so that every fact is grounded "
                 "ONLY in the provided context; remove any fact not present in the context.")

def revise_answer(state):
    resp = llm.invoke([("system", REVISE_PROMPT),
                       ("human", f"Question: {state['question']}\n"
                                 f"Current answer: {state['answer']}\nContext: {state['context']}")])
    return {"answer": resp.content, "rewrite_tries": state.get("rewrite_tries", 0) + 1}

def branch_after_support(state):
    # fully supported -> accept; else revise and re-check (loop) unless retries exhausted
    if state["is_support"] == "fully":
        return "is_use"
    if state.get("rewrite_tries", 0) >= 5:      # break the loop
        return "is_use"
    return "revise_answer"
# revise_answer loops back to is_supported
```
In the demo, the previously *partially supported* culture answer becomes **fully supported** after **one** revision (answer trimmed to only evidence-backed facts).

### Step 6 — is_use (usefulness check)
Even a fully-grounded (non-hallucinated) answer may not actually answer the question (e.g. it ignores the key doc). So usefulness is checked separately.
```python
class IsUse(BaseModel):
    is_use: Literal["useful", "not_useful"]
    reason: str

use_llm = llm.with_structured_output(IsUse)
# IS_USE_PROMPT: does the answer actually justify/answer the question?

def is_use(state):
    r = use_llm.invoke([("system", IS_USE_PROMPT),
                        ("human", f"Question: {state['question']}\nAnswer: {state['answer']}")])
    return {"is_use": r.is_use, "reason": r.reason}

def branch_after_use(state):
    return "finalize" if state["is_use"] == "useful" else "no_answer_found"   # finalize == END
```

### Step 7 — rewrite question → retrieve loop
If the answer is **not useful**, rewrite the user's question into a retrieval-optimized query, go **back to retrieve**, and repeat the whole flow. A `rewrite_tries` / max-retries guard breaks the loop (→ "no answer found").
```python
class RewriteQuery(BaseModel):
    retrieval_query: str = Field(description="Rewritten query optimized for vector retrieval against internal company PDFs")

rewrite_llm = llm.with_structured_output(RewriteQuery)
REWRITE_PROMPT = ("Rewrite the user's question into a query optimized for vector retrieval over "
                  "internal company PDFs. Keep it short, preserve key entities, add 2–5 high-signal keywords.")

def rewrite_question(state):
    r = rewrite_llm.invoke([("system", REWRITE_PROMPT),
                            ("human", f"Question: {state['question']}\n"
                                      f"Previous retrieval query: {state.get('retrieval_query')}\n"
                                      f"Current answer: {state['answer']}")])
    return {"retrieval_query": r.retrieval_query, "rewrite_tries": state.get("rewrite_tries", 0) + 1}
# graph: not_useful -> rewrite_question -> retrieve (loop with max-retries break)
# initial invoke sends BOTH question and retrieval_query (retrieval_query = question at start)
```

## 🪜 Step-by-Step Walkthrough
1. **Decide retrieval** (`ShouldRetrieve`): direct-generate for general questions, else retrieve. Build direct-generate and retrieve nodes.
2. **Relevance filter**: grade each retrieved doc (`IsRelevant`), keep relevant ones in `relevant_docs`.
3. **Generate from context** using merged relevant docs; add a `no_relevant_docs` bail-out (placeholder for web search).
4. **is_supported**: classify the answer as fully / partially / no support (`Support`) to detect hallucination.
5. **revise_answer loop**: partial/no → revise to be strictly grounded → re-check `is_supported`; break after max retries.
6. **is_use**: check whether a grounded answer actually answers the question (`IsUse`).
7. **rewrite_question loop**: not useful → rewrite retrieval query → retrieve again → repeat; break after max retries → "no answer found".

## ⚠️ Gotchas & Tips
- **Retrieval isn't always needed** — indiscriminate retrieval adds noise, lowers confidence, and wastes compute; decide first.
- **Grade documents individually** and drop the irrelevant ones before generation.
- **Grounding ≠ usefulness** — an answer can be fully grounded yet still not answer the question, so run *both* checks.
- Any node that **loops** (revise, rewrite→retrieve) must have a **max-retries break** to avoid infinite loops.
- The two "dead-end" nodes (`no_relevant_docs`, `no_answer_found`) exist as **placeholders/branch points** so you can later attach web search or looping — hence separate paths that both end.
- Use **structured output (Pydantic)** for every reflection step (`ShouldRetrieve`, `IsRelevant`, `Support`, `IsUse`, `RewriteQuery`) to get reliable decisions.
- This build uses **OpenAI LLMs**, not the paper's fine-tuned model — conceptually identical, finer details differ.

## 📌 Key Takeaways
- **Self-RAG** = self-reflective RAG; the model judges its own retrieval, evidence, and answers at every step.
- It fixes three traditional-RAG flaws: **indiscriminate retrieval**, **blind trust** in docs, and **no answer verification**.
- Four reflection questions: **retrieve?**, **docs relevant?**, **answer grounded?**, **answer useful?**
- Grounding is graded **fully / partially / no support**; partial/no triggers a **revise** loop.
- Usefulness is a **separate** check; failure triggers a **query-rewrite → re-retrieve** loop.
- Both loops carry **max-retries** guards to terminate safely.
- Built step by step in LangGraph on a "Nexa AI" company chatbot, with each reflection step as a structured-output node.
