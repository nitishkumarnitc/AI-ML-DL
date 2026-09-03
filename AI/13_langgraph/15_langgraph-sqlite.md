# Video 15 — LangGraph + SQLite: Chatbot with Database Integration

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `c6a47iX5JkU`
> **Watch:** https://www.youtube.com/watch?v=c6a47iX5JkU

## 🎯 Overview
The chatbot so far uses `InMemorySaver`, which stores conversations in **RAM** — so a page refresh or app restart wipes every thread. This video adds **persistent storage** by swapping the checkpointer to a **SQLite-backed `SqliteSaver`**. With this, messages are written to a `chatbot.db` file on disk; conversations survive restarts and can be resumed days later. Changes are required in **both** the LangGraph backend and the Streamlit frontend.

## 🧠 Key Concepts

### The problem: RAM-based persistence
Short-term memory was implemented with `InMemorySaver`, which keeps all user/AI conversations in memory. Closing the app or even reloading the page terminates the program, memory is freed, and **all conversation history is lost**. There is no permanent storage.

### The three LangGraph checkpointers
LangGraph's docs describe three checkpointer types:
1. **`InMemorySaver`** — RAM-based; what we used so far.
2. **`SqliteSaver`** — backed by a SQLite database; great for **prototyping / learning**. Small, not really production-grade.
3. **`PostgresSaver`** — backed by Postgres, a proper database; used for **production-grade** chatbots.

Since we're still learning, we use `SqliteSaver`.

### `check_same_thread=False`
When creating the SQLite connection, you must pass `check_same_thread=False`. SQLite by default restricts a connection to the single thread that created it, and raises an error if used from another thread. Since the app uses **multiple threads to handle multiple conversations**, this restriction must be lifted — `check_same_thread=False` tells SQLite not to verify that the creating and using threads are the same.

### How checkpoints are stored
- The `SqliteSaver` is created from a **connection object** and automatically writes every state value to the database; the wiring is built into LangGraph.
- The `chatbot.db` file is created automatically in the project directory on first run.
- Messages are stored **per thread** — `thread-1`'s messages are separate from `thread-2`'s, and you can extract either by thread id.
- **Multiple checkpoints per execution:** the way this graph's workflow is designed, **one execution creates three checkpoints** — one at START, one at the chat node, and one at END. So running a thread twice produces six checkpoints, etc. (The persistence video in the playlist covers exactly when checkpoints are created.)

### Retrieving all threads from the DB
The checkpointer object has a **`.list(config)`** method that returns a **generator** of checkpoints. Passing `None` returns *all* checkpoints across the database (passing a specific thread config would return only that thread's). Each checkpoint's config carries its `thread_id`. To get the **unique** threads, loop over the generator and add each `thread_id` to a **set** (dedupes automatically), then return it as a list.

## 🔧 Code / Implementation

### Backend — swap the checkpointer
Install the community library first:
```bash
pip install langgraph-checkpoint-sqlite
```

```python
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

# create / connect to the SQLite database (auto-created in project dir)
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)

# build the checkpointer from the connection object
checkpointer = SqliteSaver(conn=conn)

# ... graph built as before, compiled with checkpointer=checkpointer
chatbot = graph.compile(checkpointer=checkpointer)
```

### Backend — retrieve all unique threads
```python
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)
```

### Backend — quick test that data persists
```python
config = {"configurable": {"thread_id": "thread-1"}}

response = chatbot.invoke(
    {"messages": [HumanMessage(content="Hi my name is Nitish")]},
    config=config,
)
print(response)
```
Run once ("Hi my name is Nitish"), then run again asking "What is my name?" in the **same** thread — even though the program restarted, the answer correctly recalls "Nitish" because both messages were read back from `chatbot.db`. Switching to `thread-2` gives a separate, independent conversation.

### Frontend — the only change
The rest of the Streamlit code is unchanged. Previously `chat_threads` was initialized to an empty list (logical when there was no permanent storage). Now, since past threads live in the DB, initialize it from the backend instead:

```python
from langgraph_database_backend import chatbot, retrieve_all_threads

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()
```

## 🪜 Step-by-Step Walkthrough
1. `pip install langgraph-checkpoint-sqlite`.
2. Import `sqlite3` and `SqliteSaver` (from `langgraph.checkpoint.sqlite`) instead of `InMemorySaver`.
3. Create a connection: `sqlite3.connect("chatbot.db", check_same_thread=False)`.
4. Build the checkpointer `SqliteSaver(conn=conn)` and compile the graph with it.
5. Test: invoke with `thread-1`, restart, ask a follow-up — confirm memory persists via the DB.
6. (Optional) Inspect `chatbot.db` with the VS Code **SQLite Viewer** extension (publisher: Florian Klampfer) — you'll see multiple checkpoints per thread but a small number of *unique* threads.
7. Add `retrieve_all_threads()` to the backend using `checkpointer.list(None)` and a set of thread ids.
8. In the frontend, initialize `chat_threads` from `retrieve_all_threads()` instead of an empty list.
9. Run the UI: past threads and their full conversations appear on first load; new threads add on; refresh/restart no longer loses anything.

## ⚠️ Gotchas & Tips
- **`check_same_thread=False` is mandatory** here — otherwise SQLite throws an error under the app's multi-threaded conversation handling.
- **`chatbot.db` is auto-created** in the project directory the first time the connection runs; all data lands there.
- **Expect many checkpoints, few threads** — three checkpoints per execution is by design; the unique-thread count is what matters (use a set to dedupe).
- **`SqliteSaver` is for prototyping/learning**, not production. Use `PostgresSaver` for production-grade apps.
- **Frontend change is tiny** — just switch `chat_threads` initialization from `[]` to `retrieve_all_threads()`.
- To visually verify per-thread storage, drill into a checkpoint in the SQLite Viewer to see the ordered Human/AI messages.

## 📌 Key Takeaways
- Persistence is achieved by replacing `InMemorySaver` with `SqliteSaver`, backed by an on-disk `chatbot.db`.
- LangGraph offers three checkpointers: `InMemorySaver` (RAM), `SqliteSaver` (prototyping), `PostgresSaver` (production).
- Create the DB with `sqlite3.connect("chatbot.db", check_same_thread=False)` and wrap it in `SqliteSaver(conn=conn)`.
- LangGraph auto-persists every state value to the DB — no manual write logic needed.
- Conversations are stored per thread and survive restarts/refreshes; resume exactly where you left off, even days later.
- `checkpointer.list(None)` yields all checkpoints; dedupe `thread_id`s with a set to list unique threads.
- The frontend only needs to seed `chat_threads` from `retrieve_all_threads()` so past conversations reappear on load.
