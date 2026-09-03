# Video 13 — Streaming in LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `D1PcZaeQ2eg`
> **Watch:** https://www.youtube.com/watch?v=D1PcZaeQ2eg

## 🎯 Overview
This video continues the running chatbot project (basic chatbot → short-term memory → Streamlit UI) by adding **streaming**. Instead of waiting for the LLM to finish generating a long response and dumping it on screen all at once, we stream the answer **token by token** with a ChatGPT-style typewriter effect. The change is small in code but a huge win for user experience, and it lays the groundwork for showing step-by-step progress updates in later agentic apps.

## 🧠 Key Concepts

### What is streaming?
In LLMs, **streaming means the model starts sending tokens as soon as they are generated, instead of waiting for the entire response to be ready before returning it.** There are two ways to return a response:
1. **Non-streaming (`invoke`)** — the LLM thinks, generates the *whole* answer, and only then hands the complete text back in one go.
2. **Streaming (`stream`)** — as the LLM generates the answer, tokens flow back to you one at a time (the typewriter effect you see in ChatGPT).

Without streaming, a request for a 500-word blog makes the user stare at a blank screen for 5–10 seconds and then the whole wall of text appears at once — not very readable.

### Why streaming matters
The instructor lists several benefits:
- **Faster perceived response time.** For a long output (essay/blog), generation can take 5–10s. A non-technical user staring at a frozen-looking screen may think the app crashed and leave — causing **drop-off**. Streaming makes output appear almost instantly, signalling "it's working."
- **Human-like conversation.** Streaming builds trust, "feels alive," and keeps the user engaged moment to moment.
- **Essential for multimodal UIs.** For a voice assistant (e.g., an Alexa-type device), a 10-second silence before it speaks feels broken — like a bad phone signal. Streaming keeps the conversation seamless.
- **Better UX for long/code output.** Code printed line by line is far easier to follow than a whole block appearing suddenly.
- **Interruptibility saves money.** If you don't like the response, you can stop it mid-way. Fewer tokens are generated, and since providers charge per token, **saving tokens saves money.**
- **Progress updates, not just messages.** Streaming isn't only for the LLM's text. For an AI agent (e.g., "book me a movie ticket"), you can stream step-by-step status — "opened BookMyShow → selected movie → selected seat → selecting payment mode → paying" — so the user isn't left uncertain for a minute.

### Generators (the Python foundation)
`graph.stream(...)` returns a **generator object**. In Python, *a generator is a special type of iterator that lets you generate values on the fly, one at a time, using the `yield` keyword instead of `return`.* Because we get a generator, we simply loop over it to print its content one token at a time.

### LangGraph stream modes
When streaming in LangGraph you pass a `stream_mode`. The available modes are: **`updates`**, **`values`**, **`custom`**, and **`messages`**. For streaming an LLM's response token by token you use **`messages`**. (The other modes become useful later for agentic apps that use tools.)

### Structure of a streamed chunk
Each item yielded by the stream in `messages` mode is a **tuple of `(message_chunk, metadata)`** — the actual text lives in `message_chunk.content`, accompanied by some metadata.

## 🔧 Code / Implementation

### Backend test (swap `invoke` → `stream`)
The only change is calling `.stream()` instead of `.invoke()` and looping over the returned generator:

```python
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "thread-1"}}

# Confirm we actually get a generator
stream = chatbot.stream(
    {"messages": [HumanMessage(content="What is the recipe to make pasta?")]},
    config=config,
    stream_mode="messages",
)
print(type(stream))   # -> <class 'generator'>

# Print token by token
for message_chunk, metadata in chatbot.stream(
    {"messages": [HumanMessage(content="What is the recipe to make pasta?")]},
    config=config,
    stream_mode="messages",
):
    if message_chunk.content:
        print(message_chunk.content, end=" ", flush=True)
```

`stream()` needs three things: the **initial state** (with a `HumanMessage`), the **config** (thread id), and the **`stream_mode`**.

### Streamlit frontend (`st.write_stream`)
Streamlit exposes chat UI elements; two were already used (`st.chat_input`, `st.chat_message`). Two more are relevant here:
- **`st.status`** — a status container for showing agent progress updates.
- **`st.write_stream`** — writes generators/streams to the app **with a typewriter effect**. You just hand it a generator and it handles all the UI.

Replace the old "get AI response and append" block with:

```python
with st.chat_message("assistant"):
    ai_message = st.write_stream(
        message_chunk.content
        for message_chunk, metadata in chatbot.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="messages",
        )
    )

# st.write_stream returns the full concatenated response
st.session_state["message_history"].append(
    {"role": "assistant", "content": ai_message}
)
```

Here a generator expression yields `message_chunk.content` for every `(message_chunk, metadata)` pair; `st.write_stream` consumes it, renders the typewriter effect, and **returns the final complete response**, which we then store in session state.

## 🪜 Step-by-Step Walkthrough
1. Understand streaming conceptually and why it improves UX.
2. In the backend, change `chatbot.invoke(...)` to `chatbot.stream(...)` and add `stream_mode="messages"`.
3. Verify the return type is a generator (`print(type(stream))`).
4. Loop over the generator, printing `message_chunk.content` when non-empty.
5. Revert the backend to its clean state — **no permanent backend changes are needed.**
6. In the Streamlit frontend, wrap the response in `with st.chat_message("assistant")` and call `st.write_stream(...)` on the streaming generator.
7. Capture the returned final response and append it to `message_history` in session state.
8. Run and test with a long prompt (e.g., "Write a 500-word blog on cricket").

## ⚠️ Gotchas & Tips
- **Don't hardcode the prompt.** During the demo the content was accidentally hardcoded to "What is the recipe to make pasta?" so every query returned the same thing. Pass the actual `user_input` instead.
- **The backend graph doesn't change.** All meaningful changes are the `invoke → stream` swap and the frontend. Keep the backend in its original state.
- **`stream_mode="messages"` is specifically for token-by-token LLM text.** Other modes exist for tool/agent updates.
- **Capture `st.write_stream`'s return value** so the full message is persisted to history (otherwise the message vanishes on rerun).

## 📌 Key Takeaways
- Streaming = send tokens as they are generated, rather than waiting for the whole response.
- The one core change is `graph.invoke()` → `graph.stream(..., stream_mode="messages")`.
- `stream()` returns a **generator** yielding `(message_chunk, metadata)` tuples.
- LangGraph stream modes: `updates`, `values`, `custom`, `messages` — use `messages` for LLM tokens.
- In Streamlit, `st.write_stream(generator)` renders the typewriter effect and returns the final text.
- Benefits: faster perceived latency, human-like feel, multimodal readiness, better long/code output, interruptibility (token/cost savings), and progress updates for agents.
- Streaming is small to implement but can 10x the user experience.
