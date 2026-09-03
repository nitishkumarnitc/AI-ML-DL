# Video 22 — How to build Subgraphs in LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `wcHcocpAoX4`
> **Watch:** https://www.youtube.com/watch?v=wcHcocpAoX4

## 🎯 Overview
A **subgraph** is a graph that is embedded and executed as a node inside another (parent) graph. This concept becomes essential when building **multi-agent systems**, where a large, complex workflow is decomposed into smaller, independent agents. The video covers what subgraphs are, why they matter, their benefits, the **two mechanisms** LangGraph offers for wiring a subgraph into a parent (separate state vs. shared state), and a hands-on English→Hindi translation example implemented both ways.

## 🧠 Key Concepts

### What a subgraph is
So far we've represented any AI workflow as a **graph** whose **nodes** are tasks (an LLM call, a vector-DB retrieval, a tool call). A subgraph is what you get when you **replace one node with an entire graph**. Definition given in the video:

> *A subgraph in LangGraph usually means a graph that is embedded and executed as a node inside another graph.*

Visually: a large outer graph whose nodes are themselves graphs — those inner graphs are the subgraphs.

### Why subgraphs are needed
Early GenAI apps are simple (user query → LLM → output). Real-world GenAI systems get complex: tools, RAG, conditional routing, retries, memory, HITL, evaluation, guardrails — a lot going on at once.

**Motivating example — a software-developer agent.** The software-development process maps to: a **team lead** (planning) → **backend** and **frontend** dev teams (coding) → **testing** → **code review** → **DevOps** (deploy & monitor). Building this as one giant LangGraph graph would be enormously complex — every module might have its own tools, retry logic, memory, HITL, and guardrails.

The fix is to **decompose the big agent into small agents** (a multi-agent architecture): planning agent, two coding agents, testing agent, code-review agent, DevOps agent. **Each agent is represented by a subgraph** that contains its own internal graph, tools, memory, evaluation logic, and guardrails.

### Conceptual benefits
- **Modularity.** Like breaking a codebase into functions — a core software principle applied to graphs.
- **Reusability.** The same coding-agent subgraph can serve both the backend and frontend teams — both are "just coding," only on different files.
- **Maintainability.** Debugging is far easier: pick the specific subgraph where the problem is and debug it in isolation.

### LangGraph-specific benefits
- **Failure isolation.** If one subgraph fails or hits a problem, the rest of the parent graph still executes (with warnings). Without subgraphs, a single node failure can jeopardize the whole graph.
- **State separation.** Every graph in LangGraph has its own state (data about the graph). Building the whole complex agent as one graph forces all components to share a single state — undesirable. With subgraphs, each agent can define its own state, so states don't clash.
- **Observability.** LangGraph lets you trace at a granular level — you can trace each subgraph independently (e.g., how many tokens the coding agent consumes, its average latency), separately from the testing or review agents. This pairs with tools like LangSmith.

### The two mechanisms for adding a subgraph
The LangGraph docs say: *"When adding subgraphs, you need to define how the parent graph and the subgraph communicate."* There are two ways:

1. **Invoke a subgraph from inside a node.** ("Subgraphs are called from inside a node in the parent graph.") You build the parent graph and the subgraph **independently**, then write code inside a parent node that **invokes** the subgraph. There is no direct wiring between them. Here the two graphs **can have their own separate states**.
2. **Add a graph as a node.** ("A subgraph is added directly as a node and shares state keys with the parent.") Instead of a plain node, you place the **compiled subgraph itself as a node**. Here the parent and subgraph work on a **shared state** — the subgraph operates on the parent's state keys.

**Biggest difference:** mechanism 1 = **separate/isolated states**; mechanism 2 = **shared state**.

## 🔧 Code / Implementation

### Shared use case
User asks a question → an LLM generates an **English** answer → we want to show the user a **Hindi** answer, so a second (translator) LLM translates it. The translation is the piece we factor into a subgraph.

Parent graph: `START → generate → translate → END`.
Subgraph (translator): `START → translate → END`.

### Mechanism 1 — Invoke the subgraph from inside a node (separate states)
Two independent graphs, each with its own state (`SubState` for the subgraph, `ParentState` for the parent). The parent's `translate` node contains just one line: invoke the subgraph.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------- SUBGRAPH (built first, independently) ----------
class SubState(TypedDict):
    input_text: str        # the English answer coming in
    translated_text: str   # the Hindi translation going out

sub_llm = ChatOpenAI()

def translate_node(state: SubState):
    prompt = (
        "You will be given a text. Translate it into Hindi. "
        "Keep it natural and clear. Do not add any extra content.\n\n"
        f"{state['input_text']}"
    )
    result = sub_llm.invoke(prompt)
    return {"translated_text": result.content}

sub_builder = StateGraph(SubState)
sub_builder.add_node("translate", translate_node)
sub_builder.add_edge(START, "translate")
sub_builder.add_edge("translate", END)
subgraph = sub_builder.compile()

# ---------- PARENT GRAPH ----------
class ParentState(TypedDict):
    question: str
    english_answer: str
    hindi_answer: str

parent_llm = ChatOpenAI()

def generate_answer(state: ParentState):
    result = parent_llm.invoke(
        f"You are a helpful assistant. Answer this question: {state['question']}"
    )
    return {"english_answer": result.content}

def translate_answer(state: ParentState):
    # The ONLY job here is to invoke the subgraph with the English answer.
    sub_result = subgraph.invoke({"input_text": state["english_answer"]})
    # The subgraph returns its full final state; we pull out only the Hindi text.
    return {"hindi_answer": sub_result["translated_text"]}

parent_builder = StateGraph(ParentState)
parent_builder.add_node("generate", generate_answer)
parent_builder.add_node("translate", translate_answer)
parent_builder.add_edge(START, "generate")
parent_builder.add_edge("generate", "translate")
parent_builder.add_edge("translate", END)
parent_graph = parent_builder.compile()

final_state = parent_graph.invoke({"question": "What is machine learning?"})
# final_state has: question, english_answer, hindi_answer
```

### Mechanism 2 — Add the subgraph as a node (shared state)
No second, separate state — the subgraph works on the **parent's** state keys. The parent builds only the `generate` node itself; the `translate` step is the compiled subgraph placed **as a node**.

```python
class ParentState(TypedDict):        # single, SHARED state
    question: str
    english_answer: str
    hindi_answer: str

parent_llm = ChatOpenAI()
sub_llm = ChatOpenAI()

# ---------- SUBGRAPH designed against the SHARED state keys ----------
def translate_text(state: ParentState):
    prompt = (
        "Translate the following into Hindi, natural and clear:\n\n"
        f"{state['english_answer']}"
    )
    result = sub_llm.invoke(prompt)
    return {"hindi_answer": result.content}

sub_builder = StateGraph(ParentState)
sub_builder.add_node("translate_text", translate_text)
sub_builder.add_edge(START, "translate_text")
sub_builder.add_edge("translate_text", END)
subgraph = sub_builder.compile()

# ---------- PARENT: only ONE node defined; the translate step IS the subgraph ----------
def generate_answer(state: ParentState):
    result = parent_llm.invoke(
        f"You are a helpful assistant. Answer this: {state['question']}"
    )
    return {"english_answer": result.content}

parent_builder = StateGraph(ParentState)
parent_builder.add_node("generate", generate_answer)
parent_builder.add_node("translate", subgraph)   # <-- BIGGEST CHANGE: subgraph AS a node
parent_builder.add_edge(START, "generate")
parent_builder.add_edge("generate", "translate")
parent_builder.add_edge("translate", END)
parent_graph = parent_builder.compile()

final_state = parent_graph.invoke({"question": "What is machine learning?"})
# Same answer as Mechanism 1, but via a completely different mechanism.
```

## 🪜 Step-by-Step Walkthrough
1. Identify the reusable / self-contained piece of the workflow (here: translation).
2. **Decide the mechanism** — separate states (invoke from a node) or shared state (add as a node).
3. **Build the subgraph**: define its state (its own `SubState`, or the parent's state if sharing), add node(s), wire `START → ... → END`, and `compile()`.
4. **Build the parent graph** and its remaining nodes.
5. Wire the subgraph in — either call `subgraph.invoke(...)` inside a parent node (mechanism 1), or pass the compiled subgraph as a node via `add_node("translate", subgraph)` (mechanism 2).
6. Compile and `invoke` the parent graph; read the resulting state.

## ⚠️ Gotchas & Tips
- **Mechanism 1 (invoke from node):** the subgraph returns its **entire final state** — you must extract just the key you care about (e.g., `translated_text`) and place it into the parent state.
- **Mechanism 1 gives isolated states; mechanism 2 shares state keys** — choose based on whether the subgraph should see/modify the parent's data directly.
- **Persistence for subgraphs is automatic:** just give the **parent** graph a checkpointer, and LangGraph automatically checkpoints the child subgraph too. (Example lives in the docs.)
- You can also **stream** a subgraph's output and **view a subgraph's state** — both are shown in the official docs.
- The instructor strongly recommends reading the **official LangGraph subgraph documentation** — it mostly matches this video but adds persistence, streaming, and state-viewing details.

## 📌 Key Takeaways
- A subgraph = a graph embedded and executed as a node inside a parent graph.
- Subgraphs are the foundation of **multi-agent architectures** — decompose one big agent into small agent subgraphs.
- Conceptual benefits: modularity, reusability, maintainability.
- LangGraph-specific benefits: failure isolation, state separation, and granular observability (trace each subgraph independently).
- **Two mechanisms:** (1) invoke a subgraph from inside a node → separate states; (2) add the compiled subgraph directly as a node → shared state keys.
- Mechanism 1 requires manually extracting the needed key from the subgraph's returned final state; mechanism 2 lets it write straight into shared keys.
- Give the parent a checkpointer and subgraph persistence comes for free.
