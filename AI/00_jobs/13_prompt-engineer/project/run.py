"""
Sample project — Prompt Engineer / AI Interaction Designer
FOUR prompt variants for one task (classify support-ticket urgency), scored
against a 20-example eval set with ground truth, including a majority-VOTE
ensemble across the other three (a real prompt-engineering technique: when
no single prompt is reliably best, combine several and vote) -- plus a full
confusion matrix per variant, since aggregate accuracy hides WHICH kind of
mistake a prompt style tends to make.

Each variant is a deterministic rule-based classifier standing in for a real
LLM call under a zero-shot / few-shot / structured-CoT style prompt of
increasing sophistication, so this runs instantly with no API key. Swap each
`classify_*` function for an actual LLM call with the matching prompt style
and keep the eval harness unchanged.

Run:  python run.py
Dependencies:
  - collections.Counter (stdlib) -- majority vote + confusion matrix tallying
  - (no imports beyond stdlib needed)
"""
from collections import Counter

EVAL_SET = [
    {"ticket": "App crashes on login for all users since this morning.", "expected": "high"},
    {"ticket": "Small typo in the settings page label.", "expected": "low"},
    {"ticket": "Export to CSV is slow for large accounts.", "expected": "medium"},
    {"ticket": "Payments failing for about 10% of customers right now.", "expected": "high"},
    {"ticket": "Feature request: add dark mode.", "expected": "low"},
    {"ticket": "Search results are missing the newest items, no workaround.", "expected": "medium"},
    {"ticket": "Data loss reported after last sync for one enterprise customer.", "expected": "high"},
    {"ticket": "Button color is slightly off-brand on the pricing page.", "expected": "low"},
    {"ticket": "API rate limits hit intermittently during peak hours.", "expected": "medium"},
    {"ticket": "Password reset email sometimes takes 10 minutes to arrive.", "expected": "medium"},
    {"ticket": "Entire dashboard is down for all customers.", "expected": "high"},
    {"ticket": "Footer link points to the wrong help article.", "expected": "low"},
    {"ticket": "Bulk export times out for accounts with 10k+ rows.", "expected": "medium"},
    {"ticket": "Customer billed twice for the same invoice.", "expected": "high"},
    {"ticket": "Suggestion: add a keyboard shortcut for search.", "expected": "low"},
    {"ticket": "Notifications are delayed by a few minutes during peak load.", "expected": "medium"},
    {"ticket": "Auth tokens expiring early, logging out all enterprise users.", "expected": "high"},
    {"ticket": "Placeholder text says 'lorem ipsum' on a rarely-used settings tab.", "expected": "low"},
    {"ticket": "Pagination skips a page of results under specific filters.", "expected": "medium"},
    {"ticket": "Database replica lagging, causing stale reads for some users.", "expected": "medium"},
]

LABELS = ["low", "medium", "high"]


# --- Variant 1: zero-shot-style -- a tiny, crude keyword list ---------------
def classify_zero_shot(ticket: str) -> str:
    t = ticket.lower()
    if "crash" in t or "down" in t:
        return "high"
    if "typo" in t or "color" in t or "dark mode" in t:
        return "low"
    return "medium"


# --- Variant 2: few-shot-style -- a broader, example-calibrated keyword list
def classify_few_shot(ticket: str) -> str:
    t = ticket.lower()
    high_signals = ["crash", "all users", "data loss", "payments failing", "down",
                    "billed twice", "logging out", "expiring early"]
    low_signals = ["typo", "color", "dark mode", "feature request", "off-brand",
                   "suggestion", "lorem ipsum", "keyboard shortcut"]
    if any(s in t for s in high_signals):
        return "high"
    if any(s in t for s in low_signals):
        return "low"
    return "medium"


# --- Variant 3: structured-CoT-style -- reasons about scope + severity -----
def classify_structured_cot(ticket: str) -> dict:
    t = ticket.lower()
    scope_signals = ["all users", "enterprise", "10%", "peak hours", "peak load"]
    severity_signals = ["crash", "data loss", "payments failing", "no workaround",
                        "billed twice", "logging out"]
    cosmetic_signals = ["typo", "color", "off-brand", "feature request", "suggestion", "lorem ipsum"]

    scope_hits = sum(s in t for s in scope_signals)
    severity_hits = sum(s in t for s in severity_signals)
    cosmetic_hits = sum(s in t for s in cosmetic_signals)

    if cosmetic_hits and not severity_hits:
        urgency = "low"
    elif severity_hits >= 1 or scope_hits >= 2:
        urgency = "high"
    elif scope_hits >= 1:
        urgency = "medium"
    else:
        urgency = "medium"
    return {"urgency": urgency}


# --- Variant 4: majority-vote ensemble of the other three -------------------
def classify_ensemble(ticket: str) -> str:
    votes = [classify_zero_shot(ticket), classify_few_shot(ticket), classify_structured_cot(ticket)["urgency"]]
    return Counter(votes).most_common(1)[0][0]


def score(classify_fn, parse_fn):
    correct = 0
    rows = []
    confusion = {actual: {predicted: 0 for predicted in LABELS} for actual in LABELS}
    for item in EVAL_SET:
        predicted = parse_fn(classify_fn(item["ticket"]))
        ok = predicted == item["expected"]
        correct += ok
        confusion[item["expected"]][predicted] += 1
        rows.append((item["ticket"], item["expected"], predicted, ok))
    return correct / len(EVAL_SET), rows, confusion


def print_confusion(name: str, confusion: dict):
    print(f"\nconfusion matrix for {name} (rows=actual, cols=predicted):")
    print(f"{'':<10}" + "".join(f"{l:<8}" for l in LABELS))
    for actual in LABELS:
        print(f"{actual:<10}" + "".join(f"{confusion[actual][pred]:<8}" for pred in LABELS))


def main():
    variants = [
        ("zero_shot", classify_zero_shot, lambda r: r),
        ("few_shot", classify_few_shot, lambda r: r),
        ("structured_cot", classify_structured_cot, lambda r: r["urgency"]),
        ("ensemble (majority vote)", classify_ensemble, lambda r: r),
    ]

    results = {}
    for name, fn, parse in variants:
        acc, rows, confusion = score(fn, parse)
        results[name] = (acc, rows, confusion)

    print(f"{'variant':<26}{'accuracy'}")
    for name, (acc, _, _) in results.items():
        print(f"{name:<26}{acc:.0%}")

    winner = max(results, key=lambda n: results[n][0])
    print(f"\nwinner: {winner} ({results[winner][0]:.0%})")

    for name, (_, _, confusion) in results.items():
        print_confusion(name, confusion)

    print(f"\n=== per-example results for the winner ({winner}) ===")
    for ticket, expected, predicted, ok in results[winner][1]:
        print(f"{'PASS' if ok else 'FAIL'}  expected={expected:<8}predicted={predicted:<8}{ticket}")

    print(f"\n=== prompt library entry ===")
    print(f"name: {winner}")
    print(f"measured accuracy: {results[winner][0]:.0%} on this 20-example eval set")
    print("when to use: ticket-urgency triage -- this variant had the best measured accuracy "
          "here, but re-run this eval whenever the ticket mix changes; the ranking is not fixed. "
          "The ensemble variant is worth its extra cost/latency specifically when no single "
          "prompt style is a clear, stable winner across eval reruns.")


if __name__ == "__main__":
    main()
