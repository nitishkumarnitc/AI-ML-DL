# 02 — Agentic AI & Orchestration

> Core round. They explicitly want LangGraph/AutoGen, multi-agent orchestration, long-horizon planning, and tool-augmented reasoning.

---

## 🧠 Mental model: the agent stack

```
User / Event
   │
[ Orchestrator ]  ← control flow: single agent, supervisor, or graph
   │
[ Planner / Router ]  ← decompose task, pick next step/agent
   │
[ Reasoning loop ]  ← LLM ⇄ Tools (ReAct / plan-execute / reflection)
   │
[ Tools ]  ← retrieval, APIs, code exec, DB, other agents
   │
[ Memory ]  ← short-term (context/scratchpad), long-term (vector/KG/DB)
   │
[ Guardrails + Eval + Observability ]  ← wraps everything
```

**Principal framing:** an agent is a *distributed system with an LLM in the control loop*. Everything you know about retries, idempotency, timeouts, backpressure, and observability applies — the LLM just makes control flow non-deterministic, which makes eval and guardrails mandatory, not optional.

---

## 🔀 LangGraph vs AutoGen (know the trade-offs cold)

| | **LangGraph** | **AutoGen** |
|---|---|---|
| Model | Explicit **state graph** (nodes = steps/agents, edges = transitions), typed shared state | **Conversational** multi-agent (agents chat to solve tasks) |
| Control | Deterministic, inspectable control flow; you own the transitions | Emergent via conversation; more autonomous |
| Best for | Production, auditable, long-horizon workflows with checkpointing | Rapid prototyping, research, exploratory multi-agent |
| Persistence | First-class **checkpointing** → resume, time-travel, human-in-the-loop | Weaker out of the box |
| Auditability | High (explicit state + transitions) | Lower (chat transcripts) |
| Your pitch | **"For regulated debt workflows I default to LangGraph — the explicit state machine gives auditability and deterministic recovery, which conversational frameworks don't."** | Mention as a valid choice for internal/exploratory tooling |

**Why LangGraph wins for a regulated debt platform (say this):** explicit state → you can log/replay every transition (audit), checkpoint → human sign-off gates and crash recovery, typed state → fewer silent failures. In a lending/debt context, "I can prove exactly what the agent did and why" is worth more than autonomy.

Also be ready to name alternatives: **CrewAI** (role-based, opinionated), **OpenAI Agents SDK / Swarm** (lightweight handoffs), **LlamaIndex agents**, plain **function-calling loops**. Principal signal = "framework is an implementation detail; the state model and eval harness are what matter."

---

## 🏗️ Multi-agent patterns (be able to draw each)

1. **Single agent + tools (ReAct)** — one LLM loop, reason→act→observe. Default; don't over-engineer.
2. **Supervisor / orchestrator-worker** — a router agent delegates to specialist agents (e.g., `DocExtractionAgent`, `RiskScoringAgent`, `ComplianceAgent`), aggregates. Most common production shape.
3. **Hierarchical** — supervisors of supervisors for complex decomposition.
4. **Pipeline / sequential** — deterministic stages (extract → validate → decide → explain). Great when steps are known.
5. **Blackboard / shared state** — agents read/write shared state, coordinate loosely.
6. **Debate / reflection** — agents critique each other or self (improves quality, costs tokens/latency).

**When to use multi-agent vs single:** Default to **single agent + good tools**. Reach for multi-agent only when (a) distinct skills/prompts/models per subtask, (b) parallelizable subtasks, (c) separation for safety/auditing (e.g., a dedicated compliance-check agent). *"More agents = more latency, cost, and failure surface. I add agents to reduce complexity per unit, not to look sophisticated."*

---

## 🔁 Long-horizon planning (they named this explicitly)

Patterns to discuss:
- **Plan-and-execute** — planner drafts a plan, executor runs steps, replan on failure. Better for long tasks than pure ReAct (which drifts).
- **ReAct** — interleaved reason/act; good for short, tool-heavy tasks.
- **Reflexion / self-critique** — agent evaluates its own output, retries with feedback.
- **Tree-of-thought / search** — branch over options, score, prune (expensive; use where correctness >> cost).

**Failure modes of long-horizon agents (Principal must volunteer these):**
- **Context rot / window overflow** → summarize/compact state, external memory, structured state not raw transcript.
- **Goal drift / looping** → step budgets, loop detection, explicit termination conditions.
- **Compounding errors** → each step's error probability multiplies; add validation checkpoints, not just an end check.
- **Cost/latency blowup** → cap steps, cache, smaller models for routing/subtasks.

**Control the loop:** max steps, per-step timeouts, cost budget, human-in-the-loop gates at high-risk transitions (e.g., before writing to a system of record). Checkpoint so a failed 12-step workflow resumes at step 9, not step 1.

---

## 🛠️ Tool-augmented reasoning

- **Tool design > agent cleverness.** Good tools = narrow, well-described, validated I/O, idempotent where possible. Bad tool schemas cause most agent failures.
- **Structured outputs / function calling** — force JSON schema, validate, retry on parse failure. In fintech, never free-text a number that becomes a transaction.
- **Tool selection at scale** — with 50+ tools, the LLM picks wrong. Solutions: **retrieve relevant tools** (semantic tool-selection / RAG over tools), namespacing, or a router that narrows the toolset per subtask.
- **MCP (Model Context Protocol)** — worth mentioning: standardizes tool/context exposure to agents; relevant given your recent MCP work. Frame as "how we expose internal services to agents in a governed, reusable way."
- **Determinism where possible** — if a step can be code/SQL/rule instead of LLM, make it so. LLMs for judgment, code for arithmetic and lookups.

---

## 🧱 Platform-level abstractions & SDKs (the Principal ask)

The JD says: *"Define platform-level abstractions and SDKs that accelerate AI agent development across multiple product teams."* Have an opinion:

- **What to standardize:** agent base runtime (state, checkpointing, retries), tool registry + governance, prompt/version management, eval harness, observability/tracing, guardrail middleware, model gateway (routing, fallback, rate limits, cost tracking).
- **What to leave flexible:** business logic, prompts, tool implementations per domain.
- **SDK shape:** `@company/agent-sdk` — declare an agent (state schema, tools, model policy, guardrails) and get tracing, eval hooks, checkpointing, and a deployment path for free. Product teams write domain logic, not plumbing.
- **Golden path + escape hatches** — opinionated defaults, but escapable for edge cases. This is the classic platform-team stance.

---

## 🎙️ Likely questions + answer scaffolds

- **"Walk me through a multi-agent system you built."** → Problem → why multi-agent (skills/parallel/safety) → the graph (draw it) → state/memory → tools → how you evaluated it → what broke in prod and how you fixed it → numbers/impact.
- **"When would you NOT use agents?"** → When a deterministic pipeline/RAG/single tool call suffices. Agents add non-determinism, cost, latency, failure surface. Use for open-ended, multi-step, tool-heavy judgment tasks.
- **"How do you stop an agent from looping / running up cost?"** → step + token + cost budgets, loop detection, termination conditions, checkpointed replan, cheaper router models, caching.
- **"How do you make an agent auditable for a regulator?"** → explicit state machine (LangGraph), immutable trace of every prompt/tool-call/decision with versions, deterministic replay, human sign-off gates, and an explanation artifact per decision. → ties to [04](04_LLMOps_Eval_Guardrails.md).
- **"LangGraph vs AutoGen for us?"** → LangGraph for production/regulated (auditability, checkpointing); AutoGen for internal exploration. Framework is secondary to state model + eval.
- **"How do you handle tool errors mid-workflow?"** → typed tool results, retries w/ backoff, fallback tools, let the agent see the error and replan, checkpoint before risky writes, circuit-break repeated failures, escalate to human.

**Draw a diagram unprompted.** For any agent question, sketch the graph — it demonstrates you think in systems, not prose.
