# Video 20 — RAG using LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `E1qP9Xsnmik`
> **Watch:** https://www.youtube.com/watch?v=E1qP9Xsnmik

## 🎯 Overview
This video turns the running chatbot into a **RAG (Retrieval-Augmented Generation)** chatbot — a "multi-utility chatbot" that can chat normally, use tools/MCP, **and** answer questions over an uploaded document (e.g. a PDF). The key idea taught is that in LangGraph the cleanest way to add RAG is to **wrap the retriever as a tool** and treat it exactly like any other tool. The video has three parts: a conceptual RAG recap (why/what/how), building a RAG chatbot from scratch in a notebook, and integrating RAG into the existing chatbot project.

## 🧠 Key Concepts

### Why RAG — three primary reasons
1. **Outdated knowledge.** Every LLM has a **knowledge cutoff date**; it can't answer about events after training. Tools like ChatGPT appear to know recent facts only because they do a **web search** behind the scenes and process the retrieved info — which is conceptually RAG itself.
2. **Privacy / private data.** LLMs never saw your private or personal data during training (company financials, a personal expense sheet). RAG lets you connect private documents so the LLM can answer over them. This is the biggest, most important use case.
3. **Hallucination.** LLMs sometimes confidently produce **false information** (e.g. citing papers whose links 404). RAG **grounds** responses in the provided context — "answer only from what you're given, don't make things up."

### The core principle — in-context learning
RAG rests on **in-context learning**: if you provide extra **context** alongside the question, the LLM can answer based on that context. The normal flow is `prompt → LLM → (parametric knowledge) → response`. Parametric knowledge is what the model learned during training. When the question concerns private data the model never saw, you **paste the relevant content as context** into the prompt, and the LLM answers using query + context + its parametric knowledge.

### The context-window problem and why you filter
You can't just paste **everything** as context — the LLM's **context window** is limited (a finite number of tokens). A small expense sheet fits, but 100 e-books or an entire codebase will exceed the window. So RAG's crucial step is **context filtering**: paste only the part of the source that is relevant to the query. If the user asks "What is machine learning?", you retrieve only the few pages that discuss it — not the whole 200-page book.

### How RAG works — the architecture (indexing + retrieval)
**Indexing (done once):**
1. Take a **knowledge source** (book, web page, etc.).
2. **Split** it into smaller parts/chunks (e.g. a 100-page book → pages/chunks).
3. Generate an **embedding** for each chunk using an **embedding model** — a set of numbers capturing the chunk's **semantic meaning**.
4. Store the embeddings (and their corresponding text) in a **vector store** (specialized database), e.g. **FAISS** or **Chroma**.

**Retrieval (per query):**
5. The user's question goes to a **retriever**.
6. The retriever converts the question into an embedding (same embedding model).
7. It compares that vector against the stored vectors to find the **most similar** ones (semantic similarity) — say pages 1, 5, 99.
8. It extracts the corresponding **text** of those chunks as context.
9. The original query **plus** the retrieved page text are packed into a prompt and sent to the LLM.
10. The LLM reads the query, studies the retrieved pages, uses its parametric knowledge to phrase things, and produces a grounded response.

> Note: the vector store stores **both** the vectors **and** the corresponding text/page, so retrieval can return usable content.

### The LangGraph approach — RAG as a tool
LangGraph offers multiple ways to implement RAG, but the simplest — and an excellent, reusable template for agentic AI apps — is to **define RAG as a tool** and treat it like any other tool. The chat node then decides, per query, whether it needs RAG; if yes it routes to the tool node (which runs the retriever), gets the context back, and generates the answer.

## 🔧 Code / Implementation

### Install & imports
```bash
pip install langchain langchain-openai langchain-community faiss-cpu pypdf ...
```

### Indexing: load → split → embed → store → retriever
```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")

# 1) Load the document (a PDF book: "Intro to ML")
loader = PyPDFLoader("intro_to_ml.pdf")
docs = loader.load()

# 2) Split into chunks (size + overlap so context carries across chunks)
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# 3) Embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 4) Build vector store from chunks (embeds each chunk and stores it)
vector_store = FAISS.from_documents(chunks, embeddings)

# 5) Create a retriever (semantic similarity, top-4 results)
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 4},
)
```

### Testing the retriever
```python
results = retriever.invoke("What is a decision tree?")
len(results)          # 4 — the four most similar chunks
results[0].page_content   # the main answer text lives in page_content
results[0].metadata       # producer, author, date, etc.
```
Each returned **Document** object has `id`, `metadata`, and `page_content` (where the main answer text lives).

### Wrapping RAG as a tool
```python
from langchain_core.tools import tool

@tool
def rag_tool(query: str) -> dict:
    """Use this tool to answer any question about the uploaded document.
    It retrieves the most relevant passages from the document for the query."""
    docs = retriever.invoke(query)
    context = [d.page_content for d in docs]     # text of the top-4 chunks
    metadata = [d.metadata for d in docs]        # metadata can also help the LLM
    return {"query": query, "context": context, "metadata": metadata}
```

### Binding, nodes, and graph (identical shape to the tools video)
```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

tools = [rag_tool]
llm_with_tools = llm.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

def chat_node(state: ChatState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

tool_node = ToolNode(tools)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")   # loop back so the LLM can compose the final answer
chatbot = graph.compile()

chatbot.invoke({"messages": [
    "Using the PDF notes, explain how to find the ideal value of K in K nearest neighbours."
]})
```

## 🪜 Step-by-Step Walkthrough

### Part 2 — RAG chatbot from scratch (notebook)
1. In `rag.ipynb`, install packages, import libraries, `load_dotenv`, and define the LLM (`gpt-4o-mini`).
2. **Load** the PDF (`intro_to_ml.pdf`) with `PyPDFLoader().load()`.
3. **Split** it into chunks with `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)` — overlap preserves context between chunks.
4. Create the **embedding model** (`OpenAIEmbeddings("text-embedding-3-small")`).
5. Build the **FAISS** vector store with `FAISS.from_documents(chunks, embeddings)` — embeds and stores every chunk.
6. Create the **retriever** via `vector_store.as_retriever(search_type="similarity", k=4)`.
7. Test it: `retriever.invoke("What is a decision tree?")` returns 4 Document objects; inspect `page_content` and `metadata`.
8. Wrap the retriever in a `@tool` (`rag_tool`) that invokes the retriever, extracts `page_content` and `metadata`, and returns a dict of `{query, context, metadata}`.
9. Put the tool in a list, `bind_tools`, and build the standard graph: `chat_node` + `tools` (ToolNode), `START → chat_node`, conditional `tools_condition`, and the loop-back edge `tools → chat_node`.
10. Invoke with document questions. Each query takes ~8–9 seconds because of the round trip to the vector database; the grounded answer comes back correctly.
11. (Optional) Inspect in **LangSmith**: the flow is three steps — question → chat_node decides to call `rag_tool` → tool node retrieves 4 chunks → chunks return to chat_node, which composes the final answer.

### Part 3 — Integrate RAG into the existing project
1. In the `chatbot-in-langgraph` folder, add two files: `langgraph_rag_backend.py` (backend) and `streamlit_rag_frontend.py` (frontend).
2. In the backend, add an `ingest_pdf` function that does the three indexing steps (load → split → embed) and builds the retriever.
3. Keep the existing tools (search, calculator, get_stock_price) and **add the `rag_tool`** alongside them; bind all tools to the LLM.
4. The LangGraph code and downstream flow are mostly the same as prior videos, with a bit of extra **error handling** added.
5. In the frontend, the one major change is a **sidebar file uploader** so the user can upload a PDF; plus minor thread-handling tweaks.
6. Rename the app "Multi-Utility Chatbot" — it now supports normal chat, tools, MCP, and RAG together.

## ⚠️ Gotchas & Tips
- **Treat RAG as just another tool** — this is the simplest LangGraph pattern and the standard architecture for agentic AI apps.
- **Filter, don't dump.** Never paste an entire document as context; retrieve only the relevant chunks or you'll blow past the **context window**.
- **Use chunk overlap** in the splitter so semantic context is retained across chunk boundaries.
- **The vector store stores text too**, not just vectors — that stored `page_content` is what actually feeds the LLM.
- **`page_content` holds the answer**; `metadata` (author, producer, date, ...) can optionally be passed to the LLM as extra signal.
- **`k` controls recall/precision** — here `k=4` returns the four most semantically similar chunks.
- **Expect latency** (~8–9 s per query) due to the embedding + vector-DB round trip.
- **Write the tool's docstring carefully** so the LLM knows to invoke it for questions about the uploaded document.
- Watch the instructor's dedicated "What is RAG" (~1 hour) video if the recap feels too fast.

## 📌 Key Takeaways
- RAG matters for three reasons: **outdated knowledge**, **private data**, and **hallucination** (grounding).
- RAG is built on **in-context learning**: supply relevant context in the prompt so the LLM answers from it.
- The pipeline is **load → split → embed → store (vector DB) → retrieve (top-k) → generate**.
- Embeddings capture **semantic meaning**; vector stores (**FAISS**, **Chroma**) hold both vectors and their text.
- A **retriever** embeds the query, finds the most similar chunks, and returns their text as context.
- In LangGraph, the cleanest implementation is to **wrap the retriever in a `@tool`** and reuse the exact tools graph: `chat_node → tools → chat_node` with `tools_condition`.
- Retrieved Document objects expose `id`, `metadata`, and `page_content` (the answer text).
- Project integration adds an `ingest_pdf` step, a `rag_tool` beside existing tools, a PDF **file uploader** in the sidebar, and some error handling — producing a multi-utility chatbot combining chat, tools, MCP, and RAG.
