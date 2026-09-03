"""
Sample project — Applied AI / LLM Product Engineer
A RAG feature shipped end-to-end: local (no-download) retrieval over a
10-doc corpus, structured-output "generation", per-query latency/cost
logging, a 10-question eval set, AND multi-turn conversational memory (a
short follow-up like "what about international?" gets rewritten using the
previous question so retrieval still finds the right doc) -- a real,
lightweight technique for conversational RAG.

Retrieval uses plain bag-of-words cosine similarity (pure stdlib) instead of
a downloaded embedding model, so this runs instantly anywhere. Swap
`retrieve` for a real embedding model and `generate` for a real LLM call in
production -- the surrounding harness (logging, eval, structured output,
conversation memory) stays the same.

Run:  python run.py
      python run.py --ask "How long do I have to return something?"
      python run.py --interactive              (multi-turn REPL with memory)
      python run.py --json-out results.json    (export eval + cost log)
Dependencies:
  - math (stdlib) -- cosine similarity
  - re (stdlib) -- tokenization
  - time (stdlib) -- per-query latency logging
  - collections.Counter (stdlib) -- term-frequency vectors
  - argparse, json (stdlib) -- CLI and export
  - (no third-party packages -- swap in sentence-transformers + a vector DB for production)
"""
import argparse
import json
import math
import re
import time
from collections import Counter

DOCS = {
    "return-policy": "Items can be returned within 30 days of delivery for a full refund. "
                      "The item must be unused and in its original packaging.",
    "shipping-times": "Standard shipping takes 5-7 business days. Express shipping takes "
                       "1-2 business days and costs an extra $12.",
    "warranty": "All electronics carry a 1 year manufacturer warranty covering defects. "
                "Warranty does not cover accidental damage or water damage.",
    "international": "We ship to over 40 countries. International orders may be subject to "
                      "customs fees charged by the destination country, not by us.",
    "gift-cards": "Gift cards never expire and can be used for any product on the site. "
                  "Gift cards cannot be redeemed for cash.",
    "cancellations": "Orders can be canceled for free within 1 hour of placing them. After "
                      "that, the order has likely already entered fulfillment and cannot be canceled.",
    "price-match": "We match a competitor's lower price within 14 days of purchase if the "
                    "item is identical and in stock at the competitor.",
    "loyalty-program": "Members earn 1 point per dollar spent. 100 points can be redeemed "
                        "for a $5 discount on a future order.",
    "damaged-items": "If an item arrives damaged, contact support within 48 hours with photos "
                      "for a free replacement or full refund, no return shipping required.",
    "business-accounts": "Business accounts get net-30 invoicing and a dedicated account "
                          "manager once monthly spend exceeds $2,000.",
}

STOPWORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
             "from", "has", "have", "how", "i", "in", "is", "it", "its", "my", "of", "on",
             "our", "s", "something", "that", "the", "this", "to", "was", "we", "were",
             "what", "who", "will", "with", "you", "your", "about"}


def _stem(word: str) -> str:
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


DOC_VECTORS = {doc_id: Counter(tokenize(text)) for doc_id, text in DOCS.items()}


def cosine_sim(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def retrieve(query: str, k: int = 2):
    qv = Counter(tokenize(query))
    scored = [(doc_id, cosine_sim(qv, dv)) for doc_id, dv in DOC_VECTORS.items()]
    scored.sort(key=lambda x: -x[1])
    return scored[:k]


def generate(query: str, retrieved: list) -> dict:
    """Structured, context-only 'generation' -- extractive, no hallucination possible."""
    best_id, best_score = retrieved[0]
    if best_score < 0.05:
        return {"answer": "I don't have information on that.", "confidence": "low",
                "source_chunk_ids": []}
    text = DOCS[best_id]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    q_words = set(tokenize(query))
    best_sentence = max(sentences, key=lambda s: len(set(tokenize(s)) & q_words))
    confidence = "high" if best_score > 0.3 else "medium"
    return {"answer": best_sentence.strip(), "confidence": confidence,
            "source_chunk_ids": [doc_id for doc_id, _ in retrieved]}


LOG = []

# Follow-up phrases that signal "this question depends on the last one" --
# a lightweight, real technique: rewrite the query using recent context
# instead of running a full coreference-resolution model.
FOLLOWUP_MARKERS = ["what about", "and what about", "how about", "same for", "and for"]


def rewrite_with_memory(query: str, history: list) -> str:
    q_lower = query.lower().strip()
    if history and any(q_lower.startswith(m) for m in FOLLOWUP_MARKERS):
        last_query = history[-1]["query"]
        rewritten = f"{last_query} {query}"
        return rewritten
    return query


def answer_and_log(query: str, history: list = None, price_per_1k_tokens: float = 0.002) -> dict:
    history = history if history is not None else []
    effective_query = rewrite_with_memory(query, history)

    t0 = time.perf_counter()
    retrieved = retrieve(effective_query)
    t1 = time.perf_counter()
    result = generate(effective_query, retrieved)
    t2 = time.perf_counter()

    context_tokens = sum(len(tokenize(DOCS[d])) for d, _ in retrieved)
    output_tokens = len(tokenize(result["answer"]))
    est_cost = (context_tokens + output_tokens) / 1000 * price_per_1k_tokens

    LOG.append({
        "query": query, "effective_query": effective_query,
        "retrieval_ms": (t1 - t0) * 1000, "gen_ms": (t2 - t1) * 1000,
        "total_ms": (t2 - t0) * 1000, "est_cost_usd": est_cost,
    })
    history.append({"query": query, "effective_query": effective_query, "answer": result["answer"]})
    return result


EVAL = [
    {"q": "How long do I have to return something?", "expected_substring": "30 days"},
    {"q": "How much does express shipping cost?", "expected_substring": "$12"},
    {"q": "Does the warranty cover water damage?", "expected_substring": "does not cover"},
    {"q": "Do gift cards expire?", "expected_substring": "never expire"},
    {"q": "Who charges customs fees on international orders?", "expected_substring": "destination country"},
    {"q": "Can I cancel my order?", "expected_substring": "1 hour"},
    {"q": "Will you match a competitor's price?", "expected_substring": "match a competitor"},
    {"q": "How many points do I earn per dollar?", "expected_substring": "1 point"},
    {"q": "What do I do if my item arrives damaged?", "expected_substring": "48 hours"},
    {"q": "What do business accounts get?", "expected_substring": "net-30"},
]


def run_eval():
    correct = 0
    rows = []
    for item in EVAL:
        result = answer_and_log(item["q"])
        passed = item["expected_substring"].lower() in result["answer"].lower()
        correct += passed
        rows.append((item["q"], result["answer"], result["confidence"], passed))
    return correct / len(EVAL), rows


def run_multiturn_demo():
    print("=== Multi-turn memory demo (a follow-up rewritten using the prior question) ===")
    history = []
    turns = [
        "What's your return policy?",
        "What about international orders?",  # ambiguous alone; needs the prior turn's context
    ]
    for q in turns:
        result = answer_and_log(q, history=history)
        effective = history[-1]["effective_query"]
        print(f"Q: {q}")
        if effective != q:
            print(f"   (rewritten using memory -> {effective!r})")
        print(f"A: {result['answer']}\n")


def main():
    parser = argparse.ArgumentParser(description="Local RAG demo with cost/latency logging")
    parser.add_argument("--ask", default=None, help="ask a single custom question and exit")
    parser.add_argument("--interactive", action="store_true", help="multi-turn REPL with memory")
    parser.add_argument("--json-out", default=None, help="export eval results + cost log to this path")
    args = parser.parse_args()

    if args.ask:
        result = answer_and_log(args.ask)
        print(json.dumps(result, indent=2))
        return

    if args.interactive:
        print("Interactive mode -- ask questions (Ctrl-C to quit). Try a follow-up like "
              "'what about international?' after asking about returns.\n")
        history = []
        try:
            while True:
                q = input("you> ").strip()
                if not q:
                    continue
                result = answer_and_log(q, history=history)
                print(f"bot> {result['answer']}  [{result['confidence']}]\n")
        except (KeyboardInterrupt, EOFError):
            print("\nbye!")
        return

    pass_rate, rows = run_eval()
    print(f"{'question':<50}{'confidence':<12}{'pass'}")
    for q, answer, confidence, passed in rows:
        print(f"{q:<50}{confidence:<12}{'PASS' if passed else 'FAIL'}")
        print(f"    -> {answer}")
    print(f"\neval pass rate: {pass_rate:.0%} ({int(round(pass_rate * len(EVAL)))}/{len(EVAL)})")

    total_ms = [r["total_ms"] for r in LOG]
    total_cost = sum(r["est_cost_usd"] for r in LOG)
    print(f"\nlatency: mean {sum(total_ms)/len(total_ms):.3f}ms, max {max(total_ms):.3f}ms")
    print(f"cost: total ${total_cost:.6f} across {len(LOG)} queries "
          f"(${total_cost/len(LOG):.6f}/query)")

    oos = answer_and_log("What's the capital of France?")
    print(f"\nout-of-scope probe -> {oos}")

    print()
    run_multiturn_demo()

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"eval_pass_rate": pass_rate, "log": LOG}, f, indent=2)
        print(f"exported eval + cost log to {args.json_out}")


if __name__ == "__main__":
    main()
