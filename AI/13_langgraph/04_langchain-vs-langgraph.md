# Video 04 — LangChain vs LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `31qyMKNB2RA`
> **Watch:** https://www.youtube.com/watch?v=31qyMKNB2RA

## 🎯 Overview
The third content video and the bridge from "what is agentic AI" to "how do we build it." It answers three things: (1) a deep intuition for **why LangGraph exists** — what LangChain cannot do that forced LangGraph into being; (2) a **technical overview** of LangGraph; and (3) a side-by-side **LangChain vs LangGraph** comparison. The method: take the automated-hiring **workflow** from the previous video, try to build it in LangChain, and surface the challenges — then show how LangGraph solves each. By the end you can look at any project and know which library to reach for.

**Prerequisite:** a working idea of LangChain (at minimum the "Introduction to LangChain" and "LangChain Components" videos from the LangChain playlist).

## 🧠 Key Concepts

### Frameworks for agentic AI
Building agentic applications from scratch in plain Python is hard, so frameworks exist: **CrewAI**, **Microsoft AutoGen**, ADK (recent), and **LangGraph** (built by the **LangChain** team). This series uses **LangGraph**, which is considered one of the top agentic frameworks and benefits from LangChain's maturity.

### LangChain recap
> *LangChain is an open-source library designed to simplify the process of building LLM-based applications.*

It provides **modular building blocks**:
- **Model** — a **unified interface** to talk to any LLM provider (OpenAI, Anthropic/Claude, Hugging Face, Ollama). Swapping one LLM for another needs almost no code changes.
- **Prompts** — build and engineer prompts (prompt templates, etc.).
- **Retrievers** — fetch relevant documents from a vector store / knowledge base (the basis for RAG).
- **Chains** — LangChain's signature offering: connect components so the **output of one block automatically becomes the input of the next** (prompt → model → output parser → ...). You never wire the plumbing manually.

**What you can build with LangChain:** simple conversational workflows (chatbots, text summarizers), multi-step workflows (topic → detailed report → summary), RAG applications (retriever → context + prompt → LLM → answer), and **basic agents** via the **tools** concept (the LLM decides when to call which tool, e.g., a weather API).

### Critical distinction: Workflow vs Agent
Referencing Anthropic's blog **"Building Effective Agents"**:
- **Workflows** are systems where **LLMs and tools are orchestrated through predefined code paths.** The path is fixed by the **developer**; it runs the same way every time (**static**).
- **Agents** are systems where **LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks.** The flow is decided by the agent at runtime and can differ each run (**dynamic**).

The detailed automated-hiring flowchart in this video is a **workflow** (developer-built, static), *not* an agent — even though both use LLMs. This distinction matters throughout the playlist.

### The automated-hiring workflow (walkthrough)
A comprehensive, **non-linear** flowchart:
1. Receive a **hiring request** (prompt: remote backend engineer, 2–4 yrs).
2. **Create JD** (LLM).
3. **Human approval** of the JD → if not approved, **loop back** to Create JD (with feedback).
4. **Post JD** to platforms via **tools** (LinkedIn / Naukri APIs).
5. **Wait 7 days.**
6. **Monitor applications** (LinkedIn API) and check against a **threshold** (e.g., 20).
   - **Below threshold** → **modify JD** (loosen criteria / broaden role / raise salary) → **wait 48 hours** → re-monitor (**loop**).
   - **At/above threshold** → proceed.
7. **Shortlist** — resume-parser tool downloads/parses resumes; an LLM scores each against the JD; keep those above a score threshold.
8. **Schedule interviews** — calendar API (check availability) + mail API (invite).
9. **Conduct interview** — question bank, reminder mails, then, per candidate, **selected?** No → **regret email**; Yes → **offer letter**.
10. **Offer** (LLM + mail API) → **accepted?** No → **renegotiate** → resend; Yes → **onboarding** (HRMS: welcome email, KT session, laptop provisioning).

This flowchart is **static** — it executes the same way every time; the developer built it, so it is a workflow, not an agent.

### The eight challenges of building this in LangChain (and how LangGraph solves them)
The instructor frames the discussion as a set of points; the video walks through these seven distinct challenges/features.

#### 1. Control-flow complexity
LangChain is great for **linear** chains, but this flow is **highly non-linear** due to three things: **conditional branches** (enough applicants → one way, else another), **loops** (keep re-creating the JD until approved; keep modifying until threshold met), and **jumps** (control moving forward/backward, e.g., after a 48-hour wait). LangChain has **no constructs** for conditional branching, loops, or jumps, so you must write your own **glue code** in Python. The more glue code, the harder it is to maintain, debug, and collaborate on.

**LangGraph solution:** represent the whole workflow as a **graph** (hence the name). Each task is a **node** (a plain Python function), and **edges** connect nodes to define control flow. Because a graph is inherently a **non-linear** data structure, any complexity is easy to express — with **conditional edges** for branching and edges that **loop back**. Result: **zero glue code** and high maintainability.

#### 2. State handling
A complex workflow has **state** — data points that **evolve over time** as execution proceeds: the JD text, `jd_approved`, `jd_posted`, application count, the minimum-applications threshold, shortlisted candidates + contact details, offers sent, offer status, onboarding status, etc. Together these key-value pairs form the **state** of the workflow, and the whole flow depends on tracking it correctly.

LangChain is **stateless**: its only "memory" is **conversational memory** (chat history), not a general mechanism to store/track arbitrary key-value state. To implement state, you must **manually** maintain a global dictionary and mutate it at every step — error-prone and hectic for complex flows.

**LangGraph solution:** execution is **stateful**. When you create the graph you define a **state object** (using **Pydantic** or a **TypedDict**) — a dictionary that is **accessible and mutable by every node**. Each node receives the state as input, reads it, updates it, and returns it, so the updated state flows node-to-node. Information passing is clean and automatic no matter how many fields the state has. **Key line: LangChain is stateless; LangGraph is stateful.**

#### 3. Event-driven execution
A workflow can run **sequentially** (left-to-right, never stopping) or be **event-driven** (pause mid-way and wait for an **external trigger**, then resume). The hiring workflow needs event-driven execution in several places: **wait 7 days** after posting; **wait 48 hours** after modifying the JD; **wait** for a candidate to accept/reject an offer.

LangChain is built for **sequential** (synchronous, short-lived) execution — once a chain starts, it finishes. To fake pausing you'd split into multiple chains + external Python to track time + **manual state transfer** between them → lots of glue code.

**LangGraph solution:** event-driven execution is **inherent**. Because execution is stateful, at any node you can **save the current state** (using a **checkpointer** — in-memory or an external database), **pause**, and later **resume** exactly where you left off when the trigger arrives.

#### 4. Fault tolerance
> *Fault tolerance = whether a system can recover and continue running properly after something goes wrong.*

It matters for **long-running** workflows, and hiring can run for days or months. Two fault types: **small** (node-level, e.g., LinkedIn API down while posting) and **big** (system-level, e.g., the AWS server / Docker container hosting the workflow goes down).

LangChain has **no fault tolerance** — if a 5-step chain dies at step 3, you must **re-run from the start** (its chains are assumed short-lived).

**LangGraph solution:** built-in fault tolerance of both kinds:
- **Retry logic** for small faults (catch the error, wait, retry — e.g., retry the LinkedIn post).
- **Recovery** for big faults via the **checkpointer/persistence layer**: LangGraph snapshots state after **every node**, so a `resume` can restart from the exact node that failed (identifying the previous state and the next node) rather than from the beginning.

#### 5. Human-in-the-loop (HITL)
Many workflows need a **human decision** at a stage (e.g., approve the JD before posting). Approval may take a **long time** (e.g., 24 hours).

In LangChain there is **no default mechanism** to pause a chain indefinitely, wait for a human, then resume. Short-duration input is fine, but a long wait keeps the synchronous script alive, consuming compute and risking a crash. Workaround: split the chain in two and **manually transfer state** across the human gap → more glue code and maintainability problems. (LangChain is not designed for long-running workflows.)

**LangGraph solution:** HITL is a **first-class citizen**. Per the docs, LangGraph *"allows you to pause execution indefinitely — for minutes, hours, or even days — until human input is received,"* because it **checkpoints the graph state after every step**, so it can persist execution context and resume later, supporting **asynchronous human review without time constraints**. Analogy: **saving progress in a video game** — quit at stage 3, resume at stage 3.

> Note: challenges 3, 4, and 5 are all connected — they all rely on **stateful execution + checkpointer**.

#### 6. Nested workflows / subgraphs (a feature, not a challenge)
> *A subgraph is a graph that is used as a node in another graph* — encapsulation applied to LangGraph.

In LangGraph a single node can itself **be an entire graph**, so you can build **nested workflows**. Example: "Conduct interview" looks like one node but is really complex (generate per-candidate questions, run multiple rounds with evaluations), so model it as its own subgraph. **Two big use cases:**
- **Multi-agent systems** — e.g., a self-driving car with separate agents for sensors, driving, entertainment, and a "CEO" agent coordinating the rest.
- **Reusability** — build a reusable **approval** subgraph and reuse it wherever approval is needed (JD approval, posting approval, scheduling approval), just like reusing functions in programming.

LangChain does **not** offer this.

#### 7. Observability
> *Observability refers to how easily you can monitor, debug, and understand what your workflow is doing at run time.*

Crucial in production (errors, crashes, unexpected decisions, auditing — e.g., an agent that overspent on ads). LangChain *does* have observability via **LangSmith**, a library that monitors LLM-based apps (records each LLM call, the prompt sent, the reply, token counts, latency, etc.). **But** LangSmith can only track the **LangChain code**, not your **glue code** — so complex LangChain apps get only **partial observability** (it can't see inside your custom loops).

**LangGraph solution:** **tight LangSmith integration**. Since execution is fully stateful and there is **no glue code**, LangGraph reports everything — a complete **chronological timeline**: which node executed when, state before/after each node, human↔agent messages, and where the human gave approval. Result: **complete observability**, making debugging and auditing far easier.

### LangGraph — the summary definition
> *LangGraph is an orchestration framework that enables you to build stateful, multi-step, and event-driven workflows using LLMs. It's ideal for designing both single-agent and multi-agent agentic AI applications.*

Think of LangGraph as a **flowchart engine for LLMs**: you define the steps as **nodes**, how they connect as **edges**, and the logic governing transitions — and LangGraph handles **state management, conditional branching, looping, pausing & resuming, and fault recovery** — the features essential for robust, production-grade AI systems.

### When to use what
- **LangChain** → simple **linear** workflows: prompt chains, summarizers, a basic RAG system.
- **LangGraph** → complex **non-linear** workflows: conditional paths, loops, human-in-the-loop steps, multi-agent coordination/collaboration, and asynchronous/event-driven execution.

### Should you abandon LangChain? No.
LangGraph is **built on top of LangChain** and is **not** a replacement. You still use LangChain **components** — `ChatOpenAI`, prompt templates, retrievers, document loaders, text splitters, tools — inside LangGraph. **LangChain provides the components; LangGraph orchestrates them into a workflow.** They work hand-in-hand, and the playlist uses both.

## 🔧 Code / Implementation
*Reconstructed and conceptual — the video showed sketches, not full runnable code.*

**A subset of the flow in LangChain** (JD-approval loop) — note the required **glue code**:
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# The hiring request comes from the user
hiring_prompt = "We need to hire a software engineer for our backend team."

# Chain: create a JD from the hiring request
llm = ChatOpenAI()
jd_prompt = PromptTemplate.from_template(
    "Create a job description based on the hiring request:\n{hiring_request}"
)
jd_chain = jd_prompt | llm | StrOutputParser()

# Dummy helper functions (real logic added later)
def approve(jd: str) -> bool:
    ...            # human approval -> True/False
    return False

def post(jd: str) -> None:
    ...            # post the JD to job platforms

# GLUE CODE: LangChain has no loop/branch construct, so we write our own
approved = False
while not approved:                       # <-- custom Python loop = glue code
    jd = jd_chain.invoke({"hiring_request": hiring_prompt})
    approved = approve(jd)

post(jd)                                  # exit loop once approved
```

**The same subset in LangGraph** — nodes are plain functions, edges define flow, **zero glue code**:
```python
from langgraph.graph import StateGraph, END

# Each node is a plain Python function taking and returning the shared state.
def hiring_request(state): ...
def create_jd(state):
    state["jd"] = jd_chain.invoke({"hiring_request": state["hiring_request"]})
    return state
def check_approval(state):
    state["approved"] = approve(state["jd"])   # human approval
    return state
def post_jd(state):
    post(state["jd"])
    return state

graph = StateGraph(State)          # State = TypedDict/Pydantic model shared by all nodes

# Register nodes
graph.add_node("hiring_request", hiring_request)
graph.add_node("create_jd", create_jd)
graph.add_node("check_approval", check_approval)
graph.add_node("post_jd", post_jd)

# Edges = control flow
graph.add_edge("hiring_request", "create_jd")
graph.add_edge("create_jd", "check_approval")

# Conditional edge: loop back to create_jd if not approved, else move to post_jd
graph.add_conditional_edges(
    "check_approval",
    lambda state: "post_jd" if state["approved"] else "create_jd",
)
graph.add_edge("post_jd", END)
```
The loop and the branch are expressed **declaratively** through edges — LangGraph runs the `while`/`if-else` logic for you, and every node reads/updates the shared **state**.

## 🪜 Step-by-Step Walkthrough — the teaching arc
1. Recap **LangChain** (components + chains) and what it can build.
2. Draw the full **automated-hiring flowchart** and establish it as a **static workflow**, not an agent.
3. Try to build it in LangChain; code a small subset and expose the **glue code** problem.
4. Enumerate the **challenges** (control flow, state, event-driven, fault tolerance, human-in-the-loop) plus **features** (subgraphs, observability), showing LangChain's limits and LangGraph's solutions.
5. Land the **LangGraph definition**, **when-to-use-what**, and why **LangChain is still needed**.

## ⚠️ Gotchas & Tips
- **Glue code is the villain.** Every time you leave the library to stitch flow in raw Python, maintainability, debuggability, and observability suffer. LangGraph minimizes it to (near) zero.
- **Stateful vs stateless** is the single idea underlying event-driven execution, fault recovery, and human-in-the-loop — all powered by the **checkpointer/persistence layer**.
- A **workflow is static** (developer-defined path); an **agent is dynamic** (LLM decides the path at runtime). Don't conflate them.
- Don't discard LangChain knowledge — LangGraph **orchestrates** LangChain **components**; both are used together.
- Several advanced ideas here (checkpointers, persistence, subgraphs, HITL, observability/LangSmith) are covered in depth later in the playlist — a high-level understanding now is enough.

## 📌 Key Takeaways
- **LangChain** = an open-source library that simplifies LLM apps via **components** (model, prompts, retrievers) and **chains**; excellent for **linear** workflows.
- **LangGraph** = an **orchestration framework** for **stateful, multi-step, event-driven** workflows and **single/multi-agent** systems; a "flowchart engine for LLMs" using **nodes + edges + state**.
- LangChain **struggles with non-linear** flows (conditionals, loops, jumps) because it lacks those constructs and forces **glue code**.
- LangGraph solves the core challenges: **control-flow complexity** (graph + conditional edges), **state handling** (stateful, shared mutable state object), **event-driven execution** (checkpointer pause/resume), **fault tolerance** (retry + recovery), **human-in-the-loop** (first-class, indefinite pause), plus **subgraphs** (multi-agent + reusability) and **complete observability** (tight LangSmith integration).
- **LangChain is stateless; LangGraph is stateful** — the pivotal difference.
- **Use LangChain for simple linear tasks, LangGraph for complex non-linear/agentic tasks** — and remember **LangGraph is built on top of LangChain**, so you keep using LangChain components inside it.
