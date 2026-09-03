# 04 · Production & Interview — Real-Time Voice Assistant

> **Phase 4 of 4** · [← LLD](03_lld.md) · [Back to README](README.md)

---

## 4.1 AI-specific production concerns

### The concern that has no counterpart in the text systems: dead air

Every other system in this set fails *visibly*. A slow RAG query shows a spinner; a failed support-agent
turn shows an error. **On a phone call, failure is silence** — and silence is indistinguishable from a
dropped call. The caller says "hello?", waits two seconds, and hangs up.

This inverts a standard reliability instinct. Elsewhere, *degrade gracefully and stay quiet about it*. Here,
**never be quiet**. Concretely:

| Situation | Text system | Voice system |
|---|---|---|
| Backend slow | Spinner | **Filler audio** ("let me check that…") within 500 ms |
| Provider down | Error banner | **Pre-rendered clip** + transfer to human |
| Uncertain answer | Hedged text | Spoken clarifying question — never a guess |
| Over capacity | Queue with position | Hold message, **never a silent drop** ([E17](03_lld.md#36-edge-cases--correctness)) |

The pre-rendered clips are the subtle operational requirement: **they must be synthesized in advance and
cached**, because the failure they cover is the synthesizer being down.

### Endpointing drift is the thing that degrades silently

WER regressions show up in ASR metrics. **Endpointing degradation shows up as vibes** — "the bot feels
laggy this week" or "it keeps cutting me off" — because the failure is a distribution shift in *callers*,
not a change in the system.

A traffic mix that shifts toward slower speakers (an older demographic, a new region, a noisier channel)
raises cut-off rate with no code change and no alert firing. This is why
[`was_cut_off`](03_lld.md#turns--with-the-latency-breakdown-that-makes-the-budget-auditable) is a
first-class column and why cut-off rate and latency are alerted **as a pair**.

### The quality ceiling is not negotiable by tuning

The generator must be small-tier because a frontier model's TTFT alone exceeds the whole budget
([README finding 2](README.md#the-findings-that-matter)). When answer quality is judged insufficient, the
available moves are:

1. **Renegotiate the SLO** — 800 ms → 1,200 ms admits a mid-tier model.
2. **Narrow the domain** — a small model on a tight scope beats a large one on an open one.
3. **Escalate earlier** — treat the bot as a triage layer, not a resolver.
4. **Fine-tune the small model** on the domain.

**Prompt engineering is not on that list**, and pretending otherwise is how voice projects burn a quarter.
The constraint is arithmetic, not skill.

### Speculation makes cost non-deterministic per turn

A turn costs one LLM call or two, depending on whether the caller paused mid-sentence. At a 10–15%
false-trigger rate this is a ~$0.0002/turn effect — negligible *because* the model is small-tier. **The
constraint that created the latency problem is the same constraint that makes the fix affordable**, and that
coupling is worth stating out loud: on a mid-tier model, speculation would be both necessary and too
expensive to use freely.

### Consent and recording are a per-region correctness property

Two-party-consent jurisdictions require disclosure before recording, and the disclosure itself must be
non-interruptible ([E9](03_lld.md#36-edge-cases--correctness)). `consent_state` gates whether audio is
retained at all — not whether it is later filtered. **A recording made without consent cannot be fixed by
deleting it afterwards**, so the gate is at capture.

---

## 4.2 Runbook

### Dashboards

**Latency, per stage — not aggregate.** With ~120 ms of margin across six stages, an aggregate p95 tells you
there's a problem and nothing about where.

```
lat_asr_final_ms      p50 / p95 / p99
lat_endpoint_ms       p50 / p95 / p99      ← plus the distribution, not just percentiles
lat_llm_ttft_ms       p50 / p95 / p99
lat_tts_first_ms      p50 / p95 / p99
lat_total_ms          p50 / p95 / p99      ← the SLO
```

**The endpointing pair, always on one panel:**

```
cut_off_rate          = turns with was_cut_off / total turns          target < 2%
speculation_waste     = speculation_wasted / speculated               expect 10–15%
median silence_threshold_ms across active sessions                    expect ~250
```

**Conversation health:**

```
barge_in_rate            (rising ⇒ responses too long or wrong)
barge_in_ms p95          (< 150 ms)
turns_per_session        (rising ⇒ misunderstanding loops)
containment_rate
caller_hangup_before_resolution   ← the honest failure metric
dead_air_events          (> 1.5s with no audio in either direction)
```

**Cost:**

```
$/min split by ASR / TTS / LLM      expect ~38% / ~57% / ~5%
tts_chars per session               ← the top cost lever, so watch it directly
```

### Alerts

| Alert | Threshold | First action |
|---|---|---|
| **p95 total latency** | > 800 ms for 5 min | Read the **per-stage** panel; find the stage that moved |
| **Cut-off rate** | > 4% for 15 min | Check speaker-rate distribution; raise `MIN_ENDPOINT_MS` |
| **Dead air events** | > 0.5% of turns | Check tool latency and TTS health — this is the worst UX failure |
| **Barge-in p95** | > 200 ms | Verify the playback buffer is being **flushed**, not drained |
| **Self-interruption** | barge-in with no caller speech | AEC floor calibration ([F4](02_hld.md#25-failure-modes--blast-radius)) |
| **TTS error rate** | > 1% | Confirm fallback voice is live and cached clips are present |
| **WER** | > 10% on the canary set | Segment by codec and region before touching the model |
| **Concurrency** | > 85% of quota | Scale gateway/ASR capacity; verify overflow-to-human works |
| **Speculation waste** | > 30% | Trigger is firing too eagerly — raise `SPEC_CONFIDENCE_MIN` |

**"p95 latency breached" is deliberately not a paging alert on its own** if it's within ~10% and cut-off rate
is healthy. The pair matters: a latency alert with a *falling* cut-off rate usually means the adaptive
threshold correctly backed off for slower callers, which is the system working as designed.

### Incident playbooks

**"Callers say it cuts them off."**

1. Query cut-off rate over 7 days, segmented by region and codec.
2. Check the `silence_threshold_ms` distribution across sessions — is adaptation happening at all?
3. If the shift is one cohort, look for a traffic-mix change before a code change.
4. Immediate mitigation: raise `MIN_ENDPOINT_MS` 180 → 250. Costs ~70 ms of p95, buys correctness.
5. Only then investigate VAD sensitivity and the semantic-completeness check.

**"It keeps talking over me when I interrupt."**

1. Check `barge_in_ms` p95. If it's fine, the cancel path works and **the buffer isn't being flushed**.
2. Verify `flush_buffer: true` is set and honoured at the gateway
   ([§3.2](03_lld.md#32-api-contracts)).
3. Check gateway jitter-buffer depth — a deep buffer holds seconds of audio the flush must discard.

**"It interrupts itself mid-sentence."**

This is [F4](02_hld.md#25-failure-modes--blast-radius): AEC residual reading as caller speech. Recalibrate
`aec_floor_db` per codec and raise `BARGE_IN_ENERGY_MARGIN`. Expect it on speakerphone and narrowband
first.

**"Latency spiked but no single stage looks bad."**

Check whether **speculation hit-rate collapsed**. When speculation stops firing, the ~150 ms it contributes
disappears and every stage looks normal while the total breaches. The usual cause is an ASR change that
lowered partial-hypothesis confidence below `SPEC_CONFIDENCE_MIN`.

> This is the cost of the mitigation that closes the budget: **~18% of the latency headroom lives in a
> heuristic**, so that heuristic needs its own alert.

**"Provider outage."**

1. Fail over to the secondary (ASR or TTS).
2. If both are down: cached clips + transfer. Verify the human queue can absorb the volume — 1,000
   concurrent calls will not fit into a normal agent pool, so this is a capacity conversation held *before*
   the incident.

---

## 4.3 Common mistakes

| # | Mistake | Why it's wrong | What to do instead |
|---|---|---|---|
| 1 | **Presenting a latency budget that sums under the SLO** | Requires padding a stage or omitting one — usually audio transport or endpointing | State the ~870 ms and then close the gap explicitly ([§1.5](01_requirements.md#15-the-latency-budget--the-hardest-in-this-set)) |
| 2 | **Choosing a frontier model for quality** | Its TTFT alone exceeds the budget. This isn't a cost trade-off — it's impossible | Small-tier is forced. Renegotiate the SLO if quality is insufficient |
| 3 | **Treating barge-in as "stop TTS"** | Generation stops; buffered audio keeps playing | **Flush** the playback buffer ([F3](02_hld.md#25-failure-modes--blast-radius)) |
| 4 | **Non-streaming ASR or TTS** | Full-utterance ASR adds seconds; full-response TTS waits for the last token | Streaming end to end, sentence-chunked into TTS |
| 5 | **Fixed endpointing threshold** | No value is correct for all speakers | Per-session adaptation, asymmetric ([§3.3](03_lld.md#per-speaker-threshold-adaptation)) |
| 6 | **Optimizing LLM cost** | The LLM is ~5% of spend; TTS is ~57% | Optimize characters synthesized and ASR minutes |
| 7 | **Ignoring the caller's own audio in VAD** | AEC residual triggers self-interruption | Energy margin above the AEC floor |
| 8 | **No filler audio during tool calls** | Silence reads as a dropped call | Filler within 500 ms, second clip, then escalate |
| 9 | **Cross-region provider calls** | Two round trips at ~40 ms each is a third of the remaining margin | Co-locate ASR, LLM, TTS ([§2.2](02_hld.md#22-component-choices)) |
| 10 | **Speculating and playing immediately** | Talks over a caller who wasn't finished | Playback gated on confirmation ([E5](03_lld.md#36-edge-cases--correctness)) |
| 11 | **Recording before disclosure** | Unlawful in two-party-consent regions, and undeletable after the fact | Gate capture on `consent_state` |
| 12 | **Long, complete answers** | Correct text is bad speech — 40 spoken words is ~15 s | Short turns; offer detail on request. Rising barge-in rate is the signal |

**Mistake 12 is the one candidates almost never mention.** Voice inverts a writing instinct: thoroughness
is a virtue in text and a defect in speech, because the listener can't skim. A rising barge-in rate is
usually the system being *verbose*, not *wrong*.

---

## 4.4 Interview follow-ups

**"Your budget doesn't close. Why present it that way?"**
> Because the alternative is hiding it. Six stages sum to ~870 ms against 800 ms, and any tidy sum under the
> SLO has padded or dropped a stage. Naming the gap makes speculative endpointing an argued decision rather
> than a detail: −150 ms from speculation, −40 ms from co-location, landing near 680 ms with ~120 ms of
> margin.

**"Why not just use a bigger model and accept 1.5 s?"**
> That's a legitimate product decision, not an engineering one — and it should be made explicitly. Above
> ~800 ms callers start talking over the system, so the failure isn't "slower", it's a different and worse
> interaction. If the domain needs frontier-quality answers, I'd rather move the SLO deliberately than
> discover the threshold in production.

**"How do you tune endpointing?"**
> You don't find a value; you find a *policy*. Start at 250 ms, adapt per session, and adapt asymmetrically —
> back off ×1.4 on a detected cut-off, tighten ×0.95 for fast speakers. Cutting someone off is a correctness
> failure; 40 ms of extra latency is a mild cost. Both directions get monitored on the same panel, because
> optimizing either alone just moves the failure.

**"What if speculation is wrong?"**
> It costs a cancelled small-tier call, about $0.0002, at a 10–15% rate. The important part is what it
> *doesn't* cost: playback is gated on confirmation, so a wrong speculation never produces audio. The worst
> case is wasted compute, not a caller talked over.

**"How do you handle a caller interrupting mid-sentence?"**
> Three steps, and the second is the one people miss: cancel generation, **flush** the playback buffer, and
> discard the in-flight response. Draining the buffer means the caller keeps hearing us for seconds. And the
> response is abandoned rather than resumed — they interrupted because the answer was wrong or incomplete.

**"Where does the money go?"**
> ASR ~38%, TTS ~57%, LLM ~5%. It's the inverse of every other system here, and it means the optimization
> targets are characters synthesized and audio minutes transcribed. Shorter responses are simultaneously
> cheaper *and* better voice UX, which is a rare alignment.

**"Would you self-host ASR?"**
> At 1,000 concurrent calls, yes — and the reasoning mirrors [05](../05_document_intelligence/README.md)
> rather than [04](../04_llm_inference_platform/README.md). ASR is a small, fixed-shape model with
> near-constant GPU utilization at this volume, so the economics favour self-hosting, unlike LLM serving
> where KV-cache-bound concurrency made self-hosting ~10× worse.

**"How do you evaluate this?"**
> Three layers. Component: WER on held-out telephony audio, MOS on TTS. Turn: was the intent understood,
> was the answer correct. Conversation: containment, hangup-before-resolution, turns-to-resolution. The
> conversation layer is the one that matters and the hardest to automate — it needs the offline replay
> harness from [07](../07_llm_evaluation_platform/README.md) plus human review of sampled calls.

**"What breaks first at 10× scale?"**
> Not the LLM — the media gateway and ASR concurrency. 10,000 concurrent RTP sessions is a networking and
> capacity problem, and it's also where the escalation path breaks: an overflow-to-human design that assumed
> 1,000 calls has nowhere to put 10,000.

**"What would you cut to ship in six weeks?"**
> Diarization, emotion detection, multilingual, and voice cloning — all already non-goals. What I would
> *not* cut is barge-in or filler audio. Both look like polish and are actually the difference between a
> usable assistant and one callers hang up on.

---

## 4.5 Glossary

| Term | Meaning |
|---|---|
| **AEC** | Acoustic echo cancellation — removes the system's own output from the inbound mic signal. Its residual is what causes self-interruption |
| **Barge-in** | The caller interrupting the system mid-response; must silence output in < 150 ms |
| **Endpointing** | Deciding the caller has finished speaking. The most-tuned parameter here, failing in both directions |
| **Filler audio** | A short spoken acknowledgement covering backend latency, preventing dead air |
| **Jitter buffer** | Gateway buffer smoothing network variance; its depth is what a barge-in flush must discard |
| **MOS** | Mean opinion score — subjective speech-quality rating, 1–5 |
| **Speculative endpointing** | Starting LLM generation on a high-confidence partial transcript before end-of-turn is confirmed. Playback stays gated on confirmation |
| **TTFT** | Time to first token — the LLM's contribution to perceived latency |
| **Turn** | One caller utterance plus one system response |
| **VAD** | Voice activity detection — speech vs silence, upstream of endpointing |
| **WER** | Word error rate. Telephony audio at 8 kHz is materially worse than 16 kHz |

---

## Where this sits in the set

| | |
|---|---|
| **Hardest constraint** | Latency — 800 ms across six stages, tighter than anything else here |
| **Cost profile** | Inverted: speech ~96%, LLM ~5% |
| **Closest sibling** | [02 — Support agent](../02_customer_support_agent/README.md), same task with 2.5× the budget |
| **Shared lesson** | [05 — Document intelligence](../05_document_intelligence/README.md): self-hosting pays for small fixed-shape models, not for LLM serving |

**Next:** [09 — Multi-provider LLM platform →](../09_multi_provider_llm_platform/README.md)

[← Back to README](README.md) · [← LLD](03_lld.md) · [All systems](../README.md)
