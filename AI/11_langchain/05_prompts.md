# 05. Prompts in LangChain  (Video 4)

> 📺 [Watch on YouTube](https://www.youtube.com/playlist?list=PLKnIA16_RmvaTbihpo4MtzVm4XOQa0ER0) · ⏱️ ~1h 19m · CampusX — Generative AI using LangChain

---

## 🎯 What You'll Learn

- Why prompts are the **primary control surface** of an LLM app, and why an LLM's output can swing wildly on tiny wording changes (prompt sensitivity).
- The difference between **static** prompts (hardcoded / f-string) and **dynamic** prompts, and the three concrete things templates buy you: validation, reuse, and safety.
- **`PromptTemplate`** in depth — `template`, `input_variables`, `.invoke()`, `from_template()`, `validate_template=True`, and `partial_variables`.
- The three **message types** — `SystemMessage`, `HumanMessage`, `AIMessage` — the roles they map to, and how a chat model consumes a *list* of messages.
- Building a **CLI chatbot** that keeps a `chat_history` list so the model has memory of the conversation across turns.
- **`ChatPromptTemplate`** built from `(role, template)` tuples via `from_messages`, and the classic gotcha that trips people up.
- **`MessagesPlaceholder`** for injecting a variable-length chat history into a chat prompt.
- Persisting prompts to disk with `prompt.save(...)` and reloading them with `load_prompt(...)`.
- How prompts **compose with models** into a chain via the pipe (`|`) operator — the bridge into the LCEL / chains chapter.

---

## 📖 Overview / Why It Matters

A **prompt** is the input you send to an LLM. It sounds trivial, but it is the single most important lever you have: the same model, given two slightly different prompts, can produce dramatically different answers. This is called **prompt sensitivity** — swap "explain" for "summarize", or add "in one line", and the output changes character completely. Because the prompt is where almost all of your application's behavior lives, LangChain treats prompt construction as a first-class, structured component rather than "just a string".

Where this sits in the LangChain picture:

```
Prompt (this video)  →  Model  →  Output Parser
        │                                 │
        └────────────── chain ────────────┘   (composed with the | pipe operator)
```

Two broad categories of prompt come up:

- **Static prompt** — a fixed string you (or the user) hand to the model as-is.
- **Dynamic prompt** — a *template* with placeholders that get filled in at runtime from variables.

The whole point of this chapter is that you should almost never build a real prompt by string-concatenation or f-strings around user input. Instead you use LangChain's **prompt template** classes, which give you validation, reusability, and a clean separation between the *shape* of the prompt and the *data* that fills it.

---

## 🧠 Key Concepts

### Static vs dynamic prompts — why not just use an f-string?

Imagine a "research assistant" UI where the user picks a paper, an explanation style, and a length, and clicks *Summarize*. The naive approach is to interpolate those choices straight into a string:

```python
# ❌ fragile: raw f-string around user-controlled input
prompt = f"Summarize the paper {paper} in a {style} style of length {length}."
response = model.invoke(prompt)
```

This "works" but is brittle for three reasons, and those three reasons are exactly what prompt templates fix:

1. **Validation.** With an f-string, nothing stops you from forgetting a variable, misspelling one, or passing an extra one — you find out only when the output is wrong. A template with declared `input_variables` (and `validate_template=True`) catches a mismatch *at construction time*, before you ever call the (paid) model.
2. **Reusability.** A template is a named object you define once and reuse across your codebase, load from a file, share with teammates, or version-control independently of the calling code. An inline f-string is copy-pasted everywhere and drifts out of sync.
3. **Safety / structure.** Templates keep the fixed instruction text separate from the variable data, so you always know which parts are "your" instructions and which parts are user-supplied. This structure is also what lets prompts compose cleanly with models and parsers into a chain.

The rule of thumb: **the fixed scaffolding of the prompt is code; the values that fill it are data.** Prompt templates enforce that separation.

### `PromptTemplate` — dynamic text prompts

`PromptTemplate` is the class for building a single dynamic *string* prompt (as opposed to a list of chat messages). It lives in `langchain_core.prompts`:

```python
from langchain_core.prompts import PromptTemplate
```

Its two core pieces are:

- **`template`** — the string, with placeholders written in single curly braces: `{paper}`, `{style}`, `{length}`.
- **`input_variables`** — the list of placeholder names the template expects, e.g. `["paper", "style", "length"]`.

You render it by calling **`.invoke({...})`** with a dict mapping each variable to a value. `.invoke()` returns a `PromptValue` (specifically a `StringPromptValue`), not a bare string — that wrapper is what lets a prompt slot directly into a chain in front of a model.

**`from_template()`** is a convenience constructor: pass just the template string and LangChain parses the `{...}` placeholders and infers `input_variables` for you — less boilerplate, and no chance of the `input_variables` list drifting out of sync with the text.

**`validate_template=True`** turns on a consistency check: LangChain compares the variables it finds inside the template string against the `input_variables` you declared and raises if they disagree. This is the "catch the bug before you spend money on an API call" safeguard.

**`partial_variables`** lets you pre-fill *some* variables now and leave the rest for later. Common use: a value that is fixed for a given deployment (a format instruction, today's date, a fixed style) is baked in as a partial, so callers only supply the truly dynamic fields. `partial_variables` takes a dict and can be set at construction time or via `.partial(...)`.

### Message types — `SystemMessage`, `HumanMessage`, `AIMessage`

Text `PromptTemplate`s are fine for single-shot completions, but *chat* models think in terms of a **list of messages**, each tagged with a **role**. LangChain models these with three classes from `langchain_core.messages`:

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
```

| Message | Role | Purpose |
|---|---|---|
| `SystemMessage` | `system` | High-level instructions / persona that set the model's behavior for the whole conversation. Usually the first message. |
| `HumanMessage` | `human` (user) | What the user says. |
| `AIMessage` | `ai` (assistant) | What the model previously replied. You append these back into the list so the model can "see" its own prior turns. |

A chat model's `.invoke(...)` accepts a *list* of these messages and returns a single `AIMessage`. The system message sets the stage; the human and AI messages form the running transcript.

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI()
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Tell me about LangChain."),
]
result = model.invoke(messages)   # -> AIMessage
print(result.content)
```

### Keeping context — a CLI chatbot with `chat_history`

An LLM call is **stateless**: each `invoke` is independent, so if you only ever send the latest user message, the bot forgets everything said before. The fix is to maintain a **`chat_history`** list and send the *whole* list every turn. After each exchange you append the user's `HumanMessage` and the model's `AIMessage` back into the list, so the next call carries the full context.

This is the single most important idea for building a conversational bot, and it's just a Python list:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

model = ChatOpenAI()

chat_history = [
    SystemMessage(content="You are a helpful assistant."),
]

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    chat_history.append(HumanMessage(content=user_input))   # remember what the user said
    result = model.invoke(chat_history)                     # send the ENTIRE history
    chat_history.append(AIMessage(content=result.content))  # remember what the AI replied
    print("AI:", result.content)

print(chat_history)   # full transcript, correctly role-tagged
```

Without the two `append` lines, the model would answer every question in a vacuum. With them, you can ask a follow-up ("and its second point?") and the model resolves the reference because the earlier turns are still in the list.

### `ChatPromptTemplate` — dynamic *chat* prompts

`PromptTemplate` templatizes a single string; **`ChatPromptTemplate`** templatizes a *list of messages*, each of which can itself contain placeholders. It lives in `langchain_core.prompts`:

```python
from langchain_core.prompts import ChatPromptTemplate
```

You build it with `from_messages`, passing a list of **`(role, template)` tuples**:

```python
chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful {domain} expert."),
    ("human", "Explain in simple terms, what is {topic}?"),
])

messages = chat_template.invoke({"domain": "cricket", "topic": "LBW"})
# -> a list of a SystemMessage and a HumanMessage, with placeholders filled
```

The roles are the string tags `"system"`, `"human"`, and `"ai"`, mirroring the three message classes. Calling `.invoke()` returns a fully-rendered list of message objects ready to feed to a chat model.

> **⚠️ The classic gotcha.** It is tempting to write the messages as *actual message objects* with placeholders in the `content`, like `SystemMessage(content="You are a {domain} expert")`. Historically this did **not** substitute the placeholder reliably — the `{domain}` came out literally. The robust, recommended form is the **`(role, template)` tuple** style shown above (or plain 2-tuples inside `from_messages`). Stick to tuples for placeholder-bearing chat templates and let `from_messages` do the parsing.

### `MessagesPlaceholder` — injecting a whole history block

`ChatPromptTemplate` with fixed tuples works when you know exactly which messages exist. But a chatbot's history is **variable-length** — you don't know in advance how many prior turns there are. `MessagesPlaceholder` reserves a slot in the template that you later fill with an *entire list of messages*:

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful customer support agent."),
    MessagesPlaceholder(variable_name="chat_history"),   # <- variable-length block
    ("human", "{query}"),
])
```

At render time you pass the placeholder's `variable_name` a list of message objects (loaded from a file, a database, or an in-memory list), and it expands in place:

```python
# load past conversation, e.g. from a file, into a list of messages
chat_history = []
with open("chat_history.txt") as f:
    for line in f:
        # (toy example) reconstruct HumanMessage / AIMessage from persisted text
        chat_history.append(HumanMessage(content=line.strip()))

prompt = chat_template.invoke({
    "chat_history": chat_history,     # the whole history block gets injected here
    "query": "Where is my refund?",
})
```

This is the standard pattern for giving a chatbot long-term memory: persist the running `chat_history`, then splice it back in via a `MessagesPlaceholder` on the next request.

### Saving & loading prompts

Because a template is a real object, you can serialize it and load it back — handy for versioning prompts, sharing them, or storing a library of prompts separately from code:

```python
# save the template to disk
template.save("template.json")

# later / elsewhere — reload it
from langchain_core.prompts import load_prompt
template = load_prompt("template.json")
```

The saved JSON captures the template string, the `input_variables`, and the type, so the reloaded object behaves identically.

### Prompts compose with models — the pipe operator

The payoff of making prompts first-class objects is **composition**. A prompt template and a model can be joined with the pipe (`|`) operator into a **chain**, so you invoke the whole pipeline in one call instead of manually rendering the prompt and then passing it to the model:

```python
chain = template | model            # prompt -> model
result = chain.invoke({"paper": "Attention Is All You Need",
                       "style": "beginner-friendly",
                       "length": "short"})
print(result.content)
```

Under the hood, `template.invoke(...)` produces a `PromptValue`, which flows straight into `model.invoke(...)`. This `|` composition is the heart of LCEL and is covered in depth in the chains notes — see [08_chains.md](08_chains.md).

---

## 💻 Code Examples

### 1. A dynamic `PromptTemplate` (the research-summarizer)

```python
from langchain_core.prompts import PromptTemplate

template = PromptTemplate(
    template=(
        "Summarize the research paper titled \"{paper}\" "
        "in a {style} explanation style, of length {length}."
    ),
    input_variables=["paper", "style", "length"],
    validate_template=True,   # verify placeholders match input_variables at build time
)

prompt = template.invoke({
    "paper": "Attention Is All You Need",
    "style": "beginner-friendly",
    "length": "3-4 lines",
})
print(prompt.to_string())
```

### 2. `from_template()` — less boilerplate

```python
from langchain_core.prompts import PromptTemplate

# input_variables are inferred from the {placeholders} in the string
template = PromptTemplate.from_template(
    "Explain {topic} to a {audience} in {length}."
)
print(template.input_variables)   # ['topic', 'audience', 'length']
```

### 3. `partial_variables` — pre-filling some values

```python
from langchain_core.prompts import PromptTemplate

template = PromptTemplate(
    template="Write a {tone} tweet about {topic}. Sign it as {author}.",
    input_variables=["tone", "topic"],
    partial_variables={"author": "@campusx"},   # baked in now
)

# caller only supplies the still-dynamic fields
prompt = template.invoke({"tone": "witty", "topic": "LangChain"})
print(prompt.to_string())
```

### 4. Feeding a message list to a chat model

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

model = ChatOpenAI(temperature=0.7)

messages = [
    SystemMessage(content="You are an expert Python tutor. Be concise."),
    HumanMessage(content="What is a decorator?"),
]
reply = model.invoke(messages)         # -> AIMessage
messages.append(AIMessage(content=reply.content))
print(reply.content)
```

### 5. CLI chatbot with persistent `chat_history`

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

model = ChatOpenAI()
chat_history = [SystemMessage(content="You are a helpful assistant.")]

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    chat_history.append(HumanMessage(content=user_input))
    result = model.invoke(chat_history)          # full context every turn
    chat_history.append(AIMessage(content=result.content))
    print("AI:", result.content)
```

### 6. `ChatPromptTemplate` from `(role, template)` tuples

```python
from langchain_core.prompts import ChatPromptTemplate

chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful {domain} expert."),
    ("human", "Explain in simple terms: what is {topic}?"),
])

prompt = chat_template.invoke({"domain": "finance", "topic": "an ETF"})
for msg in prompt.to_messages():
    print(type(msg).__name__, "->", msg.content)
```

### 7. `MessagesPlaceholder` for variable-length history

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

chat_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful customer support agent."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{query}"),
])

chat_history = [
    HumanMessage(content="I want to return an order."),
    AIMessage(content="Sure — could you share your order ID?"),
]

prompt = chat_template.invoke({
    "chat_history": chat_history,
    "query": "It's #A1234, still no refund.",
})
print(prompt.to_messages())   # system + 2 history msgs + latest human
```

### 8. Save and load a prompt

```python
from langchain_core.prompts import PromptTemplate, load_prompt

template = PromptTemplate.from_template("Translate to {language}: {text}")
template.save("translate_prompt.json")

reloaded = load_prompt("translate_prompt.json")
print(reloaded.invoke({"language": "French", "text": "Good morning"}).to_string())
```

### 9. Compose prompt + model into a chain

```python
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

template = PromptTemplate.from_template("Give me 3 catchy names for a {product} startup.")
model = ChatOpenAI()

chain = template | model                       # the pipe = a chain
result = chain.invoke({"product": "coffee subscription"})
print(result.content)
```

---

## 📊 PromptTemplate vs ChatPromptTemplate vs MessagesPlaceholder

```mermaid
flowchart TD
    A[Need to build a prompt] --> B{Single string<br/>or chat messages?}
    B -->|Single string,<br/>completion-style| C[PromptTemplate]
    B -->|List of role-tagged<br/>chat messages| D[ChatPromptTemplate.from_messages]
    D --> E{History is<br/>variable-length?}
    E -->|No, fixed set of turns| F[Use (role, template) tuples only]
    E -->|Yes, inject a whole list| G[Add MessagesPlaceholder<br/>variable_name=chat_history]
```

| Feature | `PromptTemplate` | `ChatPromptTemplate` | `MessagesPlaceholder` |
|---|---|---|---|
| Import | `langchain_core.prompts` | `langchain_core.prompts` | `langchain_core.prompts` |
| Produces | one string (`StringPromptValue`) | a list of chat messages | (not standalone) a slot inside a `ChatPromptTemplate` |
| Best for | single-shot completion prompts | chat models with system/human/ai roles | injecting a variable-length history block |
| Built from | `template` + `input_variables` | list of `(role, template)` tuples via `from_messages` | `variable_name="..."` |
| Fill at runtime | `.invoke({...})` | `.invoke({...})` | pass a list of message objects to its `variable_name` |
| Key extras | `from_template()`, `validate_template`, `partial_variables` | tuple form avoids placeholder bugs | expands to as many messages as you pass |

---

## ⚠️ Gotchas & Tips

- **Never f-string raw user input into a prompt.** You lose validation, reuse, and the clean instruction/data separation. Use a template with declared `input_variables`.
- **Use tuples, not Message objects, for placeholder-bearing chat templates.** `ChatPromptTemplate.from_messages([("system", "You are a {domain} expert"), ...])` substitutes reliably; putting `{placeholders}` inside a raw `SystemMessage(content=...)` has historically failed to interpolate. When in doubt, use the `(role, template)` tuple form.
- **`.invoke()` returns a `PromptValue`, not a `str`.** Call `.to_string()` (text) or `.to_messages()` (chat) to inspect it. The `PromptValue` wrapper is exactly what lets the prompt pipe into a model.
- **Turn on `validate_template=True`.** It catches a mismatch between the placeholders in the string and your `input_variables` at build time — before you spend money on an API call.
- **A chatbot without `chat_history` has amnesia.** The model is stateless; you must append each `HumanMessage`/`AIMessage` and resend the whole list, or use a `MessagesPlaceholder`-backed template, to preserve context.
- **Distinguish roles correctly.** `SystemMessage` sets behavior for the whole session, `HumanMessage` is the user, `AIMessage` is a *prior model reply* you feed back in. Mixing these up (e.g. logging the model's answer as a `HumanMessage`) corrupts the model's view of who said what.
- **`temperature` controls randomness/creativity.** It usually ranges ~0–2. Low values (e.g. `0`–`0.3`) make output more deterministic and focused — good for factual, extraction, or code tasks. Higher values (e.g. `0.7`–`1.0+`) make it more diverse and creative — good for brainstorming or copywriting — at the cost of consistency. `temperature=0` gives the most repeatable results.
- **`partial_variables` is great for "fixed-for-this-deployment" values** (format instructions, a fixed persona, today's date) so callers only pass the truly dynamic fields.
- **Prompts are `Runnable`s.** That's why `template | model | parser` works. Everything you build here plugs straight into LCEL chains — see [08_chains.md](08_chains.md).

---

## 🧠 Key Takeaways

- The **prompt is the main control surface** of an LLM app; because of **prompt sensitivity**, small wording changes can drastically change output — so treat prompts as structured, versioned components, not throwaway strings.
- **Dynamic prompts via templates beat f-strings** on three axes: **validation** (catch bad/missing variables early), **reuse** (define once, load/share/version), and **safety** (fixed instructions kept separate from variable data).
- **`PromptTemplate`** builds a single dynamic string from a `template` + `input_variables`; `from_template()` infers the variables, `validate_template=True` guards them, and `partial_variables` pre-fills some of them.
- Chat models consume a **list of role-tagged messages** — `SystemMessage` (persona/instructions), `HumanMessage` (user), `AIMessage` (prior model reply) — and return an `AIMessage`.
- A chatbot needs a **`chat_history` list**: append each human and AI turn and resend the whole list, because each LLM call is stateless.
- **`ChatPromptTemplate.from_messages([...])`** templatizes a message list; build it from **`(role, template)` tuples**, not raw Message objects, to avoid the placeholder-substitution gotcha.
- **`MessagesPlaceholder(variable_name="chat_history")`** reserves a slot for a **variable-length** block of past messages, the standard way to give a chatbot memory.
- Prompts **persist** via `prompt.save("file.json")` and reload via `load_prompt("file.json")`.
- Prompts **compose with models** through the `|` pipe operator into a chain — the bridge into [08_chains.md](08_chains.md).
- **`temperature`** trades determinism for creativity: low for factual/consistent output, high for diverse/creative output.

---

## ❓ Revision Questions

1. What is "prompt sensitivity", and why does it make prompt design the most important part of an LLM application?
2. Give three concrete advantages of a `PromptTemplate` over building a prompt with a raw Python f-string around user input.
3. What does `validate_template=True` do, and at what point in the program's lifecycle does it help you?
4. When would you reach for `from_template()` instead of the full `PromptTemplate(...)` constructor? What does it save you from getting wrong?
5. What are `partial_variables` used for? Give a realistic example of a value you'd bake in as a partial.
6. Name the three message types, the role each maps to, and explain specifically why you feed prior `AIMessage`s back into the conversation.
7. In the CLI chatbot, what breaks if you remove the two lines that append messages to `chat_history`? Why?
8. What is the recommended way to build a `ChatPromptTemplate` that contains placeholders, and what is the classic mistake that fails to substitute them?
9. What problem does `MessagesPlaceholder` solve that a fixed list of `(role, template)` tuples cannot? What do you pass to its `variable_name` at runtime?
10. How do a prompt and a model combine into a chain, and what does the `temperature` parameter control in the model's output?
