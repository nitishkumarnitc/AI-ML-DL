# 11 · Tracing a ReAct Agent

> ← [`10-index-persistence-and-latency.md`](10-index-persistence-and-latency.md) · **Next:** [`12-tracing-langgraph.md`](12-tracing-langgraph.md) →

---

Agents are where observability stops being convenient and becomes mandatory. A chain has a shape you wrote down; an **agent decides its own control flow at runtime**. You cannot read the code and know what will happen, because what happens depends on what a model decided mid-run.

The trace is the only record of what it decided.

---

## The agent

A ReAct agent with two tools:

| Tool | Does |
|---|---|
| `duckduckgo_search` | Web search |
| `get_weather_data` | Calls a weather API for a city |

**ReAct** = *Reason + Act*. The loop:

```
Thought:       what should I do next?
Action:        which tool
Action Input:  with what arguments
Observation:   what the tool returned
   └──────────► back to Thought, with the observation appended
                until the model emits a Final Answer
```

The mechanism that makes this work is the **agent scratchpad**: a growing text buffer holding the whole Thought/Action/Observation history. It starts empty and is re-inserted into the prompt on every iteration. **The agent has no memory other than this string.**

---

## Query 1 — one tool

```
Q: What is the release date of Dhadak 2?
A: Dhadak 2 is set to hit theatres on August 26, 2025.
```

The video's author notes immediately that this is **probably wrong** — the film had already released. Keep that; it's the most instructive moment in the section. The agent executed flawlessly and returned a wrong fact, because a search result said so. **Tracing gives you provenance, not truth.** You can see exactly which snippet the model believed. What you do about a wrong snippet is a retrieval-quality and grounding problem, not an observability one.

### The trace, collapsed

Three top-level components:

```
AgentExecutor
├── agent_scratchpad initialised   (empty)
├── ChatPromptTemplate            ← the ReAct prompt
└── … the loop …
```

### The trace, expanded

**Iteration 1 — build the prompt**

```
Answer the following questions as best you can.
You have access to the following tools:

  duckduckgo_search: …
  get_weather_data:  …

Use the format:
  Thought: …
  Action: the action to take, one of [duckduckgo_search, get_weather_data]
  Action Input: …
  Observation: …
  … (repeat) …
  Thought: I now know the final answer
  Final Answer: …

Question: What is the release date of Dhadak 2?
{agent_scratchpad}          ← empty on the first pass
```

**Iteration 1 — the model decides**

```
Thought:      I should use DuckDuckGo search.
Action:       duckduckgo_search
Action Input: Dhadak 2 release date
```

**Iteration 1 — the tool runs.** Search executes; its output is the `Observation`.

**Iteration 2 — scratchpad grows.** Thought + Action + Action Input + Observation are appended, the prompt is **rebuilt with the fuller scratchpad**, and sent again.

**Iteration 2 — the model finishes**

```
Thought:      I now know the final answer.
Final Answer: Dhadak 2 is set to hit theatres on August 26, 2025.
```

→ `AgentFinish`.

> **What the trace makes visible, and nothing else does:** that the prompt is **rebuilt from scratch on every iteration** with a longer scratchpad. This is the mechanical fact behind two things people find mysterious about agents:
>
> - **Cost grows superlinearly in iterations.** Iteration *n* re-sends everything from iterations 1…*n−1*. Five iterations is not 5× one iteration; it's closer to 15× in input tokens. This is *exactly* Story B from lesson 01 — the perfectionist loop was expensive because each retry re-sent a bigger scratchpad.
> - **Long agent runs degrade.** The scratchpad eventually crowds the context window and early observations get truncated or lost in the middle.

---

## Query 2 — the other tool

```
Q: What is the current temperature of Gurgaon?
A: The current temperature of Gurgaon is 30 °C.
```

Trace: scratchpad initialised → prompt built → model chooses `get_weather_data` with `Action Input: Gurgaon` → tool called → the API returns much more than temperature (humidity, wind speed, and the rest) → **all of it recorded** → appended to the scratchpad → prompt rebuilt → Final Answer.

> **Note what "all of it recorded" implies.** The full tool response is in the trace *and* in the scratchpad, which means it's in the next prompt, which means you paid input tokens for humidity and wind speed you never used. Seeing the raw tool payload in a trace is often the moment you realise your tool should return a projection, not everything the API sends. **Trim tool outputs at the tool, not at the prompt.**

---

## Query 3 — two tools, chained

```
Q: Identify the birthplace of Kalpana Chawla, then give its current temperature.
```

This forces a genuine two-step plan, where step 2's input is step 1's output.

```
Iteration 1
  Thought:      First I need to search for Kalpana Chawla's birthplace,
                then get the current temperature of that city.
  Action:       duckduckgo_search
  Action Input: Kalpana Chawla birth place city
  Observation:  … lots of biographical text, several names …

Iteration 2
  Thought:      Now that we know the birthplace city is Karnal,
                we can get the current temperature of Karnal.
  Action:       get_weather_data
  Action Input: Karnal
  Observation:  … full weather payload …

Iteration 3
  Thought:      I now know the final answer.
  Final Answer: The current temperature in Karnal is 27 °C.
  → AgentFinish
```

**This is the trace shape that matters.** You can see the model extract `Karnal` from a wall of search text and feed it as the next tool's argument. That extraction is the step that fails most often in real agents — and it fails *silently*, producing a confident answer about the wrong city.

Which is precisely what happened on camera: the first attempt returned Gurgaon. The author diagnosed it as his own mistake (he ran the previous question without pasting the new one) and re-ran. But note the failure signature — a plausible answer about a city nobody asked about. **Without the trace, "27 °C in Karnal" and "30 °C in Gurgaon" are equally believable outputs.** With the trace, you see which city the model extracted and where it got it.

---

## What agent tracing buys you

| Question | Answered by |
|---|---|
| Which tools did it call, in what order? | The run sequence |
| What arguments did it pass? | Each tool run's input |
| What did each tool return? | Each tool run's output |
| Why did it choose that tool? | The `Thought` preceding the `Action` |
| How did step *n*'s output become step *n+1*'s input? | The growing scratchpad |
| Why did it stop? | `AgentFinish`, or hitting the iteration limit |
| Why was this run expensive? | Iteration count × per-iteration token growth |

The author's own practice, stated in the video: **always integrate LangSmith when building agents or complex graphs** — not only for debugging, but as a **learning tool** for understanding how the thing actually executes. That is not a throwaway line. Reading a ReAct trace is the fastest way anyone learns what ReAct really is.

---

## ⭐ Beyond the video — the four agent failure modes and their trace signatures

*Added. Agents fail in recognisable patterns; each has a distinctive shape in the trace.*

| Failure | Trace signature | Fix |
|---|---|---|
| **Runaway loop** (Story B) | The same Action + Action Input repeated with near-identical Observations; token count climbing per iteration | Cap `max_iterations`; add a loop-detector that halts on repeated (action, input) pairs; reword any "keep going until perfect" instruction |
| **Wrong tool chosen** | `Thought` shows the model misreading intent; a plausible but irrelevant tool fires | Sharpen tool **descriptions** — the description is the only thing the model sees. Reduce the tool count; overlapping tools cause coin-flips |
| **Malformed tool input** | Tool run's input is wrong-shaped; Observation is an error string; the agent then flails | Type the arguments (Pydantic schemas); return a *helpful* error the agent can recover from, not a stack trace |
| **Bad extraction between steps** (Query 3) | Step *n+1*'s Action Input doesn't match what step *n*'s Observation actually said | Add an explicit extraction step with structured output instead of relying on the scratchpad |

### Two guardrails to set before you deploy any agent

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=6,              # hard stop on loops
    max_execution_time=60,         # hard stop on wall clock
    handle_parsing_errors=True,    # recover from malformed LLM output
    return_intermediate_steps=True,
)
```

`max_iterations` is the direct structural fix for Story B. A prompt asking for perfection can loop forever; an executor with a ceiling cannot. **Observability tells you the loop happened; the ceiling stops it costing ₹2 while you find out.** You want both — and this is the general shape of the relationship: tracing is diagnosis, limits are containment. Neither substitutes for the other.

### A monitoring rule worth writing

Once you have lesson 13's alerting: **alert on iteration count, not just on cost.** Cost per trace is noisy because questions differ in length. Iteration count is a much cleaner signal that behaviour changed — if your agent's p95 iteration count moves from 2 to 5 after a deploy, you shipped Story B, and you'll know within the hour instead of at the end of the billing month.

---

## Recap

- Agents choose their control flow at runtime; the trace is the only record of what they chose.
- The **scratchpad** is the agent's entire memory, and the prompt is **rebuilt from it every iteration** — which is why cost grows superlinearly and long runs degrade.
- The trace shows the full Thought → Action → Action Input → Observation loop, plus `AgentFinish`.
- A correct trace can still hold a wrong answer: **tracing gives provenance, not truth.**
- Raw tool payloads in the trace reveal tokens you're paying for and not using. Trim at the tool.
- Four failure modes with distinct signatures: runaway loop · wrong tool · malformed input · bad inter-step extraction.
- Set `max_iterations` and `max_execution_time` before deploying. **Tracing is diagnosis; limits are containment.**
- Alert on **iteration count** — a cleaner behavioural signal than cost.

---

## Self-check

1. Explain why a 5-iteration agent run costs far more than 5× a 1-iteration run.
2. The agent returned a confident answer about a city nobody mentioned. Which two trace fields localise the mistake?
3. Your agent picks the wrong tool. Which artefact do you edit, and why is it the only lever the model actually sees?
4. Why is iteration count a better alerting metric than cost per trace?

---

**Next:** [`12-tracing-langgraph.md`](12-tracing-langgraph.md) →
