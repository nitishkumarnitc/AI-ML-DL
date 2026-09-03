"""
Sample project — Domain SME / AI Data Contributor (contract)
FIVE hard questions ACROSS THREE domains (coding, personal finance,
statistics) -- proving the grading pattern really is domain-agnostic, not
just a coding trick -- each with a reference answer + a point-based rubric,
graded against two candidate answers (one good, one subtly wrong) with
reviewer-style feedback that flags exactly what's wrong and WHY it matters.

Run:  python run.py
      python run.py --report-file grading_report.md
Dependencies:
  - argparse (stdlib) -- CLI flag
  - (no imports needed beyond stdlib -- pure functions over the QUESTIONS/rubrics)
"""
import argparse

QUESTIONS = [
    {
        "id": "Q1", "domain": "coding",
        "question": "Is list.append() thread-safe in CPython? Explain why or why not.",
        "reference": "Yes -- CPython's GIL serializes bytecode execution, so no two "
                     "Python-level ops can interleave inside the single append operation. "
                     "This is a CPython implementation detail, not a language guarantee.",
        "rubric": [
            ("says thread-safe (not 'no')", 2,
             lambda a: "thread-safe" in a.lower() or ("yes" in a.lower()[:20])),
            ("attributes it to the GIL specifically (not a per-object lock)", 2,
             lambda a: "gil" in a.lower() and "lock" not in a.lower().split("gil")[0][-30:]),
            ("notes this is CPython-specific, not a language guarantee", 1,
             lambda a: "cpython" in a.lower()),
        ],
        "candidates": {
            "A (flawed)": "Yes, thread-safe, because Python lists have an internal lock "
                          "per list object that prevents concurrent access.",
            "B (good)": "Yes. CPython's GIL means only one thread executes bytecode at a "
                       "time, so append() can't be interleaved. This is a CPython detail, "
                       "not something the language spec guarantees.",
        },
    },
    {
        "id": "Q2", "domain": "coding",
        "question": "Why can datetime.now() cause subtly non-reproducible test failures?",
        "reference": "Because it returns the real wall-clock time, which changes between "
                     "runs (and can cross midnight/DST boundaries), making assertions "
                     "based on it flaky. Fix: inject/mock the clock instead of calling it directly.",
        "rubric": [
            ("identifies the real-time / non-determinism as the cause", 2,
             lambda a: "real" in a.lower() or "wall" in a.lower() or "changes" in a.lower()),
            ("mentions a boundary case (midnight/DST/timezone)", 1,
             lambda a: any(w in a.lower() for w in ["midnight", "dst", "timezone", "boundary"])),
            ("proposes mocking/injecting the clock as the fix", 2,
             lambda a: "mock" in a.lower() or "inject" in a.lower() or "fixed clock" in a.lower()),
        ],
        "candidates": {
            "A (flawed)": "datetime.now() is slow, so tests time out randomly on slower machines.",
            "B (good)": "It returns real wall-clock time, which is different every run and can "
                       "cross a midnight or DST boundary, breaking time-based assertions. Mock "
                       "the clock (inject a fixed datetime) instead of calling now() directly.",
        },
    },
    {
        "id": "Q3", "domain": "coding",
        "question": "What's wrong with catching `except Exception` broadly in a retry loop "
                    "around a network call?",
        "reference": "It retries errors that should never be retried (e.g. auth failures, "
                     "bad request/4xx, programming errors like TypeError), wasting time/quota "
                     "and hiding real bugs. Catch the specific transient exceptions instead "
                     "(timeouts, connection errors) and let others propagate.",
        "rubric": [
            ("notes it retries errors that shouldn't be retried", 2,
             lambda a: "retr" in a.lower() and ("shouldn't" in a.lower() or "should not" in a.lower()
                                                  or "4xx" in a.lower() or "auth" in a.lower())),
            ("gives a concrete example of a non-retryable error", 1,
             lambda a: any(w in a.lower() for w in ["4xx", "auth", "typeerror", "bad request", "valueerror"])),
            ("recommends catching specific transient exceptions instead", 2,
             lambda a: "specific" in a.lower() or "timeout" in a.lower() or "connectionerror" in a.lower()),
        ],
        "candidates": {
            "A (flawed)": "Nothing really -- catching Exception broadly is safer because you "
                          "never miss an error, so the retry loop is more robust.",
            "B (good)": "It retries things that should never be retried, like a 401 auth error "
                       "or a TypeError from a bug -- wasting retries and hiding real problems. "
                       "Catch specific transient errors (TimeoutError, ConnectionError) instead.",
        },
    },
    {
        "id": "Q4", "domain": "personal finance",
        "question": "Why is it misleading to compare a savings account's APR directly against "
                    "another account's APY when deciding where to put your money?",
        "reference": "APY already factors in the effect of compounding within the year, while "
                     "APR does not. Comparing them directly makes the APR-quoted account look "
                     "artificially worse (or the APY one artificially better) even if the "
                     "underlying nominal rates are similar. You have to convert both to the "
                     "same basis (both APY, or both APR) before comparing.",
        "rubric": [
            ("correctly distinguishes APY (includes compounding) from APR (does not)", 2,
             lambda a: "compound" in a.lower()),
            ("says you must convert to the same basis before comparing", 2,
             lambda a: "same basis" in a.lower() or "convert" in a.lower() or "apples" in a.lower()),
            ("names the practical risk: picking the worse account by mistake", 1,
             lambda a: "worse account" in a.lower() or "by mistake" in a.lower()),
        ],
        "candidates": {
            "A (flawed)": "It's not really misleading -- APR and APY are basically two names "
                          "for the same interest rate, so you can compare them directly.",
            "B (good)": "APY already includes the effect of compounding, but APR doesn't, so "
                       "comparing them directly isn't apples-to-apples -- convert both to the "
                       "same basis first, or you might pick the worse account by mistake.",
        },
    },
    {
        "id": "Q5", "domain": "statistics",
        "question": "Why doesn't a low p-value necessarily mean a study's result is practically "
                    "important?",
        "reference": "A p-value only measures statistical significance -- how unlikely the "
                     "observed effect would be if there were truly no effect. It says nothing "
                     "about the SIZE of the effect. With a large enough sample, even a "
                     "trivially small, practically meaningless effect can produce a very low "
                     "p-value. You also need the effect size (and its confidence interval), "
                     "not just the p-value, to judge practical importance.",
        "rubric": [
            ("distinguishes statistical significance from practical/effect-size significance", 2,
             lambda a: "effect size" in a.lower() or "practical" in a.lower()),
            ("notes large sample sizes can make trivial effects statistically significant", 2,
             lambda a: "sample size" in a.lower() or "large sample" in a.lower() or "large enough sample" in a.lower()),
            ("recommends looking at effect size/confidence interval, not just the p-value", 1,
             lambda a: "confidence interval" in a.lower() or "effect size" in a.lower()),
        ],
        "candidates": {
            "A (flawed)": "It does mean the result is important -- a low p-value means the "
                          "effect is real and large, so a p-value of 0.001 is a bigger deal "
                          "than a p-value of 0.04.",
            "B (good)": "A p-value only reflects statistical significance, not effect size -- "
                       "with a large enough sample, even a tiny, practically meaningless effect "
                       "can hit a very low p-value. You need the effect size and its confidence "
                       "interval to judge whether it actually matters.",
        },
    },
]


def grade_answer(rubric, answer: str):
    results = []
    total, earned = 0, 0
    for description, points, check in rubric:
        total += points
        passed = check(answer)
        earned += points if passed else 0
        results.append((description, points, passed))
    return earned, total, results


def main():
    parser = argparse.ArgumentParser(description="Rubric-based grading across 3 domains")
    parser.add_argument("--report-file", default=None, help="write the graded report to this markdown file")
    args = parser.parse_args()

    report_lines = ["# Domain SME grading report\n"]
    summary_rows = []
    for q in QUESTIONS:
        print(f"=== {q['id']} [{q['domain']}]: {q['question']} ===")
        print(f"reference: {q['reference']}\n")
        report_lines.append(f"## {q['id']} [{q['domain']}]: {q['question']}\n")
        report_lines.append(f"Reference: {q['reference']}\n")
        for label, answer in q["candidates"].items():
            earned, total, results = grade_answer(q["rubric"], answer)
            print(f"--- Candidate {label} ---")
            print(f"answer: {answer}")
            print(f"grade: {earned}/{total}")
            report_lines.append(f"**Candidate {label}** -- {earned}/{total}\n> {answer}\n")
            for description, points, passed in results:
                mark = "PASS" if passed else "FAIL"
                pts = f"{points if passed else 0}/{points}"
                print(f"  [{mark}] ({pts}) {description}")
                report_lines.append(f"- [{mark}] ({pts}) {description}")
            if earned < total:
                missed = [d for d, _, p in results if not p]
                note = (f"missing {', '.join(missed)} means a reader trusting this answer could "
                        f"act on the wrong mechanism/fix -- that's the actual risk, not just losing points.")
                print(f"  reviewer note: {note}")
                report_lines.append(f"- reviewer note: {note}")
            print()
            report_lines.append("")
            summary_rows.append((q["id"], q["domain"], label, earned, total))

    print("=== Summary ===")
    print(f"{'question':<8}{'domain':<18}{'candidate':<16}{'grade'}")
    report_lines.append("## Summary\n\n| Question | Domain | Candidate | Grade |\n|---|---|---|---|")
    for qid, domain, label, earned, total in summary_rows:
        print(f"{qid:<8}{domain:<18}{label:<16}{earned}/{total}")
        report_lines.append(f"| {qid} | {domain} | {label} | {earned}/{total} |")

    if args.report_file:
        with open(args.report_file, "w") as f:
            f.write("\n".join(report_lines) + "\n")
        print(f"\nreport written to {args.report_file}")


if __name__ == "__main__":
    main()
