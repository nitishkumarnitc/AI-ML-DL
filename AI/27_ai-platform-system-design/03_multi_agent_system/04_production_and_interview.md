# 04 · Production & Interview — Multi-Agent System

> **Phase 4 of 4** · [← LLD](03_lld.md) · [README](README.md)

---

## 4.1 AI-specific concerns

### Token cost — the concern that dominates this design

Cost is **multiplicative** (`subtasks × turns × retries`), which is the single fact that separates
multi-agent economics from single-agent economics.

| Lever | Effect | Where |
|---|---|---|
| **Worker tier = small** | **6× reduction** — $0.94 → $0.15/run | The highest-leverage decision in the system |
| Conditional critic | ~25% fewer frontier calls, ~20 s wall-clock | [§2.2](02_hld.md#verification) |
| Blackboard over agent chat | Avoids O(n²) token growth | [§2.2](02_hld.md#coordination--the-decision-that-defines-the-system) |
| Reserve-before-call | One expensive call can't breach the cap | [§3.3](03_lld.md#the-budget-governor) |
| Five caps | Bound the worst case at $5 | [§1.6](01_requirements.md#enforcement-mechanisms--all-required) |

**The caps are a safety control, not a budget line.** `MAX_COST = $5` exists so a replanning loop
can't spend arbitrarily; the money saved is incidental.

### Latency

Wall-clock, not TTFT. **The honest finding from [§1.5](01_requirements.md#the-speedup-that-justifies-the-architecture):
measured speedup is ~1.9×, not the ≥3× the NFR asserted** — because fixed overhead (planning +
synthesis + critic ≈ 53 s) is unparallelizable and doesn't shrink with subtask count. That's Amdahl's
law applied to agents.

Recommendation: **relax the NFR to ≥2× and make the critic conditional**, landing near 2.3×. Or
require ≥15 subtasks before choosing the multi-agent path at all, since fixed overhead amortizes.

**Stating a speedup NFR is what made this discoverable.** A design asserting "parallelism helps"
without computing the critical path has stated a hope.

### Evaluation

| Tier | What's measured | Gate |
|---|---|---|
| **Plan quality** | DAG validity rate · dependency correctness · subtask count | Blocks on validity < 95% |
| **Plan determinism** | Same goal + versions → identical DAG | **Blocks on any nondeterminism** |
| Subtask success | Per-role success rate | Blocks on > 5-point drop |
| **Parallel speedup** | Critical path vs sequential sum, measured per run | **Alerts below 2× — the architecture's justification** |
| Critic efficacy | Injected-error catch rate (≥ 50%) | Blocks below 40% |
| E2E task success | ≥ 0.80 on the eval suite | Blocks on > 3-point drop |
| Cost per run | Distribution, not mean | Alerts on p95 > $1.00 |
| Safety | Allow-list violations attempted; injection suite | Blocks on any successful escape |

**Three properties specific to multi-agent evaluation:**

1. **Plan determinism is gated absolutely.** Execution varies; the plan must not. It's one call from a
   fixed prompt at `temperature=0` with a pinned model, so nondeterminism means something broke.
2. **Speedup is a continuously-measured metric, not a launch claim.** If it decays below 2×, the
   architecture has stopped justifying itself and should be replaced by a single agent. Measuring it
   means you'd notice.
3. **Cost is evaluated as a distribution.** The mean hides the retry-heavy tail, which is exactly where
   the multiplicative blow-up lives.

### Hallucination & groundedness

The failure mode unique to this architecture: **synthesis from insufficient evidence.**

| Layer | Mechanism |
|---|---|
| **Per-claim attribution** | Every claim in the deliverable cites the producing subtask |
| **Refuse-on-empty** | Synthesizer refuses when the blackboard holds no evidence ([E5](03_lld.md#36-edge-cases--correctness)) |
| Declared gaps | Failed subtasks appear in the output as stated gaps |
| Independent critic | Flags claims no gathered evidence supports |
| Schema validation | Malformed subtask results are failures, not inputs |

**[E5](03_lld.md#36-edge-cases--correctness) is the important one.** Hand a synthesizer an empty
blackboard and it will produce a fluent, well-structured, entirely fabricated comparison memo — because
that's what a language model does with a request and no data. The refusal has to be explicit, and it's
the same logic as [01](../01_production_rag_system/03_lld.md#retrieve--rerank--assemble)'s retrieval
gate.

### Prompt injection

**Worker agents read adversarial content by design** — a researcher agent fetching web pages is
consuming attacker-controllable text as its primary job.

| Vector | Control |
|---|---|
| Fetched web content | Fenced as untrusted data; never concatenated into instructions |
| Blackboard entries written by another agent | **Also fenced** — a compromised worker could write injected text for a peer to read |
| **Damage bound** | **Per-role allow-lists** — a hijacked researcher still cannot touch the database or write files |
| Side effects | Human approval via [02](../02_customer_support_agent/03_lld.md#the-policy-engine)'s policy engine |

**Per-role allow-lists are the real defence, and they're a genuine multi-agent dividend.** In a
single-agent design the tool set is the union of everything any task needs, so a successful injection
gets all of it. Here, compromising the researcher yields web search — and nothing else. This is the
strongest argument for multi-agent that *isn't* about parallelism.

**The blackboard row is the non-obvious one.** Agent-to-agent content is a legitimate injection vector:
a worker that ingests a poisoned page and writes its summary to the blackboard has laundered attacker
text into a trusted-looking internal artifact.

### Observability

Every step recorded: role, kind, tool, `args_hash`, model version, tokens, cost, latency, outcome. Plus
run-level plan, budget consumption, and governor decisions.

| Signal | Why it exists |
|---|---|
| **Speedup per run** | The architecture's justification — decay means reconsider the design |
| **Cost distribution p95** | Mean hides the retry-heavy multiplicative tail |
| Replan rate | Rising replans mean planner quality is degrading |
| **Allow-list denial rate** | Injection campaigns and role-misconfiguration both show here |
| Loop-detection trips | Workers stuck; usually a bad subtask instruction |
| Partial-delivery rate | Rising partials mean tools or caps need attention |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Metrics | Alert |
|---|---|---|
| **Speedup** | Critical path vs sequential sum, per run | **Below 2× sustained** ⚠️ |
| **Cost** | p50/p95/max per run; cap-trip rate | p95 > $1.00 · cap-trips > 5% |
| Budget | Steps, tokens, wall-clock consumed at completion | Any cap trip > 5% of runs |
| Plan quality | DAG validity rate; replan rate; subtask count distribution | Validity < 95% · replan rate > 15% |
| Tasks | Success rate by role; retry rate; skip rate | Any role below 80% |
| **Safety** | Allow-list denials by role; injection flags | Any denial spike > 3× |
| Delivery | Completed vs aborted vs partial | Partial rate > 20% |
| Critic | Trigger rate; pass rate; catch rate on seeded errors | Pass rate < 50% |

### Triage order

1. **Did the plan make sense?** `GET /v1/runs/{id}/trace` → the `plan` event. A bad DAG explains
   everything downstream and is the most common root cause.
2. **Which tasks failed, and were they skipped or failed?** `skipped` means a *dependency* failed —
   look upstream, not at the reported task.
3. **Did a cap trip?** `abort_reason` tells you immediately; a step-cap trip usually means the planner
   over-decomposed.
4. **Loop-detection trips?** Points at a specific subtask instruction being unachievable.
5. **Allow-list denials?** Either a role misconfiguration or an injection attempt.
6. **Blackboard conflicts?** High conflict rates mean two subtasks share a key they shouldn't.
7. **Only then** suspect worker model quality.

### Rollback

| Change | Rollback | Notes |
|---|---|---|
| Planner prompt | Revert version | **In-flight runs keep their plan** — `plan_version` is per-run |
| Role definitions / allow-lists | Revert config | Takes effect on the next dispatch, not mid-task |
| Worker tier | Repin | Watch cost: reverting to frontier is 6× |
| Cap values | Config change | **Lowering caps can abort in-flight runs** — apply to new runs only |
| Critic on/off | Feature flag | Instant; safe |

**Lowering a cap mid-flight would abort paid-for runs**, so cap changes apply to newly-created runs
only. That's a small implementation detail with a real user-visible consequence.

---

## 4.3 Common mistakes

> **Mistake:** Designing multi-agent without checking whether it's justified.
> **Why it's wrong:** a single agent with good tools beats it for most tasks at a fraction of the cost.
> **Do instead:** test the three conditions — parallelizable, different privileges, independent
> verification. If none hold, use [02](../02_customer_support_agent/README.md)'s design ([§1.1](01_requirements.md#establish-the-premise-before-designing)).

> **Mistake:** Free-form agent-to-agent conversation.
> **Why it's wrong:** O(n²) token growth, context drift, no deterministic termination, nothing to audit.
> **Do instead:** structured writes to a transactional blackboard ([§2.2](02_hld.md#coordination--the-decision-that-defines-the-system)).

> **Mistake:** Executing the planner's DAG without validating it.
> **Why it's wrong:** an emitted cycle is an infinite loop with a bill attached.
> **Do instead:** deterministic acyclicity + schema validation, ~50 ms ([E1](03_lld.md#36-edge-cases--correctness)).

> **Mistake:** Unbounded replanning, or extending the budget on replan.
> **Why it's wrong:** the fastest route to unbounded spend — each cycle looks locally reasonable.
> **Do instead:** cap replans at 2 **and** don't reset the budget ([F2](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** A single dollar cap as the only guardrail.
> **Why it's wrong:** it won't stop a cheap infinite loop making free blackboard reads for ten minutes.
> **Do instead:** five caps — they fail differently ([§1.6](01_requirements.md#enforcement-mechanisms--all-required)).

> **Mistake:** Last-write-wins on the blackboard.
> **Why it's wrong:** two workers finishing together silently lose one result; the run "succeeds" with a
> missing competitor and no error.
> **Do instead:** versioned compare-and-set ([F4](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** Letting one worker's exception cancel the wave.
> **Why it's wrong:** four completed research subtasks discarded because the fifth timed out.
> **Do instead:** `return_exceptions=True` and handle per-task ([§3.3](03_lld.md#the-scheduler-loop)).

> **Mistake:** Firing a parallel wave simultaneously.
> **Why it's wrong:** parallel waves *are* synchronized bursts — exactly what rate limiters punish.
> **Do instead:** stagger dispatch within the wave ([F6](02_hld.md#25-failure-modes--blast-radius)).

> **Mistake:** Synthesizing from an empty blackboard.
> **Why it's wrong:** you get a fluent, entirely fabricated deliverable.
> **Do instead:** refuse when there's no evidence ([E5](03_lld.md#36-edge-cases--correctness)).

> **Mistake:** Self-critique by the synthesizer.
> **Why it's wrong:** the context that produced an error makes the error look correct.
> **Do instead:** an independent critic that didn't produce the work ([§2.2](02_hld.md#verification)).

> **Mistake:** Giving every agent the union of all tools.
> **Why it's wrong:** discards the security dividend that partly justifies multi-agent.
> **Do instead:** per-role allow-lists at the gateway ([FR-3](01_requirements.md#execution)).

---

## 4.4 Interview follow-ups

### "Why multi-agent at all? Couldn't one agent do this?"

For most tasks, yes — and I'd say so before designing. A single agent with good tools is simpler,
cheaper, and easier to debug. Multi-agent earns its complexity on three conditions: genuinely
parallelizable subtasks, subtasks needing *different* privileges, and a need for independent
verification. The competitor-research task hits all three — five independent research streams, three
distinct privilege sets, and a critic that benefits from not having produced the work. If a task failed
all three I'd route it to a single-agent design. The contrast case is
[02](../02_customer_support_agent/02_hld.md#the-conversation-plane): a support conversation is
sequential with one privilege set, so multi-agent would triple cost for nothing.

### "You said ≥3× speedup, then measured 1.9×. What happened?"

Fixed overhead. Planning, synthesis, and criticism are roughly 53 seconds and none of it parallelizes,
so it caps achievable speedup regardless of how wide the waves are — Amdahl's law. At 10 subtasks
that's about 21% of the parallel run. My response is to relax the NFR to ≥2× (still a real win) and
make the critic conditional rather than always-on, which recovers ~20 seconds and lands near 2.3×. The
alternative is requiring ≥15 subtasks before choosing this path, since the overhead amortizes. What I
wouldn't do is keep asserting 3× — the number was a hope until I computed the critical path.

### "How do you stop a multi-agent system running away with cost?"

Five caps, because they fail differently. Tokens, dollars, step count, wall-clock, and loop detection.
A dollar cap alone won't stop a run making free blackboard reads in a cycle for ten minutes; loop
detection alone won't stop a run burning $5 in thirty seconds. The governor gates *dispatch* rather
than trusting agents to self-limit, decrements atomically under a row lock, and reserves before each
call so one expensive call can't breach the cap and only be noticed afterwards. Plus the rule that
matters most: **a replan does not extend the budget.**

### "Why a blackboard rather than agents talking to each other?"

Cost and auditability. With *n* agents, free-form chat trends toward O(n²) messages and each message
re-injects prior context, so tokens grow super-linearly in agents. A blackboard is O(n) writes and O(n)
targeted reads. It also terminates deterministically and leaves a replayable artifact — agent
conversations have neither property. For 10 agents that's roughly 90 context-carrying exchanges versus
20 targeted operations.

### "Two agents reach contradictory conclusions. What does the system do?"

Surfaces both, with attribution to the producing subtask. Silently picking one is confidently wrong
about half the time, and the contradiction is itself useful signal — it usually means the sources
disagree, which the reader needs to know. It's an open product question ([Q2](01_requirements.md#open-questions))
whether the critic should attempt resolution, but the default is transparency over false confidence.

### "A worker reads a web page containing injected instructions. What's the blast radius?"

Bounded by that role's allow-list, which is the real defence. A compromised researcher agent has web
search and nothing else — it can't reach the database or write files. Fetched content is fenced as
untrusted data, and any side-effecting action still needs approval through the policy engine. This is
actually the strongest argument for multi-agent that isn't about speed: in a single-agent design the
tool set is the union of everything, so one successful injection gets all of it. The subtlety people
miss is that **blackboard entries written by another agent also need fencing** — a worker that ingests
a poisoned page and summarizes it has laundered attacker text into a trusted-looking internal artifact.

### "Four of five research subtasks succeed. What do you return?"

The memo, with the gap explicitly declared — "Umbrella: research failed after 3 attempts." Delivering
partial work is right because the four completed subtasks are paid for and useful; the requirement is
that the output states what it couldn't cover. A memo silently missing a competitor is worse than one
that names the hole, because the reader can't tell the difference between "not researched" and "nothing
to report." If *all five* fail, though, the synthesizer must refuse — a comparison memo generated from
zero evidence is pure fabrication.

### "What breaks first at 10×?"

Provider rate limits, and it's inherent to the architecture rather than incidental. Parallel waves are
synchronized bursts — 200 concurrent runs firing 5-wide waves produces 1,000-call bursts, which is
precisely what rate limiters punish. The thing that buys speedup is the thing that trips them. The fix
is deliberate dispatch staggering plus multi-provider routing, trading a little wall-clock for a lot of
reliability. Second is blackboard write contention, which is tractable because runs never share state —
partition by `run_id` and there's no cross-partition coordination.

### "How do you know the architecture is still justified six months in?"

Measure speedup per run continuously and alert below 2×. If real task shapes turn out more serially
dependent than assumed — assumption A2, which is the lowest-confidence one — measured speedup drifts
toward 1× and the correct response is to **delete this system and use a single agent**, not to optimize
it. That's why speedup is a monitored metric rather than a launch claim.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Multi-agent system** | Several LLM agents with distinct roles cooperating on one goal | Justified only by parallelism, privilege separation, or independent verification |
| **DAG** | Directed Acyclic Graph — subtasks with dependencies, no cycles | Enables parallelism; **acyclicity must be validated, not assumed** |
| **Planner** | Agent that decomposes a goal into the DAG | Frontier tier; no tools — it plans, it doesn't act |
| **Worker** | Agent executing one bounded subtask | Small tier; narrow allow-list. Where the 6× cost saving lives |
| **Synthesizer** | Agent compiling subtask outputs into the deliverable | Must refuse on empty evidence |
| **Critic** | Independent verifier that did **not** produce the work | Self-critique shares the producer's blind spots |
| **Blackboard** | Versioned shared state agents read and write | O(n) coordination vs chat's O(n²); replayable |
| **Compare-and-set (CAS)** | Write conditional on an expected version | The lost-update guard — without it, results vanish silently |
| **Lost update** | Two concurrent writes, one silently discarded | Run "succeeds" with missing data and no error |
| **Budget governor** | Central component gating dispatch on five caps | Cannot be bypassed by a confused agent |
| **Atomic decrement** | Budget consumption under a row lock | Prevents concurrent waves both passing the same check |
| **Reserve-before-call** | Pre-flight budget reservation | One expensive call can't breach the cap unnoticed |
| **Loop detection** | Abort on `(role, tool, args_hash)` repeating 3× | Catches cheap-but-endless cycles aggregate caps miss |
| **Replan** | Regenerating the DAG mid-run | Capped at 2, and **does not extend the budget** |
| **Wave** | Set of tasks dispatched together once deps are met | The unit of parallelism — and of rate-limit burst |
| **Stagger** | Delaying dispatch within a wave | Trades wall-clock for rate-limit survival |
| **Critical path** | Longest dependency chain through the DAG | Determines wall-clock; the basis of the speedup calculation |
| **Amdahl's law** | Speedup is capped by the unparallelizable fraction | Why fixed overhead caps speedup at ~1.9× here |
| **Per-role allow-list** | Tools a given role may invoke | The security dividend of multi-agent; bounds injection damage |
| **Skipped vs failed** | Never ran (dependency failed) vs ran and failed | Distinguishing them makes gap reporting intelligible |
| **Partial delivery** | Returning work completed before an abort | Paid-for work is useful **if the gaps are declared** |
| **Plan determinism** | Same goal + versions → same DAG | Debuggability; execution may vary, the plan shouldn't |
| **Multiplicative cost** | Cost scales as subtasks × turns × retries | The single fact separating multi-agent from single-agent economics |

---

**Files:** [README](README.md) · [Requirements](01_requirements.md) · [HLD](02_hld.md) · [LLD](03_lld.md) · **Production & interview** (this file)
