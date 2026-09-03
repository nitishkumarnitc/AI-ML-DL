# 04 · Production & Interview — Enterprise AI Agent Platform

> **Phase 4 of 4 · THE CAPSTONE** · [← LLD](03_lld.md) · [Back to README](README.md)

---

## 4.1 AI-specific production concerns

### The model is not the security control, and the platform must be built as if it will be convinced

Every other guardrail discussion in this set treats the model as mostly cooperative. Here the operating
assumption is the opposite: **a sufficiently persuasive document will sometimes win.** That's not pessimism
about model quality — it's the only assumption that produces a design that holds, because injection is an
open adversarial problem with no known complete defence at the model layer.

What follows from it:

| If the model is assumed reliable | If the model is assumed convincible |
|---|---|
| "Ignore instructions in documents" is a control | It's a cheap 80% and **not** a control |
| The agent checks its own tool authorization | Authorization is checked **outside** the agent, twice |
| A good classifier is the injection defence | **Provenance is the defence**; the classifier supplements it |
| A successful injection is a bug | A successful injection is **expected**, and bounded by the user's own permissions |

**The last row is the whole point of on-behalf-of tokens.** With a service account, a successful injection is
a tenant-wide breach. With user-scoped tokens, it is bounded by what that one user could already do — which
turns a catastrophe into an incident.

### The failure that survives every fix: poisoned memory

Restart the service, patch the system prompt, upgrade the classifier — **none of it removes a malicious
instruction that has been written into long-term memory.** [F5](02_hld.md#25-failure-modes--blast-radius) is
the platform's nastiest failure mode precisely because it is *persistent state* in a system everyone
mentally models as *stateless inference*.

Operationally this means memory needs treating as a data store with its own hygiene:

```
Periodic audit:  sample memory rows by source, review agent_inferred and
                 tool_result entries — user_stated is lower risk
Cleanup query:   rows written in the incident window, from untrusted sources,
                 joined back through write_interaction_id to the audit chain
Retention:       default expiry on inferred memory. Memory that never expires
                 is a backdoor with no timeout.
```

**Default expiry on `agent_inferred` memory is the cheapest structural mitigation available**, and it costs
almost nothing in capability — an inference worth keeping will be re-derived.

### Guardrails are a real cost centre, and the two-tier split is why

~$29k/month on a $220k LLM bill ([§1.7](01_requirements.md#the-line-item-people-forget)) is ~13%, and it is
invisible in designs that treat guardrails as middleware. The fast tier isn't only a latency device — it's
what keeps the majority of clear-cut cases off the heavy tier, taking the bill to ~$12k.

**The trap is that fast-tier tuning has an asymmetric cost.** Making the fast tier *stricter* increases false
blocks on legitimate requests, which users see. Making it *more permissive* pushes volume onto the heavy tier,
which nobody sees except the invoice. **So the default drift is toward silently expensive**, and the
mitigation is watching heavy-tier volume share as a first-class metric, not just guardrail accuracy.

### 100% audit is cheap, and the arithmetic is worth carrying into the room

~$250/month against $220k of LLM spend — **0.1%**. This matters beyond the number because "we sample audit
logs for cost reasons" is the standard justification, and here it is arithmetically false. A sampled audit
log fails the only purpose an audit log has: reconstructing a specific incident, which by definition is the
one you didn't sample.

> **This is the single place across all ten designs where the arithmetic *validates* a strict requirement
> rather than invalidating it** — and it's a useful reminder that the discipline isn't there to find
> problems. It's there to find out. Contrast [01](../01_production_rag_system/README.md) (185× over cost),
> [04](../04_llm_inference_platform/README.md) (self-hosting 10× worse),
> [07](../07_llm_evaluation_platform/README.md) (3.4× over the CI ceiling), and
> [08](../08_realtime_voice_assistant/README.md) (latency short by 70 ms).

### Governance is the resource that runs out first

Compute scales with money. **Tool-registration review, policy exceptions, and approval queues scale with
people** — and they scale linearly with tenants while engineering scales sub-linearly.

At 200 tenants this is manageable. At 2,000 it is the platform's bottleneck
([§2.6](02_hld.md#10-2000-tenants--20000-agents--500k-users--2m-interactionsday)), and the mitigation has to
be designed before it hurts:

| Tool class | Registration path |
|---|---|
| Read-only, tenant-scoped data | **Self-service** with automated scope validation |
| Read-only, cross-system | Lightweight review |
| **Side-effecting** | **Full security review, always** |
| Anything with external egress | Full review + egress allow-list entry |

**Tiering registration is the same narrowing principle applied to governance itself:** the safe cases are
self-service, and human attention is spent only where the blast radius justifies it.

### Adoption is a security property

A platform teams route around produces shadow agents — built on personal API keys, with service accounts, no
audit, and no guardrails. **Every friction the platform adds is a push toward that outcome**, which makes
the < 150 ms overhead target and the < 1 day onboarding promise security requirements rather than
conveniences.

This is what the authority split ([§1.4](01_requirements.md#14-the-authority-split--how-the-builderadmin-conflict-resolves))
buys: narrowing needs no approval, so the common case is self-service, and only widening touches a queue.
**A platform where every change needs a ticket is a platform that loses to a personal API key.**

---

## 4.2 Runbook

### Dashboards

**Security — the panel that matters most here:**

```
PROVENANCE_VIOLATION count                by agent, by doc_id   ← injection attempts
TOOL_NOT_ALLOWED count                    by agent, by tool
CROSS_TENANT_RETRIEVAL count              ← must be exactly 0, always
AUDIT_CHAIN_BREAK count                   ← must be exactly 0, always
delegation_widening_rejected              (a bug or an attack; either needs looking at)
memory_writes by source                   user_stated / agent_inferred / tool_result
approval_self_approval_attempts           separation-of-duties probes
```

**Overhead — the adoption metric:**

```
platform_overhead_ms  p50/p95/p99         target p95 < 150 ms, expect ~49 ms
  split: token_exchange · policy · fast_guardrail · assembly · audit_enqueue
heavy_guardrail_ms  vs  prefill_ms        ← the overlap. If heavy > prefill, we ADD latency
side_effecting_turn_overhead_ms           expect ~+130 ms (the deliberate exception)
agent_ttft_ms  p95                        target < 2.5 s
```

**Cost and isolation:**

```
$/interaction by tenant / agent           ceiling $0.10, expect ~$0.0475
guardrail_$ / llm_$  ratio                expect ~13%, ~6% with good fast-tier routing
heavy_tier_volume_share                   ← rises silently when the fast tier drifts permissive
tenant_concurrency_utilization            per tenant, vs ceiling
worker_queue_depth by tenant              ← the F12 signal
budget_cap_hits by tenant
```

**Governance health:**

```
tool_registration_queue_age               ← becomes the bottleneck at scale
approval_queue_age  p95                   and expiry rate
definitions_failing_compile_check         (high = policy is unclear, not that builders are careless)
agents_on_stale_policy_version            ← F15 exposure
eval_gate_bypass_count                    break-glass usage
```

### Alerts

| Alert | Threshold | First action |
|---|---|---|
| **`CROSS_TENANT_RETRIEVAL` > 0** | **Immediate page** | **Potential breach.** Freeze the affected tenant's retrieval, capture the query, find the missing predicate |
| **`AUDIT_CHAIN_BREAK` > 0** | **Immediate page** | Security incident until proven otherwise. Check for a sequence *gap* as well as a hash break — a deleted tail leaves a valid chain |
| **`AUDIT_UNAVAILABLE` blocking actions** | Any sustained | Audit write path health. **Side-effecting tools are down by design** — say so in the incident channel |
| **`PROVENANCE_VIOLATION` spike on one doc** | > 5 in an hour | **Active injection campaign.** Quarantine the document, find how it entered the corpus |
| **`delegation_widening_rejected` > 0** | Any | A bug or a probe. Identify which agent and whether the definition changed |
| **`heavy_guardrail_ms` > `prefill_ms`** | p95 for 15 min | The overlap has stopped paying; the platform is now adding latency. Check guardrail model latency |
| Platform overhead p95 | > 150 ms | Per-stage panel. Usual cause: a new synchronous call added to the path |
| **`heavy_tier_volume_share`** | up > 15 pts | Fast tier drifted permissive — **silently expensive**, no user-visible symptom |
| Tenant queue depth | > ceiling for 10 min | Per-tenant concurrency ceiling. Check whether one tenant is starving others |
| Approval queue age p95 | > SLA | Escalate to a wider group. **Never relax the gate to clear the queue** |
| Tool registration queue age | > 3 days | The governance bottleneck. Consider tiering before it becomes an adoption problem |
| `agents_on_stale_policy_version` | > 10% | Policy simulation and staged re-validation |

**Two alerts have a required communication step, not just a technical one.** `AUDIT_UNAVAILABLE` means
side-effecting actions are deliberately blocked — teams will read that as an outage unless told it's the
designed behaviour. And a `PROVENANCE_VIOLATION` spike on a single document is a security event that needs
the corpus owner involved, not just a platform engineer.

### Incident playbooks

**"`CROSS_TENANT_RETRIEVAL` fired."**

1. **Freeze retrieval for the affected tenant.** This is the requirement whose violation ends the platform.
2. Capture the exact query, token claims, and result set from the audit chain.
3. Determine whether the mandatory predicate was absent (code path bug) or the ACL service returned wrong
   data (upstream).
4. **Scope the exposure from the audit log** — `doc_ids` on every entry means you can enumerate precisely
   which documents reached which user. **This is the audit log earning its cost.**
5. Notify per the breach policy. Do not wait for root cause to start scoping.

**"Injection campaign — `PROVENANCE_VIOLATION` spiking on one document."**

1. Query `idx_al_injection` for every refused action originating in that `doc_id`.
2. Quarantine the document; re-index without it.
3. **Ask how it entered the corpus** — an injected document in an enterprise knowledge base usually means an
   ingestion path accepts untrusted content.
4. Check whether any tool call from that document *succeeded* — i.e. it was allow-listed **and** had user-turn
   provenance ([F2](02_hld.md#25-failure-modes--blast-radius), the residual risk).
5. **Check memory**: did anything from that document get written into long-term memory?

**"Suspected poisoned memory."**

1. Query `agent_memory` for the incident window, filtered to `agent_inferred` and `tool_result` sources.
2. Join through `write_interaction_id` to the audit chain to see the interaction that wrote each row.
3. **Delete surgically.** The `source` and `write_interaction_id` columns exist so the response isn't
   "drop all memory."
4. Verify the memory-write guardrail was active and at what version.
5. Consider tightening default expiry on inferred memory.

**"A team says the platform is too slow / they want a bypass."**

1. Pull their `platform_overhead_ms` split — the answer is usually not the platform.
2. Check whether `heavy_guardrail_ms > prefill_ms` for their agent (a short prompt has little prefill to
   hide behind).
3. Check side-effecting turn share — those legitimately pay ~130 ms more.
4. **Treat this as a security escalation, not a performance ticket.** A team that bypasses builds a shadow
   agent with a service account and no audit — which is the outcome the whole platform exists to prevent.

**"An audit chain gap was detected."**

1. Distinguish a **hash break** (an entry was modified) from a **sequence gap** (an entry was removed).
2. A gap at the *tail* is the case a hash chain alone misses — it is why sequence numbers are checked.
3. Preserve everything; involve security. **Do not backfill**, which would destroy the evidence.
4. Establish whether the gap is a write-path bug (buffered writes lost during an outage) or tampering. **Both
   look identical at first, and only one is an incident** — but treat it as the incident until shown otherwise.

---

## 4.3 Common mistakes

| # | Mistake | Why it's wrong | What to do instead |
|---|---|---|---|
| 1 | **Agent runs as a service account** | Union of all users' permissions. Every injection becomes a tenant-wide breach | On-behalf-of user-scoped tokens |
| 2 | **The agent enforces its own tool authorization** | The manipulable component is the enforcer | Tool gateway outside the loop **and** server-side re-verification |
| 3 | **"Ignore instructions in documents" as the injection defence** | A request to the model, not a control. Fails silently | Structural separation **plus** provenance-based tool admission |
| 4 | **No provenance tracking** | An allow-listed tool named by an injected document executes | A tool call must trace to the user's turn |
| 5 | **`tenant_id` accepted from the request body** | Attacker-controlled | From the token only; mandatory data-layer predicate |
| 6 | **ACLs evaluated at index time** | Returns documents the user is no longer permitted to see | Query-time evaluation, over-fetch to compensate |
| 7 | **Memory not guardrailed** | One-shot injection becomes a permanent backdoor | Guardrail writes; mark memory as data; default expiry |
| 8 | **Sampled audit logs** | Not an audit log. And it's ~0.1% of spend | 100%, hash-chained, WORM |
| 9 | **Audit writable by the application plane** | Proves nothing in an investigation | Separate credentials, append-only |
| 10 | **Hash chain without sequence numbers** | A deleted tail leaves a valid chain | Per-tenant monotonic `seq`, checked for gaps |
| 11 | **Fully async audit for side-effecting actions** | A crash mid-action leaves an unrecorded side effect | Durable pre-action write |
| 12 | **Approval gates an agent definition can disable** | A gate that can be waived by the party it constrains | Platform-side enforcement; builders may only **add** |
| 13 | **Auto-approve on approval timeout** | Converts a gate into a delay | Escalate; never auto-approve |
| 14 | **Self-approval permitted** | Not approval | Separation of duties in the approval service |
| 15 | **Heavy guardrail inline on every request** | 150 ms is the entire overhead budget | Two tiers; heavy overlapped with prefill |
| 16 | **Overlapping the guardrail with *tool execution* too** | A tool call cannot be un-executed | Output can be halted; side effects wait for the full verdict |
| 17 | **Delegation that can widen scope** | An escalation primitive | Narrowing checked at token-exchange time |
| 18 | **Data isolation without compute isolation** | One tenant stalls 199 others; fully compliant, fully unavailable | Per-tenant concurrency ceilings |
| 19 | **Runtime policy denial instead of compile-time** | End users discover builders' config errors | Validate in CI with the line number |
| 20 | **Applying a policy tightening without simulation** | Breaks live agents at apply time | Simulate against all definitions; report what would break |
| 21 | **Rebuilding RAG / serving / gateway / evals here** | Turns a platform into a multi-year programme | Consume [01](../01_production_rag_system/README.md), [04](../04_llm_inference_platform/README.md), [07](../07_llm_evaluation_platform/README.md), [09](../09_multi_provider_llm_platform/README.md) |
| 22 | **Ignoring guardrail cost** | ~13% of the LLM bill, invisible in the design | Two-tier routing, and track heavy-tier share |
| 23 | **Treating a bypass request as a perf ticket** | Bypass means a shadow agent with a service account | Handle it as a security escalation |
| 24 | **Assuming tools support delegated auth** | [A1](01_requirements.md#assumptions). If false, the central control is unachievable | **Verify across the top 20 tools in week one** |

**Mistake 1 is the one that defines whether the design is serious.** It's also the easiest thing to build,
which is why it's the default. **Mistake 21 is the one that sinks the capstone specifically** — designing all
ten systems again in one answer signals that the composition boundaries weren't understood.

---

## 4.4 Interview follow-ups

**"What's the single most important control?"**
> The agent's identity is the user's identity. An agent running as a service account holds the union of all
> its users' permissions, so a single injected document can exfiltrate any user's data — and no amount of
> prompt hardening fixes it, because the token is genuinely privileged. With on-behalf-of tokens, a
> successful injection is bounded by what that one user could already do. **It doesn't prevent the attack;
> it collapses the blast radius**, which is the achievable goal.

**"How do you actually stop prompt injection?"**
> You don't stop it at the model — that's an open adversarial problem. You make a successful injection unable
> to *do* anything. Three layers: structural separation so untrusted content sits in labelled data blocks; a
> per-agent tool allow-list; and the one that matters most, **provenance** — a tool call is admissible only
> if it traces to the user's turn or a plan step the user's turn produced. An injected document can still say
> "call `transfer_funds`," and the platform can see that request has no user-side origin. **The classifier is
> a supplement; provenance is the structural control.**

**"What's the honest weakness of provenance?"**
> False positives on legitimate delegation. A user saying "handle whatever the ticket says" has genuinely
> delegated authority to document content, and the rule blocks it. The answer is an explicit delegation
> marker with a narrowed tool set — not a loosened rule — and it's an open question
> ([Q4](01_requirements.md#open-questions)) rather than something I'd pretend is solved.

**"Your platform adds 150 ms of budget and the guardrail alone is 150 ms. How?"**
> The naive assembly is 214 ms, so it doesn't close. The insight is that **the heavy guardrail doesn't need
> to gate the request — only the output and the first tool call.** An LLM call with no tool invocation is
> read-only, so the guardrail runs concurrently with prefill and the verdict lands before the first token is
> emitted. Inline overhead drops to ~49 ms. **The gate moved; it didn't weaken.** The exception is deliberate:
> side-effecting tool calls wait for the full verdict, because output can be halted mid-stream and a tool
> call cannot be un-executed.

**"Isn't that just hoping the guardrail finishes first?"**
> No — if it doesn't finish, emission waits. That's [F7](02_hld.md#25-failure-modes--blast-radius), and it's
> correct rather than degraded. The monitoring is explicit: `heavy_guardrail_ms` versus `prefill_ms`. When
> the guardrail exceeds prefill, the overlap has stopped paying and we're adding latency — which is a signal
> to act on, not a silent regression.

**"How do you resolve builders wanting freedom and admins wanting control?"**
> Not by compromise — by splitting authority by category and making it asymmetric. Admins own what exists:
> the tool registry, ceilings, guardrail floors, residency. Builders own choices within that: which tools,
> which model, prompts, stricter guardrails. **The invariant is that a builder can only ever narrow, never
> widen**, checked at definition-compile time in CI. So narrowing is self-service and only widening touches
> a governance queue. That's what makes the platform adoptable — and adoption is a security property,
> because a platform teams route around produces shadow agents with service accounts and no audit.

**"That narrowing rule sounds familiar."**
> It's the same rule in three places: agent-to-agent delegation narrows the parent's token, builder config
> narrows tenant policy, and in [09](../09_multi_provider_llm_platform/README.md) a per-request override
> narrows the tenant's fallback policy. **Monotonic narrowing is the general shape of safe delegation** —
> once you see it, the places you *haven't* applied it look like bugs.

**"Why 100% audit? That sounds expensive."**
> It's ~$250/month against $220k of LLM spend — about 0.1%. **There is no cost argument for sampling**, which
> matters because that's the usual justification. And a sampled audit log fails the only job it has:
> reconstructing a specific incident, which by definition is the one you didn't sample. It's also the one
> place in this whole set where the arithmetic *supported* a strict requirement instead of breaking it.

**"How do you know the audit log wasn't tampered with?"**
> Hash-chained entries plus per-tenant monotonic sequence numbers, in WORM storage, with write credentials
> separate from the application plane. The sequence numbers matter more than people expect: **a hash chain
> proves entries weren't modified, but deleting a contiguous tail leaves every remaining link valid.** The
> gap check is what catches that. And the chain is verified continuously — a chain nobody verifies is
> decoration.

**"What's the nastiest failure mode?"**
> Poisoned long-term memory. It survives service restarts, prompt patches, and classifier upgrades, because
> it's persistent state in a system everyone models as stateless inference. The controls are guardrailing
> memory *writes*, marking memory as untrusted data even when the agent wrote it, and storing `source` plus
> `write_interaction_id` so cleanup can be surgical instead of "drop all memory." Default expiry on inferred
> memory is the cheapest structural mitigation.

**"What would make this design impossible?"**
> If enterprise tools accept only service-account credentials — [A1](01_requirements.md#assumptions). Then
> on-behalf-of can't be implemented as stated. The fallback is an authorization proxy that holds the service
> credential and verifies the user's entitlement before calling, and **it's genuinely weaker**: the
> downstream system's own audit names the service account, a shim bug is a full escalation rather than a
> partial one, and the entitlement model gets reimplemented where it can drift. It's the right pragmatic
> answer and it isn't equivalent. **Verifying A1 across the top 20 tools is the first week's work**, before
> any architecture is committed.

**"What breaks first at scale?"**
> Governance, not compute. Tool-registration review, policy exceptions, and approval queues are human
> processes that scale linearly with tenants while engineering scales sub-linearly. At 2,000 tenants the
> security team's review capacity is the platform's limiting resource. The fix is tiering registration —
> read-only tenant-scoped tools self-service, side-effecting tools always fully reviewed — which is the same
> narrowing principle applied to governance itself.

**"How much of this would you actually build?"**
> Four things, and I'd say so up front: identity propagation, the trust boundary in prompt assembly, the
> audit chain, and the authority split. Everything else is composition — retrieval from
> [01](../01_production_rag_system/README.md), serving from [04](../04_llm_inference_platform/README.md),
> evals from [07](../07_llm_evaluation_platform/README.md), model access from
> [09](../09_multi_provider_llm_platform/README.md), loop budgets from
> [03](../03_multi_agent_system/README.md). **The capstone's discipline is subtraction.** Redesigning all ten
> systems in one answer is the failure mode this question is testing for.

---

## 4.5 Glossary

| Term | Meaning |
|---|---|
| **ACL-aware retrieval** | Retrieval where authorization is evaluated at query time against current ACLs, not baked in at index time |
| **Authority split** | The division of configuration between admin-owned ceilings/floors and builder-owned choices within them |
| **Authorization proxy** | Fallback when tools lack delegated auth: a platform shim holding a service credential that verifies the user's entitlement first. Weaker than true OBO |
| **Compile-time policy check** | Validation of `config ⊆ policy` in the builder's CI, producing a build failure rather than a runtime denial |
| **Confused deputy** | An escalation where a privileged component is tricked into acting for a less-privileged caller. Prevented by narrowing-only delegation |
| **Fail-open / fail-closed** | Behaviour when guardrails are unavailable. Per-agent policy; platform default closed |
| **Hash chain** | Each audit entry hashes the previous one, making modification detectable. Paired with sequence numbers to make *deletion* detectable |
| **Heavy / fast guardrail tier** | LLM-based (~120 ms, overlapped with prefill) vs. regex+classifier (~15 ms, inline) |
| **Monotonic narrowing** | The invariant that delegated authority is always a subset. Appears in delegation, builder config, and [09](../09_multi_provider_llm_platform/README.md)'s request overrides |
| **On-behalf-of (OBO)** | Token exchange giving the agent a user-scoped token. RFC 8693 actor claims make the chain auditable |
| **Provenance** | The origin of a request — user turn, plan step, retrieved content, tool output. The structural injection control |
| **Stored injection** | An injected instruction persisted into long-term memory, surviving restarts and prompt fixes |
| **Structural separation** | Placing untrusted content in delimited, labelled data blocks rather than relying on instructions to ignore it |
| **Tool gateway** | The platform component outside the agent loop that is the only path to a side effect |
| **WORM** | Write-once-read-many storage. Makes audit immutability a property of the medium, not of grants |

---

## Where this sits in the set

| | |
|---|---|
| **Hardest constraint** | The agent's identity is the user's identity — and it depends on a prerequisite the platform doesn't control |
| **What it uniquely owns** | Identity propagation · the prompt-assembly trust boundary · the audit chain · the authority split |
| **What it consumes** | [01](../01_production_rag_system/README.md) retrieval · [04](../04_llm_inference_platform/README.md) serving · [07](../07_llm_evaluation_platform/README.md) evals · [09](../09_multi_provider_llm_platform/README.md) model access · [03](../03_multi_agent_system/README.md) loop budgets · [02](../02_customer_support_agent/README.md) approval gates |
| **Cost profile** | ~$0.0475/interaction · guardrails ~13% of the LLM bill · **audit 0.1%** |
| **The rare good news** | The only design here where the arithmetic *validated* a strict requirement |

**This is the last of the ten.** [← All systems](../README.md) · [Requirements contract](../00_requirements_all_systems.md)

[← Back to README](README.md) · [← LLD](03_lld.md)
