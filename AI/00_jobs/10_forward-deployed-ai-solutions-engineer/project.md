# 10 · Sample project — Forward-Deployed / AI Solutions Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- runs the real draft-reply generator across 5 repair orders, an escalation-detection heuristic, a guardrail stress test, and follow-up questions. `--interactive` runs a live session CLI with JSON logging. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A **3-hour, time-boxed simulated customer engagement**: given a deliberately messy, ambiguous "customer" brief, ship a working prototype before the clock runs out, then document the assumptions you made and the questions you'd ask next.

## 🧠 Why this mirrors the real job
- "Sit with a customer, understand their workflow, and build a working AI solution fast" → the time box forces the same speed-under-ambiguity tradeoffs.
- "Integrate APIs/agents/RAG into messy real environments; own it end to end" → the brief below is intentionally under-specified, like a real first client conversation.
- "Feed product/eng what's missing" → your follow-up questions list is a real FDE artifact, not filler.

## 🧰 Prerequisites
- Whatever stack you're fastest in (Python/TS, an LLM API, anything free/local).
- A literal kitchen timer for the time box — the constraint is the point.
- 3 hours, in one sitting.

## 🧰 Tools, libraries & skills used here
- **Requirements triage under ambiguity**: writing down assumptions *before* coding (step 2) is the actual differentiator between a rushed prototype and a defensible one — the code itself is intentionally simple.
- **Regex-based fact extraction & a numeric guardrail** (`violates_guardrail`) — a lightweight, real technique for constraining generated text to only reuse facts that are demonstrably present in the source document.
- **Stakeholder follow-up questions** as a deliverable in their own right — the actual output of a first customer conversation, as important as any code.
- **What a real engagement adds on top**: a real LLM call (OpenAI/Anthropic/Azure) in place of the template function, a UI the advisor actually uses (**Streamlit**, **Gradio**, or a real web frontend), integration with whatever system holds the repair-order notes (a real API, not a Python dict), and often a messaging channel integration (**Twilio** for SMS) to close the loop end to end.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| re (stdlib) | built in | extracting dates/facts from the repair note and checking the guardrail |

## 🪜 Step-by-step

### 1. The brief (use this verbatim, or write your own in this style)
> *"Our service advisors get 100+ customer text messages a day asking about appointment status,
> repair estimates, and pickup times. They're drowning. We want something that reads an incoming
> text and drafts a reply using our notes on that repair order, so the advisor just has to
> approve and send. We don't really have clean data — the 'notes' are free-text from different
> systems. Can you show us something by Friday?"*

Notice what's missing: no data schema, no volume numbers, no definition of "approve," no mention of tone/liability constraints (this is customer-facing text about their car). That ambiguity is deliberate — real customers hand you exactly this.

### 2. Set a 10-minute clock: write down your assumptions before coding
Force yourself to decide, in writing, things like:
- What does a "repair order note" look like? (Make up 5 realistic messy examples.)
- Is a human always in the loop before sending? (Assume yes — draft-only, never auto-send.)
- What if the note doesn't have the answer? (Assume: draft says so honestly, doesn't guess.)

### 3. Build the prototype (aim for ~2 hours)
```python
REPAIR_NOTES = {
    "RO-1042": "Customer dropped off 7/28. Brake pads + rotors, front. Parts backordered, "
               "ETA 8/2. Advisor: Mike.",
    "RO-1088": "Oil change + multi-point inspection. Found rear tire wear, flagged for customer "
               "approval. Completed 7/29, ready for pickup.",
}

def draft_reply(customer_text: str, ro_number: str) -> str:
    note = REPAIR_NOTES.get(ro_number, "")
    if not note:
        return "[DRAFT] I don't have your repair order pulled up yet — checking now and will follow up shortly."
    prompt = f"""You draft short, warm, factual text replies for an auto service advisor.
Use ONLY the repair order note below. If it doesn't answer the question, say you'll check and
follow up — never guess at parts, pricing, or timing.

Repair order note: {note}
Customer message: {customer_text}

Draft a reply (2-3 sentences, no more):"""
    return "[DRAFT] " + call_llm(prompt)

print(draft_reply("hey is my car ready yet??", "RO-1088"))
print(draft_reply("how much longer for the brake job", "RO-1042"))
```

### 4. Add the one guardrail a real deployment needs
Never let the draft state a price or promise a date that isn't literally in the note — test it with a customer message that fishes for a number the note doesn't contain, and confirm the draft doesn't fabricate one.

## ✅ Deliverable
- The working prototype (however rough) + 3–5 example draft replies against realistic messy notes.
- Your **assumptions list** (from step 2) as a visible artifact, not just in your head.
- A **3-question follow-up list** for the "customer" — the real, valuable output of a first FDE engagement (e.g. "what's your actual message volume?", "who's liable if a draft is wrong and gets sent?", "what system holds the repair notes today?").

## ⏱️ Time box
Exactly 3 hours — stop even if it's rough. Write the assumptions/questions doc regardless of how far the code got.

## 🔁 Where to go deeper
Everything in [Applied AI / LLM Engineer's project](../05_applied-ai-llm-product-engineer/project.md) · [`18_ragapp`](../../18_ragapp/README.md) — reusable agent-stack design · [`17_claude-code`](../../17_claude-code/README.md) — directing coding agents to build this fast for real.
