# 01 · Why LLM Applications Need Observability

> **Source:** *LangSmith Crash Course — Observability in GenAI* (CampusX, Nitish) · [`4FFspU4riHk`](https://www.youtube.com/watch?v=4FFspU4riHk) · ~2 h 08 m
> **Next:** [`02-what-langsmith-is-and-what-it-records.md`](02-what-langsmith-is-and-what-it-records.md) →

---

## The one-line thesis

You can build an LLM application with nothing but LangChain. You cannot **operate** one that way — because when it breaks, the ordinary debugging reflexes (read the stack trace, reproduce the bug, add a print statement) all fail at once.

This lesson is the argument for why. It is built around three concrete failure stories, each of which fails for a *different* reason, and each of which is undebuggable with the tools you already have.

---

## 1. The three failure stories

### Story A — Latency: the cover-letter tailor

**The product.** A startup notices that job-hunting graduates repeat the same loop 10–20 times a day: browse a job board, filter, pick a role, read the job description, hand-edit their résumé and cover letter to match, apply. Nobody wants to send the *same* cover letter to twenty employers — you want the employer to feel you made an effort. So the team ships a tool:

```
Student pastes a JD link (or uploads the JD as a PDF)
   │
   ├─ 1. Read and understand the JD                      ← LLM call
   ├─ 2. Fetch the student's portfolio, résumé, project   ← Google Drive I/O
   │       write-ups from their Google Drive
   ├─ 3. Score the match: which of this student's skills  ← LLM call
   │       are relevant to *this* posting?
   ├─ 4. Write a cover letter targeted at this JD         ← LLM call
   └─ 5. Proof-read it: is the tone right? Would this     ← LLM call
           letter actually convert?
   │
   └─> tailored cover letter
```

Students love it. Daily active usage is healthy. End-to-end latency sits at **~2 minutes**, which nobody minds for a task that used to take 20.

**The break.** One morning the support inbox fills up: *the site has become very slow*. The same request now takes **7–10 minutes**. Users get impatient and churn. For a startup, that is revenue walking out of the door.

**Why you cannot debug it.** You know exactly three things:

| You know | You do not know |
|---|---|
| What the user submitted | How long stage 1 took |
| What the tool returned | How long stage 2 took |
| That the whole thing took 9 minutes | …or 3, or 4, or 5 |

There are eight extra minutes somewhere and **no per-stage breakdown**. Was it the JD read? The Drive fetch? The proof-reading pass?

The actual cause, in this story, is a bad push: a code change made stage 2 scan the *entire* Google Drive rather than one designated folder. That is a completely findable bug — *if* you can see that stage 2 went from 6 seconds to 8 minutes. Without that, you are reading diffs and guessing.

> **The generalisable point:** a multi-stage LLM workflow gives you *aggregate* latency for free and *component* latency never. Aggregate latency tells you a problem exists. Only component latency tells you where.

---

### Story B — Cost: the research assistant

**The product.** An autonomous agent for researchers. You give it a topic — say *solar energy* — and it:

1. Fetches related academic papers from Google Scholar / arXiv,
2. Reads each paper and extracts key points,
3. Summarises all the key points into a single report,
4. Lets you chat with that report afterwards, ChatGPT-style.

Cost per report is **~50 paise** in API tokens. You charge users enough to be comfortably profitable. Business is fine.

**The break.** The OpenAI dashboard shows cost climbing. Broken down: *most* reports still cost 50 paise, but **some cost ₹2** — a 4× blow-up. At any real user count, that eats the margin in weeks.

**The cause.** The last release changed *one or two sentences* of a prompt. Someone wrote, in effect, **"keep generating until the report is genuinely the best it can be."** The intent was good — better user experience, higher-quality output. The effect was that the agent's self-critique step started rejecting its own work:

```
plan → search → read → summarise → self-critique
                  ▲                      │
                  └──── "not good enough, redo" ────┘
```

For most topics the agent accepts its first draft. For certain topics it loops — re-downloading papers, re-reading, re-summarising, re-critiquing. The agent has, in Nitish's phrase, *become a perfectionist*. Perfectionism is expensive.

**Why you cannot debug it.** This is worse than Story A on three counts:

| Property | Consequence for debugging |
|---|---|
| **Intermittent** — same code, some runs cheap, some expensive | You cannot reliably reproduce it |
| **Not an error** — nothing crashed, nothing threw | There is no stack trace, nothing in your error log |
| **Multi-stage** | Even knowing cost went up, you cannot attribute it to a stage |

Nothing is *broken*. The code did exactly what the prompt asked. You are hunting a behavioural change caused by natural-language instructions, and your tooling logs exceptions.

> **The generalisable point:** in an agentic system, **a prompt edit is a control-flow change.** A sentence added for quality reasons silently rewired a loop. If your diff review treats prompts as copy rather than code, you will ship these.

---

### Story C — Correctness: the HR policy chatbot

**The product.** You are a senior developer at a very large IT services company. Thousands of freshers join every year, and every one of them asks HR the same questions: *What is the leave policy? What is the notice period? How does health insurance work?* HR is drowning in repeat questions and their productivity is suffering.

So you build a RAG chatbot over the company's policy documents:

```
Fresher's question
   │
   ├─ Retriever  → search the knowledge base → relevant policy chunks
   │
   └─ Generator  → LLM(question + chunks) → natural-language answer
```

It works. Freshers self-serve. HR gets their time back.

**The break.** Your teammates report the bot is **hallucinating**. Concretely: an employee asked about the leave policy and was told there was effectively no limit — *take leave whenever you like, go to Goa*. The employee packed a bag and went. Whose fault is that? The company's chatbot said so.

Now scale the thought. The same failure mode applied to **notice period** or **salary** questions is not a funny anecdote; it is misinformation propagating through the company with your team's name on it.

**Why you cannot debug it.** A RAG system hallucinates for one of exactly two reasons, and the fixes are unrelated:

| Failure point | What went wrong | Realistic cause | Fix |
|---|---|---|---|
| **Retriever** | Fetched irrelevant or insufficient chunks | Someone set `k = 1` in the last release. One chunk is enough for some questions, nowhere near enough for others | Raise `k`, re-rank, better chunking, hybrid search |
| **Generator** | Right chunks retrieved, LLM invented anyway | The grounding instruction is too **lenient** — it doesn't forcefully say *answer only from context; if the context is insufficient, say you don't know*. Or the model was swapped for a weaker/cheaper one | Tighten the prompt, change model, add a citation requirement |

You have the question. You have the bad answer. **You do not have the retrieved chunks, and you do not have the assembled prompt.** So you cannot tell which of the two boxes failed — which means you cannot tell which of two unrelated fixes to apply. You are 50/50 guessing, and each wrong guess is a release cycle.

> **The generalisable point:** in a pipeline, a bad final output localises to *nothing*. The intermediate values are the diagnosis. RAG has two failure points with disjoint remedies, so **the intermediate context is not a nice-to-have; it is the entire diagnostic signal.**

---

## 2. What the three stories have in common

Three different symptoms — slow, expensive, wrong. Three different architectures — a linear workflow, an autonomous agent, a retrieval pipeline. One shared root cause:

### LLM systems are non-deterministic

Take any ordinary piece of software. A calculator: multiply 2 × 4, get 8. Do it a thousand times, get 8 a thousand times. Same input, same output, always. That property is what makes conventional debugging work — you reproduce the bug, then you bisect it.

An LLM breaks that property. The same input can produce different outputs across calls. Which cascades:

| Property of LLM systems | What it costs you |
|---|---|
| **Non-deterministic outputs** | Bugs are not reliably reproducible |
| **Failures are behavioural, not exceptional** | No stack trace, no error log entry, nothing crashes |
| **Composed of many stages** | Aggregate metrics cannot be attributed |
| **The model is a black box** | No explainability for *why* it chose that action |
| **Natural language is the control surface** | Prompt edits change behaviour without changing code structure |

Every conventional instinct — reproduce it, read the trace, print-debug the branch — assumes properties that LLM systems do not have.

### The needed capability, stated precisely

> Turn the black box into a **white box**: run the application, record what every component received and produced, and inspect it afterwards, component by component.

That capability has a name.

---

## 3. Observability

The definition read in the video:

> **Observability** is the ability to understand a system's internal state by examining its external outputs — logs, metrics and traces. It allows you to diagnose issues, understand performance, and improve reliability by analysing data generated by the system. Essentially, it is about being able to answer **why** something is happening within a system — *even if you did not anticipate the problem*.

The last clause is the one that matters, and it is the difference between observability and monitoring:

| | Question it answers | Requires you to have… |
|---|---|---|
| **Logging** | "Did the thing I chose to log happen?" | …anticipated what to log |
| **Monitoring** | "Is metric X outside its expected band?" | …anticipated which metric matters |
| **Observability** | "Why is *this* happening?" | …recorded enough that you can ask questions you had not thought of |

You did not anticipate that a prompt sentence would create a loop. You did not anticipate that `k=1` would ship. Observability is the property that lets you diagnose those anyway, because the data was captured before you knew the question.

### The mechanism

```
Run the application  →  record a TRACE of the execution  →  store it
                                                              │
                        later, when something is wrong  ───────┘
                                    │
                        open the trace, walk it component by component
```

A **trace** is the recorded execution of one run, broken down by component, with inputs, outputs, timings and costs at every step. That is the artefact. Everything in this tutorial is about producing, reading and acting on traces.

---

## 4. Map the three stories to what a trace gives you

| Story | Symptom | What the trace shows immediately | Fix becomes obvious |
|---|---|---|---|
| **A** Cover letter | 2 min → 9 min | Stage 2 (Drive fetch): 6 s → 8 min; all other stages unchanged | Revert the Drive-scanning change |
| **B** Research agent | 50 p → ₹2 on *some* reports | The expensive traces contain **4 loop iterations** of search→read→summarise; cheap ones contain 1 | Bound the self-critique loop; revert or reword the prompt |
| **C** HR chatbot | Confident wrong answers | The retrieved-chunks run holds **one** chunk, about the wrong policy | Raise `k` — this was a retriever failure, not a generator one |

In each case the trace does not *interpret* the failure for you. It converts an unanswerable question ("why is it slow / expensive / wrong?") into an answerable one ("which run's numbers changed?"). That is the whole value proposition.

---

## 5. ⭐ Beyond the video — why this is harder than APM

*This section is added; it is not from the transcript. It exists because engineers with backend experience often assume they already have this problem solved.*

If you have used Datadog, New Relic or Jaeger, you may reasonably think: *distributed tracing is a solved problem, I'll just instrument it.* Traditional APM genuinely does solve Story A. It does **not** solve B or C, for four reasons:

1. **The payloads are the signal, not metadata.** A conventional span records `db.query` took 40 ms. An LLM span is useless without the *full prompt text* and *full completion text* — often kilobytes each. APM tooling is built to sample and discard payloads; here the payload *is* the diagnosis.

2. **The units are different.** You need **tokens** and **cost per call** as first-class metrics. No general-purpose APM knows that `gpt-4o-mini` at 3,000 input / 500 output tokens costs a specific fraction of a cent, or that a `RunnableParallel` has two branches whose token counts should be summed.

3. **Correctness is not binary.** HTTP 200 vs 500 is a complete health signal for a REST service. "The LLM returned a syntactically valid but factually invented answer" is a 200. Correctness needs *evaluation* — scoring outputs against references or rubrics — which is a fundamentally different subsystem from tracing, and one that has to share the same data model. (This is why LangSmith is an observability **and evaluation** platform, and why lessons 13–15 exist.)

4. **The debugging loop includes editing prose.** Having found the bad prompt, you want to edit it, re-run it against saved cases, and compare. That is a prompt playground plus a dataset — again, sharing the trace data model.

So the tooling category is genuinely new, not a rebranding. Related reading in this repo: [`Shared/03_llmops/05-observability-and-tracing.md`](../../Shared/03_llmops/05-observability-and-tracing.md).

---

## 6. The alternatives, honestly

*Also added — the video presents LangSmith without comparison, which is fair for a crash course but leaves an obvious question unanswered.*

| Tool | Nature | Pick it when |
|---|---|---|
| **LangSmith** | Hosted (cloud or self-host), built by the LangChain team | You are on LangChain/LangGraph — the integration is zero-config and the coupling is deliberate |
| **LangFuse** | Open-source, self-hostable | You need data on your own infrastructure with no vendor, or you're framework-agnostic |
| **Phoenix / Arize** | Open-source, OpenTelemetry-native | You already run OTel and want LLM spans in the same backend as everything else |
| **Weights & Biases Weave** | Hosted | Your team already lives in W&B for model training |
| **Roll your own** | Log spans to your warehouse | You have a genuinely unusual data-residency or retention requirement — and accept that you're also building the trace viewer, the evaluator runner and the dataset store |

The concepts in this tutorial — trace, span/run, project, evaluation dataset — are **portable across all of them**. Learn the concepts here; the vendor is a detail.

---

## Recap

- Three failure modes — **latency**, **cost**, **correctness** — arising from three different architectures, all undebuggable with conventional tools.
- The shared root cause is **non-determinism** plus **multi-stage composition** plus **failures that are behavioural rather than exceptional**.
- **Observability** is the ability to answer *why*, including for questions you did not anticipate; a **trace** is the artefact that makes it possible.
- Prompts are **control flow**. Review them like code.
- This is not APM with a new logo: payloads are the signal, tokens/cost are the units, and correctness needs evaluation.

---

## Self-check

1. Story B's cost spike appeared on *some* reports and not others. Why does that single fact make conventional debugging much harder than a spike affecting all reports?
2. A RAG bot gives a wrong answer. Which single piece of intermediate data most efficiently splits the diagnosis in two, and why?
3. Give a definition of observability that distinguishes it from monitoring in one sentence.
4. Why is "nothing crashed" bad news rather than good news when a cost regression appears?

---

**Next:** [`02-what-langsmith-is-and-what-it-records.md`](02-what-langsmith-is-and-what-it-records.md) →
