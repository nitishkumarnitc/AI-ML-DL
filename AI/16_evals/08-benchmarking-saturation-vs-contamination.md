# Lesson 8 — What is LLM Benchmarking: Saturation vs Contamination

> **Source:** CampusX · *Whats is LLM Benchmarking | Benchmark Saturation vs. Contamination* · 51:20 · [watch](https://www.youtube.com/watch?v=qIiU3lyjrhM&list=PLEneLIDJFpcA&index=8)
> **One-liner:** A benchmark, formally, is exactly four components (dataset, run configuration, scoring, aggregation) — demonstrated live on GSM8K, then run for real with 20 GPT-5.6 queries through the EleutherAI LM Evaluation Harness. Then: who actually runs these evaluations (3 distinct stakeholders, each with different trust levels), and four concrete reasons — not three — you cannot take a published benchmark number at face value: contamination, saturation, configuration gaming, and aggregation gaming.

---

## 🎯 TL;DR

**Definition given:** *"A benchmark is a standardized test used to measure a particular model capability."* Every benchmark, without exception, is built from four components: a **dataset** (questions + answers), a **run configuration** (the exact prompting/decoding/scoring/tool-use conditions every model must be tested under identically), a **scoring method** (how one answer is judged right or wrong), and an **aggregation method** (how thousands of individual scores become one published number). GSM8K (Grade School Math, ~8K rows) is used as the running example, including a live demo running it for real via the **EleutherAI LM Evaluation Harness** against GPT-5.6. Three groups actually run these evaluations — frontier labs, independent third-party evaluators, and AI engineering teams themselves — with very different trustworthiness. And critically: **four**, not three, distinct problems mean a published benchmark score should never be taken at face value — contamination, saturation, configuration gaming, and a less-discussed fourth one, aggregation gaming.

---

## 1. The four components of any benchmark, via GSM8K

**GSM8K** ("Grade School Math 8K") is introduced as an old (2020-2021), now largely retired benchmark — chosen deliberately as a simple teaching example rather than a currently-relevant one.

### Component 1 — Dataset and task
A benchmark's dataset always contains **both questions and answers** — functionally a golden dataset. GSM8K's ~8,500 rows are real grade-school arithmetic word problems (the lecture's own example: *"Natalia sold clips to 48 friends in April and half as many in May — how many did she sell in total?"* → 48 + 24 = **72**), publicly available on Hugging Face and Kaggle. The **task** is simply: given the word problem, produce the correct numeric answer.

### Component 2 — Run configuration
The critical point made about run configuration: whatever settings are chosen, **every model being compared must be tested under identical settings** — otherwise the comparison is meaningless. Three sub-parts:

1. **Prompt construction** — zero-shot (no worked examples shown first) vs. few-shot (worked examples shown before the real question). GSM8K is "classically reported at 8-shot" — 8 solved examples are shown in-context before the actual question. Also decided here: whether **chain-of-thought** is allowed (the model is told to reason step by step, as in the sample answer's own worked steps) versus being asked to answer directly — direct answering carries a higher error rate.
2. **Decoding/sampling configuration** — temperature is nearly always locked near zero for benchmarking (to suppress creative variance run-to-run), and a max-token budget is fixed in advance — too low truncates a chain-of-thought answer mid-reasoning; too high lets a stronger model "reason longer," which isn't a fair comparison either.
3. **Scoring strategy and tool access** — see below; and whether external tools (web search, a code interpreter) are permitted. GSM8K disallows tools; **SWE-bench**, by contrast, requires tool access (fetching real GitHub issues) since the task is inherently tool-dependent.

### Component 3 — Scoring method
Two steps: **extraction** (pull the actual answer out of however the model phrased its response — "the answer is 72," or just "72" — via structured output or regex) and **comparison**:

| Scoring strategy | Definition |
|---|---|
| **Pass@1** | Strict — the single attempt must be correct |
| **Pass@k** | Lenient — correct if *any* of k independent attempts is correct |
| **Majority@k** (self-consistency) | Ask the same question k times, take the most frequent (mode) answer as the final answer |

For a closed-form numeric answer like GSM8K's, comparison is a straightforward programmatic equality check (`72 == 72`). For benchmarks with open-ended paragraph answers, comparison instead requires an **LLM-as-judge** (or, in principle, a human).

### Component 4 — Aggregation method
Usually a simple mean across all rows (e.g. 920/1000 correct → 92%). But not always simple: **MMLU** spans 57 subjects with an uneven number of questions per subject, so a naive average-of-percentages can misrepresent the true aggregate — a **weighted mean** (weighted by question count per subject) may be required instead, and different benchmarks make different aggregation choices.

**Where all four components are actually documented:** the original research paper that introduces the benchmark. GSM8K, MMLU, SWE-bench, etc. were all first published as academic papers specifying exactly these four components — which is why reproducing "the GSM8K score" correctly requires matching the paper's stated configuration, not guessing at reasonable defaults.

---

## 2. Running a benchmark evaluation, step by step — and the eval harness

**The core loop, in pseudocode form, as described directly:** for each item in the dataset — build the prompt (inject few-shot examples, apply the chat template, add instructions) → call the model with the configured decoding settings → capture the raw output and extract the answer → score it true/false → append to a results list. Once the loop finishes, aggregate the list into a final score.

**Why this "simple loop" is deceptively hard to actually implement well:** running it reliably at the scale of thousands of LLM calls requires handling batching strategy, retry logic for failed API calls, rate-limit handling, and benchmark-specific extraction/scoring code — none of which is exotic, but all of which is real engineering overhead most people shouldn't reinvent per-benchmark.

**This is exactly what an eval harness exists to abstract away.** Definition given directly: *"An eval harness is a piece of code you write (or more commonly, use) to execute model evaluation — think of the benchmark as the exam paper, and the eval harness as the entire exam-conducting administration that handles everything else."* The named library is **EleutherAI's LM Evaluation Harness** — described as the industry-standard tool, used even by large labs, versus DeepEval's own benchmark support (real, but requiring far more manual code to point at an arbitrary model, and mostly focused on already-saturated benchmarks).

### The live demo, with real numbers

```bash
# actual command run live, evaluating GPT-5.6 against GSM8K
lm_eval --model openai-completions \
  --model_args model=gpt-5.6,num_concurrent=5,max_retries=... \
  --tasks gsm8k_cot \
  --num_fewshot 8 \
  --apply_chat_template \
  --limit 20 \
  --output_path ./results \
  --log_samples
```

Key flags explained live: `--tasks gsm8k_cot` selects GSM8K with chain-of-thought enabled; `--num_fewshot 8` matches GSM8K's canonical 8-shot configuration; `--limit 20` restricts the run to only 20 of the ~8,000 questions — explicitly **for cost reasons**: a full 8,000-question GSM8K run was estimated at roughly ₹2,300, versus ₹3–4 for a 20-question smoke test. **Result: GPT-5.6 answered 18 of 20 correctly (~90%)**, with a per-question JSON log written to disk (question, model answer, correctness) — demonstrating that a real benchmark run, end-to-end, took one command and zero hand-written loop code.

---

## 3. Who actually runs these evaluations — three stakeholders, three trust levels

| Stakeholder | Why they benchmark | Trust level for *you* as an AI engineer |
|---|---|---|
| **Frontier labs** (OpenAI, Anthropic, Google DeepMind) | Guides training direction mid-run (checkpoints tested against benchmarks during pre-training to catch bad trajectories early), informs release go/no-go decisions, and doubles as marketing (a benchmark-topping result drives press/YouTube coverage) | **Lowest** — treat published numbers as a ceiling, not a guarantee |
| **Independent third-party evaluators** (e.g. LM Arena-style leaderboards) | Evaluation itself is their product/business — they test every model under identical, disclosed conditions | **Highest** of the three — bonus: they often also publish real-world cost and latency, which labs frequently omit |
| **AI engineering teams / you** | Don't fully trust either of the above — run public benchmarks yourselves, using tools like the LM Evaluation Harness, under your own conditions, including latency and cost | Your own numbers, by construction — but still only as good as your own methodology |

**The car-mileage analogy used directly:** *"A car advertised at 25 km/l might give you 5–10 in real driving — lab numbers are a ceiling, achieved under the most favorable conditions the lab could construct, not a promise."* The instructor adds a first-person example: a heavily-hyped recent model ("Fable") did not match its hype in his own usage, despite intense pre-release buzz — a live illustration of exactly this gap between marketing-driven lab numbers and real-world performance.

---

## 4. Four reasons not to trust a benchmark number at face value

### 1. Contamination
Most well-known benchmarks (MMLU, GSM8K, etc.) are **public** — their full dataset, questions and answers included, has been sitting on the open internet for years. When a frontier lab scrapes recent internet data for pre-training, there's a real chance the benchmark's own question-answer pairs got scraped in along with everything else. If so, a model's strong score may reflect **memorization**, not genuine reasoning capability — there's no way to tell from the score alone whether the model reasoned its way to 72 or simply recalled having seen that exact question-answer pair during training. **Mitigations named:** private benchmarks (never publicly released) and dynamic benchmarks (datasets that refresh on a rolling window, so no fixed set of Q&A pairs can ever be fully absorbed into any one training run).

### 2. Saturation
A benchmark's natural life cycle, described directly: it launches hard (models score 25–36%, nobody has "seen" it before), models improve release over release (36% → 50% → 70%), and eventually most frontier models cluster near the ceiling (94–97%, with negligible gaps between competitors). At that point the benchmark **can no longer discriminate between models** — everyone scoring roughly the same tells you nothing about which model is actually better. The lecture names GSM8K, MMLU, and SWE-bench (original version) as concrete examples that have already reached this saturated, retired-from-relevance state. The industry response is always the same: retire the saturated benchmark and adopt a new, harder one.

### 3. Configuration gaming
Because run configuration has so many knobs (few-shot count, tool access, chain-of-thought, max tokens), a lab can quietly report a number obtained under unusually favorable conditions — the lecture's example: giving your model a Python interpreter tool specifically for a math benchmark, letting it solve every problem via code execution rather than raw reasoning, then reporting the resulting (inflated) score without disclosing that tool access was granted. **The rule of thumb stated directly:** never fully trust a "we destroyed this benchmark" claim from a lab without knowing their exact configuration — max tokens, temperature, reasoning effort, latency, and cost are all frequently left undisclosed.

### 4. Aggregation gaming (the less-discussed fourth pitfall)
Named directly as a *separate* problem from the first three, easy to overlook. Worked example: MMLU spans 57 subjects; a model might genuinely excel at physics while performing poorly at economics — but a lab reporting only the single blended MMLU average can bury that economics weakness completely inside a healthy-looking overall number. **The real consequence, stated as a cautionary scenario:** you build an economics-focused chatbot, see a strong overall MMLU score, deploy the model, and only then discover its economics-specific performance was actually weak all along — a failure the aggregate number never surfaced. The fix is the same instinct as before: look for (or generate yourself) per-category breakdowns, not just the single headline number.

**The lecture's overall conclusion, stated directly:** *"You have to take benchmarks with a pinch of salt — don't believe the number thrown in your face. Implement your own methodology, and decide from there which model actually works for you."* This is the same principle Lesson 7's Zomato case study already demonstrated with a full worked example — this lesson adds the underlying *reasons* benchmark numbers can mislead in the first place.

---

## 5. Key terms

| Term | Meaning |
|---|---|
| **GSM8K** | "Grade School Math 8K" — a retired, saturated arithmetic-word-problem benchmark, used here as the teaching example for benchmark anatomy. |
| **Eval harness** | Software (e.g. EleutherAI's LM Evaluation Harness) that automates the full benchmark loop — prompting, calling the model, extracting/scoring answers, aggregating — so you don't hand-write the plumbing. |
| **Pass@1 / Pass@k / Majority@k** | Strict single-attempt scoring / lenient any-of-k scoring / most-frequent-of-k (self-consistency) scoring. |
| **Contamination** | Benchmark question-answer pairs leaking into a model's pre-training data, inflating scores via memorization rather than reasoning. |
| **Saturation** | Most competitive models clustering near the score ceiling, so the benchmark can no longer meaningfully discriminate between them. |
| **Configuration gaming** | Reporting a benchmark score obtained under undisclosed, unusually favorable run-configuration settings (extra tools, generous token budgets). |
| **Aggregation gaming** | A single blended score concealing meaningfully weak performance in a specific sub-category (e.g. one MMLU subject) that a per-category breakdown would reveal. |

---

## ✍️ Notes / follow-ups
- Leaderboards themselves — which aggregate *multiple* benchmarks into a single ranking — are explicitly deferred to a dedicated future session, not covered in depth here.
- Next: the historical arc of knowledge benchmarks — how the field kept building harder replacements as each generation saturated → [Lesson 9 — The Evolution of Knowledge Benchmarks](09-evolution-of-knowledge-benchmarks.md).
- Key habit: **when you see one blended benchmark number, ask what's hidden inside the aggregation — and when you see a lab's own reported number, ask what configuration produced it.**
