# 08 · Production & Interview — Media: Content Recommendation & Ranking

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md)

---

## 4.1 AI-specific concerns

| Concern | How this design handles it |
|---|---|
| **Token cost** | **No LLM in the serving path** — 60k RPS inside 350 ms makes it neither affordable nor fast enough. Cost is GPU inference (~$73k/mo), ANN serving (~$25k/mo), feature reads (~$30k/mo), training (~$4k/mo) ⇒ **~$132k/month**. LLMs belong offline: content understanding, embedding generation, topic taxonomy maintenance |
| **The cost inversion** | Per-request cost is **~$0.0000012 — 100× inside the ceiling** while total spend is large. So the lever is **model size and fleet utilisation**, not per-request efficiency: a 20% ranker-size reduction is worth ~$15k/month, which makes distillation and quantisation roadmap items rather than optimisations |
| **Latency budget** | ~335 ms against a 350 ms SLO — **15 ms headroom, the thinnest in this collection**. The cascade exists purely because of arithmetic: the heavy ranker over 1,000 candidates would cost ~325 ms alone. Any new stage must displace an existing one |
| **Model routing & fallback** | A degradation ladder: full → light-ranker-only → cached feed → followed-source chronological. Each step is a worse product and a working one. The light ranker is therefore trained to be **usable alone**, not merely as a filter |
| **Evaluation** | **Offline metrics are computed on data this ranker generated**, so they reward reproducing its own biases. Real evaluation is: IPS-corrected offline metrics, the randomised-slot stream as ground truth, online A/B with tiered guardrails, and distribution health. Offline AUC alone is actively misleading here |
| **Hallucination / groundedness** | N/A — no generation. The analogue is **miscalibration**: a `p_report` head that has drifted is confidently wrong at scale, silently. Hence per-head calibration monitoring and head predictions stored on every impression |
| **Guardrails** | The design's centrepiece: negative heads (FR-11), versioned weights with a named owner (FR-12), satiation caps on every positive term (FR-13), pre-registered thresholds (FR-16), **auto-halt** (FR-15), a long-term holdback (FR-17), and integrity filtering *before* ranking (FR-4) |
| **Prompt injection** | N/A in the classic sense. The analogous adversary is real and continuous: **creators optimising against the ranker**. Mitigations — scores never exposed to clients, creator explanations aggregate and qualitative, exploration slots subject to a reputation floor, engagement-bait patterns handled by satiation caps rather than by whack-a-mole rules |
| **Version management** | Every impression pins `light_ranker_ver`, `heavy_ranker_ver`, `weights_ver`, `integrity_ver`, and `arm`. The weights version is the one people forget, and it is the one that decides what the product amplifies |
| **Drift** | Four kinds, on different timescales: content distribution (hours), user interest (days), **per-head calibration** (weeks), and **distribution collapse** (weeks–months, invisible to standard metrics) |
| **Feedback loops** | Treated as a primary failure mode rather than a caveat: IPS weighting, slot+propensity logging, exploration budget, randomised-slot stream, and creator-Gini/topic-entropy as **release guardrails** |
| **Label latency** | Immediate for clicks and dwell; hours for reports and "see less"; **weeks for regret surveys and 30-day retention**. This is precisely why guardrails are tiered and why only the fast tier can auto-halt |
| **PII / residency** | Behavioural data at 300M-DAU scale. User embeddings are derived and treated as personal data; deletion must propagate to embeddings, feature store, and training sets — the last is the hard one, and it is why training sets are windowed rather than cumulative |
| **Cold start** | Users: popularity + locale + declared interests with heavy diversity, personalising within ~3 interactions. Items: a guaranteed impression floor (FR-28), which is also an attack surface and therefore gated on integrity plus a creator reputation floor |

---

## 4.2 Operations & runbook

### Dashboards

| Panel | Alert |
|---|---|
| Feed p50/p95/**p99** | p95 > 340 ms · p99 > 600 ms |
| Per-stage latency (9 stages) | any stage > 1.3× budget |
| Candidate-source contribution to served impressions | any source < 1% (retire it) or a source > 70% (collapse) |
| Integrity filter removal + demotion rates | sudden change either direction |
| **Integrity decision freshness** | > 60 s (FR-27) — a *correctness* alarm |
| **Per-head calibration (ECE) — 6 heads** | any head ECE > 0.05 |
| `p_report` predicted vs observed report rate | divergence > 20% |
| **Report rate / "see less" rate / hide rate** — overall and per arm | vs pre-registered thresholds |
| **Creator Gini · top-1% impression share · topic entropy** | Gini +0.03 week-over-week |
| New-creator establishment rate | declining trend |
| New-item share of impressions | < exploration target |
| Exploration share actually served | below configured budget |
| Randomised-slot stream volume | below the level needed for unbiased eval |
| Holdback population integrity | any leak |
| Guardrail evaluator health | down ⇒ **all ramps frozen** |
| Experiments in `insufficient_data` > 48 h | (informational — usually under-allocated) |
| Realtime lane consumer lag | > 30 s |
| GPU fleet utilisation | < 55% (over-provisioned) or > 85% (no headroom) |

### On-call triage order

1. **Is the feed serving at all?** The feed *is* the product. Confirm the degradation ladder is engaged and at which rung. A cached feed is a bad day; a blank feed is an outage.
2. **Is p95 breaching?** With 15 ms of headroom, this is usually the feature store's p99 or one candidate source running long. Drop the slow source rather than waiting on it; serve stale features rather than blocking.
3. **Is the integrity filter healthy and fresh?** This is the one failure where the correct action is to **fail closed** — serve the safe subset (followed sources plus cached clearances). A single amplified violation is a reputational event; a thinner feed for ten minutes is not.
4. **Has a guardrail halted an experiment?** Working as designed. Do not override to "check whether it's real" — the evidence is in the evaluation record, and the halt costs nothing to reverse if the owner and a named approver conclude it was a false alarm.
5. **Is the guardrail evaluator down?** All ramps are frozen, which is correct. This is a high-priority fix but not a user-facing incident; resist pressure to ramp blind because a launch is scheduled.
6. **Has a head's calibration drifted?** Zero that head's weight via config until it is fixed. **The weight is the kill switch** — that is a deliberate property of putting weights in config rather than in the loss.
7. **Is creator Gini rising while offline metrics improve?** This is the feedback loop closing, and it is the slowest and most damaging failure in the system. Raise the exploration budget, check the new-item impression floor is actually being served, and look at what changed in the last few ranker versions. Nothing about this is urgent-looking, which is why it needs a standing owner rather than an on-call response.

### Rollback

| Change | Rollback | Time |
|---|---|---|
| **Objective weights** | Config push to the previous version — **no deploy, no retrain** | seconds |
| Experiment arm | Allocation to 0%; users revert on next feed load | seconds |
| Heavy ranker | Pointer flip to the previous artifact | < 1 min |
| Light ranker | Pointer flip | < 1 min |
| Integrity filter behaviour | Owned by the integrity platform; this system consumes decisions | n/a |
| ANN index | Previous index generation retained; atomic pointer swap | minutes |
| A launched change found bad by slow metrics | Full rollback, measured against the **holdback** — which is the only reason the regression was attributable at all | hours |

> Weight rollback being a config push is worth pausing on. It means the fastest possible response to "the feed is amplifying something awful" is seconds and requires no engineer to build anything. That property is the practical payoff of FR-12, and it is lost the moment weights live in the training loss.

---

## 4.3 Common mistakes

> - **Mistake:** Optimising a single engagement objective → **Why it's wrong:** the model correctly learns that outrage, cliffhangers, and extremity maximise clicks. It is not a bug, it is the objective being satisfied → **Do instead:** multi-term with explicit negative heads and versioned weights.
> - **Mistake:** Adding negative terms with small weights → **Why it's wrong:** a −1 weight on a 0.0002 base rate is arithmetic noise next to a 1.0 weight on a 0.15 engagement probability. The ranker is still single-objective, now with paperwork → **Do instead:** weights scaled to the base rates, with the rationale written down.
> - **Mistake:** Weights inside the training loss → **Why it's wrong:** changing them needs a retrain, so they change rarely, opaquely, and by whoever runs training → **Do instead:** a separate combiner stage reading versioned config with a named owner.
> - **Mistake:** Harm metrics on a dashboard beside engagement → **Why it's wrong:** engagement has an owner and a target; an advisory metric loses every argument it is in → **Do instead:** pre-registered thresholds with automatic halt.
> - **Mistake:** Treating an underpowered guardrail as a pass → **Why it's wrong:** every small experiment then passes, because a 10% regression on a 0.02% base rate is undetectable at low volume → **Do instead:** `insufficient_data` is a third verdict that blocks ramping.
> - **Mistake:** Human-in-the-loop halting → **Why it's wrong:** the halt then happens after the harm, during a debate, with a launch date in the room → **Do instead:** auto-halt with a named-approver override that leaves a record.
> - **Mistake:** Filtering integrity **after** ranking → **Why it's wrong:** leaves holes in the response and, worse, lets violating content into the training data, so the model learns the pattern and generalises it to borderline content it cannot remove → **Do instead:** filter first, and exclude removed items from training labels.
> - **Mistake:** Binary integrity decisions → **Why it's wrong:** forces the large borderline set into either full promotion or removal → **Do instead:** graded demotion multipliers.
> - **Mistake:** Training on raw impression logs → **Why it's wrong:** the model learns slot position as preference, serves it, and relearns it — the loop tightens daily → **Do instead:** slot + propensity logging, IPS weighting with clipping, and a randomised-slot stream as ground truth.
> - **Mistake:** Trusting offline AUC → **Why it's wrong:** it is computed on data this ranker generated, so a model that has collapsed the distribution scores *better* — it has become excellent at predicting its own behaviour → **Do instead:** evaluate on the randomised-slot stream and treat distribution health as a release guardrail.
> - **Mistake:** Not measuring creator concentration → **Why it's wrong:** it is the cheapest mitigation for the most damaging failure, and the only one that costs no engagement → **Do instead:** Gini and topic entropy as first-class, alerted, release-blocking metrics.
> - **Mistake:** Optimising purely for consumers → **Why it's wrong:** converges on a small set of proven creators; the supply side starves and the corpus stops renewing. The consumer objective, maximised, destroys its own input → **Do instead:** a new-item impression floor and a distribution-fairness term.
> - **Mistake:** Scoring 1,000 candidates with the heavy ranker → **Why it's wrong:** ~325 ms of a 335 ms budget → **Do instead:** cascade, with the ratio tuned against the budget.
> - **Mistake:** Exposing scores or ranking reasons to clients → **Why it's wrong:** creators optimise against exactly what you reveal; precise per-item explanations are a gaming manual → **Do instead:** aggregate, qualitative creator transparency.
> - **Mistake:** An LLM in the serving path → **Why it's wrong:** 60k RPS inside 350 ms, and ranking is a calibrated-probability problem over dense behavioural features → **Do instead:** DNN ranker; use LLMs offline for content understanding.

---

## 4.4 Interview follow-ups

**Q: Everyone says "multi-objective." What makes yours real?**
Three things, and the third is the one that usually decides it. First, the negative outcomes are **predicted heads** — the ranker outputs calibrated `P(report)` and `P(see_less)`, so it anticipates harm rather than having harm filtered off its output afterwards. Second, the weights live in **versioned config with a named owner and a mandatory written rationale**, not in a loss function, so a weight change is an auditable product decision and a rollback is a seconds-long config push. Third — and this is the one that separates a real multi-objective system from a decorated single-objective one — **the weights have to be scaled to the base rates**. Report rate is around 0.0002. A −1 weight on that is arithmetic noise next to a 1.0 weight on a 0.15 engagement probability. I'd want `w_report` around −8, so a 50× elevated report probability costs about as much as a strong engagement signal. Teams add negative terms, ship them, and change nothing measurable, because nobody checked the magnitudes.

**Q: Why does auto-halt matter so much? Can't the team just watch the dashboard?**
Because the alternative puts a human decision between the harm and the stop, and that decision happens in a room with a launch date in it. If halting requires someone to notice, believe the number, and win an argument, then the guardrail is advisory — and advisory metrics lose to metrics with owners and targets. Auto-halt inverts the default: the traffic stops, *then* the conversation happens, and reversing a halt requires a named approver and leaves a record. That inversion is the entire difference between a design that says it cares about harm and one that does. It's also why the experimentation platform is a P0 here rather than infrastructure — it's the enforcement mechanism for the primary NFR.

**Q: You can only auto-halt on fast signals. Aren't those just proxies?**
Yes, and that's a real limitation rather than something I'd paper over. Report rate and "see less" rate are detectable in minutes at this volume; regret surveys and 30-day retention are the outcomes we actually care about and they take weeks. So the guardrails are tiered: fast signals get halt authority, medium signals block full ramp, slow signals block permanent launch and are reviewed retrospectively. The mechanism that keeps the slow signals meaningful is the **long-term holdback** — a persistent population that never receives launched changes. Without it, a 30-day retention regression is unattributable because everyone has it. With it, you can still catch a bad launch six weeks later, which is slow but not blind.

**Q: What's the failure mode you'd raise unprompted?**
Feedback-loop collapse, because it's invisible to every standard metric. The training data is not a sample of user preferences — it's a sample of responses to what this ranker chose to show. So position bias gets learned as preference, never-shown items have no positive labels and are also absent from evaluation, popular items accumulate more positives and get shown more, and over weeks the creator and topic distribution narrows. The part that makes it genuinely dangerous is that **offline metrics improve while this happens**, because a model that has collapsed the distribution has become very good at predicting its own behaviour. Offline AUC up and creator Gini up together is not a paradox, it's the signature. The mitigations cost engagement — exploration budget, randomised-slot logging — except one, which is measuring concentration, and that's the one most often skipped.

**Q: Why filter integrity before ranking rather than after?**
The response-level reason is that post-filtering leaves holes in the top 20. The real reason is training data. If violating content is scored, served, and engaged with, then removed from the response only, those engagement events are still in the log — and the model learns that this kind of content performs well. It then generalises the pattern to content that is borderline but not removable, which is exactly the material the removal policy can't touch. Filtering first means the ranker never scores it, never learns from it, and never has the chance to promote it. The cost is that the filter runs over ~1,000 candidates in 25 ms, so integrity decisions have to be precomputed and served from a KV store — no synchronous model calls in that path.

**Q: The integrity store goes down. Fail open or closed?**
Closed, to a safe subset — followed sources plus items with cached clearance. That's the opposite of the fraud-detection design in [`../02_banking_fraud_detection/`](../02_banking_fraud_detection/), which fails open to rules, and the difference is what the fallback costs. There, blocking on scorer failure declines millions of legitimate cards, so fail-open is clearly right. Here, the safe subset is still a usable feed — thinner and less personalised — while the fail-open outcome is a single amplified policy violation, which is a reputational event with a long tail. The asymmetry points the other way, so the answer does too.

**Q: Your latency headroom is 15 ms. Isn't that reckless?**
It's tight and it's deliberate. The budget's structure is what buys it back: the cascade means the expensive model only sees 200 candidates, candidate sources run in parallel and are **droppable** on timeout, integrity and features are precomputed lookups rather than computation, and stale features are served rather than waited for. The consequence I'd accept explicitly is that no new stage can be added without displacing an existing one — which is a healthy constraint, because the pressure in a feed system is always to add one more signal. The likeliest breach is a feature-store p99 excursion, which is why serving stale-marked features is a first-class path rather than an error case.

**Q: Total cost is $132k/month but per-request cost is 100× inside the ceiling. What do you do with that?**
It tells me where the lever is. When per-request cost is trivially inside budget, per-request micro-optimisation is worthless — nobody is going to notice $0.0000012 becoming $0.0000009. What matters is **total fleet spend**, and that's driven by model size and utilisation. A 20% reduction in heavy-ranker size is roughly $15k/month, which makes distillation and int8 quantisation roadmap items with a dollar figure attached rather than engineering hygiene. It also means I'd watch GPU utilisation as a cost metric: below ~55% we're paying for idle capacity, above ~85% we have no headroom for a traffic spike. That inversion — trivial unit cost, large total cost — is common at consumer scale and it reliably misdirects teams who optimise the number that's already fine.

**Q: How do you handle creators optimising against the ranker?**
Partly by not telling them enough to optimise precisely: scores aren't in the response, and creator-side transparency is aggregate and qualitative ("your recent posts had a higher-than-usual 'see less' rate") rather than per-item and quantified. Precise per-item explanations are a gaming manual. But mostly by structure rather than secrecy: the satiation caps mean the classic tactics stop working arithmetically rather than by rule. Engagement-bait ("follow for part 2") is defused by weighting *retained* follows at 30 days instead of follows. Withheld-payoff content is defused by capping dwell credit. Outrage-shares are defused by signing the share term with sentiment. Whack-a-mole rules against specific tactics always lose; changing what the objective rewards doesn't.

**Q: What would you build first?**
The impression log with slot and propensity, and the distribution-health metrics — before any ranker work. They cost almost nothing, they're useless to retrofit (you cannot recover propensities for last quarter's impressions), and without them every subsequent model decision is made on data you can't trust. Then a light ranker with a *single* engagement objective, shipped honestly as such, plus integrity filter-first. Then the negative heads and the multi-term objective, which is where the design's actual value is. The experimentation platform with auto-halt has to exist before the multi-term objective ships, because the weights are the thing most in need of guarding. I would specifically not build the < 30 s realtime lane early — it's the most expensive component whose necessity is least established, and open question 3 asks exactly that.

**Q: What breaks at 100×?**
Two things change in kind. Retrieval and ranking have to merge under latency pressure: at 500B items a two-stage funnel from the full corpus isn't viable, so the architecture gains a coarse hierarchical partition — locale, language, broad topic — before any learned retrieval. That's an added stage rather than faster stages. The more interesting one is governance: one weight set cannot serve a video surface, a text surface, a search surface, and a messaging surface, and the temptation is to *learn* the weights contextually — which destroys the accountability that made FR-12 worth having. The right answer is named weight profiles per surface, each separately owned, and the real scaling problem is organisational: you now need several named owners who each understand what their profile amplifies. At 100×, what threatens this design is the governance, not the compute.

---

## 4.5 Glossary

| Term | Meaning | Why it matters here |
|---|---|---|
| **Candidate generation** | Narrowing 500M items to ~1,000 | Anything not retrieved is unreachable, however good the ranker |
| **Cascaded ranking** | Cheap model on 1,000, expensive on 200 | Pure arithmetic: the heavy ranker over 1,000 would cost ~325 ms of a 335 ms budget |
| **Multi-head ranker** | One shared trunk, several prediction heads | Cheaper than six models and keeps head correlations learned rather than assumed |
| **Objective combiner** | The stage that weights heads into one score | Separating it from training is what makes weights config, and rollback a config push |
| **Satiation cap** | Bounding credit for a positive signal | Every positive signal has a degenerate maximum; the cap is found before the model finds it |
| **Meaningful engagement** | Click + dwell + no immediate back-out | Raw clicks reward clickbait |
| **Signed share** | Share weighted by sentiment | Outrage-shares are shares *against* the content |
| **Demotion multiplier** | Graded integrity signal, 0.0–1.0 | Binary decisions force the large borderline set to either extreme |
| **Filter-first** | Integrity applied before ranking | Keeps violating content out of the *training data*, not just the response |
| **Release-blocking guardrail** | A metric that can stop a launch | The difference between caring about harm and enforcing it |
| **Auto-halt** | Automatic traffic stop on regression | Puts the stop before the debate, not after |
| **Pre-registration** | Thresholds agreed before an experiment runs | Prevents thresholds being set under launch pressure |
| **`insufficient_data`** | Underpowered evaluation | Not a pass; otherwise every small experiment passes |
| **Long-term holdback** | Users who never receive launched changes | The only way a slow-metric regression is attributable |
| **Position bias** | Slot drives clicks independent of quality | Learned as preference unless corrected |
| **Propensity / IPS** | P(item in slot \| policy), used as an inverse weight | Turns the system's own output into usable training data |
| **Randomised-slot stream** | A small fraction of requests with shuffled slots | The only bias-free evaluation set available |
| **Exploration budget** | Impressions spent on uncertain items | Buys future information; costs present engagement |
| **New-item impression floor** | Guaranteed early reach for new content | Without it, no data ⇒ never shown ⇒ never data |
| **Distribution collapse** | Creator/topic concentration over weeks | Offline metrics *improve* while it happens |
| **Creator Gini / topic entropy** | Concentration measures | The cheapest feedback-loop mitigation, and the most skipped |
| **Feedback loop** | The ranker's output becomes its training data | The reason offline evaluation is misleading by default |

---

> ← [`03_lld.md`](03_lld.md) · **Index:** [`README.md`](README.md) · **Next system:** [`../09_realestate_search_valuation/`](../09_realestate_search_valuation/)
