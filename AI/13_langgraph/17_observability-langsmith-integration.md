# Video 17 — Observability in LangGraph — LangSmith Integration

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `ikzN6byFNWw`
> **Watch:** https://www.youtube.com/watch?v=ikzN6byFNWw
>
> 📚 **Deeper dive:** [`AI/30_langsmith/`](../30_langsmith/) — full 18-lesson LangSmith tutorial (tracing, `@traceable`, monitoring, evaluation, production hardening).

## 🎯 Overview
This video adds an **observability** feature to the running chatbot project by integrating **LangSmith**. Up to this point the chatbot already has a GUI, streaming, short-term memory, and database persistence. Observability lets you trace the chatbot's execution end-to-end — every user message, every reply, token usage, latency, and the internal behavior of each node — recorded in a hosted dashboard. The instructor stresses that this feature pays off later when tools, RAG, and MCP are added, because it makes debugging complex flows far easier and provides critical production monitoring.

## 🧠 Key Concepts

### What observability means here
Observability, in this context, is the ability to trace the chatbot's execution end-to-end. When a user chats with the bot, everything they send and everything the bot replies is recorded in a software tool (LangSmith). Beyond the raw messages, LangSmith also records **token usage** (input and output tokens), **latency**, **time to first token**, execution start/end timestamps, status, and how each internal component (node, LLM) behaved.

### Prerequisite: the LangSmith crash course
The instructor explicitly does **not** re-teach the observability concept from scratch here. He points to a separate ~2-hour "LangSmith crash course" video on his channel and strongly recommends watching it first, both to understand observability deeply and to learn LangSmith in detail. This video assumes that background.

### How LangSmith organizes data — Projects → Traces → Threads
LangSmith uses a hierarchy:

- **Project** — the top level. All your traces for one application live inside a named project (here, `chatbot-project`). Projects appear under the **Tracing Projects** section of the dashboard.
- **Trace** — one turn of conversation. Each time the user sends a message and the bot replies, LangSmith captures a single trace. Clicking a trace reveals the node that ran (e.g. `chat_node`), the LLM used (e.g. `ChatOpenAI`), the input, the output, timing, status, and token counts.
- **Thread** — a grouping of traces belonging to the same conversation. Without threads, every trace (even from different conversations) piles up in one flat list, which is disorganized. Threads let each conversation's traces be stored together.

### The problem with the default (flat) setup
By default, LangSmith records every turn as a separate trace but does **not** separate different conversations. If you open a brand new thread in the chatbot and chat, that turn still lands in the same flat trace list as your previous, unrelated conversation. All conversations' messages end up mingled in one place — poor organization. The LangSmith creators anticipated this and provided threads as the solution.

### The zero-code magic (and its one exception)
The best part of LangSmith is that once environment variables are set, you need **no changes** to your main application code — LangSmith automatically traces behind the scenes. The one exception is threads: to organize traces into conversational threads you must add a small piece of extra code that explicitly passes a thread identifier when invoking the chatbot.

## 🔧 Code / Implementation

### Step 1 — Environment variables
After creating an API key in LangSmith (**Settings → API Keys → Create API Key**), add these variables to your project's `.env` file. Once present, LangSmith automatically begins tracing your LangGraph project — no changes to `main` code required.

```bash
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="<your-api-key>"      # must be exactly the key you just created
LANGSMITH_PROJECT="chatbot-project"     # name shown under Tracing Projects
```

The `LANGSMITH_PROJECT` value is the name that shows up in the LangSmith dashboard; the moment you run the app, a project by that name appears and all traces flow into it.

### Step 2 — The existing config (thread id only)
The existing code already builds a `config` variable so the thread id (stored in the session) can be sent to the LangGraph backend. LangGraph uses this thread id to organize messages into threads on **its** side:

```python
# existing config used when invoking the graph
config = {
    "configurable": {
        "thread_id": st.session_state["thread_id"]
    }
}
```

### Step 3 — Extended config to log threads + rename traces in LangSmith
To make **LangSmith** group traces into threads, replace the config above with one that adds a `metadata` key carrying the thread id, plus an optional `run_name` for readability. LangSmith reads the `thread_id` inside `metadata` to build its threads view.

```python
config = {
    "configurable": {
        "thread_id": st.session_state["thread_id"]
    },
    "metadata": {
        "thread_id": st.session_state["thread_id"]
    },
    "run_name": "chat_turn"   # optional: nicer trace name than the default "LangGraph"
}
```

- The `configurable.thread_id` part is unchanged — it still drives LangGraph's own message organization.
- The `metadata.thread_id` part is new — this is what LangSmith needs to place each trace inside the correct thread.
- `run_name` is optional. By default each trace is named `LangGraph`, which is not informative. Setting `run_name="chat_turn"` makes each trace display as **chat_turn**, since each trace represents exactly one turn of conversation.

## 🪜 Step-by-Step Walkthrough
1. Go to `smith.langchain.com` and create an account (or log in).
2. Navigate to **Settings → API Keys**, click to create an API key, add a description, and copy the generated key.
3. Paste the LangSmith environment variables (tracing flag, endpoint, API key, project name) into your project's `.env` file.
4. Re-run the **exact same** chatbot code from the previous (database persistence) video — no code changes needed for basic tracing.
5. Chat with the bot (e.g. "Give me a roadmap to study AI engineering"); the bot behaves normally.
6. Open the LangSmith dashboard → **Tracing Projects** → `chatbot-project`. Each turn appears as a separate trace.
7. Click a trace to inspect the node (`chat_node`), the LLM (`ChatOpenAI`), input/output, start/end time, time to first token, status, input+output token counts, and latency.
8. Notice the flat-list problem: separate conversations dump their traces into the same place.
9. To fix it, follow LangSmith's "Log your first thread" doc — explicitly pass a `thread_id` / session id / conversation id while invoking the chatbot, using the extended `config` with `metadata`.
10. Delete the old project (to start clean), re-run, and chat. Now traces are named `chat_turn` and appear under a single **Thread**.
11. Start a new conversation (new thread) — a second thread appears, and each conversation's turns are neatly stored under their respective threads.

## ⚠️ Gotchas & Tips
- **Watch the LangSmith crash course first.** Without it, the concept and dashboard won't fully make sense.
- **Basic tracing needs no code changes** — only the `.env` variables. The main application code stays identical to the previous video.
- **`LANGSMITH_API_KEY` must match** the key you actually created in Settings.
- **Threads require the `metadata.thread_id`.** The `configurable.thread_id` alone drives LangGraph but does not group traces in LangSmith.
- **Reuse the thread id you already track** in session state — the same value that powers your chatbot's threading should be passed to LangSmith's metadata.
- **`run_name` is optional but recommended** for readability; it replaces the generic default trace name `LangGraph`.
- **One trace = one turn.** A turn is one user message plus the bot's reply.
- The instructor didn't cover the other LangSmith features (monitoring, datasets & experiments, prompts, playground) here — those are in the dedicated crash course and may be revisited later.

## 📌 Key Takeaways
- Observability = end-to-end tracing of the chatbot's execution, recorded in **LangSmith**.
- LangSmith organizes data as **Project → Trace → Thread**; a trace is one conversational turn.
- Setup is just an API key plus four `.env` variables; tracing then happens automatically with zero changes to app code.
- Each trace exposes node/LLM details, input/output, latency, time to first token, status, and input/output token counts.
- By default all conversations share one flat trace list — a real organizational problem.
- **Threads** solve this: pass a `thread_id` in the invocation `config`'s `metadata` to group traces per conversation.
- Add an optional `run_name` (e.g. `chat_turn`) to give traces meaningful names instead of the default `LangGraph`.
- This feature becomes especially valuable when debugging more complex features (tools, RAG, MCP) and when running the chatbot in production.
