# 04 · The Three Core Concepts: Project, Trace, Run

> ← [`03-setup-and-environment.md`](03-setup-and-environment.md) · **Next:** [`05-your-first-trace.md`](05-your-first-trace.md) →

---

Everything in the LangSmith UI is one of three things. Get these right and the interface stops being confusing; get them wrong and you will spend the rest of the tutorial mildly lost.

---

## The running example

The simplest possible LLM application:

```
user question ──► PROMPT ──► LLM ──► PARSER ──► answer shown to user
```

Three components in sequence. In LangChain: `prompt | model | parser`.

---

## Project = the application

You built an application. In LangSmith that application is a **project**.

- Set by `LANGSMITH_PROJECT` (env) or `os.environ["LANGSMITH_PROJECT"]` (code).
- Auto-created on first trace.
- Found in the UI under **Tracing Projects**.

**One project per application.** Not per team, not per environment-and-team-and-quarter. The cover-letter tool is one project; the research agent is another. If you put both in one project, every list, chart and average in the UI mixes two unrelated latency distributions and becomes meaningless.

> The video demonstrates this discipline in practice: the simple LLM call goes to `LangSmith Demo`, the sequential chain to `Sequential LLM App`, the RAG app to `RAG Chatbot`, the agent and the graph to their own projects. Follow it.

---

## Trace = one end-to-end execution

You built the app; now you run it. A user arrives, asks a question, the whole pipeline fires, an answer comes out. **That single execution is one trace.**

```
Ask "What is the capital of India?"  → pipeline runs end-to-end → TRACE #1
Ask "What is the capital of Peru?"   → pipeline runs end-to-end → TRACE #2
```

Ten users today, ten traces. A thousand requests, a thousand traces.

A trace carries: input, output, total latency, total tokens, total cost, error status, tags, metadata, and any feedback.

> **The mental model that keeps it straight:** a trace is *one request's worth* of everything that happened.

---

## Run = one component's execution inside a trace

Each trace decomposes into the components that executed. Each of those executions — each thing that took an input and produced an output — is a **run**.

Our three-component app produces **three runs per trace**:

| Run | Input | Output |
|---|---|---|
| `PromptTemplate` | `{"question": "What is the capital of India?"}` | the filled-in prompt string |
| `ChatOpenAI` | the message list | the completion |
| `StrOutputParser` | the completion object | `"New Delhi"` |

Each run carries its own input, output, latency, tokens, cost, tags and metadata.

---

## The hierarchy

```
Tracing Projects
└── PROJECT              "LangSmith Demo"          — the application
    ├── TRACE #1         "capital of India"        — one execution
    │   ├── RUN  PromptTemplate
    │   ├── RUN  ChatOpenAI
    │   └── RUN  StrOutputParser
    ├── TRACE #2         "capital of Peru"
    │   ├── RUN  PromptTemplate
    │   ├── RUN  ChatOpenAI
    │   └── RUN  StrOutputParser
    └── TRACE #3 …
```

Navigation follows it exactly: **Tracing Projects → pick a project → pick a trace → expand runs.**

---

## Three summarising sentences

1. LangSmith calls your whole LLM application a **project**.
2. Every time you execute that project, that execution is a **trace**.
3. Within a trace, each component's execution is a **run**.

---

## ⭐ Beyond the video — the part the simplification hides

*Added. The video presents runs as a flat list because at this stage that is all you see. But the real model is a tree, and knowing that explains several things you will hit in lessons 07–12.*

### Runs are a tree; a trace is its root

Internally there is only **one** entity type: the run. A run may have children. A **trace is not a separate thing — it is the root run**, plus everything beneath it.

```
run  (root)  ← this is what the UI calls "the trace"
├── run
│   ├── run
│   └── run
└── run
```

Every run carries:

| Field | Meaning |
|---|---|
| `id` | this run |
| `trace_id` | the root's id — **shared by every run in the trace** |
| `parent_run_id` | the run directly above; `None` for the root |
| `run_type` | `chain` · `llm` · `tool` · `retriever` · `prompt` · `parser` · `embedding` |
| `dotted_order` | encodes position and start time, which is how the UI draws the waterfall in the right order |

Four things this immediately explains:

1. **Nesting is real.** In lesson 07 the RAG app shows a `RunnableSequence` containing a `RunnableParallel` containing two branches. That is depth 3, not a flat list.
2. **`run_type` drives the UI.** An `llm` run gets the token/cost panel; a `retriever` run gets the document viewer. When you write custom instrumentation (lesson 08), setting `run_type` correctly is what earns you the right rendering.
3. **The two-sibling-traces bug becomes legible.** The video's `setup_pipeline` and `pdf_rag_query` end up as two *separate traces* because neither was the other's parent — two roots, two `trace_id`s. Fixing it means creating one parent. That is lesson 09.
4. **Feedback and datasets attach by `run_id`.** Lessons 14 and 16 both need a run id in hand; now you know where it comes from.

### Getting at the current run from your own code

```python
from langsmith.run_helpers import get_current_run_tree

def my_step(x):
    rt = get_current_run_tree()
    if rt:                                  # None when tracing is disabled
        print("run:", rt.id, "trace:", rt.trace_id)
    return x
```

Returning `None` when tracing is off is deliberate — your code must not break because someone disabled observability. **Always guard the access.** You will use this in lesson 16 to attach user feedback to the exact run that produced an answer.

---

## Recap

- **Project** = the application. One per app, strictly.
- **Trace** = one end-to-end execution. One request's worth of everything.
- **Run** = one component's execution inside a trace.
- The UI mirrors the hierarchy: Projects → Traces → Runs.
- Underneath, there is only the **run**; runs form a **tree**, and a trace is its **root**. `trace_id` is shared by the whole tree; `parent_run_id` links a child upward.
- `run_type` determines how the UI renders a run — get it right in custom instrumentation.
- `get_current_run_tree()` gets you the current run's ids; it returns `None` when tracing is off, so guard it.

---

## Self-check

1. Your app has a prompt, two LLM calls and a parser. You run it 50 times. How many projects, traces and runs?
2. Why does one project per application matter for the *charts*, not just for tidiness?
3. What distinguishes a trace from a run at the data-model level?
4. Two separate traces appear where you expected one nested trace. In terms of `parent_run_id` and `trace_id`, what has gone wrong?

---

**Next:** [`05-your-first-trace.md`](05-your-first-trace.md) →
