# 13 · Monitoring and Alerting

> ← [`12-tracing-langgraph.md`](12-tracing-langgraph.md) · **Next:** [`14-evaluation-datasets-and-annotation.md`](14-evaluation-datasets-and-annotation.md) →

---

Everything so far has been observability: **one trace, studied in depth.** That is the right tool when you already know something is wrong and you have a specific execution to examine.

It answers the wrong question in production. In production the question is *"is something wrong right now, and did I need to know an hour ago?"* You cannot answer that by opening traces one at a time.

---

## The definition

> **Monitoring** in LangSmith looks across **many traces at once** to track the overall health of your LLM system. It aggregates metrics like latency, token usage, cost, error rates and success rates. You can set up **alerts** to notify you when these metrics drift outside acceptable ranges.

### The three, cleanly separated

| | Scope | Question | When you use it |
|---|---|---|---|
| **Observability** | **one** trace | *Why did this happen?* | You have a specific bad execution |
| **Monitoring** | **many** traces | *Is the system healthy?* | Continuously |
| **Alerting** | a threshold on a monitored metric | *Tell me when it isn't* | Before a user does |

The line from the video's slide is the one to remember:

> *Production issues often appear first as **patterns across multiple runs** rather than in a single trace.*

No single trace tells you latency is climbing. Any individual 6-second trace might just be a long question. **A distribution shifting is the signal, and a distribution is not visible from inside one sample.**

---

## The Monitoring tab

`Tracing Projects` → select project → **Monitoring**. Per-project time series:

| Chart | Reads as |
|---|---|
| **Traces per day** | Usage curve. Growth, or a drop meaning something upstream broke |
| **Trace latency** | The headline UX metric |
| **Error rate** | Hard failures — near zero in the video's example |
| **Total LLM calls** | Calls *per trace* is the agent-loop signal (lesson 11) |
| **LLM call latency** | Separates *provider slow* from *your app slow* |
| **Cost** and **cost per trace** | Total is a budget question; per-trace is an efficiency question |
| **Input tokens** / **output tokens** | Which side of the prompt is growing |
| **Tool usage** | Which tools agents actually pick |

### The two pairs that carry the most information

**Cost vs cost per trace.** Total cost rising with flat cost-per-trace is *growth* — good news, budget accordingly. Total cost rising with **cost per trace rising** is a *regression* — Story B. Same top-line number, opposite meanings, and only the pair distinguishes them.

**Trace latency vs LLM call latency.** If trace latency rises while LLM call latency is flat, the slowdown is **yours** — retrieval, tool calls, your code. If both rise together, it's the **provider**, and no amount of your own optimisation will help. This is the single most useful triage split on the page, and it takes five seconds.

---

## Alerting

Monitoring you have to look at is monitoring you will look at after the customer emails. Alerts invert that.

**Monitoring → Alerts →** pick a project, a metric, a threshold, and a delivery channel (notification or webhook).

The example: **if latency > 5 s, raise an alert and message the team** — so you go and debug *before* users churn.

> *Monitoring helps you catch these early signals before they impact users at scale. Instead of waiting for customer complaints, you are proactively alerted when performance degrades and cost spikes — enabling fast response and a more reliable application.*

The failure mode this exists to prevent, stated plainly: your application is deployed, and **silently** latency climbs or cost climbs, and you do not know. For an LLM app that is genuinely dangerous, because — unlike a crash — nothing surfaces on its own. Story B ran for an unknown number of days before somebody happened to open a billing dashboard.

---

## ⭐ Beyond the video — an alert set that won't cry wolf

*Added. The video shows the mechanism with one example; choosing thresholds well is the part that decides whether anyone still reads the alerts in six weeks.*

### Alert on percentiles, not means

A mean is dragged around by outliers and hides the tail. Alert on **p95** or **p99**.

```
❌ mean latency > 5 s        → fires late; one 60 s outlier in 1,000 hides forever
✅ p95 latency > 5 s         → fires when 1 in 20 users is suffering
```

The same argument as any SLO work: users experience the tail, not the average.

### A starter set

| Alert | Threshold | Catches | Story |
|---|---|---|---|
| **p95 latency** | > 1.5× your normal p95 | Slow regressions | A |
| **Cost per trace** | > 2× 7-day median | Loops, prompt bloat, model swap | B |
| **Error rate** | > 2% over 15 min | Provider outage, key expiry, quota | — |
| **LLM calls per trace** | p95 > your loop ceiling − 1 | Agents starting to loop | B |
| **Traces per hour** | < 20% of same-hour-last-week | **Silence** — your app stopped being called | — |
| **Negative feedback rate** | > 2× baseline | Quality regression users noticed | C |
| **`index_build` trace outside deploy window** | any | Cache invalidation bug (lesson 10) | — |

Two of these deserve a note.

**The traces-per-hour *floor*** is the alert people forget. Every other alert fires when something is too high. If your app breaks upstream — a broken deploy, a routing change, an auth failure at the edge — **the symptom is silence**, and silence trips nothing. An absence-of-traffic alert is often the first thing that tells you the app is down.

**Negative-feedback rate** is the only alert here that tracks *correctness* rather than mechanics. Everything else can look perfect while the bot confidently invents policy. It requires lesson 16.

### Compare like-for-like

Traffic is seasonal. Compare against **same hour, previous week** rather than "an hour ago" — otherwise every Monday 09:00 pages someone and the alert gets muted, which is worse than not having it.

### Route by severity

| Severity | Channel |
|---|---|
| Cost or quality drift | Slack, business hours |
| p95 latency breach | Slack, immediately |
| Error rate / traffic floor | Page someone |

An alert that pages for a cost drift trains people to ignore pages. Alert fatigue is a real failure mode with a real cost.

---

## ⭐ The one thing monitoring cannot do

*Added, because it's the bridge to the rest of the tutorial and the most commonly missed point in the whole topic.*

Look back at the metric list. Latency, cost, tokens, error rate, tool usage. Every one is **mechanical**. Not one of them measures whether the answers are *right*.

Return to Story C: the HR chatbot telling employees there is no leave policy. On every chart in this lesson, that system is **perfectly healthy** — fast, cheap, zero errors, steady usage. And it is spreading misinformation through the company.

> **Monitoring measures how the machine is running. It cannot tell you whether the machine is right.** For correctness you need a different instrument: outputs scored against expectations. That is **evaluation**, and it is why LangSmith is an observability *and evaluation* platform rather than just a tracing tool.

Two lessons follow from this.

The mature setup runs both, and they answer different questions:

| | Detects | Latency of detection |
|---|---|---|
| **Monitoring** | Mechanical drift | Minutes |
| **User feedback** (lesson 16) | Quality problems users noticed | Hours to days |
| **Online evaluation** (lesson 14) | Quality problems on live traffic, scored automatically | Minutes |
| **Offline evaluation** (lesson 14) | Quality regressions **before deploy** | Pre-merge |

And the ordering matters: offline evaluation is the only row that catches the problem *before* users see it. Everything else is a smoke detector.

---

## Recap

- **Observability = one trace. Monitoring = many traces. Alerting = a threshold on a monitored metric.**
- Production problems appear as **distribution shifts**, invisible from inside any single trace.
- The Monitoring tab: traces/day, latency, error rate, LLM calls, cost, cost per trace, tokens, tool usage.
- **Cost vs cost-per-trace** separates growth from regression. **Trace latency vs LLM-call latency** separates your slowness from the provider's.
- Alert on **percentiles**, compare **same hour last week**, and **route by severity** or people stop reading.
- Include a **traffic floor** alert — the symptom of an upstream break is silence, and silence trips nothing.
- **Every monitoring metric is mechanical.** A confidently-wrong system looks perfectly healthy. Correctness needs **evaluation** — next lesson.

---

## Self-check

1. Total cost is up 40%. Which second chart tells you whether to celebrate or roll back?
2. Trace latency p95 doubled; LLM call latency is unchanged. Where is the problem, and where is it *not*?
3. Why alert on p95 rather than the mean?
4. Name the failure that trips no threshold-exceeded alert at all, and the alert that catches it.
5. Story C's chatbot is fast, cheap and error-free while telling people there's no leave policy. Which subsystem catches it, and why can't monitoring?

---

**Next:** [`14-evaluation-datasets-and-annotation.md`](14-evaluation-datasets-and-annotation.md) →
