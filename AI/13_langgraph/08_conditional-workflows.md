# Video 08 — Conditional Workflows in LangGraph (Video 7)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `I-dvZqTz-Wc`
> **Watch:** https://www.youtube.com/watch?v=I-dvZqTz-Wc

## 🎯 Overview
Having covered sequential and parallel workflows, this video introduces the **third type: conditional workflows** — branching where, based on a condition, **exactly one** of several possible branches executes (LangGraph's equivalent of `if/else`). The instructor stresses this is *extremely* important: almost every complex workflow you build later will need conditional branching. Two examples are built: a **non-LLM quadratic-equation solver** and an **LLM-based customer-support review responder**.

## 🧠 Key Concepts

### Conditional vs. parallel workflows
Conditional workflows *look* like parallel ones (both have branches), but the behavior differs fundamentally:
- **Parallel:** you enter **all** branches at once and execute them simultaneously.
- **Conditional:** you enter **only one** branch, chosen **by a condition**. If Task 1 can lead to Task 2 or Task 3, you go to one *or* the other — never both — then continue to Task 4. This is exactly `if/else`, and there's no limit on the number of branches.

### The core mechanism: a routing function + `add_conditional_edges`
To build a conditional branch you need two pieces:
1. A **condition/routing function** — a plain Python function (not a node) that receives the state, checks a condition, and **returns the *name* of the next node** to run.
2. **`graph.add_conditional_edges(source_node, routing_function)`** — instead of `add_edge`, this tells LangGraph: after `source_node`, call the routing function; whichever node name it returns becomes the edge that fires.

In the graph visualization, conditional edges appear as **dotted arrows**, signalling that only one of them executes per run.

> There is also a second way to create conditional edges using a **`Command`** object (used for *dynamic* workflows) — covered in a later video. This video teaches the `add_conditional_edges` approach.

### Structured output for classification branches (LLM example)
For LLM-driven conditions (e.g. "is this review positive or negative?"), you need a reliable, single-word answer. Use **structured output**: define a **Pydantic schema** (with a `Literal` field constraining allowed values) and bind it via `with_structured_output`. This guarantees clean, JSON-shaped results you can branch on. You can maintain **multiple** structured models — one per schema (sentiment, diagnosis).

## 🔧 Code / Implementation

### Example 1 — Quadratic equation solver (non-LLM conditional)
For `ax² + bx + c`, compute the **discriminant** `d = b² − 4ac`, then branch:
- `d > 0` → two distinct real roots `(−b ± √d) / 2a`
- `d = 0` → one repeated root `−b / 2a`
- `d < 0` → no real roots

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class QuadState(TypedDict):
    a: int
    b: int
    c: int
    equation: str
    discriminant: float
    result: str

def show_equation(state: QuadState):
    equation = f"{state['a']}x2 + {state['b']}x + {state['c']}"
    return {'equation': equation}

def calculate_discriminant(state: QuadState):
    discriminant = state['b']**2 - (4 * state['a'] * state['c'])
    return {'discriminant': discriminant}

def real_roots(state: QuadState):
    root1 = (-state['b'] + state['discriminant']**0.5) / (2 * state['a'])
    root2 = (-state['b'] - state['discriminant']**0.5) / (2 * state['a'])
    result = f"The roots are {root1} and {root2}"
    return {'result': result}

def repeated_roots(state: QuadState):
    root = (-state['b']) / (2 * state['a'])
    result = f"Only repeating root is {root}"
    return {'result': result}

def no_real_roots(state: QuadState):
    result = "No real roots"
    return {'result': result}

# routing function -> returns the NAME of the next node
def check_condition(state: QuadState) -> Literal["real_roots", "repeated_roots", "no_real_roots"]:
    if state['discriminant'] > 0:
        return "real_roots"
    elif state['discriminant'] == 0:
        return "repeated_roots"
    else:
        return "no_real_roots"

graph = StateGraph(QuadState)
graph.add_node("show_equation", show_equation)
graph.add_node("calculate_discriminant", calculate_discriminant)
graph.add_node("real_roots", real_roots)
graph.add_node("repeated_roots", repeated_roots)
graph.add_node("no_real_roots", no_real_roots)

graph.add_edge(START, "show_equation")
graph.add_edge("show_equation", "calculate_discriminant")
# conditional branch:
graph.add_conditional_edges("calculate_discriminant", check_condition)
graph.add_edge("real_roots", END)
graph.add_edge("repeated_roots", END)
graph.add_edge("no_real_roots", END)

workflow = graph.compile()

# examples: (a=4, b=-5, c=-4) -> two real roots; (2,4,4)|neg d -> no real roots; (4,4,... ) d=0 -> one repeated root
final_state = workflow.invoke({'a': 4, 'b': -5, 'c': -4})
```

### Example 2 — Customer-support review responder (LLM conditional)
Flow: get a review → detect **sentiment** (positive/negative) → **if positive**, write a warm thank-you reply; **if negative**, run a **diagnosis** (issue type / tone / urgency) then write an empathetic resolution.

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
model = ChatOpenAI(model='gpt-4o-mini')

# --- schemas + structured models ---
class SentimentSchema(BaseModel):
    sentiment: Literal["positive", "negative"] = Field(description="Sentiment of the review")

class DiagnosisSchema(BaseModel):
    issue_type: Literal["UX", "Performance", "Bug", "Support", "Other"] = Field(
        description="The category of issue mentioned in the review")
    tone: Literal["angry", "frustrated", "disappointed", "calm"] = Field(
        description="The emotional tone expressed by the user")
    urgency: Literal["low", "medium", "high"] = Field(
        description="How urgent or critical the issue appears to be")

structured_model  = model.with_structured_output(SentimentSchema)
structured_model2 = model.with_structured_output(DiagnosisSchema)

# --- state ---
class ReviewState(TypedDict):
    review: str
    sentiment: Literal["positive", "negative"]
    diagnosis: dict
    response: str

def find_sentiment(state: ReviewState):
    prompt = f"For the following review find out the sentiment\n{state['review']}"
    sentiment = structured_model.invoke(prompt).sentiment
    return {'sentiment': sentiment}

# routing function
def check_sentiment(state: ReviewState) -> Literal["positive_response", "run_diagnosis"]:
    if state['sentiment'] == "positive":
        return "positive_response"
    else:
        return "run_diagnosis"

def positive_response(state: ReviewState):
    prompt = f"""Write a warm thank you message in response to this review:\n{state['review']}
Also kindly ask the user to leave feedback on our website."""
    response = model.invoke(prompt).content
    return {'response': response}

def run_diagnosis(state: ReviewState):
    prompt = f"Diagnose this negative review:\n{state['review']}\nReturn issue_type, tone and urgency."
    response = structured_model2.invoke(prompt)
    return {'diagnosis': response.model_dump()}   # pydantic -> dict

def negative_response(state: ReviewState):
    diagnosis = state['diagnosis']
    prompt = f"""You are a support assistant.
The user had a '{diagnosis['issue_type']}' issue, sounded '{diagnosis['tone']}',
and marked urgency as '{diagnosis['urgency']}'.
Write an empathetic, helpful resolution message."""
    response = model.invoke(prompt).content
    return {'response': response}

graph = StateGraph(ReviewState)
graph.add_node("find_sentiment", find_sentiment)
graph.add_node("positive_response", positive_response)
graph.add_node("run_diagnosis", run_diagnosis)
graph.add_node("negative_response", negative_response)

graph.add_edge(START, "find_sentiment")
graph.add_conditional_edges("find_sentiment", check_sentiment)
graph.add_edge("positive_response", END)
graph.add_edge("run_diagnosis", "negative_response")
graph.add_edge("negative_response", END)

workflow = graph.compile()
final_state = workflow.invoke({'review': 'I have been using this app for a month, the UI is incredibly clean...'})
```
Note `diagnosis` is stored as a **dict** via `response.model_dump()` (Pydantic → dictionary), so `negative_response` can read `issue_type`, `tone`, and `urgency` from it. Tested with a positive review (→ warm thank-you) and a negative login-freeze/bug review (→ diagnosis: issue=Bug, tone=frustrated, urgency=high → tailored resolution).

## 🪜 Step-by-Step Walkthrough
1. Define the **State** (`TypedDict`) with inputs, any intermediate values, and the final result.
2. Build the linear part first (`START → node → node`) and verify it runs.
3. Add the **branch target nodes** (one per possible outcome) and their functions.
4. Write a **routing function** that inspects state and **returns the name** of the next node.
5. Replace the usual `add_edge` at the branch point with **`add_conditional_edges(source, routing_function)`**.
6. Connect each branch node onward (to `END` or the next step).
7. Compile and visualize — conditional edges render as **dotted arrows** — then invoke with different inputs to exercise each branch.

## ⚠️ Gotchas & Tips
- A **conditional workflow enters only one branch**; don't confuse it with parallel (which enters all).
- The **routing function is not a node** — it returns a **node name (string)**, and its return values should match your node names exactly (typing it with `Literal[...]` helps).
- Use **`add_conditional_edges`**, not `add_edge`, at the decision point.
- For LLM classification, use **structured output** with `Literal` fields so the branch key is clean and reliable.
- Convert a Pydantic result to a plain **dict** with `.model_dump()` before storing it in a dict-typed state key.
- Keep separate **structured models** for separate schemas (one for sentiment, one for diagnosis).
- Minor `f`-string display bugs (e.g. sign formatting in the printed equation) don't affect the logic — the goal is demonstrating the branching pattern.
- A second technique, the **`Command`** object, also creates conditional edges and is used for **dynamic** workflows (covered later).

## 📌 Key Takeaways
- Conditional workflows are LangGraph's **`if/else`**: branches exist, but only **one** runs per execution based on a condition.
- Implement them with a **routing function** (returns the next node's name) + **`graph.add_conditional_edges(source, routing_fn)`**.
- Conditional edges show up as **dotted arrows** in the graph visualization.
- **Quadratic solver** (non-LLM): discriminant decides real / repeated / no real roots.
- **Review responder** (LLM): sentiment decides positive-reply vs. diagnose-then-negative-reply.
- Use **structured output + `Literal`** schemas for reliable LLM-based conditions; convert Pydantic → dict with `.model_dump()`.
- Conditional branching is one of the most-used patterns in real, complex agentic workflows.
