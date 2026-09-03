# 01 · Requirements — Real-Time Voice Assistant

> **Phase 1 of 4** · [← README](README.md) · [HLD →](02_hld.md)
> **Shared front-matter:** [`../00_requirements_all_systems.md#8-real-time-ai-voice-assistant`](../00_requirements_all_systems.md#8-real-time-ai-voice-assistant)

---

## 1.1 Problem & users

### What breaks today

A contact centre handles inbound phone calls with human agents. ~50% of calls are routine (order status,
appointment changes, balance enquiries), and each costs ~$0.60/minute of agent time. Consequences:

1. **Cost scales with call volume**, so support headcount is a tax on growth.
2. **Hold times push routine calls behind complex ones**, so the callers with the hardest problems wait
   longest.
3. **Out-of-hours coverage is unaffordable**, so a whole class of caller need goes unmet.

### Users and jobs

| User | Job | What "working" means |
|---|---|---|
| **Caller (primary)** | Resolve something by speaking naturally | The system responds **fast enough to feel like a conversation** — not fast enough to feel like a fast computer |
| Human agent | Inherit escalated calls with context | A transcript summary, not a recording to listen back to |
| Ops lead | Contain routine calls within budget | Containment rate up; caller satisfaction flat or better |
| Compliance | Recording, consent, retention handled | Per-region consent enforced; transcripts retained per policy |

### The defining constraint

**Humans notice conversational lag above ~500 ms and start talking over the system above ~800 ms.** That
number governs everything, and it is far harsher than it first appears because it must cover a
**four-stage pipeline** — ASR → endpointing → LLM → TTS — where [01](../01_production_rag_system/README.md)
gets 1.5 s for a *single* LLM's first token.

| System | Budget | Covers |
|---|---|---|
| [01 RAG](../01_production_rag_system/01_requirements.md#15-latency-budget) | 1,500 ms | TTFT only |
| [02 Support agent](../02_customer_support_agent/01_requirements.md#15-latency-budget) | 2,000 ms | First response, text |
| [06 RecSys](../06_recommendation_system/01_requirements.md#15-latency-budget) | 150 ms | Whole request (no LLM) |
| **This system** | **800 ms** | **ASR + endpointing + LLM + TTS** |

**Two consequences that fall out immediately:**

1. **A frontier-tier LLM is arithmetically impossible.** Its ~900 ms TTFT alone exceeds the entire budget.
   The generator *must* be small-tier — a quality ceiling imposed by physics rather than by cost.
2. **The budget does not close even so** ([§1.5](#15-the-latency-budget--the-hardest-in-this-set)), which is
   why speculative endpointing exists.

> **Mental model:** a phone conversation is a **duplex protocol with a strict round-trip deadline**, not a
> request/response API. Both parties may transmit at any time, and silence is meaningful.
>
> *Where the analogy breaks:* a network protocol can retransmit. A conversation can't — a missed turn or a
> talked-over response is a permanently degraded interaction, which is why barge-in
> ([FR-4](#core-pipeline)) is a P0 correctness requirement rather than a polish feature.

---

## 1.2 Functional requirements

### Core pipeline

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| **FR-1** | P0 | Stream audio in **and** out, full duplex | Bidirectional; neither direction blocks the other |
| **FR-2** | P0 | Streaming ASR with partial hypotheses | Partials < 200 ms behind speech |
| **FR-3** | P0 | **Endpointing** — detect end of the caller's turn | p95 detection < 300 ms after speech stops |
| **FR-4** | P0 | **Barge-in** — caller interrupts, system stops speaking | TTS halts **< 150 ms** after caller speech detected |
| **FR-5** | P0 | Streaming LLM response | First sentence emitted before the full response completes |
| **FR-6** | P0 | Streaming TTS, sentence-chunked | First audio < 250 ms after the first LLM sentence |
| **FR-7** | P0 | Session state across turns | Reference resolution across the call |

**FR-3 and FR-4 are the two requirements unique to voice**, and both are about *silence and interruption* —
concepts that don't exist in a text interface. Together they consume ~400 ms of an 800 ms budget, which is
why they get their own tuning discipline ([§2.2](02_hld.md#endpointing--the-most-tuned-parameter)).

**Why barge-in is P0 and 150 ms.** A system that keeps talking after the caller starts speaking reads as
*not listening* — the single most frustrating failure in voice UX, and worse than a slow response. 150 ms is
roughly the threshold below which the overlap is imperceptible.

### Conversation quality

| ID | Pri | Requirement | Acceptance criterion |
|---|---|---|---|
| FR-8 | P1 | Tool calling with **filler audio** during the wait | "Let me check that" masks tool latency |
| FR-9 | P1 | Graceful degradation on low ASR confidence | **Asks for clarification; never guesses** |
| FR-10 | P1 | Per-session transcript + trace | Audit, QA, escalation handoff |
| FR-12 | P2 | Emotion/sentiment signal to adjust responses | — |
| FR-11 | P2 | Speaker diarization for multi-party calls | — |

**Filler audio is a latency *masking* technique, and it's cheap.** A tool call adding 1.5 s cannot be
optimized away when it hits a third-party billing API — but "let me pull that up" makes the wait
conversationally normal rather than dead air. **Perceived latency is the requirement; actual latency is
only a means to it.**

---

## 1.3 Non-functional requirements

### Latency — the requirement that dominates

| NFR | Target | Why this number |
|---|---|---|
| **Response latency** (caller stops → first audio) | **p95 < 800 ms**, p50 < 500 ms | Above ~800 ms callers talk over the system; above ~500 ms it feels sluggish |
| **Barge-in stop** | < 150 ms | Beyond this the system reads as ignoring the caller |
| Endpointing decision | p95 < 300 ms after speech stops | Part of the response budget; **the most-tuned parameter** |
| First TTS audio | < 250 ms after the first LLM sentence | Keeps the pipeline flowing sentence by sentence |
| Tool-call turn | Masked by filler audio | Actual latency uncapped; **perceived** latency bounded |

### Quality

| NFR | Target | Why this number |
|---|---|---|
| **ASR WER** | **< 8%** on telephony audio | Above this, downstream intent accuracy collapses — ASR errors compound through the whole pipeline |
| **Cut-off rate** | < 2% of turns | Endpointing failing *aggressively*; directly damages the interaction |
| Containment rate | ≥ 40% of calls resolved without a human | The business case |
| Escalation recall | ≥ 0.98 | Same asymmetry as [02](../02_customer_support_agent/01_requirements.md#quality) — a missed escalation is silent |

**Cut-off rate is the NFR that pairs with the latency target**, and it exists because endpointing fails in
*two* directions. Optimizing latency alone pushes endpointing aggressive, which cuts off slow speakers —
so both numbers must be monitored together or you'll trade one failure for the other without noticing.

### Capacity, availability, cost

| NFR | Target | Why |
|---|---|---|
| Concurrency | 1,000 concurrent calls | Contact-centre sizing |
| Availability | 99.95% | **Phone calls fail loudly and immediately** — no retry, no queue |
| Audio | 8 kHz telephony / 16 kHz app | Codec constraint; 8 kHz is materially harder for ASR |
| Session duration | Up to 30 min | Context/memory management driver |
| Cost | ≤ $0.08/minute | vs ~$0.60/min human agent |

---

## 1.4 Non-goals

| Out of scope | Why | What would bring it in |
|---|---|---|
| **Music / non-speech audio understanding** | Speech only | — |
| **Voice cloning of specific individuals** | Deliberate, permanent constraint — consent and impersonation risk | Never |
| On-device inference | Cloud pipeline in v1; on-device would cut network latency but constrains model size severely | Latency proves unachievable in cloud *and* a small enough model suffices |
| Languages beyond English | v1 scope; each language needs its own ASR/TTS quality bar | Volume justifies it |
| **Outbound calling** | Inbound only — outbound carries separate consent and regulatory requirements | A validated use case with legal sign-off |
| Emotional voice synthesis | Neutral, clear delivery in v1 | — |

**Voice cloning as a permanent non-goal, not a deferred feature**, is worth stating explicitly: it's the
capability most likely to be requested and the one with the clearest impersonation-harm profile.

---

## 1.5 The latency budget — the hardest in this set

SLO: p95 < 800 ms from caller-stops-speaking to first-audio-out.

### The naive pipeline

| # | Stage | Budget (p95) | Notes |
|---|---|---:|---|
| 1 | Audio in — network + jitter buffer | 60 ms | WebRTC/SIP; jitter buffer is a real cost |
| 2 | Streaming ASR finalization after endpoint | 150 ms | Partials already computed **during** speech |
| 3 | **Endpointing decision** | **250 ms** | VAD + silence threshold. **The most-tuned parameter in the system** |
| 4 | **LLM TTFT** | **250 ms** | **Requires a small model** — a frontier model's ~900 ms alone blows the budget |
| 5 | First TTS chunk | 120 ms | Streaming TTS, sentence-level |
| 6 | Audio out — network | 40 ms | |
| | **Total** | **≈ 870 ms** | vs 800 ms SLO → ⚠️ **OVER by 70 ms** |

> **⚠️ The budget does not close, and naming that is the point.** A design that presents a tidy sum under
> the SLO has either padded a stage or ignored one. The gap is real and it's the design's central problem.

### The mitigations, and what each costs

| Option | Saves | Cost / risk |
|---|---:|---|
| **Speculative endpointing** — start the LLM on a high-confidence partial *before* endpoint confirmation | **~150 ms** | Wasted LLM calls on false endpoints (~10–15%). **Cheap on a small model** — this is why the small-tier constraint turns out to be an enabler |
| **Co-locate ASR / LLM / TTS** in one region and VPC | ~40 ms | Reduced provider flexibility; harder multi-region failover |
| Cut endpointing to 180 ms | 70 ms | **More false cut-offs** — directly worsens the cut-off-rate NFR for slow speakers |
| Pre-warm / pin LLM capacity | Removes cold-start variance | Reserved-capacity cost ([04](../04_llm_inference_platform/README.md)) |
| Filler audio | Perceptual only | Feels natural used sparingly; grating if overused |

**Recommended combination: speculative endpointing + co-location.**

```
870 − 150 (speculation) − 40 (co-location) ≈ 680 ms p95    ✅ with ~120 ms of margin
```

**Why speculation is the right lever rather than tightening endpointing.** Cutting the endpointing window
trades a latency failure for a *correctness* failure — cut-off callers — and the second is worse. Speculation
buys the same time by doing work earlier, paying only in occasional wasted small-model calls. The trade is
between money and interaction quality, and money is the cheaper currency here.

### The barge-in budget — a separate, harder deadline

| Stage | Budget |
|---|---:|
| VAD detects caller speech during playback | 60 ms |
| Cancel TTS stream + flush the audio buffer | 50 ms |
| Silence reaches the caller | 40 ms |
| **Total** | **150 ms** ✅ |

**Flushing the buffer is the part that's easy to get wrong.** Cancelling TTS generation while ~2 s of
already-synthesized audio sits in the jitter buffer means the caller keeps hearing the system talk. The
buffer must be dropped, not drained — see [§3.3](03_lld.md#barge-in).

---

## 1.6 Capacity & cost estimation

### Volume

```
1,000 concurrent calls · assume 6-min average duration (assumption A2)
  ⇒ 10,000 calls/day  ·  60,000 call-minutes/day
Assume ~4 conversational turns per minute (assumption A2)
```

### Cost per call-minute

```
ASR  (streaming, assume ~$0.006/min)                                  = $0.0060
LLM  4 turns × (800 in / 100 out), small tier:
       4 × [(800/1e6 × $0.15) + (100/1e6 × $0.60)]                    = $0.00072
TTS  assume ~600 characters/min at ~$15/1M chars                      = $0.0090
                                                                        ────────
Total per minute                                                      ≈ $0.0157   ✅ vs $0.08 ceiling

Monthly: 60,000 min/day × 30 × $0.0157 ≈ $28,300/month
```

### The cost split inverts every other system in this set

| Component | Share |
|---|---:|
| **TTS** | **57%** |
| **ASR** | **38%** |
| LLM | **4.6%** |

> **ASR + TTS are ~96% of cost; the LLM is ~5%.** That's the reverse of
> [01](../01_production_rag_system/01_requirements.md#16-capacity--cost-estimation), where tokens were
> everything. **Optimization effort belongs in speech**: shorter responses (fewer TTS characters), a
> cheaper TTS voice tier, or self-hosted ASR at this steady volume — which is exactly the profile that made
> self-hosting OCR win ~100× in [05](../05_document_intelligence/01_requirements.md#ocr--where-self-hosting-wins-100).

**A concrete consequence:** instructing the LLM to be concise saves TTS characters, and TTS is 57% of cost.
**Response brevity is a cost lever here, not just a UX preference** — and it improves latency too.

### ROI

```
Human baseline:      60,000 min/day × 30 × $0.60          ≈ $1.08M/month if fully staffed
At 40% containment:  0.4 × $1.08M                         ≈ $432k/month avoided
Platform cost:                                            ≈ $28k/month
                                                            ──────────
Net                                                       ≈ $404k/month  ⇒ ~15× return
```

**Same caveat as [02](../02_customer_support_agent/01_requirements.md#token-cost):** the saving is only cash
if headcount changes or growth is absorbed without hiring. Otherwise it's *capacity*, which is a different
business case — and worth saying which one you're claiming.

### Concurrency and capacity

```
1,000 concurrent calls:
  ASR:  1,000 concurrent streams — the binding third-party capacity question
  LLM:  1,000 calls per ~15 s of conversation ≈ 65 QPS, small tier ⇒ modest,
        BUT needs WARM, PINNED capacity: a cold start blows the 250 ms TTFT
  TTS:  ~1,000 concurrent synthesis streams

⇒ The constraint is CONCURRENT STREAM limits with ASR/TTS providers,
  not aggregate throughput. Verify quotas before committing (Q3).
```

**Concurrent-stream quotas, not QPS, are the capacity question to ask providers.** A provider comfortable
with 65 QPS of LLM calls may cap concurrent ASR streams well below 1,000 — and that ceiling arrives as
dropped calls rather than degraded latency.

---

## 1.7 Assumptions & open questions

### Assumptions

| # | Assumption | Confidence | If false |
|---|---|---|---|
| **A1** | A small-tier LLM at 250 ms TTFT gives acceptable answer quality | **Low** | **If quality is insufficient, the SLO is unreachable.** Renegotiate the SLO, not the model — see [Q1](#open-questions) |
| **A2** | 6-min calls, ~4 turns/minute | Medium | Cost scales linearly |
| **A3** | Telephony audio yields WER < 8% | **Low** | 8 kHz narrowband is genuinely hard; may need a domain-adapted ASR model |
| **A4** | Speculative endpointing false-trigger rate ~10–15% | Medium | Higher rates raise cost (still small) and risk responding to an unfinished thought |
| A5 | ASR/TTS providers support 1,000 concurrent streams | Low | A hard capacity ceiling that arrives as dropped calls ([Q3](#open-questions)) |
| A6 | ~600 TTS characters/minute | Medium | TTS is 57% of cost — this is the most cost-sensitive assumption |

**A1 is the assumption that could invalidate the design.** Every other assumption changes a number; A1
changes whether the product is possible as specified. **It's testable cheaply** — run the intended prompts
against a small model and have humans rate the answers — and worth doing before building the pipeline.

### Open questions

| # | Question | Why it blocks | Owner |
|---|---|---|---|
| **Q1** | **Is the 800 ms p95 negotiable?** | If yes, a frontier model becomes viable and answer quality rises materially. If no, [A1](#assumptions) must hold. **The single highest-leverage question** | Product — resolve first |
| **Q2** | Recording/consent requirements per region? | Two-party-consent jurisdictions change the call flow (an announcement adds seconds before the conversation starts) | Legal |
| **Q3** | Do ASR/TTS providers support 1,000 concurrent streams? | A hard capacity ceiling; surfaces as dropped calls | Vendors |
| Q4 | What is the escalation taxonomy? | Same blocker as [02 Q3](../02_customer_support_agent/01_requirements.md#open-questions) — no labels, no classifier | Support leadership |
| Q5 | Is barge-in allowed to interrupt compliance disclosures? | Some disclosures must play in full; conflicts with [FR-4](#core-pipeline) | Legal / Compliance |

**Q1 restructures the whole design depending on the answer.** At 800 ms the generator must be small-tier and
speculation is mandatory. At, say, 1,200 ms a frontier model fits, speculation becomes optional, and answer
quality improves substantially. **That's a product trade — conversational immediacy versus answer quality —
and it belongs to product, not engineering.**

**Q5 is a genuine conflict worth surfacing early.** A required disclosure that must play in full is directly
incompatible with < 150 ms barge-in, and the resolution ("disclosures are non-interruptible, everything else
is") has to be a stated policy rather than an accident of implementation.

---

**Next:** [02_hld.md →](02_hld.md) — architecture, speculative endpointing, barge-in, component choices, failure modes, and the scale plan.
