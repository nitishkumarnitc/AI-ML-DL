"""Eval harness with a CI-style eval gate.

This is the flagship LLMOps feature of the project. It:

  1. Loads a labelled dataset (``evals/dataset.jsonl``).
  2. Runs the *real* agent over every case.
  3. Scores each answer with deterministic heuristics + an LLM judge.
  4. Aggregates a mean score and compares it to ``evals/baseline.json``.
  5. Exits non-zero if the mean regresses by more than ``EPSILON``.

Step 5 is the **eval gate**. Wired into CI (see ``.github/workflows/ci.yml``),
it blocks merges that regress answer quality — the same pattern used to keep
production LLM systems from silently degrading over time.

    python -m evals.run_evals
    python -m evals.run_evals --heuristics-only   # skip the LLM judge
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from evals.judges import heuristic_score, llm_as_judge

# Tolerance band so trivial run-to-run noise doesn't trip the gate.
EPSILON = 0.02

# Weights for combining the heuristic and judge scores into a per-case score.
_HEURISTIC_WEIGHT = 0.5
_JUDGE_WEIGHT = 0.5

_ROOT = Path(__file__).resolve().parent
DATASET_PATH = _ROOT / "dataset.jsonl"
BASELINE_PATH = _ROOT / "baseline.json"


def load_dataset(path: Path) -> list[dict]:
    """Load the JSONL eval dataset."""
    cases: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def load_baseline(path: Path) -> float:
    """Load the baseline mean score to gate against."""
    if not path.exists():
        return 0.0
    return float(json.loads(path.read_text(encoding="utf-8")).get("mean_score", 0.0))


def score_case(app, case: dict, use_judge: bool) -> dict:
    """Run the agent on one case and compute its combined score."""
    from src.app import answer_question

    answer = answer_question(app, case["question"])
    h_score, detail = heuristic_score(
        answer, case.get("must_include", []), case.get("must_not_include", [])
    )
    if use_judge:
        judged = llm_as_judge(case["question"], answer, case.get("reference", ""))
        j_score = (judged["faithfulness"] + judged["helpfulness"]) / 2
        case_score = _HEURISTIC_WEIGHT * h_score + _JUDGE_WEIGHT * j_score
    else:
        judged = {}
        case_score = h_score
    return {
        "id": case.get("id", "?"),
        "heuristic": h_score,
        "judge": (judged.get("faithfulness"), judged.get("helpfulness")) if judged else None,
        "score": case_score,
        "detail": detail,
        "answer": answer,
    }


def _print_table(rows: list[dict], use_judge: bool) -> None:
    header = f"{'id':<22}{'heuristic':>10}{'judge (f/h)':>16}{'score':>8}"
    print(header)
    print("-" * len(header))
    for row in rows:
        judge = "-"
        if use_judge and row["judge"]:
            judge = f"{row['judge'][0]:.2f}/{row['judge'][1]:.2f}"
        print(f"{row['id']:<22}{row['heuristic']:>10.2f}{judge:>16}{row['score']:>8.2f}")


def run(use_judge: bool) -> int:
    """Execute the full eval run and apply the gate. Returns a process exit code."""
    app = _build_app()
    cases = load_dataset(DATASET_PATH)
    rows = [score_case(app, case, use_judge) for case in cases]

    mean_score = sum(r["score"] for r in rows) / len(rows) if rows else 0.0
    baseline = load_baseline(BASELINE_PATH)

    print()
    _print_table(rows, use_judge)
    print("-" * 56)
    print(
        f"cases={len(rows)}  mean_score={mean_score:.3f}  "
        f"baseline={baseline:.3f}  epsilon={EPSILON}"
    )

    # ---- Eval gate ----------------------------------------------------------
    if mean_score < baseline - EPSILON:
        print(
            f"\nEVAL GATE FAILED: mean {mean_score:.3f} regressed below baseline "
            f"{baseline:.3f} (tolerance {EPSILON}). Failing the build."
        )
        return 1
    print(
        f"\nEVAL GATE PASSED: mean {mean_score:.3f} >= baseline "
        f"{baseline:.3f} - {EPSILON}."
    )
    # TODO: on an intentional, verified improvement, bump baseline.json so the
    #       gate locks in the new quality floor.
    return 0


def _build_app():
    """Build the agent app, ensuring the knowledge base is ingested."""
    from src.agent.graph import build_graph
    from src.agent.retrieval import get_retriever

    retriever = get_retriever()
    if retriever.count() == 0:
        retriever.ingest()
    return build_graph(retriever=retriever)


def _has_api_key() -> bool:
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    from src.agent.config import get_settings

    return bool(get_settings().anthropic_api_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the agent eval harness + gate.")
    parser.add_argument(
        "--heuristics-only",
        action="store_true",
        help="Skip the LLM judge (the agent itself still requires an API key).",
    )
    args = parser.parse_args()

    if not _has_api_key():
        # The harness runs the real agent, which needs a key. In CI this job
        # only runs when the secret is present (see the workflow), so this is a
        # convenience guard for local `make eval` runs.
        print(
            "No ANTHROPIC_API_KEY found. The eval harness runs the real agent and "
            "requires a key; skipping (this is expected without a key)."
        )
        return 0

    return run(use_judge=not args.heuristics_only)


if __name__ == "__main__":
    sys.exit(main())
