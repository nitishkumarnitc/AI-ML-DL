# 12 · Tracing LangGraph

> ← [`11-tracing-react-agents.md`](11-tracing-react-agents.md) · **Next:** [`13-monitoring-and-alerting.md`](13-monitoring-and-alerting.md) →

---

## Why this is the tightest integration in the tool

LangGraph models an LLM application as a **graph**: state flows through nodes, each node performs a task, edges decide what runs next. That buys you conditional branching, parallelism, loops, subgraphs and persistence — and it costs you legibility. A moderately complex graph is genuinely hard to reason about, and debugging one by reading code is miserable.

LangSmith and LangGraph are built by the same team, and the coupling is deliberate. The integration reduces to **two rules**:

> 1. **One graph execution = one trace.**
> 2. **Each node = one run inside that trace.**

That's it. It also captures conditional branches, parallel paths and subgraphs automatically — so however complex the graph, the trace mirrors it.

---

## The example: an essay evaluator

From the LangGraph playlist ([`AI/13_langgraph/`](../13_langgraph/)): submit an essay, get it judged on three axes, then get an overall verdict.

```
                          ┌──────────────────────┐
                    ┌────►│  evaluate_language   │──┐
                    │     └──────────────────────┘  │
   START ──► essay ─┼────►│  evaluate_analysis   │──┼──► final_evaluation ──► END
                    │     └──────────────────────┘  │      · overall feedback
                    └────►│  evaluate_clarity    │──┘      · average score
                          └──────────────────────┘
```

Three evaluators run **in parallel** on the same state; each emits `{feedback, score}`; the final node consumes all three and produces an overall feedback plus the average.

### Structured output

Each evaluator needs a *typed* result, not prose:

```python
from pydantic import BaseModel, Field

class EvaluationSchema(BaseModel):
    feedback: str = Field(description="Detailed feedback on this dimension")
    score:    int = Field(description="Score out of 10", ge=0, le=10)

model            = ChatOpenAI(model="gpt-4o-mini")
structured_model = model.with_structured_output(EvaluationSchema)
```

### A node

```python
from langsmith import traceable

@traceable(name="evaluate_analysis")
def evaluate_analysis(state: EssayState) -> dict:
    prompt = (
        "Evaluate the depth of analysis in the following essay. "
        "Give detailed feedback and a score out of 10.\n\n" + state["essay"]
    )
    out = structured_model.invoke(prompt)
    return {"analysis_feedback": out.feedback, "individual_scores": [out.score]}
```

Note the `@traceable`. LangGraph traces the **node** automatically; the decorator additionally traces the **function**, so you see both levels. The author is explicit that this is **optional** — remove the decorators and the graph still traces fine. He keeps them because he wants function-level visibility.

### Invoking with a run name

```python
result = graph.invoke(
    {"essay": essay_text},
    config={
        "run_name": "Evaluate UPSC essay",
        "tags": ["langgraph", "essay_eval"],
        "metadata": {"model": "gpt-4o-mini", "dimensions": 3},
    },
)
```

Project: `Langgraph Essay Checker`.

### Output

```
Language feedback : …
Analysis feedback : …
Clarity feedback  : …
Overall feedback  : …
Individual scores : [4, 4, 4]
Average score     : 4
```

Nothing in that console output tells you *how* it happened. That is the point.

---

## The trace

### Collapsed

```
Evaluate UPSC essay                          ← one trace = one graph execution
├── evaluate_language      ─┐
├── evaluate_analysis       ├─ parallel      3.5 s (evaluate_analysis)
├── evaluate_clarity       ─┘
└── final_evaluation
```

Rule 2 in action: four nodes, four runs. And the **parallelism is visible** — the three evaluators overlap in the waterfall rather than stacking, which is how you confirm your fan-out is actually concurrent. (A fan-out that silently serialised is a real and common bug; the waterfall is where you catch it.)

### Expanded — one evaluator node

```
evaluate_analysis                                    3.5 s
└── evaluate_analysis  (the @traceable function)
    │   in:  the full graph STATE
    │   out: {"analysis_feedback": …, "individual_scores": [4]}
    └── RunnableSequence                    ← because of with_structured_output
        ├── ChatOpenAI          in: prompt          out: raw completion
        └── RunnableLambda      in: raw completion  out: EvaluationSchema
```

Two things to read here.

**1. A node's input is the whole graph state.** Not just what it needs — the entire state dict. That's the LangGraph contract, and seeing it in the trace is how you catch a node reading a key that isn't populated yet, which is the classic LangGraph bug.

**2. `with_structured_output` is a two-step pipeline, not a model feature.** It expands into:

```
ChatOpenAI  →  RunnableLambda(parse into the schema)
```

The `RunnableLambda` is the coercion step that turns the model's raw output into your Pydantic object.

> **This is the practically useful observation of the lesson.** Compare `final_evaluation`, which uses a **plain** model with no structured output:
>
> ```
> final_evaluation
> └── final_evaluation  (function)
>     └── ChatOpenAI              ← that's all. No RunnableSequence, no RunnableLambda.
> ```
>
> So **the trace shape tells you which kind of model call you made.** `RunnableSequence` + `RunnableLambda` under a node ⇒ structured output. Bare `ChatOpenAI` ⇒ free-form. That is genuinely useful when you're staring at someone else's graph, and it's the level where structured-output failures actually live: if the model returns something the schema can't accept, **the `RunnableLambda` is the run that fails** — not the LLM. Knowing which run to open saves the whole investigation.

### The final node

```
final_evaluation
    in:  state — now containing all three feedbacks and all three scores
    out: {"overall_feedback": …, "average_score": 4}
```

The convergence is explicit in the state: the three parallel branches wrote into it, and the final node reads it whole.

---

## Per-node numbers

Because every node is a run, you get **per-node latency and per-node cost**:

| Node | Latency | Use |
|---|---|---|
| `evaluate_analysis` | 3.5 s | Which axis is slowest? |
| `evaluate_language` | … | Can the three be trimmed? |
| `evaluate_clarity` | … | |
| `final_evaluation` | … | Is synthesis or evaluation dominant? |

In a fan-out, **total latency is the slowest branch, not the sum** — so per-node numbers tell you which single branch to optimise. Optimising any other branch changes nothing at all. That's a fact you can only act on with per-node data.

---

## The two rules again

| Rule | Consequence |
|---|---|
| Graph execution = trace | However complex, one run of the graph is one readable unit |
| Node = run | Per-node input/output/latency/cost/tags/metadata, for free |

Plus, automatically: conditional branches (you see which edge was taken), parallel paths (visible overlap), subgraphs (nested runs), and loops (repeated node runs).

> **The author's practice:** he always integrates LangSmith when building complex graphs or agentic applications — and explicitly says it is **not only for debugging** but for **understanding how the graph works**. Reading a graph trace is the fastest way to build an accurate mental model of your own control flow.

---

## ⭐ Beyond the video — three graph-specific reading skills

*Added.*

### 1. Which edge was taken

Conditional edges are the hardest thing to reason about statically, and the easiest thing to read in a trace:

```
graph
├── classify_intent          out: {"intent": "refund"}
├── handle_refund            ← this ran
│                            (handle_question, handle_escalation did not)
└── respond
```

The runs that **exist** tell you the path; the runs that are **absent** tell you the branches not taken. When a user complains "it gave me the wrong kind of answer", `classify_intent`'s output is the first and usually last thing you need to look at.

### 2. Loops and recursion limits

A cyclic graph produces **repeated runs of the same node**:

```
generate → critique → generate → critique → generate → END
```

Three `generate` runs is your signal. Two things to configure:

```python
graph.invoke(state, config={"recursion_limit": 10})
```

`recursion_limit` is LangGraph's containment for exactly Story B — same role `max_iterations` plays for agents (lesson 11). And the monitoring rule transfers: **alert on node-execution count per trace.** If `generate` used to run twice on average and now runs five times, behaviour changed.

### 3. Thread / conversation grouping

Persistent graphs use a `thread_id` for checkpointing. Put it in metadata so you can reconstruct a whole conversation from traces:

```python
config = {
    "configurable": {"thread_id": thread_id},     # LangGraph checkpointing
    "metadata": {"thread_id": thread_id},         # LangSmith filtering
    "run_name": "chat_turn",
}
```

The duplication is deliberate and worth it: LangGraph uses `configurable.thread_id` for state, LangSmith filters on `metadata`. Without the second, each turn is an orphan trace and "show me this user's whole broken conversation" is unanswerable — which is exactly the question you get asked when a multi-turn bot goes wrong.

---

## Recap

- **Two rules:** graph execution = one **trace**; each node = one **run**.
- Branching, parallelism, subgraphs and loops are captured automatically.
- A node's input is the **whole graph state** — how you catch reads of unpopulated keys.
- **`with_structured_output` expands to `ChatOpenAI` → `RunnableLambda`.** The trace shape identifies structured vs free-form calls, and schema-coercion failures live in the **lambda**, not the LLM.
- Per-node latency and cost; in a fan-out, **total = slowest branch**, so per-node data tells you the only branch worth optimising.
- Read conditional routing from **which runs exist**; read loops from **repeated node runs**.
- Set `recursion_limit`; alert on node-execution count.
- Record `thread_id` in **metadata**, not only in `configurable`, or multi-turn conversations are unreconstructable.

---

## Self-check

1. A graph with 6 nodes, of which a conditional edge means only 4 execute. How many traces and runs for one invocation?
2. You open a node and see `RunnableSequence → ChatOpenAI + RunnableLambda`. What do you now know about the code?
3. Your structured-output node returns a validation error. Which run do you open first, and why not the LLM?
4. Three parallel branches take 1 s, 2 s and 7 s. You have time to optimise one. Which, and what's the best case?

---

**Next:** [`13-monitoring-and-alerting.md`](13-monitoring-and-alerting.md) →
