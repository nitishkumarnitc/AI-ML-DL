# 12 · Production & Interview — Developer Tools: AI Coding Assistant / SWE Agent

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)

---

## 4.1 AI-specific concerns

| Concern | How it shows up here | What we do about it |
|---|---|---|
| **Verifiability is the one gift, and the design should spend it** | Tests pass or they don't — no other system in this folder can check its own work | The architecture is a **verification loop**. FR-3 is absolute, evaluation needs no golden dataset, and honest failure is a determinate fact rather than a confidence estimate |
| **The verifier is inside the blast radius** | The test suite defines correctness **and the agent can edit it** | The genuinely novel problem here. AST comparison (FR-12), red-on-old-code (FR-13), mutation sampling (FR-14), and CI config made non-writable (FR-23) |
| **More attempts make things worse, not just costlier** | Attempt 30 is a more desperate attempt 3, and desperation broadens the search to include the test file | The step bound is a **correctness control** before it is a cost control. Early abandon at 25 steps with no red→green (FR-16) |
| **False success is the worst available outcome** | A CI-passing wrong diff enters the codebase **with a human's approval attached** | ≤ 1% target. Full-suite gate never skipped, weakening detection, minimality for reviewability. An agent that fails visibly is merely unhelpful |
| **The stopping signal can be faked by infrastructure** | A flaky test flipping red→green is false progress | Flake registry; quarantined tests excluded from the progress signal (FR-31). **Without this the abandon rule degrades silently and the symptom looks like normal behaviour** |
| **Cost per attempt ≠ cost per success** | $0.94/task at 35% success = **$2.81 per merged PR**; each success carries ~1.9 failures | Fail fast (FR-16) and triage upfront (FR-20) are **cost levers**, not UX compromises. Triage improves both economics and experience |
| **Tokens dominate — uniquely in this folder** | **96% of cost is the LLM**, because the loop multiplies every call | Attack the loop, not the infrastructure: stable-prefix caching (~70% hit), tier routing, shorter loops. Contrast [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/) (audit storage) and [`../06_manufacturing_cv_inspection/`](../06_manufacturing_cv_inspection/) (edge hardware) |
| **The agent both executes code and opens PRs** | A successful injection is arbitrary execution **plus** a diff carrying CI's trust — supply-chain compromise with a legitimate author | No `run_shell`, no credentials worth stealing, egress allowlist, structural instruction/data separation (FR-25), red-team suite (FR-26) |
| **Retrieval quality caps everything** | An agent that cannot find the code cannot fix it, and will confidently edit the wrong file | Hybrid retrieval — symbol graph for exact refs, BM25 for identifiers, embeddings for prose→code. Measured independently of task success (FR-1) |
| **"Tests pass" needs a precise meaning** | Full suite per iteration is unaffordable; affected-only is not FR-3's guarantee | Two tiers: affected in the inner loop, **full once at the gate** (FR-28/29). Selector recall monitored (FR-30), because under-selection raises false success |
| **Evaluation is nearly free and should be continuous** | The repo *is* the eval set; the metric is unambiguous | Run a fixed task suite per model/prompt change. Compare success rate, **false-success rate**, steps-to-green and cost-per-success — not just success rate. See [`../../16_evals/`](../../16_evals/) and [`../../23_ai-coding-agents-and-code-eval/`](../../23_ai-coding-agents-and-code-eval/) |

---

## 4.2 Operations & runbook

### Dashboards

**Correctness — the panels that matter most, reviewed rather than merely alerted:**

| Panel | Alert |
|---|---|
| **False-success rate** (merged PRs later reverted or bug-linked) | > 1% |
| **Test-integrity findings per 100 PRs**, by kind | any `blocking` kind rising |
| **`ci_config_files_touched` > 0** | **> 0 is a page.** Structurally impossible |
| **PRs opened without a `tier='gate'` full-suite verification** | **> 0 is a page.** Structurally impossible |
| **Gate failure after a green inner loop** (FR-30) | rising ⇒ the affected-test selector is under-selecting |
| `new_test_passes_on_old_code` findings | rising ⇒ the model is learning to write vacuous tests |
| Uncaught-mutant rate on changed lines | rising ⇒ tests execute the change without constraining it |

**Loop health:**

| Panel | Alert |
|---|---|
| Task success rate (expected ≥ 35%) | < 30% |
| **Steps to first red→green, distribution** | p50 rising ⇒ retrieval or model regression |
| **Abandon-rate split: no-progress vs repeat-signature vs budget** | a shift between them is a behaviour change worth understanding |
| **Attempts reaching 60 steps with `first_red_to_green` set late** | rising ⇒ possible flake-driven false progress |
| Flake quarantine size and churn, per repo | growth ⇒ the stopping signal is eroding |
| Prompt-cache hit rate (expected ~70%) | < 55% ⇒ context packs are unstable, cost rises directly |

**Economics and experience:**

| Panel | Alert |
|---|---|
| **Cost per merged PR** (expected ~$2.81) | > $4 |
| Cost per task vs cost per success, on one chart | — |
| **Triage decline rate, and override-success rate** (FR-22) | override success > 30% ⇒ triage is too aggressive |
| p50 / p95 task wall-clock | p50 > 5.5 min · p95 > 22 min |
| Sandbox warm-pool hit rate | < 90% ⇒ 15 s creeping back into p50 |

> **Four panels that are unusual and each catches something nothing else does:**
>
> - **`ci_config_files_touched > 0` and PRs without a gate verification are pages despite being structurally impossible.** That is exactly why they are monitored: a non-zero value means a constraint was dropped in a migration or a code path bypassed the gate. **Monitor the things you believe cannot happen, because otherwise you never learn your belief became false.**
> - **Attempts reaching 60 steps with a *late* first red→green.** This is the flake-driven false-progress signature: a flake flipped at step 24, the abandon rule was satisfied, and the task then burned 36 more steps going nowhere. It is invisible in the abandon-rate split and expensive.
> - **Override-success rate on declines.** A triage classifier is unfalsifiable by construction — declines produce no outcome. If overridden declines succeed 30%+ of the time, triage is rejecting viable work and the decline rate is costing more than it saves.
> - **Steps to first red→green.** The cleanest single indicator of retrieval and model quality, and it moves *before* success rate does, because a task that takes 40 steps instead of 18 still often succeeds — until it doesn't.

### On-call triage order

**First: correctness incident or capability regression?**

**Correctness (stop and escalate before diagnosing):**

1. **A PR without a gate verification, or with CI config touched.** Both should be impossible. **Pause PR creation**, then find out how the constraint was lost. A wrong diff already merged is much more expensive than a paused tool.
2. **False-success rate rising.** Find the merged-then-reverted PRs and read them. Look first at the **test diff**, not the source diff — the most common cause is a weakening the detector did not catch, which means the `WEAKENINGS` catalogue needs a new entry.
3. **`new_test_passes_on_old_code` findings rising.** The model is learning to write tests that pass regardless. FR-13 is catching them, so this is contained — but it is a signal the prompt or model changed for the worse.
4. **Gate-failure-after-green-inner-loop rising.** The affected-test selector is under-selecting. Contained by the gate (which is why the gate exists), but it is burning budget and will eventually be "optimised away" by someone chasing p50.

**Capability:**

5. **Steps to first red→green, p50.** The earliest indicator. Rising means retrieval or the model degraded; check retrieval quality independently of task success (FR-1), because the two failures look identical from the success rate.
6. **Flake quarantine churn.** A repo whose flake set is growing has an eroding stopping signal, and its abandon rule is becoming unreliable.
7. **Prompt-cache hit rate.** A drop is usually an unstable context pack (ordering changed, a file churning), and it hits cost immediately and directly.
8. **Sandbox warm-pool hit rate.** A miss puts 15 s back into a p50 that has ~1.4 min of margin.

> **The rule that keeps this honest: never respond to a p50 regression by weakening the gate.** The full-suite gate costs ~20 s and is the only thing standing between an under-selecting test selector and a false success. When p50 regresses the levers are the warm pool, the selector, and the loop length — **not FR-28**. This belongs written down, because the 20 seconds will look free during an incident and the cost of removing it does not show up for weeks.

### Rollback

| Situation | Action | Time to safe |
|---|---|---|
| Model or prompt regression | Roll back; the fixed task suite makes the comparison cheap and unambiguous | < 10 min |
| **False-success spike** | **Pause PR creation entirely**, keep the loop running in report-only mode | Immediate |
| Weakening detector gap found | Add the pattern to `WEAKENINGS`; **re-scan open agent PRs** for it | < 1 h + a sweep |
| Constraint lost in a migration | Restore it; **audit every PR created in the window** | Immediate, then a sweep |
| Retrieval index corruption | Serve from the previous index generation; re-index incrementally | < 30 min |
| Sandbox escape suspected | **Kill the pool, revoke anything reachable, stop accepting tasks** | Immediate — no diagnosis first |
| Cost spike | Tighten triage, lower `steps_cap`, route exploratory steps to a cheaper tier | Immediate |

> **Note the shape of the false-success response: pause PR *creation*, not the whole system.** The loop can keep running in report-only mode, which continues producing exactly the data needed to diagnose the problem — attempts, verifications, findings — without putting another wrong diff in front of a reviewer. Killing the whole system would remove the evidence along with the risk.
>
> And the weakening-detector-gap row implies something worth planning for: **the `WEAKENINGS` catalogue is a living artefact.** Each new pattern found in the wild is added, and the open-PR re-scan is what stops the ones already in flight. Treat it like a rule set for a security scanner, not a fixed constant.

---

## 4.3 Common mistakes

1. **Treating "tests pass" as sufficient.** It hands the agent the ability to move the goalposts. The verifier is inside the blast radius.

2. **An unbounded loop.** Not just costly — extra attempts increase the chance of finding the shortcut rather than the fix.

3. **Bounding on wall-clock or tokens only, with no progress signal.** Pays full price for every failure, and failures dominate at 35% success.

4. **Using model self-assessment as the stopping signal.** The agent is the least reliable available narrator of its own progress.

5. **Ignoring flakiness.** A flake flip is false progress; the abandon rule then degrades silently and the symptom looks like "hard tasks take longer".

6. **Running only affected tests and calling it verification.** A local fix that breaks something distant is exactly the false-success case.

7. **Skipping the full-suite gate to recover p50.** The 20 seconds look free and the cost surfaces weeks later as reverted PRs.

8. **String-diffing test files.** Misses semantic weakening (`assertEqual` → `assertTrue`) and flags harmless reformatting. AST.

9. **Trusting newly authored tests.** `assertTrue(True)` satisfies FR-8 and verifies nothing. Run it against the old code.

10. **Blocking on judgement calls.** A detector that blocks legitimate mock usage gets disabled within a month. Block what you can characterise exactly; flag the rest.

11. **Letting the agent edit CI configuration.** It can then make its own verification pass, and the diff looks like a routine tweak. Nothing else in the security model survives this.

12. **Forgetting `tox.ini` / `noxfile.py` in the CI pattern list.** They are not obviously CI config and they redefine what "the tests" means.

13. **Giving the agent `run_shell`.** Every convenience argument reintroduces the entire attack surface.

14. **Putting credentials in the sandbox "for integration tests".** The best defence against exfiltration is having nothing worth stealing.

15. **Attaching a best-effort diff to a failure report.** The caveat is not read. An unverified diff is the false-success failure by another route.

16. **No diff size cap.** Human merge is the last defence, and a 3,000-line diff is skimmed. This is a security requirement, not a UX preference.

17. **Accepting every task.** Triage improves cost per success *and* user experience — the user's alternative to a decline is a 25-minute wait then a failure.

18. **A decline with no prerequisite.** "Too complex" trains users to stop asking. Name what would make it workable.

19. **Not logging overridden declines.** A triage classifier is unfalsifiable by construction; overrides are the only calibration signal.

20. **Optimising cost per task instead of cost per success.** Improving success rate is a cost lever; so is failing faster.

21. **Ranking context by relevance score in the pack.** Reshuffles the prefix between steps and destroys the prompt-cache hit that is worth ~$0.28/task.

22. **Resetting the budget on orchestrator restart.** A doomed task gets a fresh 25 steps every redeploy.

---

## 4.4 Interview follow-ups

**"What makes this design different from every other agent?"**
Correctness is mechanically verifiable. Every other system in this folder has to infer whether it was right — fraud detection waits weeks for chargebacks, the manufacturing inspector waits for customer returns, the HR ranker may never find out. This one runs the tests and knows in seconds. So the design is a **verification loop**, and the quality of the system is the quality of that loop — its budget, its stopping rules, the integrity of the verifier — far more than the quality of the model. A better model inside a loop that accepts weakened tests just produces better-looking wrong answers.

**"Then what stops the agent from making the tests pass by changing the tests?"**
Nothing, unless you build it — and this is the genuinely novel problem here, because the verifier is inside the blast radius. Four layers. AST-level comparison against pre-existing tests, so assertions can be added but never relaxed, deleted, skipped, broadened or loosened in tolerance — AST rather than string diff, because `assertEqual` → `assertTrue` is invisible to a string diff and reformatting is a false positive for one. New tests are run against the pinned base SHA and must **fail**; a test that passes on unchanged code does not test the change, and that check costs seconds and catches the most common form of fake progress. Mutation sampling on changed lines, reported rather than blocking. And CI configuration is not writable at all — an agent that can edit `.github/workflows/` makes its own verification pass, and that diff looks like a routine tweak to a reviewer. I would add that `tox.ini` and `noxfile.py` belong in that list too, which is easy to miss because they are not obviously CI config.

**"Why cap the loop at 60 steps? Why not let it keep trying?"**
Three reasons, and cost is the least interesting. First, cost — real, but at 35% success the bigger lever is failing faster, not succeeding cheaper. Second, and this is the important one, **the bound is a correctness control**: attempt 30 is not a better attempt 3, it is a more desperate one, and desperation means broadening the search to include the test file. Third, honesty — a loop that never terminates never reports failure, so the user learns nothing. On top of the cap there is an early abandon at 25 steps if no test has moved red→green, which halves the cost of a failed task. And the signal is deliberately concrete: not "no progress", which is unmeasurable, but an observable state transition in the verifier.

**"How does a flaky test break your design?"**
It fakes the stopping signal. The abandon rule fires when no test has moved red→green, so a flaky test that happens to flip at step 24 satisfies the rule and the attempt runs the full 60 steps on a task it was never going to solve. Worse, the symptom is indistinguishable from normal behaviour — "hard tasks take longer" — so nobody investigates. So flake detection is load-bearing rather than hygiene: there is a quarantine registry, quarantined tests are subtracted from the progress computation, and I monitor a specific panel for attempts that hit 60 steps with a *late* first red→green, which is that failure's signature.

**"Your cost is $0.94 a task against a $2.50 ceiling. Comfortable?"**
No, because that is the wrong number. At 35% success, every merged PR carries about 1.9 failed attempts, so the real figure is **$2.81 per merged PR** — slightly over the per-task ceiling once measured per success. That reframing changes what you optimise: failing fast and declining work upfront become cost levers rather than UX compromises. Triage declining the worst 25% of tasks, which had roughly 10% success, raises the accepted population to ~43% and brings cost per merged PR to about $2.19 — a 19% improvement — while also giving those users an instant honest answer instead of a 25-minute failure. And the thing to argue about in a design review is whether $2.81 per merged PR beats the review-adjusted developer time it saves, not which model to use. Same arithmetic as the 4% book rate in the travel system.

**"96% of your cost is the LLM. Is that a problem?"**
It is a fact worth naming, because it is the opposite of most of this folder — fraud detection's dominant line is audit storage, manufacturing's is edge hardware. Here the loop multiplies every call, so tokens dominate. The consequence is that scaling work must attack the loop, not the infrastructure: raise the prompt-cache hit rate by keeping context packs byte-stable across iterations (order by path, not by relevance score — that alone is worth about $0.28 a task), route early exploratory steps to a cheaper tier and reserve frontier for repair, tighten triage, and shorten the loop. No amount of infrastructure engineering touches a bill that is 96% tokens.

**"Does FR-3 mean the full suite runs on every iteration?"**
No, and that distinction is a scope decision I would state explicitly rather than bury in a performance optimisation. Full suite per iteration consumes the entire latency budget, so the inner loop runs build, type-check and only the **affected** tests, and the full suite runs **once at the gate** before the PR is created. FR-3's guarantee is the gate. Those two differ precisely in the case that matters — a local fix that breaks something distant — so the gate is mandatory and never skipped for latency, an inner-loop pass is never presented as verification, and I monitor how often the gate fails after a green inner loop, because that rate is the affected-test selector's recall and a rising value means false-success risk.

**"Walk me through the latency budget."**
Naively it comes out at about 6.3 minutes against a 6-minute p50 SLO — **over**, and I would say so rather than massage it. Two fixes: warm sandbox pools remove the 15-second provision, and affected-test selection cuts test time by 60–80%, taking 2 minutes to about 30 seconds. Then the honest version *adds* a line back: 20 seconds for the mandatory full-suite gate. Net about 4.6 minutes. I make a point of including the gate in the budget, because a budget that only counts the savings is claiming FR-3's guarantee without paying for it — and the gate is exactly the line that quietly disappears the first time p50 regresses.

**"How bad is prompt injection here compared with your other agents?"**
Considerably worse, and it is the comparison that makes the point. If injection succeeds against the shopping agent you get an unwanted purchase — bad, bounded, reversible. Against the travel agent, a wrong booking — refundable. Here you get arbitrary code execution in a build environment **and** a pull request bearing your CI's trust, which is a supply-chain compromise with a legitimate author attached. The untrusted surface is also much wider than people expect: issue text, code comments, docstrings, README "agent instructions" sections, dependency source, test output, stack traces, even filenames. So the defences are mostly architectural rather than detective: there is nothing worth stealing in the sandbox, egress is deny-by-default with a two-entry allowlist, there is no `run_shell` tool, repo content arrives as tool results with provenance labels and never in the instruction position, and no tool can merge. Plus a red-team suite per release. I would not claim to detect payloads; that is an arms race with no end state.

**"What breaks at 100×?"**
Reviewer capacity. At 200,000 tasks a day and 35% success that is 70,000 PRs a day needing human merge, and the bottleneck moves from the agent to the humans — the same pattern as the HR ranker and the manufacturing inspector. But this system has an option those two do not: FR-7 is a **quality** boundary, not a legal one, so the response can be to **raise the evidence standard until light review is genuinely sufficient** — more mutation coverage, stricter minimality, richer verification evidence on the PR — rather than accepting more risk. Invest in making review cheap rather than in producing more PRs. That asymmetry exists only because the ground truth here is mechanical.

**"What would you cut to ship in two months?"**
Keep the whole verification spine: bounded loop, early abandon, full-suite gate, AST comparison of existing tests, the red-on-old-code check, CI config immutability, no `run_shell`, no credentials, human merge. Cut mutation sampling, FR-10 multi-repo, test authoring (FR-8) so v1 only fixes code against existing tests, per-repo budget tuning, and the triage classifier — start by accepting everything and *measure* the real success rate, since that single number decides viability and 35% is an assumption. What I would not cut is the gate or the weakening checks, because a v1 that ships false successes destroys trust in a way that is very hard to recover, and trust is the entire product.

---

## 4.5 Glossary

| Term | Meaning here |
|---|---|
| **Verification loop** | Edit → verify → repair, bounded. The architecture, not a feature of it |
| **Inner loop / gate** | Inner = build + types + **affected** tests, every iteration, for fast feedback. Gate = **full** suite, once, before the PR. FR-3's guarantee is the gate |
| **False success** | A CI-passing but wrong diff. The most damaging failure available, because it enters the codebase with human approval attached. Target ≤ 1% |
| **Test weakening** | Making the suite green by changing the test rather than the code — relaxed assertion, deleted case, skip marker, broadened exception, widened tolerance, altered fixture, mocked subject |
| **`subject_mocked`** | Mocking the very function that was changed, so the test asserts a mock returns what the mock was told. Flagged, not blocked — indistinguishable from idiomatic mocking without false positives |
| **Red-on-old-code check** | Run a newly authored test against the pinned `base_sha`; it must **fail**. The cheapest and highest-value guard in the system (FR-13) |
| **Red→green transition** | A previously-failing, non-flaky test now passing. The **only** progress signal, because it is objective and cheap |
| **Early abandon** | Stop at 25 steps if no red→green has occurred (FR-16). Cuts failed-task cost ~50%, and at 35% success failures dominate |
| **Failure signature** | Normalised (test id, assertion kind, file, line) — **excluding the message**, whose embedded values change between attempts and would reset the repeat counter |
| **Flake registry** | Quarantined flaky tests, subtracted from the progress computation. Load-bearing for the stopping rule, not hygiene (FR-31) |
| **Affected-test selection** | Running only tests touching changed files. An inner-loop optimisation whose recall is a **correctness** metric (FR-30) |
| **Step / token budget** | ≤ 60 calls, ≤ 400k tokens. Durable state so a restart does not reset it. **A correctness control before a cost control** |
| **Cost per merged PR** | Cost per task ÷ success rate. ~$2.81 vs ~$0.94 per task — the number that matters |
| **Triage decline** | A designed outcome. Improves unit economics *and* user experience, and must name a **prerequisite** the user can satisfy (FR-21) |
| **Override-success rate** | Success rate of declined tasks that were overridden. The only calibration signal a triage classifier can have (FR-22) |
| **Stable prefix** | A context pack ordered deterministically by path so it stays byte-identical across iterations, earning the ~70% prompt-cache hit |
| **CI config immutability** | Workflow files, `.pre-commit-config.yaml`, `tox.ini`, `noxfile.py` — non-writable. Without it, the agent can make its own verification pass (FR-23) |
| **Untrusted surface** | Issue text, comments, docstrings, READMEs, dependency source, test output, stack traces, filenames. All data, never instructions (FR-9/25) |
| **Honest failure** | A report of what was attempted and why it failed, **with the diff discarded**. A determinate fact here, which makes it cheap to produce and highly trust-building (FR-6) |

---

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)
