"""
Sample project — RL Environments & Infrastructure Engineer
Runs the SAME separate grader against three variants EACH of TWO different
environments -- because a real RL-environment engineer ships a portfolio of
tasks, not just one:

  Env 1: a reservation service -- a CONCURRENCY bug (race condition).
  Env 2: a payment service -- a LOGIC bug (idempotency, no concurrency
         involved at all -- it fails on a delayed retry interleaved with
         other traffic).

Both graders prove they catch a plausible-but-wrong fix that passes the
obvious single-case test but fails the deliberately adversarial one.

Run:  python run.py
      python run.py --env reservation     (just env 1)
      python run.py --env payment         (just env 2)
Dependencies:
  - threading, time (stdlib) -- concurrency test in env 1's grader
  - argparse (stdlib) -- CLI flag
  - (env*_buggy.py / env*_correct_fix.py / env*_wrong_fix.py / grader*.py are local modules, not packages)
"""
import argparse
import sys

import grader
import env_buggy
import env_correct_fix
import env_wrong_fix

import grader2
import env2_buggy
import env2_correct_fix
import env2_wrong_fix

RESERVATION_VARIANTS = [
    (env_buggy.ReservationService, "buggy (no bounds check)", False),
    (env_correct_fix.ReservationService, "correct fix", True),
    (env_wrong_fix.ReservationService, "wrong fix (mutate-then-revert, no lock)", False),
]

PAYMENT_VARIANTS = [
    (env2_buggy.PaymentService, "buggy (no idempotency handling)", False),
    (env2_correct_fix.PaymentService, "correct fix (remembers every key ever seen)", True),
    (env2_wrong_fix.PaymentService, "wrong fix (remembers only the last key)", False),
]


def run_environment(env_name: str, variants, grade_fn, report_fn) -> bool:
    print(f"\n{'#' * 70}\n# Environment: {env_name}\n{'#' * 70}")
    overall_ok = True
    for service_cls, label, expected_to_pass in variants:
        print(f"\n=== Grading: {label} ===")
        service = service_cls()
        checks = grade_fn(service)
        passed = report_fn(checks)
        correct_verdict = passed == expected_to_pass
        overall_ok &= correct_verdict
        print(f"-> grader verdict: {'PASS' if passed else 'FAIL'} "
              f"({'as expected' if correct_verdict else 'UNEXPECTED -- grader is not discriminating correctly!'})")
    return overall_ok


def main():
    parser = argparse.ArgumentParser(description="Grade multiple gradable environments")
    parser.add_argument("--env", choices=["reservation", "payment", "both"], default="both")
    args = parser.parse_args()

    overall_ok = True
    if args.env in ("reservation", "both"):
        overall_ok &= run_environment("reservation service (concurrency bug)",
                                       RESERVATION_VARIANTS, grader.grade, grader.report)
    if args.env in ("payment", "both"):
        overall_ok &= run_environment("payment service (idempotency logic bug)",
                                       PAYMENT_VARIANTS, grader2.grade, grader2.report)

    print(f"\n{'=' * 70}")
    print("Each grader must PASS only its correct fix and FAIL both the buggy version and the "
          "plausible-but-wrong one. That's the actual deliverable in this job -- not the fix "
          "itself, but a grader rigorous enough to tell them apart, across DIFFERENT bug classes.")
    if overall_ok:
        print("Result: every grader run discriminates correctly across all variants.")
    else:
        print("Result: at least one grader is NOT discriminating correctly -- see UNEXPECTED lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
