# Video 03 — What is Agentic AI?

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `GWnSsjT4V68`
> **Watch:** https://www.youtube.com/watch?v=GWnSsjT4V68

## 🎯 Overview
The second content video and a fully theoretical one. It formally answers *what agentic AI is*, walks through the recurring HR-recruiter example to build intuition, and then systematically covers the **six key characteristics** of any agentic AI system and its **five high-level components**. The instructor recommends taking notes because this theory underpins all the hands-on agent building later in the playlist.

## 🧠 Key Concepts

### Definition of Agentic AI
> *Agentic AI is a type of AI that can take up a task or goal from a user and then work toward completing it on its own with minimal human guidance. It plans, takes actions, adapts to changes, and seeks help only when necessary.*

It is a software paradigm: you give the system a **goal**, and it autonomously figures out how to achieve it — doing the **planning** and **execution** itself with minimal human involvement. This contrasts with **reactive** paradigms like a generative-AI chatbot.

**Reactive vs proactive (Goa-trip analogy):** With a GenAI chatbot you ask one question at a time ("best way to reach Goa on the 15th?" → "which hotels?" → "where to visit given the weather?") and it answers exactly that, nothing more. An agentic system, told only "I want to go to Goa between these dates," *proactively* researches travel, recommends hotels, and plans the full itinerary on its own.

### The HR-recruiter example (agentic version)
Given the goal "hire a remote backend engineer, 2–4 yrs," the agent: understands the goal → **plans** (draft JD → post to best platforms → continuously monitor applications → tweak if too few apply → screen candidates → schedule interviews → send offer → onboard) → **executes** step-by-step autonomously. It asks permission at risky checkpoints (e.g., before posting), **adapts** when applications are low (switch backend→full-stack, run LinkedIn ads), uses tools (LinkedIn/Naukri APIs, resume parser, calendar, mail, HRMS), and keeps notifying you. The striking feature is how **autonomous** it is — you mostly approve; it does the heavy lifting.

### The six key characteristics
Ask these six questions of any chatbot/app; if all are "yes," it is agentic.

#### 1. Autonomy
> *Autonomy refers to an AI system's ability to make decisions and take actions on its own to achieve a given goal without needing step-by-step human instructions.*

Autonomy makes the system **proactive** (it acts before being told). It shows up in multiple aspects: **execution** (auto-running each planned step), **decision-making** (deciding how many candidates to shortlist and on what basis), and **tool usage** (deciding which tool to use when).

**Controlling autonomy (important, because unchecked autonomy is risky):**
- **Scope of permissions** — limit what tools/actions the agent can perform independently (e.g., "screen everyone, but ask before rejecting anyone").
- **Human-in-the-loop checkpoints** — insert points where human approval is required before continuing (e.g., approve before posting the JD).
- **Override controls** — let humans **stop / pause / change** the agent's behavior at any time (e.g., a "pause hiring" command).
- **Guardrails & policies** — hard rules and ethical boundaries (e.g., "never schedule interviews on weekends," "never use informal language in emails").

**Dangers of uncontrolled autonomy:** rolling out offers with incorrect salary/terms, biased shortlisting (by nationality/age — illegal in some countries), or spending unlimited money boosting a LinkedIn post.

#### 2. Goal-oriented
> *Being goal-oriented means the AI system operates with a persistent objective in mind and continuously directs its actions to achieve that objective rather than just responding to isolated prompts.*

The goal acts as a **compass** for autonomy — without a goal, autonomous functioning has no direction, so the two traits move hand-in-hand. Goals can be **independent** ("hire a backend engineer") or carry **constraints** ("...from India," "...remote only," "...within a budget"). Goals are stored in the agent's **core memory** and **can be altered midway** (e.g., abandon hiring and instead find a freelancer), which then re-triggers planning.

#### 3. Planning (the most important trait)
> *Planning is the agent's ability to break down a high-level goal into a structured sequence of actions or sub-goals.*

Agentic systems operate in two steps — **planning** then **execution** — and this is **iterative** (a loop): if step 4 turns out impossible mid-execution, the agent returns to planning and re-plans. Planning is essentially a **search problem**: from an **initial state** (company needs an engineer) to a **final state** (engineer hired), with multiple possible paths; pick the most optimized.

**Three sub-steps of planning:**
1. **Generate multiple candidate plans** (e.g., Plan A: post on LinkedIn/GitHub Jobs/AngelList; Plan B: internal referral or hiring agency).
2. **Evaluate the plans** against criteria: **efficiency** (speed), **tool availability** (reject a plan needing a Google-Search tool you don't have), **cost** (budget constraints), **risk** (chance of failure), and **alignment with constraints** (remote-friendly?).
3. **Select the best plan** — via **human-in-the-loop** input or a **pre-programmed policy**.

#### 4. Reasoning
> *Reasoning is the cognitive process through which an agentic AI system interprets information, draws conclusions, and then makes decisions — both while planning and executing.*

**Human analogy:** phone gets stolen → interpret the situation → conclude the thief may misuse your number → decide to call the carrier and block the number.

Reasoning is needed in **planning** (goal decomposition, tool selection, resource/dependency/risk estimation) and in **execution** (decision-making among options, deciding when to involve a human, and **error handling** — e.g., LinkedIn server down → retry, notify a human, or try another platform).

#### 5. Adaptability
> *Adaptability is the agent's ability to modify its plans, strategies, or actions in response to unexpected conditions, all while staying aligned with the goal.*

**Reasons to adapt:** (a) **failures** — a tool (e.g., calendar API) goes down, so the agent asks you for availability directly; (b) **external feedback from the environment** — the LinkedIn app reports very few applicants, prompting a strategy change; (c) **mid-way goal changes** — switching from hiring an engineer to hiring a freelancer. This introduces the notion of the **environment**: the world the agent operates in (a chessboard for a chess agent; road + pedestrians for a self-driving agent; applicants + LinkedIn + the human for the recruiter agent).

#### 6. Context Awareness
> *Context awareness is the agent's ability to understand, retain, and utilize relevant information from the ongoing task, past interactions, user preferences, and environmental cues to make better decisions throughout a multi-step process.*

A multi-day hiring process can't function if the agent forgets. **Context it stores:** the **original goal**, **progress so far** and human↔agent conversation, **environment state** (job posted, 8 applicants; ad budget expiring), **tool responses** (resume parser: "Candidate B has 3 yrs Django + AWS"; calendar: "free at 2 PM"), **user preferences** (company prefers remote; deliver questions via Google Doc), and **policies/guardrails**.

Context awareness is implemented through **memory**, of two kinds:
- **Short-term memory** — current-session info (like a human remembering "I'm shooting a video, due before 4 PM").
- **Long-term memory** — persistent info (like "I live in Gurgaon; my job is..."). Example: a resume-parser result is short-term; the guardrail "never send an offer letter without approval" is long-term.

### The five high-level components
1. **Brain (the LLM).** For LLM-based agents, the LLM is the brain and does most of the heavy lifting: **goal interpretation**, **planning** (goal → sub-goals), **reasoning** (in both stages), **tool selection**, and **natural-language communication** with the human.
2. **Orchestrator.** Executes the plan step-by-step. Responsibilities: **task sequencing**, **conditional routing** (which step comes next based on a result), **retry logic**, **looping/iteration**, and **delegation** (when to hand a task to a human vs the LLM). Analogy: the **nervous system** / the **project manager** of the agent. Built using frameworks like **LangGraph**, **CrewAI**, or **AutoGen**.
3. **Tools.** How the agent interacts with the external world — API calls, database changes, sending mail. Analogy: the agent's **hands and legs**. A **RAG knowledge base** is also a kind of tool (retrieve factual/domain-specific info to ground responses).
4. **Memory.** **Short-term** (current-session user messages, tool calls, immediate decisions), **long-term** (high-level goals, past interactions, user preferences, cross-session decisions), plus **state tracking** (how much is done vs remaining).
5. **Supervisor.** Implements **human-in-the-loop** — makes agent and human work together. Used for **approvals** on high-risk actions (send offer, run paid ads), **enforcing guardrails**, and handling **escalations / edge cases** (e.g., a great candidate who violates a "hire only from IITs/NITs" guardrail is flagged to a human).

## 🔧 Code / Implementation
No runnable code; the video shows one **conceptual** representation — how a goal is stored in an agent's memory (JSON-like):

```json
{
  "main_goal": "Hire a backend engineer",
  "constraints": {
    "experience_years": "2-4",
    "remote": true,
    "stack": ["Python", "Django", "AWS"]
  },
  "status": "active",
  "created_at": "<timestamp>",
  "progress": {
    "jd_created": true,
    "posted_on": ["LinkedIn", "Naukri"],
    "applications_received": 8,
    "interviews_scheduled": 2,
    "hired": false,
    "onboarded": false
  }
}
```
This is illustrative only — different libraries store goals differently.

## 📌 Key Takeaways
- **Agentic AI = goal in, autonomous plan + execution out**, with minimal human guidance and help sought only when necessary.
- It is **proactive/autonomous**, unlike the **reactive** generative-AI chatbot.
- Six defining characteristics: **Autonomy, Goal-oriented, Planning, Reasoning, Adaptability, Context Awareness** — a practical checklist for identifying an agentic system.
- **Autonomy must be controlled** via scoped permissions, human-in-the-loop checkpoints, override controls, and guardrails/policies.
- **Planning is the most important trait** — a two-step (plan → execute), iterative process, framed as a search problem: generate candidate plans → evaluate → select.
- **Reasoning** powers both planning and execution (goal decomposition, tool selection, decision-making, error handling).
- Five components: **Brain (LLM), Orchestrator, Tools, Memory, Supervisor** — brain interprets/plans, orchestrator runs the plan, tools act on the world, memory retains context, supervisor keeps humans in the loop.
