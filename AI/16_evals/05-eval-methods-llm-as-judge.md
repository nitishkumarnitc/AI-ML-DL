# Lesson 5 — LLM Eval Methods: LLM-as-a-Judge, Reference-Based vs Reference-Free

> **Source:** CampusX · *LLM Eval Methods | LLM-as-a-Judge | Reference Based vs Reference Free Evals* · 53:10 · [watch](https://www.youtube.com/watch?v=uQFLY8rQVYA&list=PLEneLIDJFpcA&index=5)
> **One-liner:** Three fully worked case studies — a Campus X RAG retriever (programmatic), a Campus X general chatbot's "helpfulness" (human), and an automated UPSC Mains answer-grading platform (LLM-as-a-judge) — each demonstrating one of the three ways an eval pipeline actually gets *executed*, plus the reference-based vs. reference-free distinction that cuts across all three.

---

## 🎯 TL;DR

**Definition given:** an LLM Eval Method is *"the mechanism you use to decide whether an LLM's output is good or not — the actual procedure that takes an output and produces a judgment about it."* Whatever eval pipeline you build, exactly one of three things actually executes it: a **program** (deterministic/programmatic), a **human**, or a **model** (LLM-as-a-judge). Each is demonstrated with a full worked case study in this lecture. Orthogonal to *who* executes the eval is *whether it needs a ground-truth answer* — **reference-based** evals compare against a known-correct answer baked into the golden dataset; **reference-free** evals judge the output against a rubric/criteria with no single correct answer defined in advance.

---

## 1. Method 1 — Programmatic (deterministic): evaluating a Campus X RAG retriever

**Case study:** a RAG chatbot for the Campus X website — evaluating just the **retriever** component in isolation.

- **Task and target:** the retriever component specifically — does it fetch the right documents from the vector database for a given query?
- **Success criterion:** **Recall@K** — *"out of all the correct items that exist, how many did the system retrieve in its top results?"*

**Worked example.** For the query *"What are the prerequisites for the ML course and how long is it?"*, the two documents that actually contain the answer are **1001 and 1003**. The retriever, run with `k=5`, returns `[1001, 1002, 1004, 1105, 1106]`. Of the 2 correct documents, only 1001 was retrieved → **Recall@5 = 1/2 = 50%**.

- **Golden dataset:** 50–100 realistic questions (covering easy, hard, edge, and random cases), each hand-labeled by a human expert with *which document(s)* in the vector database actually contain the correct answer.
- **Evaluation method chosen: programmatic.** Every question is sent to the retriever, the returned document IDs are compared in code against the golden document IDs, a per-question recall is computed, and the whole dataset's recall is averaged.
- **Worked result:** the pipeline returns an overall **Recall@K of 67%**. Analysis then points to concrete levers to fix it — **improve the embedding model** (it may not be capturing semantic meaning well enough), **query expansion** (rewrite the query via an LLM before retrieval), **increase K**, or **add a reranker** (something ranked 8th moves up into the top-5).

**Why programmatic, and not human or LLM?** The comparison here — "does this exact document ID appear in this exact list of retrieved IDs?" — is a trivial, unambiguous check a script can do perfectly. Bringing in a human or an LLM to do work a program already does perfectly would just add cost for no benefit. The lecture is explicit that recall (fraction of correct docs found) is only *one* aspect of retriever relevance — precision (how much of what's retrieved is useful) and ranking quality are separate aspects, kept out of scope here for simplicity.

---

## 2. Method 2 — Human-based: evaluating a Campus X general chatbot's "helpfulness"

**Case study:** a general-purpose Campus X chatbot (course fees, validity, certificates, refunds) — evaluating the whole application's **helpfulness**, not a single component.

- **Task and target:** the entire application; specifically its helpfulness — is the answer accurate, appropriately toned, and complete?
- **Success criterion:** explicitly flagged as **tricky to define** — there's no single correct metric for "helpfulness" the way there was a clean formula for recall. The fix: define a **1–5 rubric** (5 = correct, complete, and right tone; 3 = partially helpful; 1 = not helpful at all).
- **Golden dataset:** 50–100 realistic questions covering the range of things users might ask — but notice the dataset here has **only one column, the question** — no "correct answer" is baked in, because helpfulness is being judged holistically against the rubric, not against a single right answer.
- **Evaluation method chosen: human.** The task ("is this answer genuinely helpful, in tone and completeness?") is judged as too nuanced for a program to check automatically, and not worth an LLM judge for this illustrative case — a human reads each (question, chatbot answer) pair and assigns a 1–5 score per the rubric.
- **Why use *more than one* grader?** If two independent human graders score the same answer very differently (e.g. one gives 2, the other gives 4), that's a signal the **rubric itself is ambiguous**, not that either grader is wrong — disagreement is used diagnostically, to refine the rubric until graders converge.

### The 5 types of evaluation humans actually perform

The lecture is explicit that "human evaluation" isn't just one thing — it names five distinct categories:

| Type | What it is |
|---|---|
| **Direct grading/rating** | The case study above — a human scores an output against a rubric |
| **Red-teaming** | A dedicated team deliberately attacks an LLM-based system pre-launch to find where it breaks, feeding failures back to the development team |
| **A/B testing** | Two versions run live in production; real users' reactions/ratings decide which version wins and gets rolled out fully |
| **Golden dataset / rubric creation** | The act of a human expert deciding "the correct answer to this question lives in document 1001" (as in the retriever example) is itself a form of evaluation |
| **Human-in-the-loop** | For cases too ambiguous for a programmatic or LLM judge to resolve confidently, the decision is escalated to a human |

**The core trade-off named directly:** human judgment is the most **reliable** (a well-chosen human's judgment is trusted more than a program's or an LLM's), but the biggest disadvantage is **cost** — at scale (millions of users), paying humans to evaluate every case becomes commercially unworkable.

---

## 3. Method 3 — Model-graded (LLM-as-a-judge): an automated UPSC Mains grading platform

**The case study's premise, spelled out in detail:** "CampusX UPSC" runs mock UPSC exams. Prelims (MCQ) is trivial to auto-grade. **Mains is subjective** — normally you'd need paid subject-matter experts to grade essay answers, and at real scale (lakhs of students) that cost kills the business model. The pitch: a third-party platform claims it can grade *any* volume of subjective answers against your defined rubric via an LLM, for a fraction of human-expert cost. The lecture evaluates whether *that platform* actually works.

- **Task and target:** does this LLM-based grading platform grade Mains answers the way a human expert would?
- **Success criterion:** the platform is successful if it **evaluates answers the same way human experts do** — explicitly discussed as one reasonable success criterion among possibly several, not the only correct framing.

### Building the golden dataset

1. **Define a rubric per question.** For a real question like *"Ethical governance is impossible without administrative accountability — discuss"* (15 marks), a subject-matter expert names the dimensions a good answer should hit — e.g. explains the ethics-accountability link, gives mechanisms, cites examples, reaches a balanced conclusion.
2. **Collect real student answers** to a handful of real questions (50–100 total answers — a manageable volume specifically because this is only for building the *golden dataset*, not for grading every student).
3. **A human expert grades each answer against the rubric**, checking off which dimensions were hit and assigning marks (e.g. 13/15 for one student's answer, 4/15 for another's on the same question) — this human-graded column is the ground truth.

### The LLM-as-judge prompt, and how it's structured

The judge LLM is given, per answer: the question, the marks it's worth, the exact rubric, and the student's exact answer — then instructed explicitly: *"For each dimension, decide whether the answer genuinely addresses it, then allocate marks. Do not reward verbosity, keyword-stuffing, and confident assertions that lack substance; reward structure, relevant examples, and balanced argumentation."* The judge must also return **reasoning/justification**, not just a bare score.

### Validating the judge: Mean Absolute Error against human scores

With both a **human score** and an **LLM score** for every one of the 50–100 answers, the question becomes: how close are these two columns? The metric used is **Mean Absolute Error (MAE)**:

```text
MAE = average( |human_score_i - llm_score_i| )   across all i answers
```

**Worked interpretation:** an MAE of **2.3** means the LLM judge's scores deviate from human scores by about ±2.3 marks on average. The goal is to drive this toward **zero** — a perfectly calibrated judge would score exactly as a human would. Levers to improve it: a stronger judge model, refining the system prompt, or refining the rubric itself — then re-measuring MAE after each change, the same iterate-and-remeasure discipline from Lesson 3.

**Why LLM, not programmatic or human, for this case?** Programmatic comparison can't judge whether an essay's argument is substantively good — that requires language understanding a script doesn't have. Human grading is exactly what's being replaced, since it's the cost problem the whole platform exists to solve. LLM-as-judge is the only option that can approximate human-level subjective judgment at the volume (potentially millions of students) the business actually needs.

---

## 4. Reference-based vs. reference-free — classifying the three case studies

**Definitions given directly:**
- **Reference-based evaluation:** *"You have a reference/known-correct answer and the key things a correct answer must contain, written down in advance for each test case. You grade by comparing the output against the reference."*
- **Reference-free evaluation:** *"You have no pre-defined correct answer. You judge the output's quality directly on its own terms, against a criteria/rubric — a scale/standard, not a per-item correct answer."*

**The simple test to classify any eval:** *does the golden dataset contain a predefined correct answer for each row, or does it only contain a rubric/criteria with no single correct answer specified?*

| Case study | Reference-based or free? | Why |
|---|---|---|
| **Retriever (Recall@K)** | **Reference-based** | The golden dataset explicitly states which document IDs are correct for each question |
| **UPSC Mains grading (LLM-as-judge)** | **Reference-based** | The human-assigned score for each answer *is* the reference/correct answer the LLM judge is being measured against |
| **Chatbot helpfulness (human grading)** | **Reference-free** | The golden dataset contains only questions — no predefined correct answer; the human judges each answer purely against the 1–5 rubric, using their own judgment |

**The instructor notes this pairing was deliberate**: the human-graded example was specifically chosen to be reference-free, precisely so all three combinations (programmatic+reference-based, human+reference-free, LLM+reference-based) would be visible in one lecture — the reference-based/free split is independent of which method executes the eval, and any of the three methods can, in principle, be either.

---

## 5. Key terms

| Term | Meaning |
|---|---|
| **LLM Eval Method** | The mechanism that actually executes an eval — programmatic, human, or model-graded — as distinct from the eval pipeline's design. |
| **Recall@K** | Of all correct items that exist for a query, the fraction retrieved in the top-K results. |
| **Red-teaming** | Humans deliberately attacking a system pre-launch to surface failure modes. |
| **LLM-as-a-judge** | Using an LLM, given a rubric and reasoning instructions, to score outputs at a scale human grading can't reach affordably. |
| **Mean Absolute Error (MAE)** | The average absolute difference between an LLM judge's scores and human ground-truth scores — the metric used to validate/calibrate a judge. |
| **Reference-based evaluation** | Scoring against a predefined correct answer stated in the golden dataset. |
| **Reference-free evaluation** | Scoring against a rubric/criteria with no single predefined correct answer. |

---

## ✍️ Notes / follow-ups
- Next: evaluation doesn't stop once you've picked a method — it also has to happen both *before* deployment and *continuously after* → [Lesson 6 — Offline Evals vs Online Evals](06-offline-vs-online-evals.md).
- Key habit: **before trusting any LLM-as-judge setup in production, validate it against real human scores (track MAE) — an uncalibrated judge is just a confident guesser.**
