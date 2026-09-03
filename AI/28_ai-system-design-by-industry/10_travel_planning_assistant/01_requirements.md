# 10 · Requirements — Travel: Planning & Booking Assistant

> **Shared block:** [`../00_requirements_all_systems.md#10-travel--planning--booking-assistant`](../00_requirements_all_systems.md#10-travel--planning--booking-assistant) carries the problem statement, FR-1…FR-10, the NFR table, non-goals, the 5,300 ms latency budget, and the cost arithmetic that fails and then passes. **Those numbers are not repeated here.**
>
> **Next:** [`02_hld.md`](02_hld.md) →

---

## A. The comparison with the e-commerce agent is the fastest way to see this design

Both are Archetype C transactional agents. Reading the differences is more informative than reading either in isolation.

| | [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/) | **This design** |
|---|---|---|
| Inventory owner | Us (or a marketplace we control) | **Independent third parties** |
| Price stability | Minutes to hours | **Seconds** |
| Item independence | A cart is a bag of independent items | **Legs are interdependent — leg 3 failing invalidates legs 1 and 2** |
| Transaction | One commit against one system | **A distributed transaction with no 2PC** |
| Partial failure | Remove the item, keep the cart | **Booked legs must be released or refunded** |
| Feasibility | Not a concept | **A hard invariant — an itinerary must be physically executable** |
| Search latency | Under our control | **57% of the budget is a third-party fan-out** |
| Cost driver | Trigger gating (which sessions get the agent) | **Narration (which is a template mistake)** |

> **The one-sentence difference:** a shopping cart holds items whose availability is stable for minutes; **a travel itinerary holds seconds-long reservations across suppliers who cannot see each other.** Every hard part of this design descends from that.

---

## B. Booking is a saga, and whether holds exist decides everything

FR-6 demands atomic-or-compensated booking, and FR-7 demands idempotency. There is no two-phase commit across an airline, a hotel chain, and a transfer operator — no supplier will accept a prepare-then-wait protocol on behalf of a competitor.

### B.1 The two possible architectures

Shared open question 1 asks whether suppliers support inventory holds. It is not a detail; it selects the architecture.

| | **With holds** | **Without holds** |
|---|---|---|
| Sequence | Hold all legs → confirm all → release nothing | Book leg 1 → book leg 2 → book leg 3 |
| Failure at leg 3 | Legs 1–2 were only *held*; the holds expire or are released. **No money moved** | Legs 1–2 are **booked and paid**; must be cancelled, possibly with fees |
| Atomicity | Genuine, within the hold window | **Compensated, not atomic** — the user may see a charge and a refund |
| Financial exposure | Near zero | Cancellation fees, borne by someone (open question 4) |
| UX | "Confirming your trip…" then done | "We booked your flights but the hotel is gone — we're refunding" |
| Latency pressure | The hold window is a hard deadline for the whole confirm phase | None, but failure is expensive |

The design assumes **holds where available, sequential-with-compensation where not** — and it must know which suppliers are in which category, because the user-facing promise differs.

### B.2 Ordering matters when there are no holds

If legs must be booked sequentially with real commitments, the order is a design decision:

```
Book the LEAST cancellable leg FIRST.
```

The reasoning: if the leg with punitive cancellation terms is booked last and an earlier leg fails, you cancel cheap things. If it is booked first and a later leg fails, you cancel the expensive thing. Non-refundable flights before refundable hotels, not the other way around.

> This is counter-intuitive — the instinct is to book the *most likely to succeed* first — and it is wrong for the same reason as any other risk ordering: you want your irreversible commitment to be the last thing you make, not the first. Concretely: book the refundable hotel first (cheap to unwind), then the non-refundable flight (nothing left to fail after it).

### B.3 Idempotency is not optional and cannot be retrofitted

Every supplier call in the booking phase carries a caller-generated idempotency key derived from `(booking_id, leg_id, attempt_semantics)`. A retry after a timeout is the **normal** case, not an edge case:

| Situation | Without idempotency | With idempotency |
|---|---|---|
| Supplier returns 504 after actually booking | Retry double-books and double-charges | Retry returns the existing booking |
| Our process crashes mid-saga | Restart re-books legs already booked | Restart resumes correctly |
| User double-taps confirm | Two bookings | One |

And crucially: **a timeout is not a failure.** It is an unknown outcome, and treating it as a failure (then compensating) can cancel a booking that succeeded, or leave one orphaned. The saga needs a *reconciliation* step that queries the supplier for the idempotency key's outcome rather than assuming.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-11** | P0 | Supplier hold capability is modelled per supplier | A registry records hold support, hold duration, cancellation terms, and idempotency support; the booking strategy is selected from it |
| **FR-12** | P0 | Legs are booked in ascending order of cancellation cost when holds are unavailable | Verified by test: a failure on the last leg never requires cancelling a non-refundable earlier leg where an ordering existed that avoided it |
| **FR-13** | P0 | Every supplier mutation carries a caller-generated idempotency key | Replay test: the same call issued twice produces one booking |
| **FR-14** | P0 | A timeout is resolved by reconciliation, never assumed to be a failure | Injected-timeout test: the saga queries outcome by idempotency key and converges on the true state |
| **FR-15** | P0 | Compensation is durable and retried until confirmed | A release/refund that fails is retried with backoff and escalated to support after a bounded number of attempts; **no orphan is ever closed silently** |
| **FR-16** | P1 | The user-facing promise matches the supplier's capability | If any leg's supplier lacks holds, the confirmation screen says what "booking" means for this itinerary rather than implying atomicity |

---

## C. Feasibility is a hard invariant, not a ranking feature

FR-3 requires 100% time-feasible itineraries. This is easy to state and easy to get wrong, because feasibility is not one check.

### C.1 What "feasible" actually involves

| Check | Failure looks like |
|---|---|
| **Connection buffer** | 35 minutes between an international arrival and a domestic departure at a large airport |
| **Terminal changes** | A connection that requires an inter-terminal transfer longer than the layover |
| Airport-to-hotel transfer time | A 23:50 arrival with a hotel whose reception closes at 23:00 |
| **Check-in / check-out times** | Arriving at 06:00 for a 15:00 check-in with nowhere to go |
| Time zones and date-line crossings | An itinerary that appears to arrive before it departs |
| Local ground-transport availability | The last train has gone; only a taxi remains, at a price not in the quote |
| Minimum connection times published by the airport | Legally/operationally mandated buffers that differ per airport and per international/domestic mix |
| Multi-day coherence | Day 3's activity in a city the traveller leaves on day 2 |

### C.2 Why it must be a filter, not a score

An infeasible itinerary is not a *worse* itinerary. It is not an itinerary. Ranked with a penalty, a very cheap infeasible option outranks a slightly more expensive feasible one — and that is a trust-destroying result, because the user notices immediately and concludes the assistant does not understand travel.

> **The same lesson as hard constraints in [`../09_realestate_search_valuation/`](../09_realestate_search_valuation/) and [`../01_ecommerce_shopping_agent/`](../01_ecommerce_shopping_agent/):** boundaries are filters, preferences are scores, and putting a boundary in the scoring function is the most common way these designs fail. It recurs so often across archetypes that it is worth treating as a rule.

### C.3 And the buffers are a policy, not a constant

A 45-minute connection buffer is right for a small domestic airport and reckless for an international transfer with immigration. The buffer table is **configuration** — per airport, per connection type, per airline alliance (for baggage transfer) — and it needs an owner, because tightening it increases options and increases missed connections.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-17** | P0 | Feasibility applied as a filter before ranking | No infeasible itinerary is ever presented, at any price advantage |
| **FR-18** | P0 | Connection buffers are configurable per airport and connection type | A buffer table with an owner; changes audited, since they trade options against missed connections |
| **FR-19** | P0 | Time-zone and date-line handling is tested explicitly | Test suite includes date-line crossings, DST transitions, and same-day arrivals that precede departure in local time |
| **FR-20** | P1 | Ground-transport availability at arrival time is checked, not assumed | An arrival after last public transport is flagged with the implied transfer cost, or the itinerary is filtered |

---

## D. The narration cost error, and the general rule behind it

The shared cost block is unusual in this collection: **the naive design fails its budget by 3.7×** ($0.935 vs $0.25 per booking) and the fix is not a smaller model — it is not using a model.

### D.1 The arithmetic that fails

```
Narration of 3 options, frontier tier:
  3 × (2,200 in + 350 out) = 3 × $0.01185 = $0.0356 per session
  = 95% of the session's $0.0374 total
At a 4% book rate: $0.0374 / 0.04 = $0.935 per booking      ceiling $0.25  ✗
```

### D.2 Why it is the wrong tool, independent of cost

An itinerary is a **table**: legs, times, durations, prices, terms. Asking a language model to describe a table produces prose that is longer, harder to scan, and occasionally wrong about the numbers it is describing. Users comparing flights want a column of departure times, not three paragraphs.

| What the LLM is bad at here | What it is genuinely good at |
|---|---|
| Restating structured data | The one **comparative judgement**: "the 07:40 saves two hours for ₹1,800 more" |
| Listing times and prices accurately | Explaining *why* an option was recommended given stated preferences |
| Being scannable | Handling the messy free-text intent at the front of the flow |

### D.3 The levers, and what they cost

| Lever | Mechanism | Effect | Cost of the lever |
|---|---|---|---|
| **Template the narration** | Render the itinerary from data; LLM writes only the comparative sentence | **−70% of narration** | Less conversational feel; mitigated by the sentence being the part that reads as intelligent |
| **Narrate top 1, not top 3** | Options 2 and 3 as structured cards | −60% narration | Slightly less help comparing; the comparative sentence covers it |
| Route refinements to the small tier | Simple changes do not need frontier | −15% | Occasional quality dip on complex refinements |
| **Cache by (route, date-window, cabin)** | Popular routes repeat heavily; cache *search shape*, not prices | −25% of supplier calls and intent parsing | Cache invalidation complexity; **must never cache prices** |

```
Combined: $0.0374 → ≈ $0.010 per session ⇒ ≈ $0.25 per booking  ✅ (at the ceiling, not under it)
```

> **The general rule:** *using an LLM where a template suffices is the most common cost error in agent designs.* And note the residual honesty — after all four levers this lands **at** $0.25, not comfortably under. If the real book rate is 2% rather than 4% (open question 2), cost per booking doubles and more must come out. That sensitivity belongs in the design, not in a post-launch surprise.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-21** | P0 | Itinerary presentation is rendered from structured data | No LLM call produces times, prices, or terms; those come from the itinerary record |
| **FR-22** | P0 | LLM output is confined to comparative and explanatory prose | Prompt and response schema constrain generation to commentary; numbers referenced are injected from data, not generated |
| **FR-23** | P1 | Search-shape caching, never price caching | Cache keys exclude price; a cache hit still triggers live pricing (FR-4) |
| **FR-24** | P1 | Cost per booking is monitored against the book rate | Alert if cost/booking exceeds the ceiling, including via a book-rate decline rather than a cost increase |

---

## E. The slow supplier is the common case

The shared budget allocates 3,000 ms to supplier fan-out — 57% of the total — with a hard timeout.

### E.1 Why "wait for all suppliers" has no answer

With, say, 12 supplier calls each independently having a 5% chance of exceeding 3 s, the probability that *all* respond in time is `0.95¹² ≈ 54%`. **Roughly half of all searches have at least one slow supplier.** A design that waits for completeness fails its latency SLO on half of requests; a design that treats partial results as an error fails on half of requests.

### E.2 So partial results must produce a real answer

| Requirement | Consequence |
|---|---|
| Per-supplier timeout, not a global one | One slow supplier cannot consume the whole budget |
| The combiner works with what arrived | It cannot assume a complete flight set or a complete hotel set |
| Missing coverage is **disclosed** | "Showing results from 9 of 12 partners" — the user can retry for more |
| Late arrivals are usable | A response arriving at 3.2 s can enrich the *next* turn (the follow-up budget is 2.5 s and the data is already warm) |
| Missing a **whole category** is different from missing some options | No flights at all is a failed search; two of five hotel suppliers missing is a partial one |

That last distinction matters: an itinerary needs at least one option per required leg. Partial degradation within a category is acceptable; an empty category is not, and must be reported as such rather than presented as "no trips available".

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-25** | P0 | Per-supplier timeouts with partial-result assembly | With any subset of suppliers responding, a valid itinerary set is produced or an explicit category-level gap is reported |
| **FR-26** | P0 | Supplier coverage is disclosed to the user | The response states which supplier groups contributed, so an unusually thin result set is explicable |
| **FR-27** | P1 | Late supplier responses are captured for the following turn | Responses arriving after the timeout are stored against the session and used in refinements |
| **FR-28** | P1 | Per-supplier health circuit-breaks | A supplier failing consistently is skipped rather than repeatedly timed out, and its absence is disclosed |

---

## F. Quote accuracy: the most damaging failure

NFR: ≥ 99% of confirmed quotes bookable at the quoted price. A quoted price that fails at payment is worse than a higher price quoted honestly, because the user has already committed emotionally and has to start again.

FR-4's 60-second re-validation is the mechanism, and it has a subtlety: re-validation must happen **between confirmation and booking**, not only at presentation.

```
present itinerary → user reads, thinks, discusses (2–8 minutes) → confirms
                                                                    ↑
                             re-validating only HERE is the mistake ─┘
                             (the quote is already minutes stale at confirmation)
```

The correct sequence: present with a freshness stamp → on confirmation, **re-validate before charging** → if the price moved, show the change and require a fresh confirmation rather than silently charging the new amount or silently failing.

| Price movement | Handling |
|---|---|
| Unchanged | Proceed |
| Moved within a small tolerance, downward | Proceed, inform |
| Moved upward, any amount | **Stop. Re-confirm.** Never charge more than the confirmed number |
| Unavailable | Offer the nearest alternative with a fresh quote |

> Silently charging a higher price than the one confirmed is not a bug, it is a chargeback and possibly a regulatory matter. The tolerance for upward movement is **zero**, and that is a product rule the architecture must enforce rather than a threshold to tune.

**Requirements added here:**

| ID | Pri | Requirement | Acceptance criterion |
|---|:--:|---|---|
| **FR-29** | P0 | Re-validation occurs between confirmation and payment | Test: a price change injected after presentation but before confirmation results in re-confirmation, never a silent charge |
| **FR-30** | P0 | Upward price movement always requires fresh confirmation | Zero tolerance; enforced in the booking service, not the UI |
| **FR-31** | P1 | Quote freshness is visible to the user | The presented itinerary carries an explicit freshness indicator and expiry |

---

## G. Additional non-goals (beyond the shared block)

- **Not** a supplier connector platform — supplier APIs are consumed, and their capabilities (holds, idempotency) are *modelled* rather than built.
- **Not** payment processing — an existing PSP is called, and this design never handles card data.
- **Not** visa or immigration advice (liability), though **infeasibility caused by an obvious document requirement should be flagged, not silently ignored**.
- **Not** loyalty programme management.
- **Not** inventory ownership or dynamic pricing.
- **Not** LLM-generated prices, times, or terms (FR-21/22).

---

## H. Open questions carried into the HLD

Beyond the shared block's four:

1. **Which suppliers support holds, for how long, and with what idempotency semantics?** This selects the architecture (§B.1), and the answer differs per supplier, meaning the system runs both strategies simultaneously.
2. **What is the escalation path for a stuck compensation?** FR-15 requires no silent orphans, which means a support queue and an owner. Without that, "retry with backoff" ends in a row nobody reads.
3. **Who is authorised to accept a cancellation fee on the user's behalf?** Open question 4 in the shared block is a financial-policy question, and the saga needs a rule, not a judgement call at 3 a.m.
4. **What is the real distribution of supplier response times?** The 5% >3 s assumption drives the partial-result design. If it is 20%, coverage disclosure becomes a prominent product surface rather than a footnote.
5. **Is the 4% book rate real?** Every cost figure divides by it, and the design lands *at* the ceiling, not under it.

---

**Next:** [`02_hld.md`](02_hld.md) →
