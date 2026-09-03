# Lesson 13 — How to Test RAG Retrievers (Hands-On)

> **Source:** CampusX · *How to Test RAG Retrievers (Hands-On)* · [watch](https://www.youtube.com/watch?v=9Dkz3ckRj8c&list=PLEneLIDJFpcA&index=14)
> **One-liner:** Building the CampusX Doubt Solver's retriever from scratch, then discovering — live — that the "obvious" way to measure Recall/Precision (a chunk-ID golden dataset) is actually the *wrong* method for this app, and rebuilding it the right way with an LLM-as-judge and an ideal-answer golden dataset (DeepEval's Contextual Recall / Contextual Precision).

---

## 🎯 TL;DR

This session builds the actual retriever for the CampusX Doubt Solver, then evaluates it with two metrics — **Contextual Recall** and **Contextual Precision** — using **DeepEval**. The twist that makes this lesson worth watching closely: the intuitive way to build a retrieval golden dataset (label each question with the correct chunk IDs) is demonstrated and then explicitly rejected, because it silently breaks every time you retune chunking parameters. The fix is a golden dataset of (question, ideal-answer) pairs, scored by an LLM-as-judge that breaks the ideal answer into claims and checks which claims the retrieved chunks actually support. After building the eval, the retriever is iteratively tuned — chunk size, then a reranker, then a bigger embedding model — with recall climbing from a baseline of **80%** to **99%**, and precision from **80%** to **~85%**.

---

## 1. Project setup

A fresh, standardized project, built to be reused across the next several sessions:

```text
rag_eval_project/
├── data/            # lecture transcripts (.vtt files, one per session)
├── src/             # retriever.py, generator.py (later), rag_pipeline.py (later)
├── evals/           # eval_retriever.py, eval_generator.py (later), ...
├── goldens/         # golden datasets for each eval
├── chroma_store/    # the vector database (created on first run, not checked in)
├── pyproject.toml   # managed with uv
└── .env             # OPENAI_API_KEY
```

Setup steps performed live:
- `uv init`, pinned to Python 3.11, dependencies installed via `uv add`: **LangChain**, **OpenAI**, **DeepEval**, **pytest**, **python-dotenv**.
- Real `.vtt` transcript files (subtitle-style, timestamped) for each of the ~8–9 lectures so far, copied into `data/`.
- `.env` holding `OPENAI_API_KEY`.

---

## 2. Building the retriever (`src/retriever.py`)

The pipeline inside `build_retriever()`:

1. **`load_transcripts()`** — reads every `.vtt` file in `data/`, strips out timestamp lines (kept out deliberately: mixing raw timestamps into the text would break the semantic coherence chunking depends on), and stores each cleaned line as a LangChain `Document`. Critically, each document's **metadata carries which session it came from** — this is what lets the bot later cite *"Nitish Sir discussed this in session 5."*
2. **Chunking** — `RecursiveCharacterTextSplitter`-style chunking with an initial **chunk size of 750, overlap of 100** (deliberately kept small for the class so later tuning has room to show improvement).
3. **Embedding** — OpenAI's **`text-embedding-3-small`**.
4. **Vector store** — **Chroma**, persisted to `chroma_store/`. The code checks whether the store already exists before rebuilding it — rebuilding is only needed when the source documents or chunking parameters change.
5. **Retriever object** — `as_retriever(k=5)`, i.e. every query returns the 5 nearest chunks.

A smoke test — running `retriever.py` directly with the question *"What is regression testing?"* — confirms the pipeline works end-to-end (builds the vector store on first run, then retrieves 5 chunks) before any evaluation code is written.

> **Live caveat surfaced by a student question:** if a new lecture transcript is added later, the current setup requires manually deleting `chroma_store/` and rerunning `retriever.py` to reprocess everything from scratch — real production systems would decouple ingestion from retrieval (incremental indexing), but the class keeps this simple deliberately to keep the focus on evaluation, not production engineering.

---

## 3. The two retriever failure modes → two metrics

Before writing any eval code, the class works out *why* a retriever fails, because the failure modes are what the metrics are actually measuring:

1. **Missed context** — the chunks that would answer the question correctly exist in the vector DB, but the retriever didn't fetch them (it fetched other, irrelevant chunks instead).
2. **Noisy context** — the retriever *did* fetch the correct chunks, but also brought back extra irrelevant ones alongside them, diluting what the generator sees.

| Metric | Formal definition | Which failure mode it targets |
|---|---|---|
| **Recall** | Of all the correct contexts that exist for a question, what fraction did the retriever fetch? (e.g. 3 of 5 correct chunks retrieved → recall = 3/5) | Missed context |
| **Precision** | Of all the contexts the retriever *did* fetch, what fraction were actually correct? (e.g. 5 fetched, 2 useful → precision = 2/5) | Noisy context |

**The recall/precision trade-off, explained concretely:** the simplest way to raise recall is to increase `k` (fetch more chunks) — but that mechanically drops precision, since you're now pulling in more noise alongside the same correct chunks. Pushing recall toward 100% by brute-forcing `k` upward pushes precision toward 0%. Both metrics matter; neither can be optimized in isolation.

Both are explicitly identified as **reference-based evals** — you cannot score either without knowing, per question, what the "correct" context actually is.

---

## 4. The wrong way to build the golden dataset (and why it fails)

The intuitive approach, demonstrated live before being rejected: a golden dataset with two columns — `question` and `correct_chunk_IDs` (e.g. "chunks 72, 89, and 100 discuss regression testing"). Recall/precision would then be simple set arithmetic between retrieved chunk IDs and golden chunk IDs.

**Why this breaks in practice, worked out with the class as a thought exercise:** creating this dataset means a human has to read *every single chunk* (the transcript corpus here has ~800+ chunks) for *every single question* to find which ones are relevant — already a brutal, unscalable task for even 50 questions. But the fatal flaw isn't the effort — it's what happens next: **the moment you change any chunking parameter** (chunk size, overlap) to try to improve your retriever, **every chunk ID shifts**, because the chunk boundaries are now different. The entire golden dataset — built against the old chunk IDs — silently becomes meaningless. You'd have to manually rebuild the golden dataset every single time you tune chunking, which defeats the purpose of having a fast, iterable eval loop.

> This method *does* work for RAG apps where documents are cleanly, permanently separated (so chunking parameters never need retuning) — but not here, where information about one topic can be spread across multiple sessions/documents and chunking will be actively tuned.

---

## 5. The right way: ideal-answer golden dataset + LLM-as-judge

Instead, the golden dataset has two columns: `question` and **`ideal_answer`** — a correct, human-verified answer written directly from the actual transcript content (not from Google, not from the model's own knowledge). Crucially, **this ideal answer is stable even when chunk boundaries move** — the underlying information hasn't changed, only which chunk it happens to sit in. This is the property that makes the golden dataset reusable across every chunking-parameter experiment.

### Contextual Recall — worked example

1. Send the question to the retriever; get back 5 chunks.
2. Bring in an **LLM-as-judge**. Give it the ideal answer and ask it to break the answer into discrete **claims** (e.g. an answer with 3 sentences might yield 3 claims).
3. For each claim, ask the judge: *does this claim's information appear anywhere in the 5 retrieved chunks?*
4. Contextual Recall for that question = (claims found in the retrieved chunks) / (total claims in the ideal answer).

If chunking changes later and a claim's information simply moves to a different chunk, the *same* ideal answer still scores correctly against the new chunk set — no golden dataset rebuild required. This is the entire payoff of the redesign.

### Contextual Precision — worked example, and why it's rank-aware

For precision, the judge is shown each retrieved chunk (not broken into claims this time) alongside the question and ideal answer, and asked a direct yes/no: *does this chunk help produce the expected answer?* The fraction of "yes" chunks is the naive precision.

But naive precision has a blind spot, demonstrated with two cases that have **identical** precision (2 correct chunks out of 5 in both) but very different retriever quality:

- **Case A**: the 2 correct chunks are ranked 1st and 2nd (top of the list).
- **Case B**: the 2 correct chunks are ranked 4th and 5th (bottom of the list).

Naive precision scores both as 2/5 — identical — even though Case A is obviously the better retriever, since a generator using only the top few chunks would still see the right information. DeepEval's **Contextual Precision** fixes this by being **rank-aware**: it computes precision-at-each-cutoff (precision@1, @2, @3, @4, @5) and averages them. Because Case A's correct chunks are seen early, its early cutoffs (precision@1 = 1/1, precision@2 = 2/2) are much higher than Case B's (precision@1 = 0/1, precision@2 = 0/2), so the averaged score is meaningfully higher for Case A — correctly reflecting that where the correct chunks rank matters, not just whether they're present.

---

## 6. Four ways to build a golden dataset (and which was used)

| Method | How it works | Tradeoff |
|---|---|---|
| **Hand-authored** | You personally write every (question, ideal-answer) pair, drawing only on material you know is actually in the source | Least error-prone (human judgment used throughout) but doesn't scale |
| **LLM-assisted drafting** | Upload the source material to an LLM, have it draft the dataset, then a human reviews/corrects every entry | Faster, but the LLM can invent an answer that sounds plausible but wasn't actually taught in the course — human review is what catches this |
| **DeepEval's Synthesizer module** | An automated pipeline that generates golden entries directly from your chunked corpus | Demonstrated live and found to produce low-quality, oddly-phrased or off-topic questions for this specific course corpus (e.g. a UPSC-exam-flavored question that had nothing to do with what was actually taught) — **not used** for this project's real golden dataset |
| **Mined from production** | Once deployed, pull real user questions (and thumbs-up-confirmed answers) into the golden dataset | Can't be your *first* method — you need some initial coverage before you have production traffic |

**What was actually used:** LLM-assisted drafting, one question at a time (rather than all-at-once, for better quality control) — 15 questions were generated this way, then manually verified against the actual transcripts before being saved to `goldens/retriever_goldens.json`.

---

## 7. The DeepEval code pattern

Every DeepEval-based eval file follows the same three-part structure:

```python
# 1. LLM Test Cases — one per row of your golden dataset
test_case = LLMTestCase(
    input=question,
    expected_output=ideal_answer,       # or: retrieval_context for retriever evals
    retrieval_context=retrieved_chunks,
)

# 2. Metric(s) — what you're scoring the test cases against
metric = ContextualRecallMetric(threshold=0.7, model="gpt-4.1", include_reason=True)

# 3. evaluate() — runs every metric against every test case
evaluate(test_cases=[...], metrics=[metric])
```

`eval_retriever.py` loads the golden dataset, loops over every row, calls the retriever for that question, builds an `LLMTestCase` from (question, ideal answer, retrieved chunks), and evaluates it against both `ContextualRecallMetric` and `ContextualPrecisionMetric` — `include_reason=True` so a failing test case also reports *why* it failed.

**A real setup snag hit live:** running `eval_retriever.py` directly threw `ModuleNotFoundError: No module named 'src'`, because relative imports don't resolve when a script is run directly from inside a subfolder. Fix: add `__init__.py` to both `src/` and `evals/` (turning them into proper Python packages) and invoke the eval as a module from the project root instead of as a bare script:

```bash
python3 -m evals.eval_retriever
```

---

## 8. Iterating on the retriever — the actual numbers

| Change made | Contextual Recall | Contextual Precision | Failing test cases (of 15) |
|---|:---:|:---:|:---:|
| **Baseline** (chunk_size=750, overlap=100) | 80% | 80% | 5 |
| Chunk size → 1000, overlap → 150 | **97%** | 83% | 3 |
| + Reranker added (sentence-transformer cross-encoder) | 92% | **85%** | 2 |
| + Bigger embedding model (`text-embedding-3-large`) | **99%** | 85% | 3 |
| Reduced k to 3 (tried, then reverted) | — | ~84% (no real gain) | — |

**What each change actually did:**
- **Bigger chunks** gave the retriever more surrounding context per chunk, sharply improving recall (fewer split answers) with a modest precision cost.
- **Adding a reranker** (which reorders the retrieved set so the most useful chunks move to the top) improved precision as expected — precision is exactly the metric a reranker should help, since it's about *which* of the retrieved chunks are useful, not how many exist.
- **Switching to a larger embedding model** pushed recall further (to 99%) at no precision cost — better embeddings simply capture semantic similarity more accurately.
- **Reducing k** was tried as a lever to trade recall for precision but didn't produce a clean win here — a reminder that not every "obvious" lever pays off on real data, and that with only 15 golden questions, some run-to-run variance is expected regardless.

**Final state:** recall settled above 95%, precision around 85% — good enough to move forward with confidence to building the generator, while noting there's still room to try better rerankers or further chunking sweeps later.

---

## 9. Key terms

| Term | Meaning |
|---|---|
| **Contextual Recall** | LLM-judged fraction of an ideal answer's claims that are actually present somewhere in the retrieved chunks. |
| **Contextual Precision** | LLM-judged, rank-aware fraction of retrieved chunks that are actually useful — chunks found earlier in the ranking count for more than chunks found later. |
| **LLM-as-judge** | Using an LLM (here, GPT-4.1) to make the relevance/support judgment calls a golden-answer comparison requires, since exact-match or embedding-similarity comparison can't capture "does this chunk support this claim." |
| **Reranker** | A second-stage model that reorders an initial retrieved set so the most useful chunks surface higher — directly targets precision, especially rank-aware precision. |
| **Golden dataset (retrieval)** | Here: (question, ideal-answer) pairs written from verified source content — deliberately *not* (question, chunk-ID) pairs, because chunk IDs are fragile to chunking-parameter changes. |

---

## ✍️ Notes / follow-ups
- Next: build the generator, evaluate it in isolation (Faithfulness, Answer Relevancy), then connect it to this retriever and run the full RAG Triad on the pipeline → [Lesson 14 — Evaluating RAG: Testing the Generator & Full Pipeline with the RAG Triad](14-evaluating-rag-generator-pipeline-rag-triad.md).
- Key habit: **before building any golden dataset, ask whether the parameter you're about to tune will invalidate it** — if yes, the dataset's ground-truth column needs to be something more stable than an ID.
