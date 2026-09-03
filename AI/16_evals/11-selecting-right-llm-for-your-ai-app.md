# Lesson 11 — Selecting the Right LLM for Your AI App: Running Custom Model Evals

> **Source:** CampusX · *Selecting the Right LLM for Your AI App: Running Custom Model Evals* · [watch](https://www.youtube.com/watch?v=RG5A-W3eMHI&list=PLEneLIDJFpcA&index=12)
> **One-liner:** A live, hands-on walkthrough of picking the backend LLM for a real feature (ESPN Cricinfo's "Ask Cricinfo" text-to-SQL bot) — gather requirements → shortlist from a leaderboard → run a custom eval on 5 finalists → watch the actual scores decide the winner.

---

## 🎯 TL;DR

This is the first fully hands-on class in the playlist. The case study: you're an AI engineer at ESPN Cricinfo, tasked with building a **text-to-SQL** feature ("Ask Cricinfo") that lets cricket fans ask natural-language questions and get answers straight from the match database. The whole class is about answering one question properly — *which LLM should power this?* — via a 3-stage process: **(1) gather requirements** (cost ceiling, latency, context, correctness bar), **(2) shortlist 5–10 candidates from a leaderboard**, **(3) run a custom eval on real data** and let the numbers pick the winner. Live results on 5 real models: Grok 4.5 and Claude Sonnet 5 finish as co-leaders (90% and 85%), GPT-5.6 Terra costs the most for 80%, and — the lesson's best moment — the hyped Kimi K3 (a 1-trillion-parameter frontier open-weight model that shook up the industry days earlier) turns out slow and only ~50–55% accurate on this specific task.

---

## 1. The problem statement: Ask Cricinfo

ESPN Cricinfo runs live match commentary and used to have human analysts answer fan questions ("What's Kohli's average against Pakistan?") by manually querying their database — a process that couldn't scale during high-traffic matches (India vs. Pakistan can spike to thousands of questions a minute). Their fix: a feature called **Ask Cricinfo** where a fan types a question in plain English, an LLM converts it to SQL against the match database, the SQL runs, and the result comes back — no human analyst in the loop.

This is explicitly **not a RAG system** — there are no external documents to retrieve. The model is given the database schema once (in the system prompt) and generates SQL from the question and that schema every time.

> The class frames this as a real assignment: *"You are an AI engineer at Cricinfo. You've been asked to build this feature. Before you write a line of code, which LLM do you use — and how do you justify that choice to your team?"*

---

## 2. Stage 1 — Gather requirements

Before touching a leaderboard, the class works out concrete numbers for every constraint that matters.

### Cost ceiling — worked from first principles

The team lands on a budget with the class (₹3–5 lakh/month), then reverse-engineers what "cost" actually means for this app:

| Quantity | Value used |
|---|---|
| Input tokens per query (system prompt + schema + question) | ~400 |
| Output tokens per query (just a SQL string) | ~100 |
| Estimated queries/day | 5,000 |
| Days/month | 30 |
| USD→INR | 95 |

Worked example for **Claude Opus 5** ("Fable 5" in the recording) at $10/$50 per million input/output tokens:

```text
cost per query  = (400/1e6)*10 + (100/1e6)*50 = $0.0090
monthly cost     = 0.0090 * 5000 * 30 * 95 ≈ ₹12.8 lakh
```

Against a ₹3 lakh ceiling, that's **~4x over budget** — Opus 5 is eliminated on cost alone before a single quality question is asked. The lesson: *"You cannot pick a model just because it's the best on a leaderboard. You have to first check whether it's even affordable for your traffic."*

### Prompt caching changes the math

The class digs into a detail visible on a real pricing page: **5-minute cache** and **1-hour cache** read/write rates. The mechanism: the system prompt + schema is byte-identical across nearly all 5,000 daily queries — only the question changes. Providers let you cache that stable prefix:

- First query in a cache window: pay a **cache-write** rate (~1.25× normal input price).
- Every subsequent query within the window: pay a **cache-read** rate (~1/10th normal input price) instead of full input price.
- The cache expires and refreshes on a fixed cycle (5 min or 1 hr, provider-dependent).

For a high-traffic app like Ask Cricinfo, a 5-minute cache is almost always warm (a new question arrives before the window closes), so nearly every query after the first pays the cheap cache-read rate. In the worked numbers this took the naive ₹12.8 lakh/month estimate down toward **~₹6–7 lakh** — real, but still not enough to save Opus 5 in this case. The caveat: **this optimization doesn't help a RAG chatbot**, because the retrieved context changes on every query — there's no stable prefix to cache.

### The other requirement dimensions

| Dimension | Answer for this app | Why |
|---|---|---|
| **Latency** | ≤ 2–3 seconds | Users are asking live, mid-match — anything slower triggers "did my request even go through?" anxiety |
| **Context window** | Doesn't matter much | Each question is a single, disjoint turn — no multi-turn conversation, no large document to fit |
| **Deployment** | Public API is fine, even preferred | No privacy/data-residency constraint; a public API's infra/reliability beats a self-hosted setup for a team this size |
| **Correctness** | Matters *a lot* | Cricket fans are "super finicky about records" — a wrong stat gets screenshotted and posted publicly, which is reputational risk for Cricinfo |

---

## 3. Stage 2 — Shortlist from a leaderboard

**Text-to-SQL-specific leaderboards were rejected.** The class checked BIRD-SQL and Spider, and rejected both: they're stale (missing current-generation models, some already fine-tuned specifically for those benchmarks — not representative of an off-the-shelf model you'd actually call) and one is scored via an opaque third-party "agent harness" rather than a plain model.

**Fallback: use a coding leaderboard as a proxy.** SQL generation is treated as a coding-adjacent capability, so the class uses **llm-stats.com**, an aggregator that blends multiple coding benchmarks and — critically — was fully up to date with current-generation models (GPT-5.6, Fable 5/Opus, Kimi K3, Grok 4.5, GLM, Qwen, Minimax) and included per-model cost and speed.

**A gotcha in the leaderboard's pricing column:** the leaderboard shows one blended price per model, not separate input/output prices. It's computed as a **4:1 blended rate**: `(4×input + 1×output) / 5`. The class's own app happens to have almost exactly a 4:1 input:output token ratio (400:100) — so that blended number is directly usable for this app's cost estimate without extra math, which the instructor calls a lucky coincidence worth knowing how to spot.

**Shortlisting formula.** After hard-filtering out anything over the (₹5 lakh, in the actual pre-class run) budget, remaining models were ranked by:

```text
score = 0.9 * normalized(coding_rating) + 0.1 * normalized(speed)
```

Both `coding_rating` and `speed` (characters/second) were min-max normalized to [0, 1] first. **Why 90/10, not 50/50?** Because the output here is just a short SQL string (~100 tokens) — even a "slow" model finishes printing it in a couple of seconds. Speed would matter far more if the output were a long generated document.

This produced a top-10 list spanning frontier paid models (GPT-5.6 Terra, Claude Fable/Opus) down to cheap open-weight Chinese models (Minimax M3, GLM, Qwen) that scored surprisingly close on the blended metric despite costing a fraction as much.

**Final 5 picked for the live demo** (one slot per "family," to keep the demo diverse and affordable):

| Model | Why picked |
|---|---|
| **GPT-5.6 Terra** | Top-ranked, expensive — the benchmark to beat |
| **Kimi K3** | 1T-parameter open-weight model from Moonshot AI, huge recent hype/controversy for undercutting frontier pricing |
| **Claude Sonnet 5** | The Anthropic representative (chosen over Opus on cost) |
| **Grok 4.5** | xAI's entry — "never underestimate this one," per the instructor |
| **Minimax M3** | Representative of the cheap Chinese open-weight tier |

---

## 4. Stage 3 — The custom eval

### Project setup

- **Data**: real IPL ball-by-ball data from Kaggle (2008–2024), trimmed to **2020–2024** to keep the live demo fast — loaded into a local **SQLite** database via a `db.py` script. Two tables: `matches` (one row per match) and `deliveries` (one row per ball).
- **Schema extraction**: a `schema_extractor.py` script introspects the live database and writes the table/column/type definitions to `schema.sql` — this text gets pasted into the system prompt every call, since the model can't generate correct SQL without knowing the schema shape.
- **Golden dataset**: `golden_dataset_generator.py` holds 20 hand-picked *hard* questions (joins, aggregations, filters — e.g. *"the bowler with the best economy rate among bowlers who've bowled at least 500 legal balls"*), each paired with a correct SQL query written by a human ("data analyst" role) and a flag for whether row order matters (`ORDER BY` present). Running this script executes every golden query against the database first, purely to catch SQL syntax errors in the golden set itself (20/20 passed) — it does **not** check whether the *answers* are semantically correct yet, just that the queries are valid. `make_golden_dataset.py` then exports the validated set to `golden_hard.csv`.
- **Multi-provider access via OpenRouter**: rather than writing separate integration code for OpenAI, Anthropic, Grok, and two Chinese providers, the whole eval runs through **OpenRouter**, which exposes every model behind one unified API (and works natively with LangChain). A `model_openrouter_slug.py` file maps each of the 5 chosen models to its exact OpenRouter model slug.
- **Flow smoke test**: `test.py` runs one throwaway question through GPT-4o-mini (not a candidate model — just a flow check) to confirm prompt → API → SQL round-trip works before spending money on the real candidates.

### The evaluator: comparing result tables, not query text

The core design decision, explained at length: **you cannot compare generated SQL to golden SQL as strings.** Two syntactically different queries can return identical result tables (there are many correct ways to write the same query), so string/AST comparison produces false negatives. The only reliable check is: **run both queries against the database and compare the actual result tables.**

`evaluator.py` implements that comparison with three steps:
1. **Row count check** — different row counts means the tables can't match; fail immediately.
2. **Value normalization** — `2` and `2.0` are treated as equal; `2999` and `2999.00`-style formatting differences are normalized away, so a correct query isn't marked wrong purely because of type/format drift.
3. **Order-aware or order-agnostic comparison** — if the golden query's flag says row order matters (i.e. it has an `ORDER BY`), compare the two tables row-by-row as-is; otherwise **sort both tables** before comparing, since two correct queries without an explicit order clause can legitimately return rows in a different sequence.

`main.py` orchestrates the whole run: load schema → load golden dataset → connect to the database → for each of the 5 models, loop over all 20 golden questions, generate SQL, execute it, execute the golden SQL, evaluate the pair, and log a match/mismatch per question — producing a final accuracy percentage per model.

### Live results

| Model | Accuracy (20 Qs) | Notable behavior |
|---|:---:|---|
| **Grok 4.5** | **90%** | Fastest of the strong performers, zero SQL syntax errors, handled the "brutal" questions well |
| **Claude Sonnet 5** | **85%** | Very fast, one of the fastest overall, reliable |
| **GPT-5.6 Terra** | 80% | Correct but most expensive of the finalists |
| **Minimax M3** | ~65% | Cheap open-weight model, 3+ SQL syntax errors — "made up its own syntax where it wasn't sure" |
| **Kimi K3** | ~50–55% | Slow (likely reasoning-model overhead) and multiple SQL syntax errors, despite huge pre-release hype |

> **The lesson's central takeaway:** *"A model being exciting on the leaderboard/in the news doesn't guarantee it'll do well on your specific task."* Kimi K3's underperformance here — a genuinely frontier-scale model that was making headlines that same week — is presented as living proof that leaderboard buzz and custom-eval results can diverge sharply.

### Final decision: Grok 4.5 vs. Claude Sonnet 5

With GPT-5.6 Terra eliminated on cost/accuracy tradeoff and the two Chinese models eliminated on accuracy, the real decision comes down to two models with similar cost (~₹2.5–2.8 lakh/month) and similar speed. The instructor's own lean: **Claude Sonnet 5**, for a soft but real reason — perceived API reliability/stability of the provider — while explicitly noting this last mile is a judgment call the team makes together (down to a literal vote), not something the eval numbers alone decide.

---

## 5. Key terms

| Term | Meaning |
|---|---|
| **Text-to-SQL application** | An app where an LLM converts a natural-language question into a SQL query executed against a fixed, known database schema — distinct from RAG, since there's no external document retrieval. |
| **Cost ceiling** | The maximum monthly spend a business stakeholder authorizes for a feature; computed from tokens/query × price × expected query volume. |
| **Prompt/KV caching** | Paying a premium to cache a stable prompt prefix once, then a steep discount to reuse it on every subsequent call sharing that prefix — doesn't help when the prompt's content changes every call (e.g. RAG context). |
| **Blended pricing** | A single per-token price a leaderboard computes from a fixed input:output ratio (e.g. 4:1), useful only if it matches your app's actual token ratio. |
| **Golden dataset (for text-to-SQL)** | Hand-verified (question, correct-SQL, order-sensitivity flag) triples used as ground truth; validated by actually running the SQL, not just eyeballing it. |
| **Execution-based evaluation** | Scoring generated SQL by running it and comparing the resulting tables (row count → normalized values → sorted/unsorted comparison), never by comparing query text. |

---

## ✍️ Notes / follow-ups
- Model Evals are now complete as a topic (benchmarks + custom model evals). Next: the playlist pivots fully to **Application Evals** → [Lesson 12 — How to Answer "How Do You Evaluate Your RAG App?" in GenAI Interviews](12-how-to-answer-evaluate-rag-app-interview.md).
- Key habit demonstrated live: **run the eval before trusting the leaderboard's hype** — Kimi K3's real-world underperformance on this task is the single clearest moment of the whole class.
