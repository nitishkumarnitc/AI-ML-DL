# 06 · Organising Traces: Projects from Code, Run Names, Tags, Metadata

> ← [`05-your-first-trace.md`](05-your-first-trace.md) · **Next:** [`07-tracing-rag-what-auto-tracing-misses.md`](07-tracing-rag-what-auto-tracing-misses.md) →

---

One trace is easy to read. Ten thousand are not. This lesson is everything you do at write-time so that traces are findable at read-time — and the framing to hold onto is that **you are building your own future search index.** Every tag and metadata key you add is a query you will be able to run during an incident. Every one you skip is a query you won't.

---

## The example application

`02_sequential_chain.py` — a two-step app:

1. Generate a **detailed report** on a topic.
2. Generate a **five-point summary** of that report.

```
topic ──► prompt1 ──► model1 ──► parser ──► prompt2 ──► model2 ──► parser ──► summary
```

---

## Change 1 — set the project from code

The `.env` says `LANGSMITH_PROJECT=LangSmith Demo`. But this is a *different application* and should not share a project with lesson 05's app (lesson 04: one project per application).

You can rename in the UI, or — better, because it lives with the code — set it in the script:

```python
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGSMITH_PROJECT"] = "Sequential LLM App"
```

### The precedence rule

```
1. load_dotenv()  reads .env      → LANGSMITH_PROJECT = "LangSmith Demo"
2. os.environ[...] = ...          → LANGSMITH_PROJECT = "Sequential LLM App"   ← wins
```

**Code overrides `.env`**, because it runs afterwards and writes the same variable. Which means the assignment must come **after** `load_dotenv()` — reverse the two lines and `.env` clobbers your setting. This is a real and easy mistake.

> **⭐ The cleaner alternative** *(added)*: rather than mutating global state, scope it:
> ```python
> from langsmith.run_helpers import tracing_context
>
> with tracing_context(project_name="Sequential LLM App"):
>     chain.invoke({"topic": "Unemployment in India"})
> ```
> Use `os.environ` for a script that *is* one application. Use `tracing_context` when one process serves several logical applications — a FastAPI server with three endpoints, say — where a global would be wrong.

---

## Change 2 — pin models explicitly, per step

```python
from langchain_openai import ChatOpenAI

model1 = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)   # report generation
model2 = ChatOpenAI(model="gpt-4o",      temperature=0.5)   # summarisation
```

Two different models on purpose, and this is a pattern worth internalising: **match the model to the step, not to the application.** Report generation is the bulk-token step, so the cheap model does it; summarisation is short and quality-sensitive, so the strong model gets it. LangSmith then shows you per-run cost, which is exactly the data you need to decide whether that split was right.

---

## Change 3 — tags and metadata

Attached via a `config` dict on `.invoke()`:

```python
config = {
    "tags": ["llm_app", "report_generation", "summarization"],
    "metadata": {
        "model1":      "gpt-4o-mini",
        "model1_temp": 0.7,
        "model2":      "gpt-4o",
        "model2_temp": 0.5,
        "parser":      "StrOutputParser",
    },
}

result = chain.invoke({"topic": "Unemployment in India"}, config=config)
```

---

## Change 4 — name the run

Without this, LangSmith names the trace after the object it traced: `RunnableSequence`. Useless in a list.

```python
config = {
    "run_name": "sequential_chain",
    "tags": [...],
    "metadata": {...},
}
```

Now the trace is called `sequential_chain`.

---

## The full script

```python
# 02_sequential_chain.py
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGSMITH_PROJECT"] = "Sequential LLM App"   # AFTER load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt1 = PromptTemplate.from_template(
    "Generate a detailed report on the following topic.\n{topic}"
)
prompt2 = PromptTemplate.from_template(
    "Generate a five-point summary from the following text.\n{text}"
)

model1 = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
model2 = ChatOpenAI(model="gpt-4o",      temperature=0.5)
parser = StrOutputParser()

chain = prompt1 | model1 | parser | prompt2 | model2 | parser

config = {
    "run_name": "sequential_chain",
    "tags": ["llm_app", "report_generation", "summarization"],
    "metadata": {
        "model1": "gpt-4o-mini", "model1_temp": 0.7,
        "model2": "gpt-4o",      "model2_temp": 0.5,
        "parser": "StrOutputParser",
    },
}

print(chain.invoke({"topic": "Unemployment in India"}, config=config))
```

> **Note the chain shape.** `prompt1 | model1 | parser | prompt2 | model2 | parser` works because `parser` emits a string and `prompt2` has exactly one input variable (`text`), so LangChain feeds the string straight in. With two or more variables you would need a dict-producing step between them.

---

## What the UI shows

### At trace level

- Name: `sequential_chain`.
- **Tags:** `llm_app`, `report_generation`, `summarization`.
- **Metadata:** your five keys — *plus* system-added entries LangSmith contributes on its own (framework and dependency versions, and so on).

### At run level

Six runs, in order:

```
sequential_chain
├── PromptTemplate      in: {"topic": "Unemployment in India"}
│                       out: "Generate a detailed report on…"
├── ChatOpenAI          model: gpt-4o-mini    ← the long report
├── StrOutputParser
├── PromptTemplate      out: "Generate a five-point summary from…"
├── ChatOpenAI          model: gpt-4o         ← the summary
└── StrOutputParser
```

Two things to notice, both of them LangSmith adding value without being asked:

**1. Auto-generated positional tags.** Each run carries its own sequence tag — `seq:step:1` on the first prompt, `seq:step:2` on the first model, and so on. You did not write these. They let you reason about position in a long chain without counting rows.

**2. Per-run metadata is genuinely per-run.** Open the first `ChatOpenAI`: model `gpt-4o-mini`. Open the second: model `gpt-4o`. LangSmith records what each individual call actually used, independently of the trace-level metadata *you* declared.

> **And that is the point of the exercise.** Your trace-level metadata says `"model2": "gpt-4o"` — that is a *claim*. The run-level metadata says what was *actually invoked*. When those two disagree, you have found a bug: a stale config, an override you forgot, a fallback that fired. **Declared vs observed is a diffable pair.** That is worth more than either field alone.

---

## Which knob for which job

| Knob | Scope | Set via | Use for |
|---|---|---|---|
| **Project** | application | env or `os.environ` or `tracing_context` | separating apps |
| **`run_name`** | one trace or run | `config` | making trace lists scannable |
| **Tags** | trace + runs | `config` | coarse flat buckets you filter on |
| **Metadata** | trace + runs | `config` | structured values you *group and compare* by |

### A tagging convention that survives contact with production

*⭐ Added — the video's tags are illustrative; these are the ones that pay rent.*

```python
config = {
    "run_name": "support_answer",
    "tags": ["prod", "v3", "rag"],
    "metadata": {
        # --- who ---
        "user_id":          user.id,          # pseudonymous, never an email
        "session_id":       session.id,
        "tenant":           org.slug,
        # --- what ran ---
        "prompt_version":   "support_v3",
        "retriever_config": "hybrid_k8_rerank",
        "embedding_model":  "text-embedding-3-small",
        # --- where from ---
        "git_sha":          os.getenv("GIT_SHA", "dev"),
        "env":              os.getenv("APP_ENV", "local"),
    },
}
```

Each of those keys buys you one incident question you can actually answer:

| Question during an incident | Key that answers it |
|---|---|
| "Is this one customer or everyone?" | `tenant` |
| "Did this start with the deploy?" | `git_sha` |
| "Is the new prompt worse?" | `prompt_version` |
| "Is staging polluting prod metrics?" | `env` |
| "Show me this user's whole conversation" | `session_id` |
| "Did the retriever change help?" | `retriever_config` |

**The rule: if you would ever want to filter or group by it, it must be in metadata at write time.** You cannot add it retroactively to traces already written — a trace is immutable once recorded. Ten minutes of forethought here versus a blind incident later is not a close trade.

**And the counter-rule:** metadata is shipped to LangSmith and stored. Put identifiers in it, never contents. `user_id`, yes. Email address, name, account number, the customer's message text — no. See lesson 17.

---

## Recap

- **Project from code overrides `.env`** — and the assignment must come *after* `load_dotenv()`.
- `tracing_context(project_name=...)` is the scoped alternative to mutating `os.environ`.
- **Match models to steps**, not to applications; per-run cost then tells you if you chose well.
- `config` on `.invoke()` carries **`run_name`**, **`tags`** and **`metadata`**.
- LangSmith adds its own positional tags (`seq:step:N`) and per-run metadata for free.
- **Declared metadata vs observed run metadata is a diffable pair** — disagreement is a bug.
- Tags for coarse buckets, metadata for structured grouping. Design the metadata schema **before** you need it; traces are immutable.
- Identifiers in metadata, never content.

---

## Self-check

1. You put `os.environ["LANGSMITH_PROJECT"]` *above* `load_dotenv()`. Which project gets the traces, and why?
2. Your trace-level metadata says `gpt-4o` and the LLM run says `gpt-4o-mini`. What has probably happened, and why is this worth an alert?
3. `prompt_version`: tag or metadata? Defend it.
4. An incident starts. You want p95 latency for tenant `acme` on the current deploy only. Which two metadata keys must already have been written?

---

**Next:** [`07-tracing-rag-what-auto-tracing-misses.md`](07-tracing-rag-what-auto-tracing-misses.md) →
