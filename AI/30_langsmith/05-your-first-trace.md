# 05 · Your First Trace: A Simple LLM Call

> ← [`04-project-trace-run.md`](04-project-trace-run.md) · **Next:** [`06-tags-metadata-and-run-names.md`](06-tags-metadata-and-run-names.md) →

---

## The code

`01_simple_llm_call.py` — an ordinary LangChain script with **not one line of LangSmith code in it**.

```python
# 01_simple_llm_call.py
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = PromptTemplate.from_template("Answer the following question.\n{question}")
model  = ChatOpenAI()
parser = StrOutputParser()

chain = prompt | model | parser

answer = chain.invoke({"question": "What is the capital of Peru?"})
print(answer)
```

Run it:

```bash
python 01_simple_llm_call.py
# The capital of Peru is Lima.
```

---

## The point of this lesson

Look again at the file. There is no `import langsmith`. No handler, no wrapper, no decorator, no callback registration. The script is exactly what you would have written before you had ever heard of LangSmith.

**And it is fully traced.** Because `.env` set `LANGSMITH_TRACING=true`, an endpoint, an API key and a project name, LangChain's callback system shipped the whole execution to LangSmith while your script ran.

> This is the adoption story in one paragraph: **instrumenting an existing LangChain application is a configuration change, not a refactor.** If your team has fifteen LangChain scripts, all fifteen become observable by editing one `.env`.

---

## Reading the UI

### Level 1 — Tracing Projects

Two projects are listed:

| Project | Where it came from |
|---|---|
| `default` | Auto-created; the fallback when no project is named |
| `LangSmith Demo` | Your `LANGSMITH_PROJECT` value |

### Level 2 — the trace list

Open `LangSmith Demo`. One trace, because you ran the script once. The columns are the trace-level summary from lesson 02:

| Column | This run |
|---|---|
| Start time | when it ran |
| Input | `What is the capital of Peru?` |
| Output | `The capital of Peru is Lima.` |
| Error | none |
| Latency | total wall-clock, end to end |
| Tokens | total in + out |
| Cost | derived from tokens × model price |

### Level 3 — the runs

Click the trace. Three runs, matching the three components exactly:

```
RunnableSequence                          ← the trace root
├── PromptTemplate
├── ChatOpenAI            1.11 s
└── StrOutputParser
```

Click each one:

| Run | Input | Output |
|---|---|---|
| `PromptTemplate` | `{"question": "What is the capital of Peru?"}` | the filled template text |
| `ChatOpenAI` | a `HumanMessage` | an `AIMessage` |
| `StrOutputParser` | the `AIMessage` object | the plain string |

And per-run latency. In the video's run, `ChatOpenAI` took **1.11 s** — while the template fill and the string extraction were negligible.

> **Read that distribution, because it generalises.** In almost every LLM application, essentially all latency is in the LLM calls and the I/O (retrieval, tool calls, network). Your Python is free. This is why optimising an LLM app looks nothing like optimising a normal service: you are not profiling your code, you are counting and shrinking model calls.

### Run it again

Change the question to `India`, save, run:

```python
answer = chain.invoke({"question": "What is the capital of India?"})
```

Refresh the project. **Two traces** now — one per execution, exactly as lesson 04 said. Open the newest and you get its own three runs with its own numbers.

---

## What you can already diagnose

With nothing but this, Story A from lesson 01 is solved. Component-level latency is right there. A five-stage workflow where stage 2 went from 6 s to 8 min shows the anomaly in the waterfall on first glance.

What you cannot do yet: organise many apps cleanly (lesson 06), see anything that isn't a LangChain runnable (lessons 07–08), or aggregate across traces (lesson 13).

---

## ⭐ Beyond the video — three things worth doing on day one

*Added.*

### 1. Pin the model explicitly

```python
model = ChatOpenAI()                                    # ← what the video runs
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # ← what you should write
```

`ChatOpenAI()` uses a provider default that **can change under you**. Six months later your traces show a model you never chose, your costs move, and your outputs drift — for reasons entirely outside your repo. Since LangSmith records the model as metadata, pinning it also makes your traces self-documenting: `metadata.ls_model_name` tells you what actually ran, which is exactly what you want when comparing a trace from today against one from March.

### 2. Give the trace a name

`RunnableSequence` is what LangSmith auto-names an anonymous chain, and a project full of identically-named traces is hard to scan.

```python
answer = chain.invoke(
    {"question": "What is the capital of Peru?"},
    config={"run_name": "capital_lookup"},
)
```

Full mechanics in lesson 06.

### 3. Know how to turn it off per-call

Sometimes you want a call *not* traced — a health check, a warm-up ping, a loop over 10,000 rows that would flood the project.

```python
from langsmith.run_helpers import tracing_context

with tracing_context(enabled=False):
    chain.invoke({"question": "warm-up"})       # not traced
```

`tracing_context` is a context manager and also takes `project_name=`, `tags=` and `metadata=`, which makes it the cleanest way to route a block of work to a different project without touching the environment. Sampling for high-volume production is lesson 17.

---

## Exercise

1. Add a second LLM call to the chain and predict the number of runs before you look. Verify.
2. Break the API key deliberately (`OPENAI_API_KEY=sk-wrong`) and run. Does a trace appear? What does the failing run show? Compare with the "no trace at all" symptom from a bad *LangSmith* key — these two failures look nothing alike, and telling them apart quickly is a real skill.
3. Wrap the invoke in `tracing_context(enabled=False)` and confirm no trace lands.
4. Run the same question twice with `temperature=0.9`. Compare the two traces' outputs — you have just observed lesson 01's non-determinism in your own data.

---

## Recap

- Tracing needs **zero application code**. Env vars only. This is the whole adoption story.
- UI navigation: **Tracing Projects → project → trace → runs**.
- A `prompt | model | parser` chain gives **three runs** per trace, each with input, output and latency.
- **Almost all latency is in LLM calls and I/O.** Your Python is free.
- One execution = one trace; run twice, get two traces.
- Day-one habits: pin the model, name the run, know how to disable tracing per block.

---

**Next:** [`06-tags-metadata-and-run-names.md`](06-tags-metadata-and-run-names.md) →
