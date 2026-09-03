# 02 · Core Concepts and the Data Model

> ← [`01-why-langfuse-and-how-it-differs.md`](01-why-langfuse-and-how-it-differs.md) · **Next:** [`03-setup-and-keys.md`](03-setup-and-keys.md) →

---

If you have read [`../30_langsmith/04-project-trace-run.md`](../30_langsmith/04-project-trace-run.md) you already own most of this. The concepts are the same; the vocabulary differs in two places that matter, and LangFuse has two first-class entities LangSmith handles by convention.

---

## The vocabulary map

Read this table first and the rest of the folder reads easily:

| LangSmith | LangFuse | Note |
|---|---|---|
| **Project** | **Project** (inside an *Organization*) | Same idea — one per application |
| **Trace** | **Trace** | One end-to-end execution |
| **Run** | **Observation** | ⚠️ **The main rename.** A unit of work inside a trace |
| `run_type="chain"` | Observation of type **`span`** | Generic work |
| `run_type="llm"` | Observation of type **`generation`** | A model call — gets token/cost treatment |
| — | Observation of type **`event`** | A point in time, no duration |
| Feedback | **Score** | Richer: four data types, attachable to trace/observation/session |
| Metadata convention | **`session_id`** | ⭐ First-class in LangFuse |
| Metadata convention | **`user_id`** | ⭐ First-class in LangFuse |
| Tags | **Tags** | Same |
| Dataset | **Dataset** | Same |
| Experiment | **Dataset run** / experiment | Same |

> **The one substitution to internalise: LangSmith "run" = LangFuse "observation".** Everything else is close enough to guess. And where LangSmith has one `run` with a `run_type` field, LangFuse names the three shapes — `span`, `generation`, `event` — as observation *types*, which in v4 you select with `as_type=`.

---

## 1. Trace

One end-to-end execution of your application. One user request's worth of everything.

Carries: input, output, timing, metadata, tags, and — distinctively — a `user_id` and `session_id`.

---

## 2. Observation — the three types

An observation is a unit of work inside a trace. Observations **nest**, forming a tree whose root is the trace, exactly as runs do in LangSmith.

### `span` — generic work

Anything with a duration that isn't a model call: retrieval, a tool call, parsing, your own business logic.

### `generation` — a model call

The type that earns special treatment. A generation carries model name, model parameters, prompt/completion, **token usage** and **cost**. This is where the token and cost rollups in the UI come from, so **typing a model call as a plain `span` silently costs you your cost analytics** — the call is recorded, but it doesn't count.

> Same lesson as `run_type` in [`../30_langsmith/04-project-trace-run.md`](../30_langsmith/04-project-trace-run.md): the type is not cosmetic, it selects the rendering *and* the aggregation.

### `event` — a point in time

No duration. A discrete thing that happened: a cache hit, a guardrail triggered, a retry fired, a fallback engaged. Useful precisely because it does not pretend to be an interval.

```
TRACE  "support_answer"
├── span        "retrieve_context"        320 ms
│   ├── span        "embed_query"          40 ms
│   └── span        "vector_search"       210 ms
├── event       "cache_miss"                —
├── generation  "answer"      gpt-4o-mini · 1,240 in / 180 out · $0.0004
└── span        "post_process"             12 ms
```

---

## 3. ⭐ Session — the entity LangSmith makes you invent

A **session** groups traces that belong to one conversation.

This is the one place LangFuse's model is straightforwardly better for a common case, and it is worth dwelling on. In LangSmith, a multi-turn chatbot produces one trace per turn and nothing links them — so [`../30_langsmith/12-tracing-langgraph.md`](../30_langsmith/12-tracing-langgraph.md) has to advise duplicating `thread_id` into metadata purely so that "show me this user's whole broken conversation" is answerable at all.

In LangFuse, `session_id` is a field on the trace, the UI has a session view, and the question is answerable by default.

```
SESSION  "sess_8f21"
├── TRACE  turn 1  "what's the leave policy?"          👍
├── TRACE  turn 2  "and for contractors?"              👍
├── TRACE  turn 3  "can I carry it over?"              👎  ← the failure
└── TRACE  turn 4  "never mind"                         —
```

**Why the session, not the trace, is often the right unit of analysis:** turn 3 went wrong, but the *cause* is frequently in turns 1–2 — context that accumulated, a misunderstanding that stuck, a retrieved document that anchored the model. Debugging turn 3 alone shows you a wrong answer with no visible reason.

Scores can attach to a session, which lets you ask *"was this conversation successful?"* — a question no per-turn metric answers.

---

## 4. ⭐ User — the other first-class field

`user_id` on the trace, with a user view in the UI: every trace for a user, their cost, their score distribution.

Two things it buys during an incident:

| Question | Without it |
|---|---|
| "Is this one customer or everyone?" | Unanswerable — the single most useful triage question |
| "What did *this* user actually experience?" | You grep metadata and hope you wrote it |

**Put a pseudonymous id here, never a name or an email.** Same rule as [`../30_langsmith/06-tags-metadata-and-run-names.md`](../30_langsmith/06-tags-metadata-and-run-names.md): identifiers in, content out. This field is *designed* for an identifier — do not let the name tempt you into putting a human-readable one in it.

---

## 5. Score — the evaluation primitive

A score is a judgement attached to a trace, an observation, or a session. Richer than LangSmith's feedback, in a useful way: **four data types.**

| Type | Value | For |
|---|---|---|
| **`NUMERIC`** | float | Continuous quality — faithfulness 0.82, latency budget used |
| **`CATEGORICAL`** | string | Bucketed judgements — `"correct"` / `"partially_correct"` / `"wrong"` |
| **`BOOLEAN`** | `1` = true, `0` = false | Pass/fail — did it refuse when it should have? |
| **`TEXT`** | string, 1–500 chars | Free-text annotation — a reviewer's note |

Scores come from four places, and the platform treats them identically:

```
human annotation  ─┐
end-user feedback ─┤
LLM-as-a-judge    ─┼──►  SCORE  ──► trends · experiment comparison · CI gates
code evaluator    ─┘
```

> **`CATEGORICAL` and `TEXT` are the two LangSmith makes awkward, and both earn their place.** A reviewer distinguishing *partially correct* from *wrong* is giving you strictly more information than a 0.5, and it survives aggregation honestly — you can count categories, whereas averaging a 0.5 that meant "half right" with a 0.5 that meant "unsure" produces a number meaning neither.

Full mechanics in [`10-scores-and-user-feedback.md`](10-scores-and-user-feedback.md).

---

## 6. The whole model, one diagram

```
ORGANIZATION
└── PROJECT                          "support-bot-prod"
    ├── SESSION  sess_8f21           ← a conversation
    │   ├── TRACE  turn 1            user_id · tags · metadata
    │   │   ├── observation  span        "retrieve"
    │   │   ├── observation  event       "cache_miss"
    │   │   └── observation  generation  "answer"  ← tokens + cost live HERE
    │   │       └── SCORE  faithfulness  NUMERIC 0.91
    │   └── TRACE  turn 2
    │       └── SCORE  user_feedback  BOOLEAN 0
    └── SCORE  session_success  CATEGORICAL "resolved"   ← on the SESSION

    DATASET  "support-golden"
    └── dataset items ──► EXPERIMENT run ──► SCOREs per item
```

Three things this picture says that a list of definitions doesn't:

1. **Tokens and cost live on `generation` observations.** Mistype a model call and the rollups lose it.
2. **Scores attach at three levels** — observation, trace, session — and each answers a different question.
3. **Datasets connect to the same score primitive** as production feedback. That is the unified-platform property from [`../30_langsmith/02`](../30_langsmith/02-what-langsmith-is-and-what-it-records.md): a production failure can become a test case because both speak `score`.

---

## 7. ⭐ Environments — a small feature worth using from day one

LangFuse carries an **`environment`** attribute (propagated to nested observations, per lesson 07). Use it: `production`, `staging`, `development`.

The alternative — one project per environment — sounds tidy and is worse, because it splits datasets, prompts and score history across projects that cannot be compared. **You want one project with an environment dimension you can filter on**, not three projects with a third of the history each.

This is a cheap decision that is annoying to reverse, because traces are immutable and cannot be relabelled later.

---

## Recap

- **LangSmith "run" = LangFuse "observation".** The one rename that matters.
- Three observation types: **`span`** (work), **`generation`** (model call — carries tokens and cost), **`event`** (point in time).
- **Typing a model call as a `span` silently loses your cost analytics.**
- **`session_id` is first-class** — the multi-turn grouping LangSmith makes you invent via metadata. The session is often the right unit of analysis, because turn 3's failure was caused in turn 1.
- **`user_id` is first-class** — answers "one customer or everyone?". Pseudonymous ids only.
- **Scores** have four data types (`NUMERIC` · `CATEGORICAL` · `BOOLEAN` · `TEXT`) and attach to observation, trace **or session**.
- Set **`environment`** rather than splitting environments across projects.

---

## Self-check

1. You instrument a call to the OpenAI API as an observation. Which type, and what do you lose by choosing wrong?
2. A user reports the bot's 4th reply was nonsense. Which entity do you open, and why is the 4th trace alone insufficient?
3. A reviewer wants to mark answers *correct* / *partially correct* / *wrong*. Which score type, and why is that better than 1.0 / 0.5 / 0.0?
4. Why is `environment` as an attribute better than one project per environment?

---

**Next:** [`03-setup-and-keys.md`](03-setup-and-keys.md) →
