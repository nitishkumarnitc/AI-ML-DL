"""
Sample project — RL Environment / Task Author (contract)
TWO vendor-style task submissions covering DIFFERENT bug classes -- because a
real contractor's portfolio isn't one task, it's a growing library:

  Task 1: auth bypass (deny-list vs allow-list logic bug).
  Task 2: path traversal (naive '..' string-matching vs resolved-path check).

Each task's grader proves it isn't fooled by a plausible-but-wrong patch that
would pass an obvious, narrow test.

Run:  python run.py
      python run.py --task auth        (just the auth-bypass task)
      python run.py --task path        (just the path-traversal task)
Dependencies:
  - sys, os, tempfile (stdlib) -- CLI exit code + real filesystem sandbox for task 2
  - argparse (stdlib) -- CLI flag
  - (env_*.py / grader*.py are local modules, not packages)
"""
import argparse
import sys

import grader
import env_buggy
import env_correct_fix
import env_wrong_fix

import grader_path
import env_path_buggy
import env_path_correct_fix
import env_path_wrong_fix

AUTH_VARIANTS = [
    (env_buggy.AccountService, "buggy (no auth check at all)", False),
    (env_correct_fix.AccountService, "correct fix (allow-list: caller_role == 'admin')", True),
    (env_wrong_fix.AccountService, "wrong fix (deny-list: blocks only 'user')", False),
]

PATH_VARIANTS = [
    (env_path_buggy.FileService, "buggy (no containment check at all)", False),
    (env_path_correct_fix.FileService, "correct fix (resolved-path containment check)", True),
    (env_path_wrong_fix.FileService, "wrong fix (blocks the '..' substring only)", False),
]


def run_task(task_name: str, variants, grade_fn, report_fn) -> bool:
    print(f"\n{'#' * 70}\n# Task: {task_name}\n{'#' * 70}")
    overall_ok = True
    for cls, label, expected_to_pass in variants:
        print(f"\n=== Grading: {label} ===")
        checks = grade_fn(cls) if grade_fn is grader_path.grade else grade_fn(cls())
        passed = report_fn(checks)
        correct_verdict = passed == expected_to_pass
        overall_ok &= correct_verdict
        print(f"-> grader verdict: {'PASS' if passed else 'FAIL'} "
              f"({'as expected' if correct_verdict else 'UNEXPECTED -- grader is not discriminating correctly!'})")
    return overall_ok


def main():
    parser = argparse.ArgumentParser(description="Grade multiple authored tasks")
    parser.add_argument("--task", choices=["auth", "path", "both"], default="both")
    args = parser.parse_args()

    with open("task.md") as f:
        print(f.read())

    overall_ok = True
    if args.task in ("auth", "both"):
        overall_ok &= run_task("auth bypass", AUTH_VARIANTS, grader.grade, grader.report)
    if args.task in ("path", "both"):
        overall_ok &= run_task("path traversal", PATH_VARIANTS, grader_path.grade, grader_path.report)

    print(f"\n{'=' * 70}\n=== Submission notes ===")
    print(
        "Task 1 (auth bypass):\n"
        "- Chose an auth-bypass bug class because it's common, realistic, and easy to verify.\n"
        "- Assumption (task brief was silent on this): case sensitivity of caller_role is not\n"
        "  in scope -- the correct fix treats 'Admin' as unauthorized, matching literal 'admin' only.\n"
        "- Deliberately NOT covered: concurrent balance updates from two admins at once.\n\n"
        "Task 2 (path traversal):\n"
        "- Chose path traversal as a second, DIFFERENT bug class to show breadth, not just depth\n"
        "  on one vulnerability type.\n"
        "- Assumption: symlinks inside base_dir that point outside it are out of scope for this\n"
        "  task -- a real hardened version would also need to resolve and check symlink targets.\n"
        "- Deliberately NOT covered: filename-length/encoding edge cases (null bytes, unicode\n"
        "  normalization tricks) -- flagged as a follow-up task, not silently ignored.\n"
    )

    if overall_ok:
        print("Result: every grader run discriminates correctly across all variants.")
    else:
        print("Result: at least one grader is NOT discriminating correctly -- see UNEXPECTED lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
