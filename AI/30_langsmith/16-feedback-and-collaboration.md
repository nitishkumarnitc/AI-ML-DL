# 16 · User Feedback and Team Collaboration

> ← [`15-prompt-experimentation.md`](15-prompt-experimentation.md) · **Next:** [`17-production-hardening.md`](17-production-hardening.md) →

---

Two smaller features that punch above their weight, because they close the loop between what your system did and what humans thought of it.

---

## Part 1 — User feedback integration

### The mechanism you already know

Under every ChatGPT answer there is a 👍 and a 👎. Click one and you are telling OpenAI whether that particular response was any good. That is **user feedback**, and like any feedback it is how the system improves.

LangSmith lets you add the same mechanism to your own app:

> It lets you capture **thumbs up/down ratings** or **structured feedback** from users in production. Feedback is **logged alongside traces**, tied to the **exact prompt, model and state**, and it supports **bulk analysis** of what users like and dislike.

### Why "logged alongside traces" is the whole point

A raw thumbs-down is nearly useless. *Something* was wrong with *some* answer.

A thumbs-down **attached to a trace** is a complete bug report, already written:

| You get, for free | Because it's on the trace |
|---|---|
| The exact question asked | trace input |
| The exact chunks retrieved | retriever run |
| The exact prompt sent | prompt run |
| The exact model and parameters | run metadata |
| The exact answer produced | trace output |
| Latency, tokens, cost | trace metrics |
| Which prompt version, tenant, deploy | your metadata (lesson 06) |

**You can open a thumbs-down and see everything needed to diagnose it.** No "can you reproduce it?", no "what did you ask exactly?" — the failing execution is preserved in full.

And then, from lesson 14: **`Add to Dataset`**. That thumbs-down becomes a permanent regression test. This is the complete loop, and it is the most valuable thing in the entire platform:

```
user dislikes an answer
      │
      ▼
trace with full context, already captured
      │
      ▼
dataset row with the corrected expected output
      │
      ▼
CI gate — this specific failure can never silently return
```

Users report a bug once. It stays fixed forever.

### Where it shows in the UI

- **Per trace:** a **Feedback** section on the trace itself. Every trace can carry its feedback score alongside its runs.
- **Aggregate:** feedback scores appear in the **Monitoring** tab (lesson 13) — so you see sentiment *across* traces, not just per answer. This is the "negative feedback rate" alert from lesson 13's alert set, and it is the only alert on that list that tracks **correctness** rather than mechanics.

### ⭐ Wiring it up

*Added — the video shows the UI; here is the code.*

**Step 1: capture the run id when you answer.**

```python
from langsmith import trace

def answer_question(question: str) -> tuple[str, str]:
    with trace(name="support_answer", inputs={"question": question}) as rt:
        answer = rag_chain.invoke(question)
        rt.end(outputs={"answer": answer})
        return answer, str(rt.id)          # ← hand the run id to the frontend
```

**Step 2: return the run id with the answer.**

```python
@app.post("/ask")
def ask(body: AskBody):
    answer, run_id = answer_question(body.question)
    return {"answer": answer, "run_id": run_id}    # opaque to the user
```

**Step 3: submit feedback against it.**

```python
from langsmith import Client
client = Client()

@app.post("/feedback")
def feedback(body: FeedbackBody):
    client.create_feedback(
        run_id=body.run_id,
        key="user_rating",
        score=1 if body.thumbs_up else 0,
        comment=body.comment,          # optional free text — the most useful field
    )
    return {"ok": True}
```

Three notes worth having:

- **Feedback is asynchronous and out-of-band.** It arrives seconds or hours after the trace closed. That's fine — it attaches by `run_id`.
- **Go beyond binary where you can.** `key="user_rating"` for 👍/👎, and separately `key="was_answer_used"`, `key="escalated_to_human"`, `key="user_edited_output"`. Implicit signals like *did they copy the answer* or *did they immediately rephrase the question* are often **more honest than explicit ratings**, because most users never click the buttons at all. A rephrase-immediately signal is a thumbs-down that the user didn't bother to give you.
- **The `run_id` is a UUID, but treat it as capability-bearing.** Don't leak it into logs a third party reads, and don't let a client submit feedback for arbitrary ids without at least rate-limiting; otherwise your quality metric is trivially pollutable.

---

## Part 2 — Collaboration

### The problem it replaces

Before tools like this, debugging an LLM app as a team went: notice that one particular execution had high latency or high cost → **take screenshots** → email or Slack them to a teammate → *"look, this is the issue."*

Lossy, static, and the recipient cannot investigate anything you didn't happen to screenshot.

### What LangSmith does

Every trace has a **copy-link button**. Share the link; your teammate opens **the exact trace as it is on your machine** — every run, every input, every output, every timing, fully explorable.

> **The upgrade is not "sharing is easier."** It is that you are sharing an **artefact** rather than a **description**. Your colleague can expand runs you never looked at, check the assembled prompt you didn't think to screenshot, and find that the real bug is two runs above the one you flagged. That happens often enough to matter.

### The rest of the collaboration surface

| Feature | Use |
|---|---|
| **Shareable trace links** | "Look at this specific execution" |
| **Prompt versioning with collaborators** | Several people iterating on prompts (lesson 15) |
| **Custom dashboards, shareable** | A view per team — cost for finance, latency for platform, feedback for product |
| **Shared datasets** | One golden set the whole team evaluates against (lesson 14) |

LangSmith was designed from the start for teams to build LLM applications together — which matters most with large teams, where "who owns this prompt and why did it change" is otherwise unanswerable.

### ⭐ Two cautions

*Added.*

**1. A shared trace link may expose payloads.** The trace contains the full prompt, retrieved documents and completion. If any of that is customer data, a public link is a data-sharing decision, not a convenience. Check whether your link is org-scoped or genuinely public before pasting it anywhere, and treat "share externally" as a privacy review. Lesson 17 covers keeping the sensitive data out in the first place, which is the better fix.

**2. Dashboards need an owner.** A dashboard nobody owns stops being looked at within a month and then becomes actively harmful — a stale panel that everyone assumes someone is watching. Either an alert fires (lesson 13) or a named person reviews it on a schedule. "It's on a dashboard" is not monitoring.

---

## Recap

- Feedback attached to a trace is a **complete bug report**: question, chunks, prompt, model, answer, cost, metadata — all preserved.
- Feedback → `Add to Dataset` → CI gate is the **full loop**: users report a bug once and it stays fixed.
- Feedback appears **per trace** and **aggregated in Monitoring** — the only correctness-tracking alert available.
- Implementation: capture `run_id` when answering, return it, `client.create_feedback(run_id=..., key=..., score=...)`.
- **Implicit signals often beat explicit ratings** — most users never click the buttons; an immediate rephrase is a thumbs-down.
- Collaboration: share a **trace link**, not screenshots — an artefact your colleague can explore, not a description.
- Shared links may carry customer data. Dashboards need a named owner or an alert.

---

## Self-check

1. Why is a thumbs-down attached to a trace worth so much more than a thumbs-down in a support ticket?
2. Name two implicit feedback signals, and explain why they can be more reliable than explicit ratings.
3. Feedback arrives an hour after the trace closed. What makes that work?
4. Give the concrete privacy risk in pasting a trace link into a public channel.

---

**Next:** [`17-production-hardening.md`](17-production-hardening.md) →
