# 01 · Requirements — Multi-Agent System

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#3-multi-agent-ai-system`](../00_requirements_all_systems.md#3-multi-agent-ai-system)

---

## 1.1 Problem & users

### Establish the premise before designing

Most "design a multi-agent system" answers begin by drawing agents. The stronger answer begins by
asking whether multi-agent is warranted at all — because **a single agent with good tools beats a
multi-agent system for most tasks, at a fraction of the cost and with far less to debug.**

**The three conditions that justify the complexity.** Multi-agent earns its keep when *at least one*
holds strongly:

| Condition | Why it justifies multi-agent | Fails if… |
|---|---|---|
| **Parallelizable subtasks** | Wall-clock becomes the slowest *chain*, not the sum. This is the only condition that delivers a speed win | Subtasks are strictly sequential — then you've added handoff loss for nothing |
| **Different tools or privileges** | A web-research agent and a database agent can hold different, narrower allow-lists — least privilege becomes enforceable per role | All subtasks need the same permissions — one agent with all the tools is simpler and safer |
| **Independent verification** | A critic that did not produce the work catches errors the producer is blind to | The output is deterministically checkable — then use a checker, not an agent |

### The task class chosen here

Tasks that decompose into independent research-and-synthesis work. The worked example:

> *"Research these 5 competitors and produce a comparison memo."*

Checked against the conditions:

| Condition | Holds? | Evidence |
|---|---|---|
| Parallelizable | ✅ **Strongly** | 5 competitors researched independently; 5× theoretical parallelism |
| Different privileges | ✅ | Web research (external, read-only) vs internal DB (sensitive) vs file write (side-effecting) |
| Independent verification | ✅ | A critic checks claims against gathered evidence without having produced it |

All three hold, so the architecture is justified. **If a task fails all three, the honest answer is to
route it to [02](../02_customer_support_agent/README.md)'s single-agent design** — and saying so is a
stronger signal than building the elaborate thing regardless.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **Knowledge worker (primary)** | Delegate a multi-step task | A correct compiled deliverable, without babysitting |
| Platform operator | Keep spend bounded | No run can exceed its cap; cost per run is attributable |
| Reviewer | Trust the output | Sources traceable; the critic's verdict visible |

### The defining constraint

**Cost is multiplicative.** In a single-agent system, cost scales with conversation length. Here it
scales with `subtasks × turns-per-subtask × retries` — and each factor is itself variable. A design
that budgets by analogy to single-agent systems will be wrong by an order of magnitude.

> **Mental model:** the planner is a **project manager**, workers are **contractors**, the blackboard
> is the **shared job file**, and the budget governor is the **finance controller who can stop the
> project.**
>
> *Where the analogy breaks:* contractors notice when a job is going nowhere and stop. An agent will
> cheerfully retry the same failing approach until something external stops it — which is exactly why
> the budget governor and loop detection are infrastructure rather than optional polish.

---

## 1.2 Functional requirements

### Planning

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Decompose a goal into a **DAG** of subtasks | Valid, **acyclic**, dependency-correct; rejected and re-planned if cyclic |
| FR-11 | P2 | Dynamic replanning when a subtask reveals new information | Bounded by the step cap; **cannot extend the budget** |

**Why a DAG and not a list.** A list forces sequential execution and forfeits the parallelism that is
the entire justification for the architecture. A DAG makes dependencies explicit, so the scheduler can
dispatch everything whose inputs are ready. **Acyclicity must be validated, not assumed** — a planner
LLM will occasionally emit a cycle, and an unvalidated cycle is an infinite loop with a bill attached.

### Execution

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-2** | P0 | Execute independent subtasks **in parallel** | Wall-clock < sum of subtask durations; ≥ 3× speedup on parallelizable DAGs |
| **FR-3** | P0 | **Per-agent tool allow-lists** | An agent cannot invoke a tool outside its list — enforced at the gateway, not the prompt |
| **FR-4** | P0 | Shared state readable by all agents | Consistent reads; **no lost updates** under concurrent writes |
| FR-7 | P1 | Retry a failed subtask **without restarting the run** | Subtask execution is idempotent; completed work is preserved |
| FR-10 | P1 | Human checkpoint before side-effecting actions | Reuses [02](../02_customer_support_agent/03_lld.md#the-policy-engine)'s policy-engine pattern |

**FR-3 is where multi-agent pays a security dividend.** With one agent, the tool set is the *union* of
everything any task might need — the agent that answers a question can also write files. Per-agent
allow-lists make least privilege enforceable per role: the web-research agent cannot touch the
database, and the writer agent cannot make outbound HTTP calls.

### Control — the P0 that designs usually defer

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-5** | P0 | **Hard budget caps: tokens, wall-clock, step count, dollars** | Run aborts at any cap with partial results; **never runs away** |
| **FR-6** | P0 | Synthesize subtask outputs into one deliverable | Cites which subtask produced each claim |
| FR-8 | P1 | Verifier/critic reviews the result before return | Catches ≥ 50% of injected errors on the eval set |
| FR-9 | P1 | Full run trace: plan, every step, tool calls, cost | Replayable |

**FR-5 is P0 because the failure it prevents is unbounded.** Every other requirement here degrades
gracefully if unmet — a slower run, a worse memo. Without caps, a replanning loop can spend
arbitrarily much money before anyone notices. **The cap is the difference between a bounded product
and an open-ended liability.**

---

## 1.3 Non-functional requirements

### Performance

| NFR | Target | Why this number |
|---|---|---|
| E2E run time | p95 < 5 min for 10 subtasks | Async UX — the user starts it and does something else. Beyond ~5 min they lose the thread |
| **Parallel speedup** | **≥ 3×** vs sequential | **The architecture's justification.** Below 3×, single-agent is the better trade |
| Step cap | ≤ 50 agent steps/run | Runaway backstop; ~5 steps × 10 subtasks |
| Scheduler dispatch latency | < 100 ms after deps satisfied | Idle workers waste wall-clock, which is the metric we're buying |

**Stating a speedup target makes the architecture falsifiable.** If measured speedup is 1.4×, the
design has failed on its own terms and should be replaced by a single agent — and having a number
means you'd notice.

### Cost

| NFR | Target | Why |
|---|---|---|
| Cost per run | ≤ $2.00 | Above this, a human doing the task is cheaper for most tasks in this class |
| **Hard abort** | **$5.00** | Circuit breaker — bounds worst-case blast radius per run |
| Worker model tier | Small | Workers do bounded, well-specified subtasks; frontier reasoning is wasted on them |
| Planner/critic tier | Frontier | Planning and criticism are the genuinely hard reasoning steps |

**The tier split is the main cost lever.** Running 50 worker steps on a frontier model costs ~5× more
for work that a small model does adequately, because a well-specified subtask ("summarize this page's
pricing section") needs execution, not reasoning.

### Correctness & reliability

| NFR | Target | Why |
|---|---|---|
| Task success | ≥ 0.80 on the eval suite | Below this, users stop delegating |
| **Plan determinism** | Same input + versions → **same plan** | Debuggability. Execution may vary; the plan should not |
| Critic catch rate | ≥ 50% of injected errors | Sets whether human review is optional or mandatory |
| Availability | 99.9% | Async; retries absorb transient failures |
| **State isolation** | One agent's failure cannot corrupt the blackboard | Transactional writes with optimistic concurrency |

**Plan determinism, not execution determinism.** LLM execution is inherently variable and forcing
determinism there would mean `temperature=0` everywhere plus caching — expensive and brittle. But the
*plan* is a single call from a fixed prompt, so it can be made reproducible, which is what you actually
need when debugging "why did this run go wrong?"

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Open-ended autonomy** | Every run is goal-scoped and bounded. Unbounded agents are unbounded cost and liability | Never at this maturity |
| **Free-form agent-to-agent chat** | Burns tokens, degrades into loops, no audit point. Coordination goes through the blackboard | Never — see [§2.2](02_hld.md#22-component-choices) |
| Agents writing production code unreviewed | Side-effecting actions gate through human approval | — |
| Self-modifying agents | Agents cannot alter their own prompts, tools, or budgets | — |
| Emergent role negotiation | Roles are statically defined with fixed allow-lists | Would require rethinking [FR-3](#execution) entirely |
| Long-running (hours/days) runs | 10-minute wall-clock cap | A genuine batch use case emerges — different design |

**"No free-form agent chat" is the non-goal most worth defending**, because it's what people imagine
multi-agent systems *are*. Agents conversing in natural language produces: quadratic token growth,
context drift, no deterministic termination, and no artifact to audit. Structured blackboard writes
give the same information sharing with bounded cost and a replayable trace.

---

## 1.5 Latency budget

Wall-clock, not TTFT — this is async. **The target is that parallelism actually pays off.**

### A 10-subtask DAG with 5 parallel branches

| Stage | Budget (p95) | Notes |
|---|---:|---|
| Planning (1 frontier call) | 8 s | Longest single call; produces the whole DAG |
| DAG validation | 50 ms | Acyclicity + schema check, deterministic |
| **Wave 1** — 5 parallel subtasks, ~5 steps each | **90 s** | The *slowest branch*, not the sum |
| **Wave 2** — 3 parallel subtasks (depend on wave 1) | **60 s** | |
| **Wave 3** — 2 parallel subtasks | 45 s | |
| Synthesis (1–2 frontier calls) | 25 s | |
| Critic (1–2 frontier calls) | 20 s | |
| **Total** | **≈ 4 min 8 s** | vs 5 min SLO → ~50 s headroom ✅ |

### The speedup that justifies the architecture

```
Sequential equivalent: 10 subtasks × ~18 s each  = 180 s
                     + planning 8 + synth 25 + critic 20 = 233 s ≈ 3 min 53 s

Wait — sequential is FASTER than the parallel budget above (4 min 8 s)?
No: the parallel waves are bounded by their SLOWEST branch, and the slowest
branch contains more steps than the average subtask.

Honest recomputation with per-subtask times:
  subtask durations: [90, 40, 35, 30, 25, 60, 45, 30, 45, 20] s   (assumption A1)
  sequential sum                                        = 420 s
  critical path through the DAG (wave maxima 90+60+45)  = 195 s
  ⇒ speedup on execution = 420/195 ≈ 2.2×

  With fixed overhead (planning 8 + synthesis 25 + critic 20 = 53 s):
  sequential total = 473 s ; parallel total = 248 s ⇒ overall ≈ 1.9×
```

> **⚠️ This does not meet the ≥ 3× NFR, and that matters.** Two honest conclusions:
>
> 1. **Fixed overhead (planning + synthesis + critic = 53 s) is unavoidable and unparallelizable**, so
>    it caps achievable speedup — Amdahl's law applied to agents. At 10 subtasks it's ~21% of the
>    parallel run.
> 2. **Speedup improves with more subtasks**, since fixed overhead amortizes: at 20 subtasks with the
>    same critical-path structure, overall speedup approaches ~2.8×.
>
> **Options:** relax the NFR to ≥ 2× (defensible — still a real win), require ≥ 15 subtasks before the
> multi-agent path is chosen at all, or cut fixed overhead by making the critic conditional on
> subtask-level confidence rather than always-on. **My recommendation: relax to 2× and make the critic
> conditional**, which recovers ~20 s and lands near 2.3×.

**Getting to this finding is the point of writing the budget out.** A design that asserts "≥ 3× speedup"
without computing the critical path has stated a hope, not a target.

---

## 1.6 Capacity & cost estimation

Rates per [`../00_requirements_all_systems.md#shared-conventions`](../00_requirements_all_systems.md#shared-conventions).

### The naive run

```
Structure: 10 subtasks × 5 turns each, plus planner/synthesizer/critic

Worker turns on FRONTIER tier (the naive default):
  per turn: (3000/1e6 × $3.00) + (500/1e6 × $15.00) = $0.009 + $0.0075 = $0.0165
  10 × 5 × $0.0165                                                     = $0.825

Overhead calls (planner 3, synthesizer 2, critic 2 = 7 frontier calls):
  7 × $0.0165                                                          = $0.116
                                                                         ───────
Total                                                                  ≈ $0.94/run   ✅ under $2.00
```

### Where it explodes

```
+ ONE retry per subtask:        10 × 5 × $0.0165 again        ⇒ ≈ $1.77   ← at the ceiling
+ Critic fails once, re-run:    + synthesis + affected work   ⇒ ≈ $2.40   ← OVER
+ Unbounded replanning:                                        ⇒ UNBOUNDED
```

**Three multiplicative factors, each individually reasonable, jointly fatal.** This is why
[FR-5](#control--the-p0-that-designs-usually-defer) is P0.

### With the worker tier fixed

```
Workers on SMALL tier:
  per turn: (3000/1e6 × $0.15) + (500/1e6 × $0.60) = $0.00045 + $0.0003 = $0.00075
  10 × 5 × $0.00075                                                     = $0.0375
Overhead stays frontier (planning/criticism need it)                    = $0.116
                                                                          ───────
Total                                                                   ≈ $0.15/run

⇒ 6× cheaper than naive, and now a retry-heavy run (~$0.30) is still well
  inside budget. The tier split is the single highest-leverage cost decision.
```

### Enforcement mechanisms — all required

| Control | Mechanism | Limit |
|---|---|---|
| Token budget | Atomic decrement per call; abort at zero | Derived from the $ cap |
| **Step cap** | Hard counter across all agents | 50 steps |
| **Wall-clock cap** | Run deadline; abort with partials | 10 min |
| **Dollar cap** | Running total; pre-flight estimate per call | $5.00 hard |
| **Loop detection** | Abort if `(agent, tool, args_hash)` repeats 3× | 3 |
| Replan cap | Replans per run | 2 |

**Why all five and not just the dollar cap.** They fail differently: a dollar cap won't stop a run
stuck making free blackboard reads for ten minutes; a wall-clock cap won't stop a run that burns $5 in
thirty seconds; loop detection catches a cheap-but-pointless cycle that no aggregate cap would notice
until it had run a long time.

### Throughput

```
Assume 500 runs/day
  Cost:  500 × $0.15 = $75/day ≈ $2,250/month
  LLM calls: 500 × (50 worker + 7 overhead) ≈ 28,500/day ≈ 0.33 QPS  ⇒ trivial

Concurrency: assume 20 runs in flight × up to 5 parallel workers = 100 concurrent agent steps
  ⇒ the constraint is PROVIDER RATE LIMITS during parallel waves — bursty, not sustained.
    A 5-wide wave fires 5 calls simultaneously; 20 concurrent runs ⇒ 100-call bursts.
```

**Burstiness, not volume, is the capacity risk.** Average QPS is negligible but parallel waves produce
synchronized bursts, which is exactly what provider rate limiters punish. Needs client-side shaping —
see [F6](02_hld.md#25-failure-modes--blast-radius).

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | Tasks decompose into ≤ 10 subtasks with the stated duration profile | Medium | Deeper DAGs breach the step cap and need hierarchical planning |
| **A2** | Subtasks are **mostly independent** | **Low** | **Serial dependencies erase the speedup — and remove the justification for the architecture.** The highest-stakes assumption |
| **A3** | Critic catches ≥ 50% of errors | Low | Human review becomes mandatory, changing the product |
| A4 | Small-tier workers are adequate for well-specified subtasks | Medium | Cost rises ~6× to $0.94/run — still under ceiling, so this is a comfort not a dependency |
| A5 | Planner produces valid DAGs ≥ 95% of the time | Medium | Validation + replan absorbs it, at the cost of one extra frontier call |
| A6 | 500 runs/day | Low | Cost scales linearly; burst behaviour is the real concern |

**A2 is existential, not merely important.** If subtasks turn out serially dependent, measured speedup
approaches 1× and **the correct response is to delete this system and use a single agent** — not to
optimize it. Measure the DAG shape on real tasks before committing.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | Is **partial output** acceptable when a run aborts at a cap? | Determines the synthesizer's contract — can it produce a memo from 7 of 10 subtasks? | Product |
| **Q2** | What happens when two agents reach **conflicting conclusions**? | Needs an explicit resolution policy; silently picking one is confidently wrong half the time | Product |
| **Q3** | Should the critic block delivery or annotate it? | Blocking risks never delivering; annotating risks the user ignoring it | Product |
| **Q4** | What is the real DAG shape on production tasks? | Assumption A2 — **resolve first, it decides whether the project should exist** | Us — measure |
| Q5 | Who owns per-role tool allow-lists? | Governance; unowned lists drift toward union-of-everything | Security |

**Q4 first.** Every other question is about refining a system whose premise Q4 tests.

---

**Next:** [02_hld.md →](02_hld.md) — planner/executor split, blackboard vs message-passing, the budget governor, failure modes, and the scale plan.
