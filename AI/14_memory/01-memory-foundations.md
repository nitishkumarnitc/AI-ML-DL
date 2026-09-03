# 01 · Memory Foundations — "LLMs Don't Have Memory, So How Do They Remember?"

> Framework-agnostic, first-principles notes. This is the conceptual base for the two
> LangGraph implementation notes: [Short-Term Memory](02-short-term-memory-langgraph.md)
> and [Long-Term Memory](03-long-term-memory-langgraph.md).

**Source video:** *LLMs Don't Have Memory — So How Do They Remember?* (Agentic AI using LangGraph playlist, by Nitesh)

---

## Why memory matters

Almost no GenAI application can function without memory. A chatbot or an agent that
cannot recall past context is "highly frustrating" — the user has to re-explain
everything on every turn. So memory is not a nice-to-have; it is foundational.

The whole video builds memory **from first principles** — as if we were inventing it —
starting from one plain statement and building solutions around it until we arrive at
how modern GenAI systems actually handle memory.

---

## 1. An LLM at inference is a parameterized math function

> **An LLM at inference is just a parameterized math function:**  `y = f_θ(x)`

**Parameterized function** = a function whose output depends not only on its input but
also on some **parameters**.

- Example: `y = a·x²` — to compute `y` you need `x` (from the user) *and* `a` (from somewhere else).
- Concrete ML example — **linear regression**: fit `y = m·x + b` to data. Here `m` (slope)
  and `b` (intercept) are **parameters**, and their values come **from the training data**.

Rewriting linear regression as `y = f(x; m, b)` gives the same shape as an LLM:

| Symbol | Linear regression | LLM |
|--------|------------------|-----|
| `x`    | input feature | **input tokens / the prompt** you send at inference |
| `θ`    | `m, b` (2 params) | **billions of parameters** (the weights) |
| `y`    | prediction | **output tokens** the model returns |

Key facts about the three components:

- **`θ` (theta)** — billions of parameter *values*. **Fixed at training time.** The user
  has zero control over it at inference. (This is why we say "a 70B / 100B parameter model".)
- **`x`** — the input tokens (the prompt). **The user can change this**, which is why a
  different prompt gives a different output.
- **`y`** — the output, which depends on **both** `θ` and `x`.

---

## 2. The function is *stateless*

> A system is **stateless** if its output depends **only on the current input** and not on
> anything that happened before.

Call the model twice:

```
x1 , θ  ->  y1
x2 , θ  ->  y2        # θ is still the same
```

Because the system is stateless, `y2` was computed from `x2` (and `θ`) **only**. `x1` and
`y1` played no part. Every function call is **unique and independent** of the previous one.

**Practical demo (OpenAI LLM):**

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI()

llm.invoke("My name is Nitesh.")   # x1 -> y1: "Nice to meet you, Nitesh."
llm.invoke("What is my name?")     # x2 -> y2: "I'm sorry, I don't know your name."
```

The model has no idea what you said in the previous call. **Two things learned so far:**

1. An LLM at inference can be represented as a math function `y = f_θ(x)`.
2. That function is **stateless by nature**.

---

## 3. The deadlock (and the escape)

- **Fact 1:** LLMs are stateless → **LLMs have no intrinsic memory.** They cannot remember
  past conversations.
- **Fact 2:** Practically **every** GenAI / agentic app *needs* memory to function.

→ We are in a **deadlock**.

- **Fact 3 (the escape):** If the LLM has no memory but we need memory, we must build the
  memory feature **externally** — a system *around* the LLM (with the LLM at the center)
  that *acts like* memory.

---

## 4. Two enabling concepts

### a) Context window

> The **context window** is the amount of text an LLM can read and "remember" at one time,
> before answering.

**Analogy — a camera:** the LLM is the camera, the context window is the **lens**. A small
lens captures a small part of the scene; a big lens captures a large portion. The bigger the
context window, the more text the model can process before answering.

- Modern LLMs: **128k tokens** or more. Gemini models: up to **1 million** tokens.
- 128k tokens ≈ a ~200-page PDF you could paste in.

**Why it matters here:** we can send *a lot* of tokens in `x`. That is the power we'll exploit.

### b) In-context learning (ICL)

- **Parametric knowledge** — knowledge captured in the weights `θ` during training on huge
  data (the whole internet). At inference the prompt searches this parametric knowledge.
- **In-context learning** = an *emergent* ability that lets an LLM use information and
  patterns **present in the prompt itself**, *in addition to* its trained parametric
  knowledge, to answer.
  - Example: paste a 100-page private company PDF into the prompt and ask a question about
    it. The answer isn't in the weights, but the model reads the PDF **in context** and answers.

---

## 5. First-principles solution → Short-Term Memory

Combine the two concepts: **every time we invoke the LLM, concatenate the entire
conversation so far into `x`.**

```
turn 1:  y1 = f_θ(x1)                      # nothing before it
turn 2:  y2 = f_θ( concat(x1, y1, x2) )    # send the whole history
```

- **Context window** makes it feasible to send all that text.
- **In-context learning** lets the model read `x1, y1` to answer `x2` (e.g. recall the name).

**Code — a growing `messages` list:**

```python
messages = [{"role": "user", "content": "My name is Nitesh."}]      # x1
y1 = llm.invoke(messages)                                            # "Nice to meet you, Nitesh"
messages.append(y1)                                                  # append the AI reply

messages.append({"role": "user", "content": "What is my name?"})     # x2 concatenated
y2 = llm.invoke(messages)                                            # "Your name is Nitesh"
```

The `messages` variable now acts as **state** — the previously stateless system has become
**stateful**. This buffer is often called the **conversation buffer**.

It *acts like* memory but isn't intrinsic: restart the program and the model forgets you
again. Because it's temporary, this is called **Short-Term Memory (STM)**.

---

## 6. Short-Term Memory in chatbots

- A **conversation** = one session with the chatbot (open → talk about a topic → close).
- STM is **conversation-scoped**: each conversation gets its own STM. Switch conversations
  and the STM resets to that conversation's messages.
- A conversation is also called a **thread**, so: **STM is thread-scoped.** Outside its
  thread, an STM does not exist.

Why per-conversation and not one global buffer? With 1000 conversations, a single buffer
would be far too long and incoherent — the LLM couldn't answer well. So we draw a **logical
boundary**: one conversation = one boundary = one STM.

---

## 7. Problems with Short-Term Memory

### Problem 1 — STM is fragile
The `messages` buffer lives in the running process. If the code resets or the server
crashes, the whole conversation context is gone. (Switching to a "new chat" and back shows
nothing if it was never saved.)

**Solution — persistence:** connect a database. Before leaving a conversation, store its
messages under a **thread ID** in a DB. When you return to that thread, load its messages
back into the buffer so context is preserved.

```
thread_id = 1  ->  [messages...]   # stored in DB
thread_id = 2  ->  [messages...]   # stored in DB
# revisiting thread 1: load its messages back before continuing
```

### Problem 2 — the context window problem
Long conversations accumulate many messages. Since we resend the whole history each turn,
the token count can **exceed the context window** → the model becomes incoherent or
hallucinates.

**Solution — trimming + summarization (used together):**
- **Trimming:** send only the most recent *N* messages (e.g. last 50 of 500), assuming the
  live context lives in the recent messages.
- **Summarization:** the messages you drop are sent to *another* LLM to produce a **summary**;
  then you send `summary + recent N messages`. This preserves older context instead of
  discarding it.

> Implementation of persistence, trimming, and summarization in LangGraph is covered in
> [Short-Term Memory in LangGraph](02-short-term-memory-langgraph.md).

---

## 8. Why we need Long-Term Memory

STM being **thread-scoped** is a feature (it lets conversations stay coherent) but it also
creates three problems:

1. **No continuity between conversations.** If in one chat you tell the LLM "I only know
   Python, not Java," a new chat two days later has forgotten that entirely.
2. **Learning never compounds.** Effort spent teaching the assistant in one chat (e.g.
   "write optimized SQL with window functions, not sub-queries") must be repeated from
   scratch in every new conversation.
3. **Cross-thread reasoning is impossible.** You can't ask "what did we decide yesterday?" —
   every new conversation makes you a **stranger** to the assistant again.

→ A true **personal assistant** — one that knows the user in-and-out and evolves with them —
is impossible with STM alone, because a user's profile is assembled from **many** different
conversations (one reveals they prefer Python, another that they're a developer, another
that they like simple explanations).

**We need a new kind of memory with two properties:**
1. It stores **special, long-lived information** that **survives a single conversation/session**
   (useful for days or months — e.g. facts gathered while writing a book over months).
2. It is **very selective** — we don't blindly dump the whole chat; we extract only the
   **stable, useful, reusable** pieces and ignore the rest.

This is **Long-Term Memory (LTM)** — memory that lives *outside* any single conversation for
a long period.

---

## 9. The three types of Long-Term Memory

| Type | Stores | Answers | Example |
|------|--------|---------|---------|
| **Episodic** | past events | "What did we do last time? Have we tried this before?" | last session the user rejected a solution; a deploy failed due to wrong credentials |
| **Semantic** *(most common & important)* | **facts** about the user / system / task | "What is true about the user and the system?" | user prefers Python; user is a beginner; system uses PostgreSQL; ticket budget is ₹10,000 |
| **Procedural** | strategies, rules, learned behaviors — **how to do things** | "What's the right way to do this for *this* user?" | "avoid sub-queries in SQL"; "if tool X fails, try tool W"; "always explain step by step" |

Procedural memory is what makes an agent feel like it gets **better over time** and adapts
to you.

---

## 10. How Long-Term Memory works — 4 steps

1. **Creation (a.k.a. Update)** — *during* a conversation, decide what is worth remembering
   beyond this conversation. Steps: extract memory candidates from messages / model
   responses / tool outputs → filter out noise, keep the core fact → decide **scope**
   (user-level / app-level / agent-level) → decide whether to **create new**, **update
   existing**, or **ignore**.
2. **Storage** — save the memory in a **durable store** and tag it with identifiers +
   metadata so retrieval is easy later. Must survive restarts/crashes. Store choice depends
   on the memory type: relational DB, key-value store, a log/text file, or a **vector DB**
   for semantic search.
3. **Retrieval** — in a *new* conversation, before replying the model asks "given the current
   situation, what should I recall?" Then it **searches** the store and pulls a **small,
   relevant subset**. Retrieval is **selective, not exhaustive** (unlike STM).
4. **Injection** — **never** let the LLM touch long-term memory directly. Retrieved memory is
   pulled into **short-term memory** (the conversation buffer), becomes part of the context
   window, and reaches the LLM as **just more input tokens** (extra content added to the
   user's prompt by the system).

---

## 11. Engineering challenges & the emerging ecosystem

**Hard parts of building an LTM system:**
1. **Creation** — deciding what's worth remembering out of noisy chat is genuinely difficult.
2. **Retrieval** — figuring out in real time which memories help the current conversation.
3. **Orchestration** — wiring memory stores into an already-complex agentic system (many
   moving parts, hard engineering).

**Managed memory-layer solutions** (do the create/store/retrieve work for you):
- **LangMem** — from the LangChain family; integrates easily with LangGraph.
- **Mem0** — popular managed memory layer for GenAI apps.
- **Supermemory** — founded by a 15-year-old; manages LTM for GenAI apps.

**Research toward intrinsic memory:** Google's **Titans + MIRAGE** line of work explores new
transformer architectures with **built-in intrinsic memory**, so all this external plumbing
would no longer be necessary. Expect this field to grow fast.

---

## TL;DR

- LLM at inference = `y = f_θ(x)`, **stateless** → **no intrinsic memory**.
- Memory must be built **externally** around the LLM.
- **Short-Term Memory** = concatenate the conversation history into the prompt each turn
  (enabled by a large **context window** + **in-context learning**); thread-scoped;
  fragile (→ persistence) and can overflow the context window (→ trimming + summarization).
- **Long-Term Memory** = selective, durable, cross-conversation memory of **episodic**,
  **semantic**, and **procedural** information; works via **create → store → retrieve →
  inject** (always injected *through* STM, never used directly).

**Next:** [02 · Short-Term Memory in LangGraph →](02-short-term-memory-langgraph.md)
