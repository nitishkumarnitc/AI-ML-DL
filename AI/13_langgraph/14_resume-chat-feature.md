# Video 14 — How to build a Resume Chat feature like ChatGPT

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `N2nVG2MGWJ8`
> **Watch:** https://www.youtube.com/watch?v=N2nVG2MGWJ8

## 🎯 Overview
Building on the streaming chatbot, this video adds a **ChatGPT-style "resume chat" feature**: a sidebar with a **New Chat** button and a list of **past conversations**, so the user can start fresh threads and jump back into any previous one. Crucially, **no backend (LangGraph) changes are needed** — everything is done in the Streamlit frontend by managing session state, dynamic thread IDs, and reading conversation history back from the graph's checkpointer.

## 🧠 Key Concepts

### Break the feature into small tasks
The instructor stresses a programming principle: decompose a big feature into small tasks and execute them one by one. The resume-chat feature is split into four sets of tasks:
1. Build the sidebar UI (title, New Chat button, "My Conversations" section).
2. Generate a **dynamic thread ID** and store it in session.
3. Give **New Chat** functionality (new thread + reset history) and **retain past thread IDs** in a list.
4. Make each thread **clickable** so its conversation loads into the main area (resume).

### Session state holds three things
- **`message_history`** — a list of the messages (dicts of `{role, content}`) exchanged in the current thread; looped over to render the chat.
- **`thread_id`** — the current conversation's thread id.
- **`chat_threads`** — a list of *all* thread ids created, kept in session so past threads aren't lost when a new chat starts.

### Dynamic thread IDs with `uuid`
Previously the thread id was hardcoded (`"thread-1"`). That doesn't work once a user can create arbitrarily many chats via New Chat, so IDs must be generated **programmatically** using Python's `uuid` library (`uuid.uuid4()`) — each call yields a random new thread id.

### Reading past conversations from the graph
LangGraph's `chatbot.get_state(config)` returns a **`StateSnapshot`** object; its **`.values`** attribute is a dict containing a `messages` key — a list of the messages stored for that thread. This is how a clicked thread's history is retrieved.

### Format compatibility problem
`get_state(...).values["messages"]` returns **LangChain message objects** (`HumanMessage`, `AIMessage`), but `message_history` stores **dicts** shaped `{"role": ..., "content": ...}`. So loaded messages must be converted: check each message's type (`isinstance(msg, HumanMessage)` → role `"user"`, else `"assistant"`) and rebuild the dict list.

## 🔧 Code / Implementation

### Utility functions
```python
import uuid

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    # 1. new thread id, 2. store in session, 3. keep it in the threads list, 4. clear history
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(st.session_state["thread_id"])
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    return chatbot.get_state(
        config={"configurable": {"thread_id": thread_id}}
    ).values["messages"]
```

### Session setup
```python
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = []

# add current thread to the list on first load
add_thread(st.session_state["thread_id"])

config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
```

### Sidebar UI + resume logic
```python
st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")

# reversed so the most recent chat shows on top
for thread_id in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state["thread_id"] = thread_id           # important: switch active thread
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            temp_messages.append({"role": role, "content": msg.content})

        st.session_state["message_history"] = temp_messages
```

The existing loop that renders `message_history` and the `chatbot.stream(...)` call (which now uses `config` built from `st.session_state["thread_id"]`) handle the rest automatically.

## 🪜 Step-by-Step Walkthrough
1. **Sidebar UI** — add `st.sidebar.title(...)`, `st.sidebar.button("New Chat")`, and `st.sidebar.header("My Conversations")`.
2. **Dynamic thread id** — write `generate_thread_id()` (uuid4); initialize `thread_id` in session if absent; pass `st.session_state["thread_id"]` into the stream config instead of a hardcoded value.
3. **Display current thread** — temporarily show the current thread id via `st.sidebar.text(...)` to verify.
4. **New Chat behavior** — `reset_chat()` generates a new id, stores it, and clears `message_history`, wiping the main area for a fresh conversation.
5. **Retain threads** — create `chat_threads` list in session; write `add_thread()`; call it on load and inside `reset_chat()` so no thread is lost.
6. **List all threads** — loop over `chat_threads` and render each id as a sidebar **button** (must cast to `str`). Reverse the list so recent chats appear first.
7. **Resume on click** — on a thread button click, set the active `thread_id`, call `load_conversation()`, convert the returned message objects to the `{role, content}` dict format, and assign to `message_history`.
8. Test: create multiple chats with different names/topics, switch between them, and confirm each remembers its own context (e.g., "What is my name?" returns the right name per thread).

## ⚠️ Gotchas & Tips
- **No backend changes** — the existing LangGraph backend is sufficient; all work is in the Streamlit frontend.
- **Cast thread id to `str`** before passing to `st.sidebar.button(...)` — the button expects a string, otherwise it errors.
- **Set the active `thread_id` when resuming** — easy to forget; without it, subsequent messages won't go to the clicked thread.
- **Convert message formats** — graph state returns `HumanMessage`/`AIMessage` objects; `message_history` needs `{role, content}` dicts.
- **Reverse the thread list** (`[::-1]`) so the newest conversation shows at the top, matching ChatGPT.
- **Homework:** replace raw UUIDs in the sidebar with meaningful, logical conversation names (like ChatGPT auto-titles).

## 📌 Key Takeaways
- The resume-chat feature is entirely a **frontend/session-state** exercise; the LangGraph backend is untouched.
- Manage three session objects: `message_history`, current `thread_id`, and `chat_threads` (list of all threads).
- Generate thread IDs dynamically with `uuid.uuid4()` — never hardcode.
- `chatbot.get_state(config).values["messages"]` retrieves a thread's stored messages.
- Convert LangChain message objects to `{role, content}` dicts to stay compatible with the render loop.
- New Chat = new thread id + reset history; resume = set thread id + load and convert messages.
- **Limitation:** persistence uses `InMemorySaver`, so a refresh/restart wipes all threads from RAM — solved in the next video by connecting to a database.
