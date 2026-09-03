"""
Sample project -- Member of Technical Staff, Frontier AI (Research/Data Quality Lead)

PART 1 -- Ops-to-research translation: tag raw, free-text ops notes against
candidate hypothesis categories and count hits, so a real recurring pattern
(multiple independent notes) is visible against a one-off anecdote.

PART 2 -- Research signal judgment / quality gate: run FIVE research claims
through a four-check trustworthiness gate (sample size, annotator agreement,
contamination, reproducibility) and print a hard STRONG/BLOCKED verdict with
a specific, falsifiable next step for every failing check.

Run:  python run.py
      python run.py --report-file signal_gate_report.md
Dependencies:
  - argparse (stdlib) -- CLI flag
  - (no imports needed beyond stdlib -- pure keyword matching + rule checks)
"""
import argparse

# --------------------------------------------------------------------------
# PART 1 -- ops-to-research translation
# --------------------------------------------------------------------------

OPS_NOTES = [
    "agent gave a confident wrong total after combining 3 spreadsheet formulas",
    "user said the multi-step calculation was wrong but the agent sounded very sure",
    "agent lost track of the running total across several linked cells",
    "response was slow but otherwise fine, no correctness issue",
    "agent refused to answer a simple one-step lookup, seemed overly cautious",
    "agent confidently miscalculated a value that depended on two prior steps",
    "agent was hesitant and asked for confirmation on an easy single-step question",
]

CATEGORY_KEYWORDS = {
    "multi-hop value tracking": ["multi-step", "combining", "linked cells", "two prior steps", "running total"],
    "overcautious on simple tasks": ["refused", "overly cautious", "hesitant", "single-step"],
    "latency / performance": ["slow"],
}


def tag_note(note: str):
    lower = note.lower()
    hits = [category for category, kws in CATEGORY_KEYWORDS.items() if any(kw in lower for kw in kws)]
    return hits or ["uncategorized"]


def cluster_ops_notes(notes):
    counts = {}
    assignments = []
    for note in notes:
        categories = tag_note(note)
        assignments.append((note, categories))
        for c in categories:
            counts[c] = counts.get(c, 0) + 1
    return counts, assignments


# --------------------------------------------------------------------------
# PART 2 -- research signal judgment / quality gate
# --------------------------------------------------------------------------

class Check:
    def __init__(self, name, passed, detail, next_step=None):
        self.name = name
        self.passed = passed
        self.detail = detail
        self.next_step = next_step


def check_sample_size(report):
    ok = report["sample_size"] >= report["min_sample_required"]
    detail = f"{report['sample_size']} vs required minimum {report['min_sample_required']}"
    return Check("sample_size", ok, detail,
                 None if ok else f"collect samples up to the minimum of {report['min_sample_required']} before repeating this claim")


def check_agreement(report):
    ok = report["annotator_agreement"] >= report["agreement_threshold"]
    detail = f"{report['annotator_agreement']:.0%} vs threshold {report['agreement_threshold']:.0%}"
    return Check("annotator_agreement", ok, detail,
                 None if ok else "have a second SME re-grade the disputed subset; the rubric wording is the likely culprit, not the model")


def check_contamination(report):
    ok = not report["contamination_risk"]
    detail = "no leakage risk found" if ok else "flagged as possible leakage, not yet cleared"
    return Check("contamination", ok, detail,
                 None if ok else "re-test against a decontaminated / freshly authored sample before trusting this number")


def check_reproducibility(report):
    state = report["reproduced_fresh_sample"]
    ok = state is True
    if state is False:
        detail = "did not reproduce on a fresh held-out sample"
    elif state is None:
        detail = "not yet tested on a fresh sample"
    else:
        detail = "reproduced on a fresh held-out sample"
    return Check("reproducibility", ok, detail,
                 None if ok else "re-run on a fresh, held-out sample before trusting this number")


def evaluate_signal(report):
    checks = [check_sample_size(report), check_agreement(report),
              check_contamination(report), check_reproducibility(report)]
    verdict = "STRONG" if all(c.passed for c in checks) else "BLOCKED"
    return verdict, checks


CLAIMS = [
    {
        "id": "C1",
        "claim": "Agent fails multi-hop spreadsheet tasks 60% of the time",
        "sample_size": 8, "min_sample_required": 30,
        "annotator_agreement": 0.95, "agreement_threshold": 0.85,
        "contamination_risk": False,
        "reproduced_fresh_sample": None,
    },
    {
        "id": "C2",
        "claim": "New guardrail reduces unsafe outputs by 40% on the safety eval set",
        "sample_size": 500, "min_sample_required": 100,
        "annotator_agreement": 0.55, "agreement_threshold": 0.85,
        "contamination_risk": False,
        "reproduced_fresh_sample": True,
    },
    {
        "id": "C3",
        "claim": "Model scores 92% on the new coding benchmark, beating the prior release",
        "sample_size": 200, "min_sample_required": 100,
        "annotator_agreement": 0.90, "agreement_threshold": 0.85,
        "contamination_risk": True,
        "reproduced_fresh_sample": True,
    },
    {
        "id": "C4",
        "claim": "Agentic tool-use success rate improved 15pp after the new planner prompt",
        "sample_size": 150, "min_sample_required": 100,
        "annotator_agreement": 0.88, "agreement_threshold": 0.85,
        "contamination_risk": False,
        "reproduced_fresh_sample": True,
    },
    {
        "id": "C5",
        "claim": "Refusal rate on out-of-scope medical questions is now near-zero",
        "sample_size": 40, "min_sample_required": 100,
        "annotator_agreement": 0.70, "agreement_threshold": 0.85,
        "contamination_risk": False,
        "reproduced_fresh_sample": False,
    },
]


def main():
    parser = argparse.ArgumentParser(description="Ops-to-research clustering + research signal-judgment quality gate")
    parser.add_argument("--report-file", default=None, help="write the full report to this markdown file")
    args = parser.parse_args()

    report_lines = ["# Ops-to-research translation & signal-judgment report\n"]

    # --- Part 1 ---
    print("=== Part 1: Ops-to-research translation (pattern clustering) ===\n")
    report_lines.append("## Part 1 — Ops-signal clustering\n")
    counts, assignments = cluster_ops_notes(OPS_NOTES)
    for note, categories in assignments:
        print(f"  note: \"{note}\"")
        print(f"    -> {', '.join(categories)}")
        report_lines.append(f"- \"{note}\" -> {', '.join(categories)}")
    print("\n  Category counts (>=2 independent hits = candidate research pattern):")
    report_lines.append("\n**Category counts** (>=2 independent hits = candidate research pattern):\n")
    for category, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        flag = " <- PATTERN, worth structuring into an eval category" if count >= 2 else " (anecdote, not yet a pattern)"
        print(f"    {category:<32}{count}{flag}")
        report_lines.append(f"- {category}: {count}{flag}")
    print()
    report_lines.append("")

    # --- Part 2 ---
    print("=== Part 2: Research signal-judgment quality gate ===\n")
    report_lines.append("## Part 2 — Signal-judgment quality gate\n")
    summary_rows = []
    for report in CLAIMS:
        verdict, checks = evaluate_signal(report)
        print(f"--- {report['id']}: {report['claim']} ---")
        print(f"Verdict: {verdict}")
        report_lines.append(f"### {report['id']}: {report['claim']}\n")
        report_lines.append(f"**Verdict: {verdict}**\n")
        failing = []
        for c in checks:
            mark = "PASS" if c.passed else "FAIL"
            print(f"  [{mark}] {c.name}: {c.detail}")
            report_lines.append(f"- [{mark}] {c.name}: {c.detail}")
            if not c.passed:
                failing.append(c.name)
        if verdict == "BLOCKED":
            print("  Next steps:")
            report_lines.append("- Next steps:")
            for c in checks:
                if c.next_step:
                    print(f"    - {c.next_step}")
                    report_lines.append(f"  - {c.next_step}")
        print()
        report_lines.append("")
        summary_rows.append((report["id"], report["claim"], verdict, failing))

    print("=== Summary ===")
    print(f"{'claim':<6}{'verdict':<10}{'failing checks'}")
    report_lines.append("## Summary\n\n| Claim | Verdict | Failing checks |\n|---|---|---|")
    for claim_id, claim, verdict, failing in summary_rows:
        print(f"{claim_id:<6}{verdict:<10}{', '.join(failing) or '-'}")
        report_lines.append(f"| {claim_id} ({claim}) | {verdict} | {', '.join(failing) or '-'} |")

    if args.report_file:
        with open(args.report_file, "w") as f:
            f.write("\n".join(report_lines) + "\n")
        print(f"\nreport written to {args.report_file}")


if __name__ == "__main__":
    main()
