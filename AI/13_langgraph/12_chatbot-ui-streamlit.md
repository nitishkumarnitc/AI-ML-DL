# Video 12 — Building a Chatbot with UI in LangGraph & Streamlit

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `voZAgDmO-rk`
> **Watch:** https://www.youtube.com/watch?v=voZAgDmO-rk

## 🎯 Overview
The chatbot built earlier worked (including short-term memory) but had one big flaw — **no user interface**; you had to interact with it inside a Jupyter notebook. This video fixes that by giving the chatbot a clean **web UI built with Streamlit**. The core idea is to **split the chatbot into a backend (the LangGraph workflow) and a frontend (the Streamlit web app)**. The video teaches Streamlit chat fundamentals (`st.chat_message`, `st.chat_input`, `st.session_state`), builds a "copycat" dummy bot to master those primitives, and then wires the frontend to the existing LangGraph backend to produce a real AI chatbot with a UI.

## 🧠 Key Concepts

### Backend / Frontend split
The chatbot now has two components:
- **Backend** (`langgraph_backend.py`) — builds the LangGraph workflow/graph. This is **exactly the same code from the earlier chatbot video** (imports, `ChatState`, single `chat_node`, `START → chat_node → END`, compiled with an `InMemorySaver` checkpointer).
- **Frontend** (`streamlit_frontend.py`) — the Streamlit web app. This corresponds to the old console loop that asked for input, invoked the bot, and printed the reply.

Flow: user types in the frontend → frontend sends the message to LangGraph → LangGraph returns a response → frontend displays it.

### The two Streamlit chat UI components
1. **`st.chat_message(role)`** — the box that displays a single message. The `role` (`"user"` or `"assistant"`) determines the avatar/icon shown. Inside it you render text with `st.text(...)` (or `st.write`).
2. **`st.chat_input(placeholder)`** — the input box pinned at the bottom where the user types; returns whatever the user submitted (on Enter).

### Streamlit reruns the whole script on every interaction
This is the central gotcha. **Every time the user presses Enter, Streamlit re-executes the script top to bottom.** A normal Python list declared at the top of the script is therefore **reset on every rerun**, wiping any conversation history you appended to it.

### `st.session_state` — persistent storage across reruns
`st.session_state` is a dictionary-like object whose contents **survive reruns**. It is only reset when the user **manually refreshes the page**. Store the conversation history here (`st.session_state["message_history"]`) so messages accumulate instead of vanishing.

### Message history structure
History is a Python **list of dictionaries**, one per message, each with two keys: `role` (`"user"` / `"assistant"`) and `content` (the message text). On each rerun you first **loop over the history and render every message**, then handle the new user turn.

### Connecting to the LangGraph backend
To get real AI replies you **import the compiled `chatbot` object from the backend** and call `chatbot.invoke(...)`. Because the backend uses a checkpointer, the invoke **must include a `config` with a `thread_id`** — forgetting this is an error. You wrap the user's text in a `HumanMessage`, invoke, and extract the last message's `content` as the AI reply.

## 🔧 Code / Implementation

### Backend — `langgraph_backend.py` (unchanged from earlier video)
```python
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

llm = ChatOpenAI()

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

checkpointer = InMemorySaver()
chatbot = graph.compile(checkpointer=checkpointer)
```

### Learning the primitives — basic components
```python
import streamlit as st

# a user message box
with st.chat_message("user"):
    st.text("Hi")

# an assistant message box
with st.chat_message("assistant"):
    st.text("How can I help you?")

# input box at the bottom
user_input = st.chat_input("Type here")
if user_input:
    with st.chat_message("user"):
        st.text(user_input)
```
Run with: `streamlit run streamlit_frontend.py`

### Copycat bot WITHOUT session_state (buggy — history disappears)
```python
import streamlit as st

message_history = []      # RESET on every rerun -> this is the bug

for message in message_history:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type here")
if user_input:
    # user message
    message_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)
    # assistant echoes the same text (dumb copycat)
    message_history.append({"role": "assistant", "content": user_input})
    with st.chat_message("assistant"):
        st.text(user_input)
```

### Copycat bot WITH session_state (fixed)
```python
import streamlit as st

# initialise history once; survives reruns
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

# 1) load & render the full conversation history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

# 2) handle the new user turn
user_input = st.chat_input("Type here")
if user_input:
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    st.session_state["message_history"].append({"role": "assistant", "content": user_input})
    with st.chat_message("assistant"):
        st.text(user_input)
```

### Final — real AI chatbot (Streamlit + LangGraph)
```python
import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph_backend import chatbot          # import compiled backend graph

CONFIG = {"configurable": {"thread_id": "thread-1"}}   # checkpointer needs a thread_id

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

# render history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("Type here")
if user_input:
    # show + store user message
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    # get AI response from LangGraph
    response = chatbot.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
    )
    ai_message = response["messages"][-1].content

    # show + store assistant message
    st.session_state["message_history"].append({"role": "assistant", "content": ai_message})
    with st.chat_message("assistant"):
        st.text(ai_message)
```

## 🪜 Step-by-Step Walkthrough
1. Create a new project folder with two files: `langgraph_backend.py` (already-written chatbot code) and `streamlit_frontend.py` (empty), plus a `.env` holding the OpenAI key and a virtualenv with `langchain`, `langgraph`, `streamlit` installed.
2. Learn `st.chat_message` by rendering a hardcoded user message and an assistant message; note the role-based avatars.
3. Add `st.chat_input` and display whatever the user types inside a user chat box.
4. Build a **copycat bot** where the assistant echoes the user's text — observe that on the second message the old messages disappear (history is reset each rerun).
5. Diagnose: Streamlit re-runs the script top-to-bottom on every Enter, so the plain list is recreated empty.
6. Fix with `st.session_state["message_history"]`: initialise it once, load/render it at the top, append new user & assistant messages into it.
7. Verify the copycat bot now keeps full history across turns.
8. Swap the dummy echo for real AI: `from langgraph_backend import chatbot`, call `chatbot.invoke({"messages": [HumanMessage(...)]}, config=CONFIG)`, extract `response["messages"][-1].content`.
9. Fix the missing-`thread_id` error by defining `CONFIG` with a `thread_id` and passing it to `invoke`.
10. Re-run — a clean web chatbot with short-term memory (remembers your name, chains questions).

## ⚠️ Gotchas & Tips
- **Streamlit reruns the entire script on every interaction** — never rely on ordinary module-level variables for state; they reset each rerun.
- **Use `st.session_state`** for anything that must persist across reruns (here, the message history). It only clears on a manual page refresh.
- **Render history first, then the current turn** — loop over `session_state["message_history"]` at the top so past messages always reappear before the new user/assistant messages.
- **The backend needs a `thread_id`.** Since the compiled graph uses a checkpointer, `chatbot.invoke(...)` **must** receive `config={"configurable": {"thread_id": ...}}`, or it errors — this was the instructor's bug.
- **Only the assistant-message block changes** when going from the copycat bot to the real bot: replace `user_input` with the extracted `ai_message` in both the append and the display.
- **`role` drives the avatar/icon**; you can customise it via the `avatar` parameter, but the default icons are fine.
- Run the app with `streamlit run streamlit_frontend.py`; refresh the page to clear session state between tests.
- Streamlit is recommended here as the fastest way to demo a chat UI, but other frontend options exist.

## 📌 Key Takeaways
- Give a LangGraph chatbot a UI by **splitting it into a Streamlit frontend and a LangGraph backend**.
- The **backend is the unchanged chatbot graph**; the frontend replaces the old console loop.
- Two Streamlit primitives build the chat UI: **`st.chat_message(role)`** (display) and **`st.chat_input()`** (input).
- **Streamlit reruns the whole script on each interaction**, so plain variables lose state — this is why a naive history list gets wiped.
- **`st.session_state`** is a rerun-persistent dictionary; store `message_history` (a list of `{role, content}` dicts) there.
- Always **load/render the full history first**, then append and display the new user and assistant messages.
- Connect to AI by **importing the compiled `chatbot`** and calling `chatbot.invoke({"messages": [HumanMessage(...)]}, config=CONFIG)`, extracting `response["messages"][-1].content`.
- The checkpointer-backed backend **requires a `thread_id`** in the invoke config.
