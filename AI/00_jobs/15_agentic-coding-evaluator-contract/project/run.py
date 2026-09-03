"""
Sample project -- Agentic Coding Evaluator (contract)
THREE coding tasks, each with TWO candidate "agent-generated" solutions
(one flawed, one correct) that get ACTUALLY EXECUTED -- not just read --
against a normal test and a deliberate edge case, catching a real runtime
failure or wrong result for each flawed candidate and naming which
code-hallucination pattern (see lesson 23_ai-coding-agents-and-code-eval,
lesson 2) it is.

Run:  python run.py
      python run.py --report-file comparison_report.md
Dependencies:
  - argparse (stdlib) -- CLI flag
  - exec() over fixed, hand-authored source strings -- no external input,
    no imports needed beyond stdlib
"""
import argparse

TASKS = [
    {
        "id": "T1",
        "name": "has_duplicates(items) -> bool",
        "fn_name": "has_duplicates",
        "spec": "Goal: return True if the list has any repeated value. "
                "Acceptance: correct on an empty list, a list with no dupes, "
                "AND a list with a duplicate.",
        "tests": [
            ("empty list", ([],), False, 1),
            ("no duplicates", ([1, 2, 3],), False, 1),
            ("EDGE: has a duplicate", ([1, 2, 2, 3],), True, 2),
        ],
        "candidates": {
            "A (flawed)": (
                "def has_duplicates(items):\n"
                "    return len(items) == len(set(items))\n"
            ),
            "B (good)": (
                "def has_duplicates(items):\n"
                "    return len(items) != len(set(items))\n"
            ),
        },
        "pattern_hint": "plausible-but-wrong logic (the comparison is backwards -- "
                        "it reads fine and passes the two easy cases, but is inverted)",
    },
    {
        "id": "T2",
        "name": "dedupe_orders(orders) -> list[dict], keep latest per id",
        "fn_name": "dedupe_orders",
        "spec": "Goal: given order dicts with 'id' and 'ts' keys, return one record "
                "per id -- the one with the highest 'ts'. "
                "Acceptance: correct on a normal list with a duplicate id, AND on an "
                "empty list.",
        "tests": [
            (
                "normal: duplicate id, keep highest ts",
                ([{"id": 1, "ts": 5}, {"id": 1, "ts": 9}, {"id": 2, "ts": 1}],),
                [{"id": 1, "ts": 9}, {"id": 2, "ts": 1}],
                1,
            ),
            ("EDGE: empty list", ([],), [], 2),
        ],
        "candidates": {
            "A (flawed)": (
                "def dedupe_orders(orders):\n"
                "    return orders.unique(key='id')\n"  # invented API: list has no .unique()
            ),
            "B (good)": (
                "def dedupe_orders(orders):\n"
                "    latest = {}\n"
                "    for o in orders:\n"
                "        if o['id'] not in latest or o['ts'] > latest[o['id']]['ts']:\n"
                "            latest[o['id']] = o\n"
                "    return list(latest.values())\n"
            ),
        },
        "pattern_hint": "invented API -- 'orders.unique(key=...)' is not a real list "
                        "method; this is the plain-Python analogue of inventing a "
                        "pandas/library kwarg that doesn't exist",
    },
    {
        "id": "T3",
        "name": "safe_average(numbers) -> float",
        "fn_name": "safe_average",
        "spec": "Goal: return the average of a list of numbers. "
                "Acceptance: correct on a normal non-empty list, AND returns 0.0 "
                "(never raises) on an empty list.",
        "tests": [
            ("normal list", ([2, 4, 6],), 4.0, 1),
            ("EDGE: empty list must not crash", ([],), 0.0, 2),
        ],
        "candidates": {
            "A (flawed)": (
                "def safe_average(numbers):\n"
                "    return sum(numbers) / len(numbers)\n"
            ),
            "B (good)": (
                "def safe_average(numbers):\n"
                "    if not numbers:\n"
                "        return 0.0\n"
                "    return sum(numbers) / len(numbers)\n"
            ),
        },
        "pattern_hint": "missed edge case -- correct on the happy path, but the "
                        "acceptance criteria explicitly required the empty-list case "
                        "and it was never tested for",
    },
]


def run_candidate(source: str, fn_name: str, args: tuple):
    """Actually EXECUTE the candidate source and call the function -- no guessing."""
    namespace = {}
    try:
        exec(source, namespace)          # nosec -- fixed, hand-authored strings only
        fn = namespace[fn_name]
        return {"ok": True, "result": fn(*args), "error": None}
    except Exception as exc:
        return {"ok": False, "result": None, "error": f"{type(exc).__name__}: {exc}"}


def grade_candidate(task, source: str):
    total, earned = 0, 0
    results = []
    for label, args, expected, points in task["tests"]:
        total += points
        outcome = run_candidate(source, task["fn_name"], args)
        if outcome["ok"] and outcome["result"] == expected:
            earned += points
            results.append((label, points, True, None))
        else:
            reason = outcome["error"] or f"expected {expected!r}, got {outcome['result']!r}"
            results.append((label, points, False, reason))
    return earned, total, results


def main():
    parser = argparse.ArgumentParser(description="Execution-based grading of AI-generated code candidates")
    parser.add_argument("--report-file", default=None, help="write the full comparison to this markdown file")
    args = parser.parse_args()

    report_lines = ["# Agentic coding evaluation report\n"]
    summary_rows = []

    for task in TASKS:
        print(f"=== {task['id']}: {task['name']} ===")
        print(f"spec: {task['spec']}\n")
        report_lines.append(f"## {task['id']}: {task['name']}\n")
        report_lines.append(f"Spec: {task['spec']}\n")

        task_grades = {}
        for label, source in task["candidates"].items():
            earned, total, results = grade_candidate(task, source)
            task_grades[label] = (earned, total)
            print(f"--- Candidate {label} --- grade: {earned}/{total}")
            report_lines.append(f"**Candidate {label}** -- {earned}/{total}\n")
            report_lines.append(f"```python\n{source.rstrip()}\n```\n")
            for test_label, points, passed, reason in results:
                mark = "PASS" if passed else "FAIL"
                pts = f"{points if passed else 0}/{points}"
                line = f"  [{mark}] ({pts}) {test_label}"
                if not passed:
                    line += f" -- {reason}"
                print(line)
                report_lines.append(f"- [{mark}] ({pts}) {test_label}" + (f" -- {reason}" if not passed else ""))
            if earned < total:
                note = (f"reviewer note: pattern = {task['pattern_hint']}. A developer "
                        f"trusting this candidate would ship it, then hit the failure "
                        f"above the first time the untested case occurs in production.")
                print(f"  {note}")
                report_lines.append(f"- {note}")
            print()
            report_lines.append("")

        summary_rows.append((task["id"], task["name"], task_grades))

    print("=== Summary ===")
    print(f"{'task':<6}{'candidate A':<14}{'candidate B':<14}")
    report_lines.append("## Summary\n\n| Task | Candidate A | Candidate B |\n|---|---|---|")
    for task_id, name, grades in summary_rows:
        a_earned, a_total = grades["A (flawed)"]
        b_earned, b_total = grades["B (good)"]
        print(f"{task_id:<6}{f'{a_earned}/{a_total}':<14}{f'{b_earned}/{b_total}':<14}")
        report_lines.append(f"| {task_id} ({name}) | {a_earned}/{a_total} | {b_earned}/{b_total} |")

    if args.report_file:
        with open(args.report_file, "w") as f:
            f.write("\n".join(report_lines) + "\n")
        print(f"\nreport written to {args.report_file}")


if __name__ == "__main__":
    main()
