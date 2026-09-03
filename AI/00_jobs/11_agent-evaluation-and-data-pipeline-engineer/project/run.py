"""
Sample project — Agent Evaluation & Data-Pipeline Engineer
An LLM-as-judge eval harness over 20 transcripts, validated against human
labels, comparing TWO judges side by side: a naive one (biased toward
confident-sounding phrasing -- a real, documented LLM-judge failure mode)
and an improved one (checks the actual reference first). Reports both raw
agreement AND Cohen's kappa (agreement corrected for chance), since raw
agreement alone can look deceptively high on an imbalanced label set.

Run:  python run.py
      python run.py --report-file eval_report.md
Dependencies:
  - collections.Counter (stdlib) -- grade-distribution summaries
  - argparse (stdlib) -- CLI flag
  - (no third-party packages -- swap naive_judge()/improved_judge() for real LLM-as-judge calls to go live)
"""
import argparse
from collections import Counter

# ---------------------------------------------------------------------------
# 20 agent transcripts: task, agent's answer, and the REFERENCE correct answer.
# ---------------------------------------------------------------------------
TRANSCRIPTS = [
    {"task": "What is 12 * 8?", "answer": "96", "reference": "96"},
    {"task": "What is 12 * 8?", "answer": "Definitely 92, I'm very confident.", "reference": "96"},
    {"task": "Capital of Australia?", "answer": "Sydney", "reference": "Canberra"},
    {"task": "Capital of Australia?", "answer": "Canberra", "reference": "Canberra"},
    {"task": "Is water wet?", "answer": "Yes, water is wet.", "reference": "yes"},
    {"task": "sum of 1..10", "answer": "The sum of 1 through 10 is clearly 60, no doubt.", "reference": "55"},
    {"task": "sum of 1..10", "answer": "55", "reference": "55"},
    {"task": "Largest planet?", "answer": "Jupiter, without question the largest.", "reference": "Jupiter"},
    {"task": "Largest planet?", "answer": "I think it might be Saturn?", "reference": "Jupiter"},
    {"task": "Boiling point of water at sea level (C)?", "answer": "100", "reference": "100"},
    {"task": "What is 7 * 6?", "answer": "42", "reference": "42"},
    {"task": "What is 7 * 6?", "answer": "Certainly 48, no doubt about it.", "reference": "42"},
    {"task": "Capital of Canada?", "answer": "Toronto", "reference": "Ottawa"},
    {"task": "Capital of Canada?", "answer": "Ottawa", "reference": "Ottawa"},
    {"task": "Freezing point of water (C)?", "answer": "0", "reference": "0"},
    {"task": "Smallest prime number?", "answer": "Clearly 1, obviously.", "reference": "2"},
    {"task": "Smallest prime number?", "answer": "2", "reference": "2"},
    {"task": "Number of continents?", "answer": "I think maybe 6?", "reference": "7"},
    {"task": "Number of continents?", "answer": "7", "reference": "7"},
    {"task": "Speed of light (km/s, approx)?", "answer": "Definitely 150,000, very sure.", "reference": "300000"},
]

HUMAN_LABELS = ["correct", "wrong", "wrong", "correct", "correct", "wrong",
                "correct", "correct", "wrong", "correct", "correct", "wrong",
                "wrong", "correct", "correct", "wrong", "correct", "wrong",
                "correct", "wrong"]

CONFIDENCE_WORDS = ["definitely", "clearly", "without question", "no doubt", "certain", "obviously"]
HEDGE_WORDS = ["might", "i think", "possibly", "not sure", "?", "maybe"]


def naive_judge(answer: str, reference: str) -> str:
    """Biased toward confident phrasing -- a real, documented failure mode:
    fluent, confident-sounding WRONG answers get over-rated."""
    text = answer.lower()
    ref_present = reference.lower() in text
    has_confidence = any(w in text for w in CONFIDENCE_WORDS)
    has_hedge = any(w in text for w in HEDGE_WORDS)
    if has_hedge:
        return "wrong"
    if ref_present:
        return "correct"
    if has_confidence:
        return "correct"  # BUG: fooled by confident tone alone
    return "wrong"


def improved_judge(answer: str, reference: str) -> str:
    """Checks the reference FIRST and ignores tone entirely -- the fix a
    real eval engineer makes once the naive judge's bias is caught."""
    return "correct" if reference.lower() in answer.lower() else "wrong"


def agreement_rate(human, judge):
    return sum(1 for h, j in zip(human, judge) if h == j) / len(human)


def cohens_kappa(human, judge, labels=("correct", "wrong")) -> float:
    """Agreement corrected for chance -- raw agreement alone can look good
    just because one label dominates the dataset. kappa=0 means no better
    than chance; kappa=1 means perfect agreement."""
    n = len(human)
    p_observed = agreement_rate(human, judge)
    p_chance = 0.0
    for label in labels:
        p_human = sum(1 for h in human if h == label) / n
        p_judge = sum(1 for j in judge if j == label) / n
        p_chance += p_human * p_judge
    if p_chance == 1.0:
        return 1.0
    return (p_observed - p_chance) / (1 - p_chance)


def run_judge(judge_fn):
    return [judge_fn(t["answer"], t["reference"]) for t in TRANSCRIPTS]


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge harness with two judges compared")
    parser.add_argument("--report-file", default=None, help="write the comparison to this markdown file")
    args = parser.parse_args()

    naive_judged = run_judge(naive_judge)
    improved_judged = run_judge(improved_judge)

    print(f"{'#':<3}{'task':<32}{'answer':<40}{'human':<9}{'naive':<9}{'improved'}")
    for i, (t, human, naive, improved) in enumerate(zip(TRANSCRIPTS, HUMAN_LABELS, naive_judged, improved_judged)):
        print(f"{i:<3}{t['task']:<32}{t['answer'][:38]:<40}{human:<9}{naive:<9}{improved}")

    naive_rate = agreement_rate(HUMAN_LABELS, naive_judged)
    naive_kappa = cohens_kappa(HUMAN_LABELS, naive_judged)
    improved_rate = agreement_rate(HUMAN_LABELS, improved_judged)
    improved_kappa = cohens_kappa(HUMAN_LABELS, improved_judged)

    print(f"\n{'judge':<12}{'raw agreement':<16}{'Cohen kappa'}")
    print(f"{'naive':<12}{naive_rate:<16.0%}{naive_kappa:.3f}")
    print(f"{'improved':<12}{improved_rate:<16.0%}{improved_kappa:.3f}")

    print("\n=== Disagreement analysis (naive judge) ===")
    for i, (t, human, judge) in enumerate(zip(TRANSCRIPTS, HUMAN_LABELS, naive_judged)):
        if human != judge:
            reason = ("judge over-trusted confident-but-wrong phrasing" if judge == "correct"
                       else "judge penalized hedged phrasing that was actually correct")
            print(f"- #{i} '{t['task']}': human={human}, judge={judge} -- {reason}")

    print("\n=== Dashboard summary (naive judge) ===")
    dist = Counter(naive_judged)
    for grade, n in dist.items():
        print(f"  {grade}: {n}/{len(naive_judged)} ({n/len(naive_judged):.0%})")

    verdict = ("SHIP the improved judge unsupervised" if improved_kappa >= 0.8 else
               "The improved judge is better but still verify a sample before trusting it fully.")
    print(f"\nVerdict: naive judge kappa={naive_kappa:.3f} (too low to trust unsupervised); "
          f"improved judge kappa={improved_kappa:.3f}. {verdict}")

    if args.report_file:
        lines = [
            "# Agent eval judge comparison\n",
            f"- naive judge: {naive_rate:.0%} raw agreement, kappa={naive_kappa:.3f}",
            f"- improved judge: {improved_rate:.0%} raw agreement, kappa={improved_kappa:.3f}\n",
            "| # | task | answer | human | naive | improved |",
            "|---|---|---|---|---|---|",
        ]
        for i, (t, human, naive, improved) in enumerate(zip(TRANSCRIPTS, HUMAN_LABELS, naive_judged, improved_judged)):
            lines.append(f"| {i} | {t['task']} | {t['answer']} | {human} | {naive} | {improved} |")
        with open(args.report_file, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\nreport written to {args.report_file}")


if __name__ == "__main__":
    main()
