# Video 11 — Persistence in LangGraph & Time Travel

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `_IPP7_Bi8uA`
> **Watch:** https://www.youtube.com/watch?v=_IPP7_Bi8uA

## 🎯 Overview
This is a foundational, deep-dive video on **persistence** — the ability to *save and restore the state of a workflow over time*. Persistence is the base that many other LangGraph features are built on. The video first explains what persistence is and why it matters, then introduces the two supporting concepts (**checkpointers** and **threads**), and finally demonstrates the four big things persistence unlocks: **short-term memory, fault tolerance, human-in-the-loop, and time travel** — with hands-on code for each.

## 🧠 Key Concepts

### Recap: the two core ideas of LangGraph
1. **Graph** — decompose a high-level goal into tasks; represent tasks as **nodes** and execution order as **edges**.
2. **State** — a dictionary of the important data a workflow needs. Every node can **read from and write to** the state.

### Default behaviour vs persistence
Normally, when a workflow finishes executing, the state's values are **erased from RAM** and cannot be recovered later. **Persistence changes this**: it saves the state somewhere (typically a database) so you can inspect and reuse those values in the future.

Definition used in the video: *"Persistence in LangGraph refers to the ability to save and restore the state of a workflow over time."*

### The key insight: intermediate values are stored too
Persistence does **not** store only the *final* state — it stores the state at **every intermediate stage**. Example: with a `name` variable going `A` (start) → `B` (node 1) → `C` (node 2), persistence saves the value at each step (A, B, C, and final), not just `C`. This is exactly what enables fault tolerance and time travel.

### Checkpointers
Persistence in LangGraph is implemented via a **checkpointer**. It divides the graph's execution into **checkpoints** and saves the state's values at each one.
- **A checkpoint is created at every superstep.** A superstep groups nodes that execute together (parallel branches at the same level count as one superstep).
- At each checkpoint, all state values (intermediate + final) are saved to the store.
- **`InMemorySaver` / `MemorySaver`** saves to RAM — used for demos. Production uses durable checkpointers like the **Postgres** or **Redis** checkpointers.

**Checkpointer example (state has `numbers: Annotated[list[int], reducer]`):** if start=`[1]`, node1 adds `2` → `[1,2]`, then nodes produce `3,4,5` → `[1,2,3,4,5]`, each checkpoint stores the running list. A 4-checkpoint graph ends with 4 saved state snapshots.

### Threads
Every time you execute a workflow, you pass a **thread_id**. All state values for that run are stored **against that thread_id**. This lets you later retrieve exactly one execution's values — e.g., "give me the state stored against thread_id 2." For a chatbot, each conversation gets its own thread_id, which is precisely how you build a **resume-chat** feature: fetch all messages stored against that thread_id.

### The four benefits of persistence
1. **Short-term memory** — persistence is *the only way* to implement short-term memory in LangGraph; conversation history is saved so chats can resume.
2. **Fault tolerance** — because every intermediate state is saved, if a workflow crashes at a node you can resume from *exactly that point* rather than restarting from the beginning.
3. **Human-in-the-loop** — the workflow can be **interrupted** (temporarily suspended) at a point, wait indefinitely for human input (seconds or days), then **resume** from that exact point when input arrives. Persistence is what makes resuming possible.
4. **Time travel** — you can go back to a particular checkpoint and **replay** execution from there, optionally **updating the state** at that point to branch into an alternative outcome. Primarily useful for **debugging** complex workflows.

## 🔧 Code / Implementation

### The demo workflow — joke + explanation generator
```python
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

llm = ChatOpenAI()

class JokeState(TypedDict):
    topic: str
    joke: str
    explanation: str

def generate_joke(state: JokeState):
    prompt = f"Generate a joke on the topic {state['topic']}"
    response = llm.invoke(prompt).content
    return {"joke": response}

def generate_explanation(state: JokeState):
    prompt = f"Write an explanation for the joke: {state['joke']}"
    response = llm.invoke(prompt).content
    return {"explanation": response}

graph = StateGraph(JokeState)
graph.add_node("generate_joke", generate_joke)
graph.add_node("generate_explanation", generate_explanation)

graph.add_edge(START, "generate_joke")
graph.add_edge("generate_joke", "generate_explanation")
graph.add_edge("generate_explanation", END)

checkpointer = InMemorySaver()
workflow = graph.compile(checkpointer=checkpointer)
```

### Running with a thread_id and inspecting state
```python
config1 = {"configurable": {"thread_id": "1"}}
workflow.invoke({"topic": "pizza"}, config=config1)

# final state for this thread
workflow.get_state(config1)

# ALL checkpoint states (intermediate + final) for this thread
list(workflow.get_state_history(config1))
```
`get_state_history` returns **4 snapshots** for this 2-node graph:
- before START — empty state, `next = START`
- before `generate_joke` — only `topic`, `next = generate_joke`
- before `generate_explanation` — `topic` + `joke`, `next = generate_explanation`
- before END — `topic` + `joke` + `explanation`, `next = ()` (nothing left)

### Different threads store independently
```python
config2 = {"configurable": {"thread_id": "2"}}
workflow.invoke({"topic": "pasta"}, config=config2)
# get_state(config2) -> pasta joke; get_state(config1) -> pizza joke (still there)
```

### Fault tolerance (crash + resume)
```python
import time

class State(TypedDict):
    input: str
    step1: str
    step2: str
    step3: str

def step_2(state):
    print("step 2 running...")
    time.sleep(30)          # long delay -> we manually interrupt here to simulate a crash
    return {"step2": "done"}
# ... step_1, step_3 similar (simple print + state update)

graph = graph.compile(checkpointer=checkpointer)

# First run: interrupt (KeyboardInterrupt) during step_2 -> simulated crash
graph.invoke({"input": "start"}, config={"configurable": {"thread_id": "1"}})
# get_state shows: input='start', step1='done', but NO step2 -> crashed at node 2

# Resume from where it crashed by passing None as input (same thread_id)
graph.invoke(None, config={"configurable": {"thread_id": "1"}})
# Execution restarts at step_2 (NOT step_1) and completes step_3
```
Passing **`None`** as the input tells LangGraph to **resume the existing thread** from the last checkpoint rather than starting fresh.

### Time travel — replay from a checkpoint
```python
# 1) find the checkpoint where only `topic` exists (joke not yet generated)
for snapshot in workflow.get_state_history(config1):
    print(snapshot.config, snapshot.values)   # each has its own checkpoint_id

# 2) target that checkpoint by its checkpoint_id
config_tt = {"configurable": {"thread_id": "1",
                              "checkpoint_id": "<copied-checkpoint-id>"}}

# read the state AT that checkpoint
workflow.get_state(config_tt)     # -> {"topic": "pizza"}

# 3) replay forward from that checkpoint (None = resume, don't re-seed input)
workflow.invoke(None, config=config_tt)
# -> a NEW joke + explanation (LLM is probabilistic) -> creates a branch in history
```

### Updating state at a checkpoint (branching)
```python
# overwrite topic at the "pizza" checkpoint, creating a new branch
new_state = workflow.update_state(config_tt, {"topic": "samosa"})

# IMPORTANT: replay from the checkpoint_id returned by update_state (the NEW branch),
# NOT from the old pizza checkpoint
config_new = {"configurable": {"thread_id": "1",
                               "checkpoint_id": new_state["configurable"]["checkpoint_id"]}}
workflow.invoke(None, config=config_new)   # -> joke + explanation now about "samosa"
```

## 🪜 Step-by-Step Walkthrough
1. Build the joke→explanation workflow and compile it with an `InMemorySaver` checkpointer.
2. Invoke with `{"topic": "pizza"}` and `thread_id="1"`.
3. Use `get_state(config)` for the final state; `get_state_history(config)` for all 4 checkpoint snapshots.
4. Invoke again with `{"topic": "pasta"}` and `thread_id="2"`; confirm both threads are stored separately.
5. **Fault tolerance:** build a 3-step workflow with a 30s delay in step 2, invoke it, manually interrupt during step 2 (simulated crash), inspect state (step1 done, step2 missing), then `invoke(None, ...)` on the same thread to resume from step 2.
6. **Time travel:** locate the checkpoint holding only `topic`, copy its `checkpoint_id`, `get_state` at it, then `invoke(None, ...)` with that `checkpoint_id` to replay forward — a new branch appears in history.
7. **State update:** call `update_state(...)` at the pizza checkpoint to set `topic="samosa"`, then replay from the *new* branch's checkpoint_id to get a samosa joke.

## ⚠️ Gotchas & Tips
- **`InMemorySaver` is RAM-only** — great for demos, but everything is lost when the program stops. Use Postgres/Redis checkpointers in production.
- **`thread_id` is required** whenever persistence is on; it namespaces all stored state so you can retrieve a specific run.
- **Resume with `invoke(None, config=...)`** — passing `None` (instead of an initial state) means "continue this thread from its last checkpoint."
- **For fault tolerance / human-in-the-loop the mechanics are the same**: the difference is that a crash is caused by *external* factors, whereas human-in-the-loop is a *deliberate* interrupt.
- **The instructor's time-travel mistake:** after `update_state` created a new "samosa" branch, replaying from the *old* pizza checkpoint_id still produced a pizza joke. You must replay from the **checkpoint_id returned by `update_state`** (the new branch), not the original checkpoint.
- **Keyboard-interrupt demo** worked in Google Colab but not VS Code for the instructor — environment-dependent.
- Time travel results differ each replay because **LLMs are probabilistic**; branches accumulate in `get_state_history`.

## 📌 Key Takeaways
- **Persistence = save + restore workflow state over time**, and it stores **every intermediate state**, not just the final one.
- It is implemented with a **checkpointer**, which saves state at each **checkpoint** (one per **superstep**).
- **Threads (`thread_id`)** separate and identify individual executions/conversations in the store.
- Persistence powers **four features**: short-term memory, fault tolerance, human-in-the-loop, and time travel.
- **Fault tolerance:** resume a crashed workflow from the exact failing point via `invoke(None, ...)`.
- **Human-in-the-loop:** interrupt and later resume from the same point — persistence remembers where.
- **Time travel:** inspect/replay from any `checkpoint_id`; use `update_state` to branch into alternate outcomes (mainly a debugging tool).
- Use `get_state(config)` for the final state and `get_state_history(config)` for the full checkpoint timeline.
