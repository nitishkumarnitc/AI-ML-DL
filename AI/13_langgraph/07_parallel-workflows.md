# Video 07 — Parallel Workflows in LangGraph (Video 6)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `O6ryuSpqdOw`
> **Watch:** https://www.youtube.com/watch?v=O6ryuSpqdOw

## 🎯 Overview
Building on the previous (sequential) video, this one teaches **parallel workflows** — where, after a starting point, **multiple nodes execute simultaneously** and their outputs are later merged. Two examples are built: (1) a simple **non-LLM cricket batsman stats** calculator, which surfaces the critical *partial-state-update* rule, and (2) a more realistic **LLM-based UPSC essay evaluator** that combines three concepts at once: parallelization, **structured output**, and **reducer functions**.

## 🧠 Key Concepts

### What makes a workflow "parallel"
The flow starts at `START`, **fans out** into several independent nodes that run at the same time (none depends on another's output), then **fans in** to an aggregator/summary node before `END`. The batsman example computes strike rate, boundary percentage, and balls-per-boundary — three quantities that all read the same inputs but don't depend on each other, so they can be computed in parallel.

### The parallel-update problem → partial state updates (most important lesson)
If each parallel node **returns the entire state**, LangGraph raises an **`InvalidUpdateError`: "At key 'runs' can receive only one value per step."** Why? All three nodes return the whole state, so LangGraph thinks all three are trying to write the shared input keys (`runs`, `balls`, `fours`, `sixes`) simultaneously — a conflict it can't resolve (whose value wins?).

**Fix:** each node should return **only the key(s) it actually computes**, as a small dictionary — a **partial state update** — not the full state. This works because node functions accept a dict (the state) as input *and may return a dict* as output; you don't have to return the full state object.

> Recommendation: **use partial state updates everywhere** — in sequential *and* parallel workflows. It's the one approach that works in both cases. (Returning the whole state is only safe in sequential flows.)

### Reducers (why parallel score-merging needs them)
When multiple parallel nodes each write to the **same** state key (e.g. three LLMs each producing one score that must land in one `individual_scores` list), the default **overwrite** behavior would lose two of the three values. A **reducer** changes the update policy so values **merge/append** instead. You attach it in the type annotation:

```python
from typing import Annotated
import operator
# each parallel node contributes [score]; operator.add concatenates the lists
individual_scores: Annotated[list[int], operator.add]
```
`operator` is a Python module exposing functional equivalents of operators; `operator.add` behaves like `+` (which merges lists). Other reducers (e.g. `max`, `min`) are possible depending on need.

### Structured output (reliable, schema-shaped LLM responses)
When you need the LLM to return an exact shape (here: a text **feedback** *and* a numeric **score 0–10**), a plain prompt is unreliable — it might return "seven" instead of `7`, which you can't average. **Structured output** fixes this: define a **Pydantic schema**, bind it to the model with `with_structured_output(schema)`, and the model returns objects matching the schema every time (JSON-shaped). `gpt-4o-mini` supports structured output. Access fields with `.feedback` / `.score`. (This was taught in the LangChain playlist.)

## 🔧 Code / Implementation

### Example 1 — Batsman stats (non-LLM parallel workflow)
```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class BatsmanState(TypedDict):
    runs: int
    balls: int
    fours: int
    sixes: int
    sr: float                 # strike rate
    bpb: float                # balls per boundary
    boundary_percent: float
    summary: str

def calculate_sr(state: BatsmanState):
    sr = (state['runs'] / state['balls']) * 100     # NOTE: multiply by 100
    return {'sr': sr}                               # PARTIAL update

def calculate_bpb(state: BatsmanState):
    bpb = state['balls'] / (state['fours'] + state['sixes'])
    return {'bpb': bpb}

def calculate_boundary_percent(state: BatsmanState):
    boundary_percent = ((state['fours'] * 4 + state['sixes'] * 6) / state['runs']) * 100
    return {'boundary_percent': boundary_percent}

def summary(state: BatsmanState):
    summary = f"""Strike Rate: {state['sr']}
Balls per boundary: {state['bpb']}
Boundary percent: {state['boundary_percent']}"""
    return {'summary': summary}

graph = StateGraph(BatsmanState)
graph.add_node("calculate_sr", calculate_sr)
graph.add_node("calculate_bpb", calculate_bpb)
graph.add_node("calculate_boundary_percent", calculate_boundary_percent)
graph.add_node("summary", summary)

# fan-out: START -> three parallel nodes
graph.add_edge(START, "calculate_sr")
graph.add_edge(START, "calculate_bpb")
graph.add_edge(START, "calculate_boundary_percent")
# fan-in: three nodes -> summary
graph.add_edge("calculate_sr", "summary")
graph.add_edge("calculate_bpb", "summary")
graph.add_edge("calculate_boundary_percent", "summary")
graph.add_edge("summary", END)

workflow = graph.compile()

initial_state = {'runs': 100, 'balls': 50, 'fours': 6, 'sixes': 4}
final_state = workflow.invoke(initial_state)
```
Two bugs surfaced live: (a) originally each node returned the whole `state`, causing the `InvalidUpdateError` — fixed by returning partial dicts; (b) strike rate was accidentally *divided* by 100 — fixed to *multiply* by 100.

### Example 2 — UPSC essay evaluator (LLM parallel + structured output + reducer)
```python
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# structured-output model
model = ChatOpenAI(model='gpt-4o-mini')

class EvaluationSchema(BaseModel):
    feedback: str = Field(description="Detailed feedback for the essay")
    score: int = Field(description="Score out of 10", ge=0, le=10)

structured_model = model.with_structured_output(EvaluationSchema)

class UPSCState(TypedDict):
    essay: str
    language_feedback: str
    analysis_feedback: str
    clarity_feedback: str
    overall_feedback: str
    individual_scores: Annotated[list[int], operator.add]   # reducer merges parallel scores
    avg_score: float

def evaluate_language(state: UPSCState):
    prompt = f"Evaluate the language quality of the following essay and provide a feedback and assign a score out of 10.\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {'language_feedback': output.feedback, 'individual_scores': [output.score]}

def evaluate_analysis(state: UPSCState):
    prompt = f"Evaluate the depth of analysis of the following essay and provide a feedback and assign a score out of 10.\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {'analysis_feedback': output.feedback, 'individual_scores': [output.score]}

def evaluate_thought(state: UPSCState):
    prompt = f"Evaluate the clarity of thought of the following essay and provide a feedback and assign a score out of 10.\n{state['essay']}"
    output = structured_model.invoke(prompt)
    return {'clarity_feedback': output.feedback, 'individual_scores': [output.score]}

def final_evaluation(state: UPSCState):
    prompt = f"""Based on the following feedbacks create a summarized feedback:
Language feedback: {state['language_feedback']}
Depth of analysis feedback: {state['analysis_feedback']}
Clarity of thought feedback: {state['clarity_feedback']}"""
    overall_feedback = model.invoke(prompt).content          # normal model, not structured
    avg_score = sum(state['individual_scores']) / len(state['individual_scores'])
    return {'overall_feedback': overall_feedback, 'avg_score': avg_score}

graph = StateGraph(UPSCState)
graph.add_node("evaluate_language", evaluate_language)
graph.add_node("evaluate_analysis", evaluate_analysis)
graph.add_node("evaluate_thought", evaluate_thought)
graph.add_node("final_evaluation", final_evaluation)

graph.add_edge(START, "evaluate_language")
graph.add_edge(START, "evaluate_analysis")
graph.add_edge(START, "evaluate_thought")
graph.add_edge("evaluate_language", "final_evaluation")
graph.add_edge("evaluate_analysis", "final_evaluation")
graph.add_edge("evaluate_thought", "final_evaluation")
graph.add_edge("final_evaluation", END)

workflow = graph.compile()
final_state = workflow.invoke({'essay': essay_text})
```
The three evaluators run in parallel; each returns its feedback plus a **single-element score list**. The reducer (`operator.add`) concatenates those into `individual_scores = [7, 8, 8]`. `final_evaluation` summarizes all feedback (using the **normal** model so it doesn't emit an extra score) and computes the average. Tested with a good essay (high scores) and a deliberately bad one (low scores).

## 🪜 Step-by-Step Walkthrough
1. Define the **State** with input keys, output keys, and any key that receives parallel writes (give it a reducer).
2. Write each computation as a **node function returning a partial dict** (only its own key).
3. Fan out: `add_edge(START, node)` for every parallel node.
4. Fan in: `add_edge(node, aggregator)` for every parallel node.
5. `add_edge(aggregator, END)`; compile; visualize; invoke with an initial state.
6. For the LLM version: first build a **Pydantic schema** + `with_structured_output` model and test it standalone, then wire it into the parallel graph, adding the `operator.add` reducer for the score list.

## ⚠️ Gotchas & Tips
- **Never return the whole state from parallel nodes** — you'll hit `InvalidUpdateError` ("can receive only one value per step"). Return **partial dicts**.
- Prefer **partial state updates everywhere** (sequential and parallel) — it's the universally safe approach.
- Any state key written by **multiple parallel nodes** needs a **reducer** (`Annotated[..., operator.add]`), or values overwrite each other.
- Have each parallel node contribute its score as a **list** (`[score]`) so `operator.add` can concatenate them.
- Use **structured output** (Pydantic schema + `with_structured_output`) when you need machine-readable fields like a numeric score; `Field(description=...)` guides the LLM, and `ge`/`le` can constrain values.
- In the summarizing node, use the **plain** model (not the structured one) if you don't want it to fabricate an extra score.
- Watch simple math bugs (strike rate: `* 100`, not `/ 100`).

## 📌 Key Takeaways
- Parallel workflows **fan out** from a start node into simultaneous nodes, then **fan in** to an aggregator.
- The defining rule: parallel nodes must return **partial state updates**, not the full state, to avoid `InvalidUpdateError`.
- **Reducers** (`Annotated[list[int], operator.add]`) let multiple parallel nodes safely merge into one key.
- **Structured output** (Pydantic + `with_structured_output`, e.g. `gpt-4o-mini`) gives reliable, schema-shaped LLM results.
- Built a non-LLM **batsman stats** graph and an LLM **UPSC essay evaluator** combining parallelization + structured output + reducers.
- LangChain (models, schemas) and LangGraph (orchestration) continue to work hand in hand.
