# 10 · Production & Interview — Travel: Planning & Booking Assistant

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)

---

## 4.1 AI-specific concerns

| Concern | How it shows up here | What we do about it |
|---|---|---|
| **The LLM is the wrong tool for most of this flow** | Naive narration of 3 itineraries: **$0.935/booking against a $0.25 ceiling**, 3.7× over | Render from data; the LLM writes **one** comparative sentence (FR-21/22). It also returned ~490 ms of latency — when a change improves cost *and* latency, the original design was using the wrong tool, not a badly tuned one |
| **Generated numbers are a chargeback risk, not a quality issue** | An LLM restating a table occasionally gets a price or a time wrong | Numbers are structurally impossible to generate: the response schema has one prose field, and every figure comes from the itinerary record. **Enforced by API shape, not by prompt discipline** |
| **Intent extraction must ask, not guess** | "Next month", "somewhere warm", "under 60k" — genuinely underdetermined | FR-1: ambiguous slots return questions with candidates. A confident search for a trip nobody wanted is worse than a question, because the user cannot tell it was a guess |
| **Non-determinism meets a financial write path** | The same intent may produce different itineraries across turns | The write plane never re-derives anything. `itinerary_id` pins exactly what the user saw; `confirmed_amount` and `accepted_terms_hash` pin what they agreed to. **The LLM is never in the loop after confirmation** |
| **Feasibility cannot be learned** | The training signal (missed connections) is rare, weeks-delayed and confounded by weather | Feasibility is a **rule filter** over an owned buffer table (FR-17/18). Learning is used to *validate* the table, never to replace it |
| **Ranking learns; filtering does not** | Preference ranking is a genuine ML problem; feasibility is not | Filters before scores. The most common failure of this archetype is a boundary implemented as a penalty term — see [`../09_realestate_search_valuation/`](../09_realestate_search_valuation/) and [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/) |
| **Commentary must not outlive its data** | Re-validation changes a price; the cached sentence still says "₹1,800 more" | Regenerate or drop the commentary after re-validation. Prose disagreeing with the card beside it is worse than no prose |
| **Cost is hostage to a rate we do not control** | Every per-booking figure divides by the book rate; the design lands **at** $0.25, not under | FR-24 alerts on cost/booking including via a **book-rate decline**. A 2% real rate doubles cost per booking with no cost change at all — the failure looks like nothing on a cost dashboard |
| **Evaluation needs a feasibility suite, not a quality score** | "Was the itinerary good?" is subjective; "was it executable?" is not | Golden set of adversarial itineraries: date-line crossings, DST layovers, 35-minute Heathrow connections, 23:50 arrivals at hotels closing at 23:00. **100% must be filtered.** This is a gate, not a metric — cf. [`../../16_evals/`](../../16_evals/) |

---

## 4.2 Operations & runbook

### Dashboards

**Read plane — is search working?**

| Panel | Alert |
|---|---|
| First-itinerary p95 vs 6 s SLO | > 5.5 s for 10 min |
| **Per-supplier p95 and timeout rate** | any supplier timeout rate > 15% |
| **Searches with ≥ 1 slow supplier** (expected ~46%) | > 65% — something systemic |
| Category-gap rate (a whole category empty) | > 1% |
| Circuit breakers open | any open > 15 min |
| Infeasible-bundle discard rate | sudden drop ⇒ **filter may have stopped running** |
| Shape-cache hit rate (expected ~25%) | < 15% ⇒ cost lever eroding |
| Clarification rate | sharp move either way ⇒ intent extraction changed behaviour |

**Write plane — is money correct?**

| Panel | Alert |
|---|---|
| **Quote accuracy** — confirmed quotes bookable at the quoted price | < 99% |
| Re-validation outcome mix (held / down / **up**) | upward rate > 5% |
| Saga outcomes: booked / compensated / **escalated** | any escalation |
| **Open compensations by age and financial exposure** | any item > 24 h, or exposure > threshold |
| **`unknown` steps entering reconciliation, and resolution rate** | unresolved > 0.1% |
| Double-charge count | **> 0 is a page** |
| **Orphan candidates** — booked legs with no live itinerary | **> 0 is a page** |
| Cost per booking, and book rate, on one chart | cost/booking > $0.25 |
| Ledger-vs-supplier reconciliation discrepancies | any |

> **The three panels teams usually lack, and each catches a failure nothing else sees:**
>
> - **Infeasible-bundle discard rate.** A *drop* here is the alarm, not a rise. If the discard rate falls from 25% to 0%, the feasibility filter has been bypassed — and every subsequent search silently ships infeasible itineraries while every latency and cost metric looks better than ever.
> - **Book rate on the same chart as cost per booking.** FR-24. Unit economics can break with costs perfectly flat.
> - **Orphan candidates.** A booked supplier leg with no corresponding live itinerary is, by definition, something we are paying for on a user's behalf that nobody is tracking. It should be structurally impossible; measure it anyway, because that is how you find out the structure has a hole.

### On-call triage order

**First question: read plane or write plane?** They have different urgencies and different owners.

**Read plane** (degradation is expected; users are inconvenienced):

1. **Per-supplier panel.** One supplier's timeout rate spiking explains most search complaints and takes five seconds to see.
2. **Circuit breakers.** An open breaker is working as designed; a *flapping* one is worse than either state.
3. **Category-gap rate.** If a whole category is empty, is it all suppliers (infrastructure) or our normalisation rejecting valid responses (our bug)?
4. **Infeasible-discard rate.** A drop means the filter stopped. Treat as a write-plane-severity incident — we are shipping unexecutable itineraries.
5. **Cache hit rate.** A collapse points at a supplier-set version change invalidating everything.

**Write plane** (correctness is absolute; money is involved):

1. **Escalated compensations, oldest and largest first.** These are real charges against real users. Every one has a named owner.
2. **Unresolved `unknown` steps.** Suppliers we cannot get a straight answer from. Check whether `supports_outcome_query` is still accurate for that supplier — capability regressions happen silently after supplier API changes.
3. **Upward re-validation rate.** A spike means a supplier's pricing became volatile, and users are hitting re-confirmation walls. Consider shortening the presented freshness window.
4. **Double-charges and orphans.** Both should be zero. Either is a page, and the first action is to **stop new bookings against the affected supplier** before diagnosing.

> **The rule that keeps this manageable: never debug the write plane by retrying it.** A retry against a supplier whose state you do not understand is how a single orphan becomes three. Read the saga log, reconcile by idempotency key, then act.

### Rollback

| Situation | Action | Time to safe |
|---|---|---|
| Bad ranker or combiner deploy | Standard rollback; read plane is stateless | < 5 min |
| **Bad feasibility change** | Rollback **and** re-check itineraries presented in the window; expire their quotes | < 5 min + a sweep |
| Buffer table tightened wrongly | Revert to the prior `effective_from` row — the table is versioned for exactly this | < 1 min |
| Supplier degraded | Force the breaker open; coverage disclosure explains the thinner results | Immediate |
| **Bad booking-service deploy** | Rollback, then **drain the saga log** — in-flight sagas must complete or compensate under the *old* semantics | Minutes, and never rushed |
| Prompt change producing bad commentary | Disable commentary entirely (a feature flag on one field) | Immediate |
| Cost spike | Narrate top 0 (cards only); tighten the cache window | Immediate |

> **The write plane's rollback is not a rollback of state, it is a drain.** A saga half-executed under the old code must not be resumed by new code with different compensation semantics — that is how you get a leg released twice or not at all. Deploys to the booking service are gated on saga-log quiescence, which makes them slower and is the correct trade.

---

## 4.3 Common mistakes

1. **Narrating structured data with a frontier model.** 3.7× over budget, slower, less scannable, and occasionally wrong about its own numbers. An itinerary is a table.

2. **Feasibility as a ranking penalty.** A large enough price advantage always defeats a finite penalty. Boundaries are filters; preferences are scores.

3. **Waiting for all suppliers.** ~46% of searches have at least one slow supplier. A design that needs complete data fails on its most frequent situation.

4. **A global timeout instead of per-supplier.** One slow supplier consumes the whole budget and you return nothing, when nine suppliers had answered.

5. **Treating a timeout as a failure.** The highest-frequency correctness trap here. Compensating on a timeout can cancel a booking the traveller is now relying on.

6. **Random idempotency keys per HTTP attempt.** Provides no idempotency while looking like it does. Keys must be *derived* from `(booking, leg, action, attempt semantics)`.

7. **Booking the most-likely-to-succeed leg first.** The instinct, and backwards. Ascending cancellation cost keeps the irreversible commitment last.

8. **Sorting booking order by price.** Price and cancellation cost are different axes. A cheap non-refundable flight is the worst thing to book early.

9. **Re-validating only at presentation.** Users think for 2–8 minutes. The quote is stale exactly when it matters.

10. **A tolerance band for upward price movement.** However small, it is charging an amount the user did not agree to. Zero tolerance, enforced in the service, not the UI.

11. **Caching prices.** Fast, and it directly causes the single most damaging failure in the system. Cache the search *shape*.

12. **Inline compensation.** If the orchestrator dies, the compensation dies with it — producing the orphan FR-15 forbids. Durable queue, separate worker.

13. **Auto-closing escalated compensations.** An expiry on `ESCALATED` is how orphans become invisible. Only a human closes it.

14. **Promising atomicity the supplier mix cannot deliver.** The partial booking is the symptom; the mis-set expectation is the failure (FR-16).

15. **Conflating booking order with travel order.** Iterating the saga in travel order maximises damage — it books the trip in the order it happens, which is rarely the order that is cheapest to unwind.

16. **A single global connection buffer.** Either loses good itineraries at small airports or ships missed connections at large ones.

17. **Naive local-time arithmetic.** Instants for gaps, IANA zones for wall-clock rules. Mixing them produces "arrives before it departs" and 90-minute layovers that are really 30.

18. **Assuming the book rate.** Every cost figure divides by it, and the design sits *at* the ceiling. A book-rate decline breaks unit economics with cost dashboards perfectly flat.

---

## 4.4 Interview follow-ups

**"You have no two-phase commit. So what happens when leg 3 fails?"**
It depends on a fact I would establish first: whether the suppliers involved support inventory holds. With holds, legs 1–2 were only held, the holds are released or lapse, and no money moved — genuine atomicity within the hold window. Without holds, legs 1–2 are booked and paid, and I compensate: durable queue, idempotent release/refund calls, bounded retries, then a named human owner. And critically, the damage was minimised *before* the failure by booking in ascending cancellation cost — so the leg that failed had nothing expensive booked ahead of it. The registry that records hold capability per supplier is what makes both paths possible in one system.

**"A supplier times out after possibly booking. What do you do?"**
Nothing irreversible. The step goes to `unknown`, not `failed` — those are different states in my schema and only `unknown` routes to reconciliation. I query the supplier for that idempotency key's outcome; if it can't tell me, I safely replay the call, which returns the existing booking if one was made. If neither works I escalate to a human with the full saga log. The two tempting answers are both wrong: compensating may cancel a real booking the traveller depends on, and proceeding may double-charge. **A timeout is an unknown, not a failure**, and most implementations lack the state to say so.

**"Why is feasibility a filter and not a feature?"**
Because an infeasible itinerary is not a worse itinerary, it is not an itinerary. As a ranking penalty, a sufficiently cheap infeasible option outranks a feasible one — and the user notices a 35-minute Heathrow connection immediately and concludes the assistant does not understand travel. I go further and make it unrepresentable: `CHECK (feasible)` on the itinerary table, so infeasible candidates are never persisted. A ranker cannot promote what does not exist. The same filters-versus-scores rule is the most common failure across this whole archetype.

**"Your cost analysis fails by 3.7×. Talk me through the fix."**
The naive design narrates three itineraries with a frontier model — $0.0356 per session, which is 95% of session cost, giving $0.935 per booking against a $0.25 ceiling. The fix is not a cheaper model; it is not using a model. An itinerary is structured data: legs, times, prices, terms. Rendering it as cards costs nothing and reads better. The LLM keeps the one thing it is genuinely good at — the comparative judgement, "the 07:40 saves you two hours for ₹1,800 more." That plus narrating one option instead of three, small-tier refinements and shape caching gets to ~$0.010 per session. I would flag two things: it lands **at** $0.25, not under, and the whole figure divides by an assumed 4% book rate. At 2% it doubles and more has to come out.

**"~46% of searches have a slow supplier. How is that a good system?"**
Because that number is a property of depending on twelve third parties, not of my design — twelve suppliers each with a 5% chance of exceeding 3 s gives `1 − 0.95¹² ≈ 46%`. What my design controls is what happens then. Per-supplier deadlines so one slow supplier cannot eat the budget; partial assembly so nine replies produce a real answer; explicit coverage disclosure so a thin result set is explicable and retryable; late responses captured for the next turn. And one distinction that matters: missing *some* hotel options is partial degradation, while missing *all* flights is a failed search and must say "we couldn't reach the airlines" rather than "no trips available" — the second sends the user to a competitor over an infrastructure blip.

**"Where does the LLM sit in the write path?"**
Nowhere, deliberately. After confirmation, nothing is re-derived. `itinerary_id` pins what the user saw, `confirmed_amount` pins what they agreed to pay, `accepted_terms_hash` pins which cancellation terms they accepted. Non-determinism is acceptable in search and unacceptable where money moves, so the boundary is drawn at confirmation and the write plane is entirely deterministic.

**"How do you test feasibility?"**
An adversarial golden set that must be 100% filtered: date-line crossings, DST transitions inside layovers, 35-minute connections at large international airports, terminal changes longer than the layover, 23:50 arrivals at hotels whose reception closes at 23:00, day-3 activities in a city departed on day 2, and arrivals after last public transport. It is a **gate, not a metric** — a 99% pass rate is a failure, because the 1% is an itinerary a real person cannot execute. This is one of the rare places where a hard gate is right and a score is not.

**"What breaks at 10×?"**
Not the read plane — it is stateless and scales horizontally. **Supplier rate limits and commercial terms** break first: at 4,000 searches/s we are a meaningful fraction of some suppliers' query volume, and if their pricing is per-search rather than per-booking, the shape cache stops being a cost optimisation and becomes the business model. Second is the compensation queue tail: 3.2M bookings/month at even a 0.5% compensation rate is 16k items, and every exhausted retry needs a human. At 100× the genuinely computational limit is the combiner — bundling is the only superlinear stage — and buffer-policy governance, which no single owner can maintain across hundreds of airports. **The scaling story is commercial and organisational, not computational.**

**"What would you cut to ship in three months?"**
Keep: the saga with idempotency and reconciliation, feasibility as a filter, re-validation between confirm and pay, zero tolerance on upward price movement, durable compensation with human escalation. Cut: FR-10 disruption monitoring, FR-9 corporate policy, activities as a category, multi-city itineraries (single origin-destination-return only), and the shape cache — accepting worse unit economics initially and measuring the real book rate before optimising against an assumed one. What I would **not** cut is any part of the write plane, because a partial booking is a financial defect and a support case, and shipping that to learn from it is not a trade worth making.

**"One supplier lacks holds and lacks outcome query. Do you still sell it?"**
Yes, with the promise adjusted. `atomicity_promise = "compensated"` flows to the confirmation screen so the user is told what "booking" means for this itinerary before they commit (FR-16). And that supplier's legs are ordered by cancellation cost like any other, so a failure elsewhere unwinds cheaply. What I would not do is show the same confident "we'll book your whole trip" language as for an all-holds itinerary — the mis-set expectation is the real failure, and the partial booking is only its symptom.

---

## 4.5 Glossary

| Term | Meaning here |
|---|---|
| **Read plane / write plane** | The organising split. The read plane may lose data (partial results are valid); the write plane may not lose money |
| **Saga** | A distributed transaction executed as a sequence of local commitments with compensating actions, used because 2PC is unavailable across suppliers |
| **Compensation** | The undo action for a completed saga step — release a hold, cancel a booking, refund a charge |
| **Hold** | Supplier-side inventory reservation for a bounded window. Its availability **selects the architecture** |
| **`unknown` state** | A saga step whose outcome is not known (typically a timeout). Routes to **reconciliation**, never to compensation. The most important state in the schema |
| **Reconciliation** | Querying a supplier for an idempotency key's true outcome. FR-14: a timeout is an unknown, not a failure |
| **Idempotency key** | Caller-generated, **derived** from `(booking_id, leg_id, action, attempt_semantics)`. A random per-attempt UUID provides no idempotency |
| **`attempt_semantics`** | The term that distinguishes a *retry of the same intent* (reuse the key) from a *new intent* on the same leg (increment it) |
| **Booking order vs travel order** | Booking order is ascending cancellation cost (FR-12); travel order is `leg_seq`, what the user sees. Conflating them maximises damage |
| **Orphan** | A booked or held supplier leg with no live itinerary — something we are paying for that nobody tracks. Structurally impossible; measured anyway |
| **Feasibility filter** | The hard gate before ranking: buffers, terminals, transfers, check-in windows, transport availability, time zones, multi-day coherence |
| **`feasibility_proof`** | Every check with its margin, persisted. Support needs the argument; buffer changes need the margins |
| **Connection buffer** | Minimum layover, per airport × connection type × terminal × alliance. **Owned, audited configuration** (FR-18), never a global constant |
| **Published MCT** | An airport's mandated minimum connection time. Our policy may only be more conservative, never less — validated on write |
| **Category gap vs option gap** | Zero options in a required leg (a failed search, say so) vs some suppliers missing (partial, disclose it) |
| **Coverage disclosure** | "Showing results from 9 of 12 partners" (FR-26) — makes a thin result set explicable and retryable |
| **Shape cache** | Cached search *shape* by (route, date-window, cabin) — supplier set, fare families, normalisation hints. **Never prices** (FR-23) |
| **Freshness stamp** | `priced_at` / `price_expires_at`, user-visible (FR-31). 60 s per FR-4 |
| **Commentary** | The single LLM-generated field. Regenerated or dropped after re-validation so it can never contradict the card beside it |
| **`atomicity_promise`** | `atomic` or `compensated`, derived from the supplier mix and shown before confirmation (FR-16) |
| **Book rate** | Look-to-book conversion. Assumed 4%; every cost figure divides by it, and the design lands *at* the ceiling |

---

> ← [`03_lld.md`](03_lld.md) · **Folder index:** [`README.md`](README.md) · **All systems:** [`../README.md`](../README.md)
