# Lesson 1 — Master LLM Evaluations (Playlist Intro)

> **Source:** CampusX · *Master LLM Evaluations: The Step-by-Step Playlist for 2026* · 23:24 · [watch](https://www.youtube.com/watch?v=6W92_t9FveA&list=PLEneLIDJFpcA&index=1)
> **One-liner:** After a year and a half of CampusX content teaching people to *build* LLM applications (LangChain, RAG, agents, LangSmith, prompt engineering, no-code tools), this playlist tackles the far less-covered skill of *evaluating* them — motivated by three real lawsuits/PR disasters, and framed around one core distinction: "vibe testing" a personal project vs. proving a system is fit to serve millions of users.

---

## 🎯 TL;DR

The instructor's own framing: an **AI engineer** is someone who builds applications on top of foundation models — and CampusX's content up to this point has taught the *building* half (LangChain, RAG, agents, frameworks like LangGraph/CrewAI/Agno, LangSmith for LLM Ops, prompt engineering, no-code tools like n8n). What's been missing is the *evaluating* half — deciding whether an app is actually fit to launch. This matters for two concrete reasons: it's now a near-guaranteed GenAI interview question ("how do you evaluate your RAG/agentic application?"), and few competing candidates study it seriously because good resources are still scarce. The core problem the whole playlist exists to fix is **"vibe testing"** — informally trying a few prompts and judging by feel — which is explicitly named as *not* viable once an application needs to serve real production traffic rather than just impress an interviewer.

---

## 1. Why this playlist, and why now

The instructor's own definition, stated directly: *"An AI engineer is someone who builds applications and products on top of foundation models."* CampusX's prior year-and-a-half of content mapped almost entirely onto the *building* half of that definition — LangChain basics, RAG chatbots, agent frameworks (LangGraph, CrewAI, Agno), a flavor of LLM Ops via LangSmith, a dedicated prompt engineering course, and no-code tools like n8n. This playlist is explicitly framed as the next, less-common topic: **how do you evaluate what you built, and decide whether it should actually go to production?**

**Two concrete benefits promised for studying this topic seriously:**
1. **Competitive edge** — very few people preparing for AI engineering roles study LLM evaluation seriously, partly because good resources are still scarce online; studying it puts you ahead of that pool.
2. **A mindset shift** — up to now, most personal projects are built to the standard of "show it to an interviewer and it looks like it works." Studying evaluation properly shifts your thinking toward "how would this serve *crores* (tens of millions) of real users" — a genuinely different design mindset, not just an added skill.

---

## 2. The core anti-pattern: "vibe testing"

**Definition given directly:** *"Vibe testing" means casually trying an LLM application with a few prompts and judging it by feel* — ask it 5–10 questions, the answers look good, so you assume the project works. The instructor predicts (and expects agreement from) more than half of any audience: most people who've built an LLM app have never evaluated it more rigorously than this.

**Why it fails, stated plainly:** vibe testing is **informal, subjective, and not repeatable** — you can't apply the same "feel" methodology consistently to the next version of your project and get a comparable result. It's fine at the scale of a personal project you show an interviewer once. It is **not viable** for a production system real users depend on — doing so risks exactly the kind of public failure the next section documents.

---

## 3. Three real-world case studies — what happens when you skip evaluation

### Case 1 — Air Canada's bereavement-fare chatbot

A customer, dealing with a family death, asked Air Canada's website chatbot about their bereavement fare policy (a discount airlines offer for last-minute emergency travel). The chatbot **hallucinated**: it told the customer to book at full price and claimed a refund would be issued afterward. The actual policy was the opposite — the discount had to be applied *before* booking, with no after-the-fact refund. The customer booked based on the bad answer, was later refused a refund by human representatives, and took Air Canada to court.

**Air Canada's defense, and why it failed:** the airline argued the chatbot was "a separate entity" not responsible for its own words. The judge rejected this directly — a chatbot deployed on your website is your property, exactly like the website itself, so the company is liable for whatever the chatbot says. Air Canada lost and had to refund the customer in full — a small amount financially, but reputationally damaging, global news coverage, for entirely the wrong reasons.

### Case 2 — Chevrolet dealership's "$1 car" jailbreak

A Chevrolet dealership (not Chevrolet corporate itself) deployed a ChatGPT-powered chatbot for customer questions. A user socially engineered/jailbroke it — first getting it to agree it had to comply with whatever the user said as "a customer," then asking it to sell a car for $1. The compromised chatbot agreed and issued what it phrased as **a binding offer**, in writing. The user screenshotted the entire exchange and posted it publicly, generating a wave of negative press for the dealership — even though they obviously never had to honor the "offer," the reputational damage from public mockery was real and avoidable.

### Case 3 — A lawyer's fabricated ChatGPT case citations (Mata v. Avianca)

A passenger injured by a service cart on a Colombian airline sued. Their lawyer asked ChatGPT to find precedent cases where an airline had been held liable and had to pay damages for a similar injury. ChatGPT **confidently fabricated entire cases** — invented names, dates, and case specifics that didn't exist — and the lawyer filed them with the court **without verifying them**. When opposing counsel checked, the cases were found to not exist at all. The judge fined the lawyer and their firm roughly **$5,000** and they lost the case; the story went viral as a cautionary tale about blind trust in LLM output.

**The common thread across all three:** in every case, a team or individual deployed/relied on LLM output **without evaluating it first** — the exact gap this playlist exists to close. Together the three cases map onto three distinct failure categories evaluation has to guard against: **hallucinated/wrong facts** (Air Canada), **unsafe/adversarial behavior** (Chevrolet jailbreak), and **fabricated, unverified claims presented as fact** (the lawyer's citations).

---

## 4. Why evaluating LLM applications is fundamentally trickier than testing regular software

Two core differences are named directly:

### Difference 1 — Determinism vs. probabilism

Traditional software is **deterministic**: a calculator given `2 + 2` always outputs `4`, every time, and you can state the expected output in advance. LLM-based applications are **probabilistic by nature**: the same question — *"What is overfitting in machine learning?"* — can get a differently-worded answer today, a differently-worded answer in 6 months, and neither is necessarily wrong. There's no single fixed expected output to assert against, which is why exact-match testing (the bread and butter of traditional software QA) doesn't transfer.

### Difference 2 — Single correctness check vs. multi-dimensional check

In traditional software, the only benchmark is usually **correctness** — does the output match the expected value, yes or no. For an LLM application, a human has to judge the output along **multiple simultaneous dimensions** — the examples given: **factuality**, **completeness**, **tonality**, **groundedness** (is it actually supported by real sources), **latency**, and **cost** to produce that answer. Critically, **which dimensions matter is application-specific** — the dimensions that matter for a Campus X educational chatbot are not the same set that would matter for some other company's chatbot. There is no fixed, universal checklist — you have to decide which axes matter for *your* application.

**This combination — no single expected output, and no single correctness dimension — is stated as exactly why so many teams skip evaluation altogether**, and exactly the challenge this playlist is built to walk through systematically.

---

## 5. The playlist roadmap, in the order given

The instructor lays out the intended arc chronologically:

1. **What exactly is an LLM Eval?** — a proper conceptual definition, with an example (this becomes Lesson 2).
2. **The complete landscape of LLM Evals** — a high-level map of the techniques and tools that exist, so new terminology has a mental "slot" to land in as it comes up.
3. **Evaluating LLMs themselves** — benchmarks: what they are, and why a new model launch is always accompanied by "scored highest on Benchmark X" claims.
4. **Evaluating LLM-based applications** — building your own eval pipeline from scratch: curating a golden dataset, defining your own rubrics, and testing them against a real application.
5. **RAG-specific evaluation.**
6. **Agent-based evaluation.**
7. **Safety-based evaluation.**
8. **Operational evaluation** — evaluation doesn't stop at deployment; once a system is live, you still track metrics like latency, tokens/second, time-to-first-token, and system load.

> The instructor is explicit that this is a rough, intended arc — exact titles and ordering may shift as the playlist develops — but the throughline is fixed: go deep enough on the *currently under-taught* topics that finishing the playlist genuinely levels up what kind of systems you're capable of shipping, not just what kind you're capable of building.

---

## 6. Key terms

| Term | Meaning |
|---|---|
| **AI Engineer** (instructor's working definition) | Someone who builds applications and products on top of foundation models (LLMs). |
| **Vibe testing** | Casually trying an LLM application with a few prompts and judging it by feel — informal, subjective, not repeatable; the anti-pattern this playlist replaces. |
| **Hallucination** | An LLM confidently generating false information (a policy, a case citation) that doesn't actually exist. |
| **Jailbreak / prompt injection** | Adversarially manipulating a model (e.g. via emotional/social framing) into ignoring its intended constraints. |
| **Determinism vs. probabilism** | Traditional software gives the same output for the same input every time; LLMs can validly give different phrasings for the same input, which breaks exact-match testing. |
| **Multi-dimensional evaluation** | Judging an LLM output on several axes at once (factuality, completeness, tone, groundedness, latency, cost) rather than a single correct/incorrect check — and which axes matter is application-specific. |

---

## ✍️ Notes / follow-ups
- Next: a proper definition of what an LLM Eval actually is (and the crucial "eval ≠ metric" distinction), plus the Model Eval vs. Application Eval split → [Lesson 2 — Model Evals vs Application Evals](02-model-evals-vs-application-evals.md).
- Key habit to carry forward: **whenever you finish an LLM-based project, ask whether you've done anything beyond vibe testing — if not, you haven't actually evaluated it yet.**
