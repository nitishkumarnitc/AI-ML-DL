# 12 · The interview loop

> ← [`11-the-fde-toolkit.md`](11-the-fde-toolkit.md) · **Index:** [`README.md`](README.md) · **Next:** [`13-exercises-and-first-90-days.md`](13-exercises-and-first-90-days.md) →

---

## 12.1 The shape of an FDE loop

Companies vary, but the rounds converge on a consistent set. Each row names the round, what it's actually testing (usually not what it appears to test), and where in this tutorial the substance lives.

| Round | Looks like it's testing | Actually testing | Prep in |
|---|---|---|---|
| **Recruiter screen** | Fit, comp, logistics | Whether you can describe the role back accurately | [01](01-what-the-role-actually-is.md) |
| **Take-home / live-coding project** | Can you code | Can you ship something real under a deadline with real ambiguity | The [job-card exercise](../00_jobs/10_forward-deployed-ai-solutions-engineer/project.md) + [11](11-the-fde-toolkit.md) |
| **System / architecture design** | Do you know RAG/agents | **Do you make the right trade-off under a stated constraint** | [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md) |
| **Customer role-play** | Communication skills | Do you reframe before you answer; do you separate dangerous from imperfect | [10](10-stakeholder-communication.md) |
| **Case study / whiteboard scoping** | Can you plan | Do you ask the right questions before proposing a solution | [03](03-discovery-and-scoping.md) |
| **Behavioral / values** | Culture fit | Have you actually shipped ambiguous things and can you narrate it honestly | 12.5 below |
| **Bar-raiser / hiring manager** | Everything | Would they trust you unsupervised at a customer next week | All of the above, integrated |

**The unifying test across every round:** *would this person survive a real customer without a spec, without clean data, and without me in the room?* Every question is a proxy for that.

---

## 12.2 The design round, worked

This is where [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md) is your unfair advantage — but only if you use it as a *conversation*, not a memorised architecture.

### The prompt you'll get

> "A [insurance / logistics / healthcare] company wants to use AI for [claims triage / demand forecasting / clinical summarisation]. Design it."

### The trap

Jumping straight to an architecture diagram. That answers a question nobody asked — this is an FDE round, so it's implicitly scoped to *one customer's messy reality*, not a general product.

### The structure that scores well

**1. Scope it like discovery, out loud, first — even in a 45-minute interview.**
> "Before I design anything — what's the volume, what's today's process, and who reviews the output? Those three numbers change the architecture more than any model choice."

**2. Name the real tension in the domain**, not a generic RAG diagram. This is where knowing [`28_`](../28_ai-system-design-by-industry/README.md) pays off — you can go straight to the thing that actually matters instead of a diagram-shaped answer:

| If they say... | The tension to name immediately |
|---|---|
| Insurance claims | Regulated settlement timelines vs. fraud investigation being inherently slow — see [`07`](../28_ai-system-design-by-industry/07_insurance_claims_automation/) |
| Logistics/demand | Point forecasts hide the uncertainty that actually drives decisions — quantiles, not a point estimate — see [`05`](../28_ai-system-design-by-industry/05_logistics_forecast_optimisation/) |
| Fraud/risk | Human review capacity is the real threshold-setter, not model accuracy — see [`02`](../28_ai-system-design-by-industry/02_banking_fraud_detection/) |
| Manufacturing QC | Two conflicting NFRs (miss nothing vs. reject nothing extra) can't both be satisfied by one binary threshold — see [`06`](../28_ai-system-design-by-industry/06_manufacturing_cv_inspection/) |
| HR/recruiting | The most natural training signal (human decisions) is the one that reproduces bias — see [`11`](../28_ai-system-design-by-industry/11_hr_recruitment_matching/) |
| Healthcare | Citation accuracy is the safety property, not top-line accuracy — see [`04`](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/) |

**3. Name a rejected alternative, with the reason.** This single habit signals more seniority than any other move in the round.

> "I'd reject a single accuracy threshold here — an infeasible or dangerous output isn't a *worse* output, it's not a valid one, so it needs to be a hard filter, not a score. I'd use a three-way output instead: confident-good, confident-bad, and a review band sized to whatever human capacity actually exists."

**4. Ask about the human loop before the model.** "Who reviews this, and how many can they review per shift?" is the single highest-signal question in this round — see [03.5](03-discovery-and-scoping.md).

**5. State the FDE-specific constraint the general design would skip:** *this has to work on one customer's actual data, this month, with a security review nobody's booked yet.* An interviewer who's actually done the job will visibly relax when you say this, because it shows you're not answering a generic system-design question.

### What NOT to do

Don't recite a memorised design verbatim — interviewers notice, and it reads as pattern-matching instead of reasoning. **Use `28_`'s designs as a library of *moves* you can reach for** — hard-constraint-as-filter, human-capacity-sets-the-threshold, blocking dimensions, fail-open-vs-fail-closed asymmetry — and apply the move that fits *their* specific prompt.

---

## 12.3 The take-home / live project

Almost every FDE loop includes a time-boxed build. See the [job card's sample project](../00_jobs/10_forward-deployed-ai-solutions-engineer/project.md) for a full worked run of exactly this format.

### What's actually being scored (rarely stated explicitly)

| Signal | How it shows up |
|---|---|
| **Did you write assumptions down before coding** | The single strongest differentiator. Most candidates skip straight to code |
| Did you handle the ambiguous brief without asking to have it disambiguated | Real customer briefs are always underspecified; asking to fix that first is a mild red flag |
| Is there *any* guardrail, however small | A model that can't fabricate a price beats a fluent draft that might |
| Did you stop at the time box | Ignoring the deadline to "finish it properly" reproduces the Purist failure mode from [01.8](01-what-the-role-actually-is.md) |
| **Are your follow-up questions good** | This is graded as seriously as the code. Weak questions ("does this look okay?") score worse than strong code |

### The follow-up questions that score well

Not "did it work" — questions that show you know what you *don't* know yet:

- "What's your actual message volume, and what's the peak?"
- "Who's liable if a draft with a wrong fact gets sent, and is a human always in the loop before send?"
- "What system holds the source data today, and does it have an API?"
- "Of the messages you get, what fraction are actually the happy path I built for?"

Notice these are exactly [03.2](03-discovery-and-scoping.md)'s discovery questions, compressed. **The take-home is discovery practice with a deadline**, and the questions you'd ask next are graded as a deliverable in their own right — not padding.

---

## 12.4 The customer role-play, in the room

[10](10-stakeholder-communication.md) has five full scripts. The meta-advice for the live version:

**Ask a clarifying question before answering anything.** *"What happens today when this goes wrong?"* or *"What does the board actually need to see?"* This is the single highest-scoring move across every FDE role-play — it demonstrates you consult before you commit, which is the entire job in one gesture.

**Never defend the technology.** If they push on accuracy, don't explain how LLMs work. Reframe to the human baseline, to error cost, to the system-level design. The interviewer wants to see you protect the *relationship and the outcome*, not the model's honour.

**Get comfortable saying "I don't know, here's how I'd find out."** Interviewers deliberately ask something you can't know (their exact infra, a number that wasn't given). Bluffing is instantly visible and instantly disqualifying; a clean "I don't know, and here's the question I'd ask to find out" reads as senior.

**If they escalate (angry, urgent, unreasonable), match their urgency without matching their emotion.** The escalation script in [10.7](10-stakeholder-communication.md) — endorse the drastic action, commit to a time, then actually investigate — is the template. Calm and fast beats calm and slow, and both beat panicked.

---

## 12.5 Behavioral round — the FDE-specific angle

Standard STAR structure, with content that's specific to this role. The distinguishing signal in FDE behavioral rounds is **narrating failure honestly**, because the interviewer is testing for exactly the trust-calibration skill from [10](10-stakeholder-communication.md).

### The questions that come up specifically because it's this role

| Question | What a strong answer contains |
|---|---|
| "Tell me about a project you'd have killed earlier" | A specific number that should have triggered the kill decision sooner, and what you'd instrument differently next time |
| "Tell me about pushing back on a customer" | The specific ask, the specific data you brought, and — critically — **what you offered instead**, not just the refusal |
| "Tell me about a time the customer was wrong" | How you disagreed *and stayed trusted*, not just that you were right |
| "Tell me about shipping something imperfect on a deadline" | What you explicitly labelled as throwaway, and whether it actually got thrown away |
| "Tell me about a failure that reached a user" | Whether your story includes *checking if it was one case or a class* — see [10.7](10-stakeholder-communication.md) |
| "Tell me about learning an unfamiliar domain fast" | The actual mechanism — shadowing, reading their tickets, three good discovery questions — not "I'm a fast learner" |

### The pattern that scores worst

A story where nothing went wrong. FDE work is inherently ambiguous and messy; a friction-free narrative signals either dishonesty or a shallow engagement. **Bring the story where you were wrong about the approach, caught it, and said so before the customer had to.** That's the actual job.

---

## 12.6 Questions to ask them — and what the answers tell you

From [`../00_jobs/README.md`](../00_jobs/README.md)'s spirit and this role's specific failure modes ([01.8](01-what-the-role-actually-is.md), [09.1](09-pilot-to-production.md)):

| Ask | Listen for |
|---|---|
| "After a pilot succeeds, who owns running it — me, the customer, or a separate team?" | Disambiguates builder vs. consultant vs. demo machine ([01.3](01-what-the-role-actually-is.md)) |
| "What's your average time from pilot to production, and what's the longest it's taken?" | If they don't know, exit criteria probably don't exist here either |
| "How does field learning reach the product team — what's the actual mechanism?" | "We have a Slack channel" is a weak answer. A real feedback loop has an owner and a cadence |
| "What's a project that didn't make it to production, and why?" | Tests self-awareness. "We don't really have those" is a red flag, not a good sign |
| "Is there a quota tied to this role?" | If yes, you're closer to a Sales Engineer than an FDE — decide if that's what you want |
| "What does a bad week look like here?" | The honest answer tells you more about day-to-day reality than any perk |

---

## 12.7 The synthesis question

Some loops end with a version of: *"Walk me through how you'd approach your first 30 days."* This is the round where every prior file in this tutorial should visibly compose into one coherent answer. See [13](13-exercises-and-first-90-days.md) for the full 30/60/90 — the short version, for the room:

> "Week one is discovery and a data profile, not a prototype — shadow someone doing the task, get a real sample, and ask what they'd stop doing if this worked. In parallel I'd start the enterprise clock: who approves this, and how long does each approval typically take, because that's usually the real critical path.
>
> Week two, I'd measure whether the task is even well-defined — get three of their experts to independently label thirty real examples and check their agreement. That number sets my accuracy target, or tells me the target needs a definition workshop first.
>
> Weeks three and four, a stratified golden set and the first real prototype, evaluated against it, not against my own taste. I'd expect the demo-level number to drop hard on real data, and I'd say so before it happens rather than after.
>
> By week six I want written exit criteria signed by one named person — accuracy bar, volume, who reviews the output and their actual capacity, which security reviews apply and who owns them. That document is what turns 'is it good enough' from an opinion into a measurement, and it's the single biggest predictor of whether this reaches production instead of dying quietly in month four."

---

> ← [`11-the-fde-toolkit.md`](11-the-fde-toolkit.md) · **Index:** [`README.md`](README.md) · **Next:** [`13-exercises-and-first-90-days.md`](13-exercises-and-first-90-days.md) →
