# 10 · Stakeholder communication

> ← [`09-pilot-to-production.md`](09-pilot-to-production.md) · **Index:** [`README.md`](README.md) · **Next:** [`11-the-fde-toolkit.md`](11-the-fde-toolkit.md) →

**This file and [04](04-evals-are-the-deliverable.md) are the two that most separate a strong FDE from a strong engineer.** The interview loop's customer role-play round is drawn directly from what's here.

---

## 10.1 The four conversations you'll have every week

| Conversation | What's really being asked | Where it goes wrong |
|---|---|---|
| **"Will it be right every time?"** | *Can I stake my reputation on this?* | Answering with a probability instead of a system |
| **"Why is this taking so long?"** | *Am I being managed or misled?* | Defending the timeline instead of making the invisible work visible |
| **"Can it also do X?"** | *Is this the platform I hoped for?* | Saying yes, or saying no |
| **"It got this wrong."** | *Should I still trust it?* | Explaining the model instead of fixing the loop |

All four have the same underlying shape: **the customer is trying to calibrate their trust, and you're the instrument.** Every technique below is about making that instrument readable.

---

## 10.2 The five rules

**1. Never give a bare date.** Always date + confidence + the thing that would move it.

> "Production pilot in front of five advisors by 14 March — 80% confident. The 20% is DMS API access; every week that slips past the 28th moves this a week. Who can I talk to about accelerating it?"

Commits, quantifies uncertainty, names the dependency, asks for help. **The most useful sentence pattern in the role.**

**2. Lead with the finding, not the verdict.** "I pulled 200 real claims and 61% are missing a field the decision needs" lands. "This won't work" starts a fight.

**3. Quantify, always.** "Accuracy is a bit low" is an opinion. "68% against the 80% bar, and 90% of the gap is one segment" is a shared fact you can both act on.

**4. Deliver bad news early, in writing, with an option attached.** Early bad news is competence. Late bad news is a betrayal, regardless of the engineering.

**5. Say "I don't know, I'll have an answer by Thursday."** Then have it by Thursday. One guessed answer that turns out wrong and every subsequent answer gets audited.

---

## 10.3 Role-play 1 — the non-determinism conversation

**The hardest one, and it comes up in every engagement and most interviews.**

> **VP Service:** "So once this is live, it'll get the replies right every time?"

**What they're actually asking:** *If this sends something wrong to a customer, am I the one who gets blamed?*

### ❌ Bad answer A — the reassurance
> "It's very accurate — we're seeing great results."

Fails because it's unfalsifiable, so it doesn't transfer any trust. And the first error destroys everything you said.

### ❌ Bad answer B — the technically correct lecture
> "Well, LLMs are probabilistic systems, so no — there's inherent non-determinism. We can't guarantee any specific output."

Fails because it's true and useless. You've handed them the risk with no structure for managing it, and they now think you don't understand their business.

### ✅ Good answer
> "No — and neither does your team, which is the useful comparison.
>
> We measured it. Three of your senior advisors labelled the same 100 messages, and they disagreed with each other on 12 of them. So 'right every time' isn't available on this task even in principle — for about 12% of messages, your own experts don't agree on the right reply.
>
> What we're building instead is a system that's right more often than today *and* fails safely. Three parts.
>
> First, on the two things that would actually hurt you — inventing a date or a price, and guessing when the note doesn't have the answer — we don't rely on the model behaving. Those are hard-blocked in code. Every date and price in a draft has to appear verbatim in the repair order or the draft doesn't get shown. That's zero out of 150 on our test set, and it's zero by construction rather than by luck.
>
> Second, the advisor approves every message. Nothing goes to a customer without a human pressing send.
>
> Third, when we're not confident, the draft says so — 'let me check and come back to you' — rather than guessing.
>
> So the honest answer is: individual drafts will sometimes be imperfect, the dangerous failures are structurally prevented rather than statistically unlikely, and a human is the last step. The measurable claim I'll stand behind is that advisors send 74% of drafts unchanged and 91% with at most a small edit, and I'll show you the dashboard that tells us the day that stops being true."

### Why it works

| Move | Effect |
|---|---|
| **Reframe to the human baseline first** | Changes the question from "is the AI perfect" to "is the system better than today" — the only answerable version |
| Give the disagreement number | Proves you measured rather than asserted, and makes "right every time" visibly incoherent |
| **Separate dangerous failures from imperfect ones** | This is the core move. "Zero by construction" is a much stronger claim than a high percentage |
| Name the human checkpoint plainly | Answers the unspoken question about blame |
| End on a monitored, falsifiable number | Gives them something to hold you to, which is what earns trust |

> **The transferable insight:** customers don't need certainty. They need to know **which failures are possible and what catches them.** A system with a known 26% edit rate and zero fabricated facts is more trustworthy than one claiming 95% accuracy with no failure taxonomy.

---

## 10.4 Role-play 2 — the impossible deadline

> **Director:** "Board demo is in two weeks. I need this live across all 40 stores by then."

**What they're actually asking:** *Help me not look bad in front of the board.*

### ❌ Bad answer
> "That's not realistic — security review alone is six weeks."

True, and you've made their problem worse without helping. They'll go around you.

### ✅ Good answer
> "Two weeks to all 40 stores isn't achievable — security review alone is six weeks and it hasn't started. I want to be straight about that now rather than in week two.
>
> But let me ask a different question: what does the board actually need to see?
>
> If they need to see it *working*, I can have it live with three advisors at your Whitefield store in two weeks. Real messages, real drafts, real advisors, and I'll have two weeks of numbers — acceptance rate, time saved per advisor-hour, cost per draft. That's a stronger board slide than a rollout announcement, honestly, because it has evidence in it.
>
> If they need to see *scale*, then the thing I need from you is the security review booked this week. That's the critical path, not the engineering. Get me a slot and 40 stores becomes a March conversation instead of a June one.
>
> Which of those is the board actually asking for?"

### Why it works

| Move | Effect |
|---|---|
| Refuse clearly and immediately | No ambiguity later; you're the reliable narrator |
| **Ask what the demo is for** | The stated deadline is usually a proxy for a softer need. Often "working at one store" fully satisfies it |
| Offer a real, smaller thing with evidence | Gives them a win they can actually use |
| **Convert your blocker into their action** | "Book the security review" makes them a participant in the timeline rather than a victim of it |
| Hand the decision back | They keep control, which is what makes them accept the constraint |

---

## 10.5 Role-play 3 — the threatened expert

> **Senior advisor, arms folded:** "So you're automating my job."

**What they're actually asking:** *Am I about to be redundant, and is my judgement being called worthless?*

**This is the most important conversation in the engagement and it's usually mishandled.** This person can quietly kill your project by not using it, and their tacit knowledge is the thing you most need.

### ❌ Bad answer
> "No no, it's just a tool to help you be more efficient!"

Dismissive of a real concern, and "efficient" is exactly the word that precedes headcount conversations. They won't believe you.

### ✅ Good answer
> "It's a fair thing to ask, and I'd rather answer it directly than reassure you.
>
> What it does is draft replies to the easy status questions — 'is my car ready.' What it explicitly won't touch is complaints, anything where the note doesn't have the answer, and anything where a judgement call is needed. Those come to you, and honestly they come to you *faster*, because you're not digging through 60 routine texts to find them.
>
> Here's the part I actually need from you. Right now it drafts in a generic voice and two advisors have told me it doesn't sound like them. I want to build the tone from your own sent messages, and I want you to tell me which of these fifteen drafts you'd never send and why. The 'why' is the thing I can't get anywhere else.
>
> And I'll be straight about what I don't control: I can't promise you what your management does with the time this frees up. What I can tell you is what they told me they want, which is advisors handling more customers rather than fewer advisors. You should probably ask them directly too — that's a reasonable thing to want in writing."

### Why it works

| Move | Effect |
|---|---|
| Take the question seriously | The reassurance reflex reads as evasion |
| **Be concrete about the boundary** | "It won't touch complaints" is checkable; "it's just a tool" isn't |
| Name the benefit *to them*, specifically | Fewer routine texts, faster access to the interesting work |
| **Ask for their expertise, genuinely** | Converts a threat into authorship. People don't sabotage things they helped build |
| **Don't promise what you don't control** | Never say "nobody's job is at risk" unless you know. Point them at who does know |

> **The recruitment move:** the expert who tells you which fifteen drafts are wrong becomes your best labeller, your internal advocate, and the reason the rollout works. **Every hour spent here returns more than an hour of prompt engineering** — and it's how you get the tacit knowledge that isn't written down anywhere.

---

## 10.6 Role-play 4 — "we need 99% accuracy"

> **Head of Ops:** "For anything customer-facing we'd need 99% accuracy minimum."

**What they're actually asking:** *I don't have a framework for thinking about error rates, so I'm naming a number that sounds safe.*

### ❌ Bad answer A
> "That's not achievable with current models."

You've said no to a number they picked arbitrarily, and now you're arguing about the number instead of the problem.

### ❌ Bad answer B
> "Sure, we can get to 99%."

You've agreed to something you can't deliver and probably can't even define.

### ✅ Good answer
> "Let's work out what number you actually need, because 99% might be too low or way too high depending on the failure.
>
> Two questions. First: when a reply goes out with a wrong pickup date, what happens? Second: how often does that happen today?
>
> *[VP: "Customer turns up, car isn't ready, they're annoyed. Maybe an hour of someone's time and a bad review sometimes. Today? Honestly it happens — advisors are guessing from bad notes."]*
>
> That's really useful. So the cost of that error is roughly an hour of staff time and some reputational risk — unpleasant, not catastrophic. And critically, the baseline isn't zero: it happens today at some rate nobody's measured.
>
> Now here's why 99% is the wrong target shape. Your own senior advisors agree with each other on 88 of 100 messages. So a single number above 88% isn't meaningful on this task — there isn't one right answer for the other 12%.
>
> What I'd propose instead is two numbers and a structure.
>
> **Fabricated facts: zero.** Not 99% — zero, enforced in code. Every date and price must appear verbatim in the repair order or the draft isn't shown. That's the failure that produces your waiting-room scenario, and it's the one worth being absolute about.
>
> **Send-as-is rate: target 70%+.** That's a productivity number, not a safety number. If it's 70%, advisors save time. If it's 40%, they still save time but less. Nobody gets hurt either way, because an advisor approves every message.
>
> Does that split match how you actually think about the risk?"

### Why it works

| Move | Effect |
|---|---|
| **Don't negotiate the number — reframe the question** | Arguing 99% vs 85% is unwinnable. Asking about error cost changes the frame entirely |
| Ask what the error costs, in real terms | Almost nobody has done this. Doing it with them is genuinely valuable |
| **Establish the current baseline isn't zero** | The comparison is never "AI errors vs no errors." It's "AI errors vs human errors" |
| Use the human-agreement ceiling | Makes the impossible target visibly incoherent rather than merely hard |
| **Split safety from productivity** | The key structural move: absolute on the dangerous failure, target-based on the useful one |

> **The generalisable principle:** *asymmetric error costs deserve asymmetric guarantees.* One blanket accuracy number bundles a catastrophic failure with a mildly annoying one and prices them the same. This is the same reasoning as blocking dimensions in [04.4](04-evals-are-the-deliverable.md) and hard-constraints-as-filters throughout [`../28_ai-system-design-by-industry/`](../28_ai-system-design-by-industry/README.md).

---

## 10.7 Role-play 5 — the production escalation

> **Slack, 4:40pm Friday, from the VP:** "This just sent a customer completely wrong information about their car. Turning it off."

### ❌ Bad answer
> "Can you send me the example? It's probably an edge case — the model is at 74% accuracy so occasional errors are expected."

Three failures: you've asked *them* to do work, you've minimised it, and you've cited a statistic at someone who's angry. "Expected" is the worst word available here.

### ✅ Good answer — in this order

**Immediately (within minutes):**
> "Turning it off is the right call — do it now, the kill switch is in Settings → AI Drafting → Disable, and advisors fall back to manual with nothing lost. I'm pulling the record for that message now and I'll have the specifics within the hour. I'll come back with what happened and whether it's one case or a class."

**Within the hour:**
> "Here's what happened.
>
> RO-4471. The customer asked about a pickup time. The note said 'parts ETA 8/2, waiting on supplier.' The draft said the car would be ready 8/2. That's wrong — 8/2 was the parts arrival date, not the completion date, and the draft treated them as the same thing.
>
> The grounding check passed because '8/2' *was* in the note verbatim. So this is a real gap in our checks, not a random model error: we verify that a date exists in the note, but not that it means what the draft claims it means.
>
> I've checked the other 340 drafts from this week against the same pattern. Four more have it, all where a note contains a parts ETA and no completion date. Three were edited by the advisor before sending; one went out.
>
> Two fixes. Immediately: any note containing a parts-ETA pattern with no completion date routes to 'I'll check and confirm' rather than drafting a date — I can ship that Monday morning and I've added the five cases to the eval set. Structurally: the grounding check needs to verify the *role* of an extracted fact, not just its presence, and that's a bigger piece of work — I'd want a week and I'll bring you the design.
>
> On the customer who received it: I'd suggest your team calls them today rather than waiting. Happy to draft the internal note explaining what happened.
>
> My read is: keep it off until Monday's fix is in and verified, then turn it back on. I'd rather lose two days than have this happen twice."

### Why it works

| Move | Effect |
|---|---|
| **Agree with turning it off, immediately** | Never defend uptime over trust in the first message. Endorsing the kill decision is what preserves your credibility |
| Commit to a specific time and deliver | The hour matters more than the fix |
| **Do the work yourself** — don't ask them for the example | You have the audit log. Using it is the whole point of having built it |
| Explain the mechanism precisely | "The check passed because the date was present but its meaning was wrong" is honest and specific |
| **Say whether it's one case or a class** | The single most important question, and the one they can't answer themselves. Checking 340 records is what turns panic into a manageable fact |
| Separate the immediate fix from the structural one | Shows judgement about what to rush and what not to |
| Address the affected customer | Their problem is a person, not a bug |
| Give a recommendation, not just options | They want a decision from someone who understands it |

> **Escalations are trust-building opportunities.** A well-handled incident buys more credibility than three months of things working, because it's the only time the customer sees how you behave under pressure. The audit log from [08.5](08-security-and-enterprise-blockers.md) is what makes this possible — without per-decision records, you're reduced to asking the angry VP to do your investigation.

---

## 10.8 The weekly written update

The highest-return 20 minutes of your week. It's how you stay trusted when things slip.

```markdown
# Draft-reply project — week of 10 March

## Status: ON TRACK for 14 March pilot (80% confident)

## Done this week
- Golden set expanded to 150 examples (+40 insufficient-note cases)
- Grounding check moved from prompt to code — fabricated facts 11 → 0
- Shadow mode running on live traffic since Tuesday

## Numbers
                        last week    this week    target
  send-as-is rate          68%         74%         70%  ✅
  fabricated facts        11/150       0/150         0  ✅
  p95 latency             3.4s         2.6s        <3s  ✅
  cost per accepted       $0.031      $0.028         —
  shadow vs golden gap       —          3pp        <5pp ✅

## Risks
1. 🔴 Security review not booked. This is the critical path to production.
   Owner: [name]. Asked 3 March, 10 March. Need a slot this week.
2. 🟡 Two advisors report tone mismatch. Building per-advisor few-shot from
   their sent history. Fix by 17 March.

## Decisions needed from you
- Confirm the 5 advisors for the pilot (asked 3 March, still open)

## Next week
- Per-advisor tone, pilot cutover prep, runbook v1
```

Four properties make it work:

| Property | Why |
|---|---|
| **A confidence on the headline status** | "On track, 80%" is information. "On track" is a claim |
| **The same metrics table every week** | Trends are visible; nobody has to ask "is that better?" |
| **Risks with an owner and an ask-date** | "Asked 3 March, 10 March" is a factual record, not a complaint — and it's the thing that protects you when the date slips |
| **A "decisions needed from you" section** | Makes their inaction visible without you having to raise it |

> **Write it even in a bad week — especially in a bad week.** The update you skip because the news is bad is the one that would have preserved trust. Slipping a date in a written update three weeks early is a schedule change; discovering it two days before is a credibility event.

---

## 10.9 Handling "can it also do X?"

Scope creep arrives as enthusiasm, which is why it's hard to refuse.

**Never say no. Never say yes. Say "that's v2, and here's what it would take."**

> "Good idea, and I think it's genuinely valuable. It's a different project though, and I'd rather be honest about that than quietly absorb it and miss March.
>
> Handling approval responses means writing to the DMS, which means a new service account, a sandbox you don't currently have, and a compliance review — call it six weeks after we finish this. I'll add it to the v2 list with that estimate.
>
> The thing that would make that conversation easy in six weeks: if the drafting pilot is running at 70%+ acceptance, you'll walk into the security review with evidence instead of a proposal. So finishing this well is the fastest route to that."

You've validated the idea, priced it honestly, protected the current date, and made the current work the path to the thing they want. **Maintain a visible v2 list** — it's where good ideas go to be remembered rather than absorbed, and its existence is what makes deferral feel like acknowledgement rather than refusal.

---

## 10.10 Interview signal

The role-play round *is* this file. What they're scoring:

| They're watching for | Not |
|---|---|
| Do you ask what the number is *for* | Do you know the model's accuracy |
| Do you reframe to the human baseline | Do you defend the technology |
| Do you separate dangerous from imperfect failures | Do you promise a percentage |
| Do you give a recommendation | Do you list options and wait |
| Do you say "I don't know" cleanly | Do you bluff |
| Do you handle being wrong without defensiveness | Do you cite statistics at an angry person |

**The single highest-scoring move across all five scenarios:** *asking a clarifying question that reframes the problem before answering.* "What does the board actually need to see?" — "What happens today when a reply is wrong?" — "How often does that happen now?" Interviewers are explicitly listening for whether you consult before you commit.

**The single lowest-scoring move:** citing a model capability or an accuracy statistic as an answer to a question about risk or trust. It reads as someone who understands models and not customers, which is precisely the failure mode this round exists to detect.

---

> ← [`09-pilot-to-production.md`](09-pilot-to-production.md) · **Index:** [`README.md`](README.md) · **Next:** [`11-the-fde-toolkit.md`](11-the-fde-toolkit.md) →
