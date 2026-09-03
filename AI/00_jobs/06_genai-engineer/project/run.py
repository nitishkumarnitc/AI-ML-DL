"""
Sample project — GenAI Engineer
A RAG chatbot over a small doc corpus, now with SENTENCE-LEVEL CHUNKING (not
whole-doc retrieval), measured retrieval quality (recall@k, MRR, precision@k)
against a labeled query->doc set, a scope guardrail that refuses out-of-scope
questions, AND a PII-redaction guardrail that scrubs anything email/phone-
shaped out of a generated answer before it's returned -- two DIFFERENT
guardrail types, because "refuse if unsure" and "redact if sensitive" are
solving two different problems.

Retrieval is a simple local vector store (bag-of-words + light stemming,
pure stdlib) instead of a downloaded embedding model / vector DB, so this
runs instantly anywhere. Swap `retrieve` for Chroma + sentence-transformers
in production -- the recall@k/MRR/precision@k harness below doesn't change.

Run:  python run.py
      python run.py --k 5              (retrieve top-5 chunks instead of top-3)
Dependencies:
  - math (stdlib) -- cosine similarity
  - re (stdlib) -- tokenization + PII pattern matching
  - collections.Counter (stdlib) -- term-frequency vectors
  - argparse (stdlib) -- CLI config
  - (no third-party packages -- swap in Chroma + sentence-transformers for production)
"""
import argparse
import math
import re
from collections import Counter

DOCS = {
    "deploys": "We deploy to production every weekday at 2pm via the automated CI/CD "
               "pipeline. Deploys outside that window require a manager approval. "
               "Rollbacks are triggered automatically if error rate exceeds 1% for 5 minutes.",
    "oncall": "The on-call engineer rotates weekly and is paged through the incident tool "
              "for any P1 or P2 alert. On-call shifts start Monday 9am. Escalations that "
              "aren't acknowledged in 10 minutes page the secondary on-call automatically.",
    "code-review": "All pull requests need at least one approval before merging. Changes "
                   "to the payments service need two approvals. Reviews should focus on "
                   "correctness and security, not style, since a linter enforces style.",
    "testing": "Unit tests run on every commit. Integration tests run nightly and before "
               "every production deploy. Flaky tests are quarantined, not deleted, and "
               "tracked in a dashboard until fixed.",
    "access": "New engineers get read access to all repos on day one. Write access to "
              "the payments service requires a security training completion. Admin access "
              "requires director approval and is reviewed quarterly.",
    "incidents": "Every P1 incident gets a postmortem doc within 48 hours. Postmortems are "
                 "blameless and shared company-wide. For urgent escalations outside normal "
                 "channels, contact incident-response@internal.example.com directly.",
    "vacation": "Engineers get unlimited PTO but should coordinate with their team lead "
               "before taking more than a week off. There's no carryover since PTO isn't "
               "accrued in the first place.",
    "onboarding": "New hires get a laptop, repo access, and a 30-60-90 day plan from their "
                  "manager in the first week. IT support can be reached for setup issues "
                  "during the first week at extension 4-2200.",
    "security-training": "All engineers complete security training annually. It covers "
                          "phishing, secrets management, and the incident reporting process.",
    "release-notes": "Release notes are auto-generated from merged PR titles and published "
                     "to the internal changelog every Friday.",
}

STOPWORDS = {"a", "an", "and", "are", "at", "before", "by", "do", "does", "for", "from",
             "get", "how", "i", "in", "is", "it", "of", "on", "our", "the", "to", "was",
             "we", "what", "when", "who", "will", "with", "you", "your"}


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


# ---------------------------------------------------------------------------
# Sentence-level chunking -- each doc becomes several independently-ranked
# chunks instead of one big blob, which is what lets retrieval find the
# ONE sentence that answers a question in a doc that also covers other topics.
# ---------------------------------------------------------------------------
def chunk_doc(doc_id: str, text: str):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [(f"{doc_id}#{i}", doc_id, s) for i, s in enumerate(sentences) if s]


CHUNKS = [chunk for doc_id, text in DOCS.items() for chunk in chunk_doc(doc_id, text)]
CHUNK_VECTORS = {chunk_id: Counter(tokenize(text)) for chunk_id, _, text in CHUNKS}
CHUNK_TEXT = {chunk_id: text for chunk_id, _, text in CHUNKS}
CHUNK_PARENT = {chunk_id: parent for chunk_id, parent, _ in CHUNKS}


def cosine_sim(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def retrieve_chunks(query: str, k: int = 3):
    qv = Counter(tokenize(query))
    scored = sorted(CHUNK_VECTORS, key=lambda c: -cosine_sim(qv, CHUNK_VECTORS[c]))
    return scored[:k]


def retrieve_docs(query: str, k: int = 3):
    """Doc-level ranking derived from chunk ranking, for recall@k/MRR against
    doc-level ground truth -- de-duplicates chunks down to their parent doc,
    preserving rank order."""
    seen = []
    for chunk_id in retrieve_chunks(query, k=k * 3):  # over-fetch chunks, then dedupe
        doc_id = CHUNK_PARENT[chunk_id]
        if doc_id not in seen:
            seen.append(doc_id)
        if len(seen) >= k:
            break
    return seen


# ---------------------------------------------------------------------------
# Labeled retrieval eval set
# ---------------------------------------------------------------------------
RETRIEVAL_EVAL = [
    {"query": "When do production deploys happen?", "relevant_doc_id": "deploys"},
    {"query": "How often does on-call rotate?", "relevant_doc_id": "oncall"},
    {"query": "How many approvals does a payments PR need?", "relevant_doc_id": "code-review"},
    {"query": "When do integration tests run?", "relevant_doc_id": "testing"},
    {"query": "What access do new engineers get on day one?", "relevant_doc_id": "access"},
    {"query": "How soon after a P1 incident is the postmortem due?", "relevant_doc_id": "incidents"},
    {"query": "How much PTO do engineers get?", "relevant_doc_id": "vacation"},
    {"query": "What does a new hire receive in their first week?", "relevant_doc_id": "onboarding"},
    {"query": "What requires manager approval for a deploy?", "relevant_doc_id": "deploys"},
    {"query": "Who needs to approve a payments service change?", "relevant_doc_id": "code-review"},
    {"query": "What happens if error rate is too high after a deploy?", "relevant_doc_id": "deploys"},
    {"query": "What does security training cover?", "relevant_doc_id": "security-training"},
    {"query": "How are release notes generated?", "relevant_doc_id": "release-notes"},
    {"query": "What happens to flaky tests?", "relevant_doc_id": "testing"},
    {"query": "What is required for admin access?", "relevant_doc_id": "access"},
]


def evaluate_retrieval(k=3):
    hits, reciprocal_ranks, precisions = 0, [], []
    for item in RETRIEVAL_EVAL:
        retrieved = retrieve_docs(item["query"], k=k)
        relevant_in_top_k = sum(1 for d in retrieved if d == item["relevant_doc_id"])
        precisions.append(relevant_in_top_k / k)
        if item["relevant_doc_id"] in retrieved:
            hits += 1
            rank = retrieved.index(item["relevant_doc_id"]) + 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)
    n = len(RETRIEVAL_EVAL)
    return hits / n, sum(reciprocal_ranks) / n, sum(precisions) / n


# ---------------------------------------------------------------------------
# Generation with TWO guardrails: scope refusal + PII redaction
# ---------------------------------------------------------------------------
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\bextension\s+\d[\d-]{2,}\b", re.I),               # internal extension
]


def redact_pii(text: str) -> tuple:
    redacted = text
    hit = False
    for pattern in PII_PATTERNS:
        if pattern.search(redacted):
            hit = True
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted, hit


def chat(query: str, k: int = 3, sim_threshold: float = 0.2) -> dict:
    qv = Counter(tokenize(query))
    best_chunk = max(CHUNK_VECTORS, key=lambda c: cosine_sim(qv, CHUNK_VECTORS[c]))
    score = cosine_sim(qv, CHUNK_VECTORS[best_chunk])
    if score < sim_threshold:
        return {"answer": "I don't have information on that.", "guardrail": "scope_refusal"}
    answer, redacted = redact_pii(CHUNK_TEXT[best_chunk])
    return {"answer": answer, "guardrail": "pii_redacted" if redacted else None,
            "source_chunk": best_chunk}


def main():
    parser = argparse.ArgumentParser(description="Chunked RAG chatbot with retrieval metrics + guardrails")
    parser.add_argument("--k", type=int, default=3, help="top-k for recall/precision/MRR (default: 3)")
    args = parser.parse_args()

    print(f"indexed {len(DOCS)} docs -> {len(CHUNKS)} sentence-level chunks\n")

    recall, mrr, precision = evaluate_retrieval(k=args.k)
    print(f"recall@{args.k}={recall:.2f}  MRR@{args.k}={mrr:.2f}  precision@{args.k}={precision:.2f}")
    print(f"(precision@{args.k} is low almost by construction here -- each query has exactly ONE "
          f"relevant doc, so the theoretical ceiling at k={args.k} is 1/{args.k}={1/args.k:.2f}. "
          f"Precision matters more when multiple docs could be relevant per query.)\n")

    print("=== in-scope questions (chunk-level retrieval means a precise sentence, not a whole doc) ===")
    for item in RETRIEVAL_EVAL[1:4]:
        result = chat(item["query"], k=args.k)
        print(f"Q: {item['query']}\nA: {result['answer']}  [chunk: {result.get('source_chunk')}]\n")

    print("=== scope-refusal guardrail probes ===")
    for q in ["What's the capital of France?", "Write me a poem about cats."]:
        result = chat(q, k=args.k)
        print(f"Q: {q}\nA: {result['answer']}  [guardrail: {result['guardrail']}]\n")

    print("=== PII-redaction guardrail probe (a doc that legitimately contains an email/extension) ===")
    for q in ["Who do I contact for an urgent incident escalation?", "Who do I contact for laptop setup issues?"]:
        result = chat(q, k=args.k)
        print(f"Q: {q}\nA: {result['answer']}  [guardrail: {result['guardrail']}]\n")


if __name__ == "__main__":
    main()
