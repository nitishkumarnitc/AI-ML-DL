# 06 · Agentic AI and MCP

> ← [`05-security-compliance-and-safety.md`](05-security-compliance-and-safety.md) · **Index:** [`README.md`](README.md) · **Next:** [`07-the-production-postmortem-question.md`](07-the-production-postmortem-question.md) →

---

## Q26 — When do you build an agentic system versus just calling an LLM directly?

### The worked example that opens the answer

> Imagine you started a hotel business and linked it to a food-delivery platform. Three months in, you notice your sales are lower than competitors'. You could analyze this yourself — or you could **develop an agent** that analyzes your own business *and* your competitors' businesses: what promo codes they're running, on which days, at what times. You just tell the agent "this is my problem." **It thinks on its own, analyzes on its own, and finally produces a report — and can even generate the code to act on its findings.** That's the agentic behavior: planning on its own, dividing the problem itself, and solving it, refining as needed.

### The actual decision rule

| Use an **agent** when... | Use a **simple LLM call** when... |
|---|---|
| The task requires **multiple tools** (search, calculator, API calls) | The task is **single-step, well-defined** |
| The steps genuinely **can't be planned upfront** — they depend on what's discovered along the way | Speed and **high volume** matter more than flexibility |
| You need to interact with **external systems** dynamically | |

### The cautionary counter-example, given explicitly as a warning

> A startup tried to build an agentic customer chatbot where **every single query** went through a 5-step planning process, used 3 tools, and did self-verification per response — taking **18 seconds per response** and driving costs up. The pushback given: *"Every interviewer has built an agent for everything at some point. Showing you know **when not to use an agent** is the more valuable signal."*

---

## Q27 — How do you prevent an agent from getting stuck in an infinite loop?

The presenter notes this is covered in more depth in a separate 5-part agentic-AI series (linked from the original video's description) and gives the short version here:

- **Impose hard iteration limits** — e.g. cap execution at 10–15 steps, so a loop can't run indefinitely
- **Loop detection** — detect when the agent is repeating the same action/state (this is the actual "backtracking" mechanism — the agent needs a way to recognize it's looping and break out)
- **A supervisor agent pattern** — a separate agent whose only job is to **watch the primary agent's progress** and call a clear termination when it detects the main agent isn't converging

Named example of where this bites in practice: getting caught in a loop while using **LangGraph** for agent orchestration — a real, common failure mode, not a hypothetical.

---

## Q28 — What is MCP (Model Context Protocol)?

### The problem MCP solves — explained through the "before" state

> Before MCP: if your project needs to use Postgres, call some cache memory, and hit a few different APIs, you had to **write separate custom integration code for each one** — write the connection logic, check whether the connection was working, format the input, format the output, handle errors — **for every single tool, separately.**

### What MCP actually changes

> With MCP, you define your API/tool **once**, as an MCP server. The AI model just **calls the MCP endpoint** — MCP itself handles the connection check, the input formatting, and the output handling. You write the integration once; any MCP-compatible model (Claude, GPT, Gemini) can now use it.

### The two analogies given, both worth keeping

**1. USB-C for AI.** *"Before USB-C, every device had its own cable — headphones, camera, printer, all different standards. USB standardized everything. MCP does the same thing for AI tools: build once, work everywhere."*

**2. The Notion example.** *"Before MCP, connecting Claude to your company's Notion meant writing custom Python code against the Notion API — handling OAuth, handling formatting, handling errors — weeks of work. With MCP, you install the Notion MCP server, configure it once, and Claude can immediately read and write Notion. The same MCP server works for any MCP-compatible model — you're not rewriting the integration per model."*

**One-line definition to give in an interview:** *"MCP is a universal standard, created by Anthropic, for connecting an AI model to any tool, app, or data source — without writing custom integration code for each one."*

---

## Q29 — What is Agentic AI, in one clear example?

Given as a companion to Q26, with a fresh worked example specifically to nail the "biggest gap" question — i.e. what makes something *agentic* rather than just an LLM call with tools:

> A **marketing manager agent**, told "launch my new product on social media," would: **generate five different posts**, **generate and schedule matching images**, **post to LinkedIn, X, and Instagram itself**, **respond to comments**, and **send a daily report every three days** — from a single high-level instruction. Roughly "30 minutes of manager-level work," done end-to-end without being told each individual step.

The distinguishing property, stated plainly: the human gives the *goal*, not the *steps*. The agent plans, executes across multiple tools/platforms, and reports back — that's what separates it from a single well-defined LLM call.

---

> ← [`05-security-compliance-and-safety.md`](05-security-compliance-and-safety.md) · **Index:** [`README.md`](README.md) · **Next:** [`07-the-production-postmortem-question.md`](07-the-production-postmortem-question.md) →
