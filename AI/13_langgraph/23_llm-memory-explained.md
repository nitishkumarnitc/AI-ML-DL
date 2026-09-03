# Video 23 — LLMs Don't Have Memory — So How Do They Remember?

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `DcPKJrOF9Wo`
> **Watch:** https://www.youtube.com/watch?v=DcPKJrOF9Wo

## 🎯 Overview
This is a **conceptual, framework-agnostic** deep dive into memory for LLM applications, taught from **first principles** — as if we were inventing memory ourselves. It establishes that an LLM at inference is a stateless mathematical function with no intrinsic memory, yet almost every GenAI app needs memory. It then shows how **context window** + **in-context learning** let us build external memory (short-term memory / a conversation buffer), why short-term memory is fragile and thread-scoped, and finally motivates and defines **long-term memory** (episodic, semantic, procedural) and how it works end-to-end. This video is the theory prerequisite for the hands-on Video 24.

## 🧠 Key Concepts

### An LLM at inference is a parameterized math function
Statement to internalize: *an LLM at inference is just a parameterized math function*, written `y = f_θ(x)`.

- A **parameterized function** produces output that depends on its input **and** on some parameters. Example: `y = a·x²` needs both `x` (from the user) and `a` (from elsewhere).
- Concrete example — **linear regression**: fit `y = m·x + b`; the parameters `m` (slope) and `b` (intercept) are learned **from data** during training.
- For an LLM, `θ` (theta) represents the model's **billions of parameters** (hence "70B" or "100B parameter model"), fixed at training time.
- The three components:
  - `θ` — the (billions of) parameter values, **fixed** after training; the user cannot change them at inference.
  - `x` — the **input tokens** (your prompt); the user **can** change this — which is why different prompts give different outputs.
  - `y` — the **output tokens**, produced from the combination of `θ` and `x`.

### The LLM function is stateless → LLMs have no intrinsic memory
> *A system is stateless if its output depends only on the current input and not on anything that happened before.*

If you send `x1` and get `y1`, then send `x2` and get `y2`, computing `y2` used only `x2` and `θ` — **not** `x1` or `y1`. Every function call is unique and independent of prior calls.

**Demonstrated in code:** invoke the LLM with *"My name is Nitish"* (`x1`) → it replies nicely. Invoke again with *"What is my name?"* (`x2`) → it replies *"I'm sorry, I do not know your name."* This proves the LLM is stateless — it does not remember the previous call.

**Fact 1:** LLMs are stateless at inference, so they have **no intrinsic memory** — they cannot remember past conversations.
**Fact 2:** Almost no GenAI application can function **without** memory (a chatbot with no memory would be highly frustrating). → We are in a deadlock.
**Fact 3 (the escape):** Since LLMs have no built-in memory but we need it, we must **build memory externally** — a system around the LLM that acts like memory.

### Two enabling concepts

**1. Context window.**
> *The context window is the amount of text an LLM can read and remember at one time before answering.*

Analogy: the LLM is a **camera** and the context window is its **lens** — a bigger lens captures more of the scene, a bigger context window processes more text before answering. Modern LLMs have context windows of **128K tokens or more**; some (e.g., Gemini) reach **1 million tokens**. A 128K window can hold roughly a **200-page PDF**. The key takeaway: you can send **a lot** of tokens in `x`, and that power will let us build memory.

**2. In-context learning (ICL).**
> *In-context learning is an emergent ability that lets an LLM use information and patterns present in the prompt itself, in addition to its trained parametric knowledge, to generate an answer.*

During training, the LLM stores knowledge in its parameters — **parametric knowledge**. By default it answers by searching this parametric knowledge. But as models grew, an **emergent phenomenon** appeared: they can also answer using knowledge **hidden inside the prompt**. Example: paste a 100-page private company PDF into the prompt and ask a question about it — the answer isn't in parametric knowledge, but the model reads the PDF from the prompt and answers. That is in-context learning.

### The first-principles solution: a conversation buffer = short-term memory
Combine the two concepts. Every time we invoke the LLM, **concatenate the entire conversation so far into `x`**:

- Turn 1: send `x1` → get `y1` (no prior chat exists).
- Turn 2: instead of `y2 = f_θ(x2)`, send `y2 = f_θ(concat(x1, y1, x2))`.

Why it works: the **context window** is large enough to hold the whole history, and **in-context learning** lets the model read `x1, y1` to answer `x2` (e.g., "What is my name?" → it reads that you said your name is Nitish and replies *"Your name is Nitish."*).

We aren't teaching the LLM to *remember* anything — we just provide **continuity** by re-passing the full conversation every time. The variable holding this history turns a stateless system into a **stateful** one; it is often called a **conversation buffer**. Because it's temporary (restart the program and it's gone), this is called **short-term memory (STM)**.

### How short-term memory is implemented in chatbots (thread scoping)
Chatbots (ChatGPT, Gemini) have the concept of a **conversation** = one session with the bot. STM is **conversation-scoped**: each conversation gets its own short-term memory; outside a conversation it doesn't exist. When you switch to a different conversation, the `messages` buffer is emptied and repopulated with that conversation's messages. A conversation is also called a **thread**, so STM is often described as **thread-scoped** (one thread = one conversation = one STM boundary). This logical boundary keeps the buffer from becoming impossibly long and incoherent across thousands of unrelated conversations.

### Problems with short-term memory

**Problem 1 — STM is fragile.** The `messages` buffer lives in memory, so if the code resets or the server crashes, the entire conversation context is lost. **Solution: persistence** — connect the STM buffer to a **database**. Store each conversation's messages against a **thread ID**; when you return to a conversation, load its messages back from the DB by thread ID so context is not lost. (The instructor notes this is already built in the LangGraph playlist.)

**Problem 2 — the context-window problem.** In a long-running chat, re-sending the full history every turn makes the `messages` list huge. If its token size **exceeds the LLM's context window**, the model stops understanding, gives incoherent replies, or hallucinates. **Solution: two approaches merged:**
- **Trimming** — send only the most recent *n* messages (e.g., last 50 of 500), assuming the relevant context is recent. Risk: you may drop important older context.
- **Summarization** — take the older messages you'd drop, send them to another LLM to generate a **summary**, and send *recent messages + summary* together. The summary is far smaller than the raw messages, so the total stays within the limit while preserving context. This is the most widely accepted solution.

**Problem 3 (most critical) — STM is thread-scoped.** Being thread-scoped is what enables conversation continuity, but it also creates three negatives:
1. **No user continuity between conversations.** Example: in one conversation you tell it you only know Python (not Java), and it complies — but two days later, in a new conversation, it again gives you Java/C++ examples. It cannot remember user preferences across conversations.
2. **Learning never compounds over time.** Effort spent teaching the model (e.g., "write optimized SQL with a window function instead of a subquery") is lost; in a new conversation it reverts to the old, unoptimized approach. It never adapts or evolves with you.
3. **Cross-thread reasoning is impossible.** You can't ask "What did we discuss yesterday?" or "What solution did we land on last time?" — those past conversations are forgotten because STM is thread-bound. Every new conversation, you become a stranger to the LLM again.

The consequence: a true **personal assistant** (which must know its user in and out and evolve with them) is impossible with STM alone, because a user's profile is assembled from **many** conversations (one reveals you like Python, another that you're a developer, another that you like simple explanations, another that you like to travel).

### The solution: long-term memory (LTM)
We need a new kind of memory with two key properties:
1. **Stores special information for a long time** — information whose relevance **survives beyond a single conversation/session** and can stay useful for days or months (e.g., while writing a book over several months). It identifies and stores things like: who the user is (male, Indian, a teacher who teaches AI), how the system should behave for this user, what has worked/failed in the past, and past decisions/processes and their outcomes.
2. **Must be very selective** — don't blindly dump entire chats into memory. Extract only the **stable, useful, reusable** pieces from each conversation and store those; ignore the rest.

Because it lives **outside** any single conversation for a long period (unlike STM, which dies when the conversation ends), we call it **long-term memory**.

### The three types of long-term memory
1. **Episodic memory** — *what happened in the past*. E.g., "last session the user rejected this solution," "these deployment credentials were wrong," "this solution worked / didn't work." Lets the agent answer "What did we do last time? Have we already tried this technique?" and act better in the current conversation.
2. **Semantic memory** (most common, most important) — **facts** about the user and the system. E.g., "user prefers Python," "user is a beginner," "the system uses PostgreSQL," "this booking has a ₹10,000 budget constraint." Facts about what is *true* about the user / system / task.
3. **Procedural memory** — *how to do things*: strategies, rules, and learned behaviors. E.g., "avoid subqueries when solving SQL problems for this user," "if tool X fails, try tool Y," "always explain step by step to this user." This compounds over time and is why an agent starts to *feel* better and more tailored to you.

### How long-term memory works — four steps
1. **Creation / Update.** During a conversation, decide whether anything worth remembering *beyond* this conversation just happened. Inspect user messages, model responses, and (for agents) tool outputs. Sub-steps: extract memory **candidates** (e.g., "I prefer Python over Java"), **filter out noise** to keep the core fact, **decide scope** (user-level / app-level / agent-level tagging), and finally decide to **create new**, **update existing**, or **ignore**.
2. **Storage.** Save the memory in a **durable store** and tag it with **identifiers and metadata** so future retrieval is easy; the goal is for the memory to survive resets/crashes. Store choice depends on the memory type: relational DB, key-value store, a log/text file, or a **vector database** for semantic search.
3. **Retrieval.** In a new conversation, before the model replies it asks "given the current situation, what should I remember right now?" Steps: look at the current user input, decide whether memory is needed, and if so **search** the memory store and pull a **small relevant subset**. Key point: **retrieval is selective, not exhaustive** (unlike STM, which brings everything).
4. **Injection.** Critically, you **never** let the LLM interact with long-term memory directly. The retrieved relevant info is pulled into **short-term memory** (the conversation buffer), becomes part of the context window, and reaches the LLM as just more input tokens. So LTM first becomes part of STM / the prompt, then the model sees it.

### Challenges in building an LTM system
- **Memory creation is hard** — deciding what in a noisy conversation is worth remembering long-term is genuinely difficult.
- **Retrieval is hard** — in real time, figuring out which pieces of the whole LTM store help the current conversation.
- **Orchestration is hard** — you're already building a complex agent; layering the whole memory system (connecting memory stores, many moving parts) on top is engineering-heavy and tricky to run reliably.

### Emerging help
Managed **memory-layer** libraries/platforms now handle the create/store/retrieve work so you can focus on your app: **LangMem** (from the LangChain family, integrates easily with LangGraph), **Mem0**, and **Supermemory** (notably founded by a 15-year-old). This field is growing fast. There is also research toward LLMs with **intrinsic** memory — e.g., the Google research paper **Titans** (and Miras) — building transformer architectures with their own built-in memory so external systems are less necessary.

## 🪜 Step-by-Step Walkthrough (the STM code demo)
1. Create a `messages` list and add the first prompt `x1` = *"My name is Nitish."*
2. `llm.invoke(messages)` → the LLM replies *"Nice to meet you, Nitish."* (`y1`).
3. **Append** `y1` back into `messages` (now it holds `x1`, `y1`).
4. New user prompt `x2` = *"What is my name?"* → append; `messages` now holds `x1, y1, x2`.
5. `llm.invoke(messages)` → now it answers *"Your name is Nitish."* — the buffer supplied continuity.
6. Restart the file → the LLM again fails to recall the name, proving STM is temporary/fragile.

## ⚠️ Gotchas & Tips
- STM works purely by **re-sending the whole conversation** each turn — the LLM itself remembers nothing.
- STM is **fragile**: without persistence, a reset/crash wipes all context. Persist to a DB keyed by **thread ID**.
- Long conversations risk **exceeding the context window** → trim and/or summarize; keep input tokens **well below** the window.
- **Retrieval from LTM must be selective**, not exhaustive — search and pull only relevant pieces.
- **Never** connect LTM directly to the LLM — inject retrieved memory into STM/the prompt first.
- Choose the LTM store by memory type (relational, key-value, log/file, or vector DB for semantic search).
- Consider managed memory layers (LangMem, Mem0, Supermemory) instead of hand-rolling the whole LTM pipeline.

## 📌 Key Takeaways
- An LLM at inference is `y = f_θ(x)`: a **stateless, parameterized** function with **no intrinsic memory**.
- Memory must be built **externally** around the LLM; two enablers make it possible — a **large context window** and **in-context learning**.
- **Short-term memory** = a **conversation buffer**: re-send the full conversation history each turn; it's **thread/conversation-scoped** and **temporary**.
- STM's problems: **fragility** (fix: persistence via DB + thread IDs) and **context-window overflow** (fix: trimming + summarization).
- STM is **thread-scoped**, so no cross-conversation continuity, no compounding learning, no cross-thread reasoning → true personalization is impossible with STM alone.
- **Long-term memory** stores selective, durable info across conversations; its three types are **episodic** (past events), **semantic** (facts), and **procedural** (how-to strategies).
- LTM works in four steps: **creation/update → storage → retrieval (selective) → injection** (always via STM, never directly to the LLM).
- Building LTM is hard (creation, retrieval, orchestration); managed layers like **LangMem, Mem0, Supermemory** help, and research (Google's **Titans**) aims to give LLMs intrinsic memory.
