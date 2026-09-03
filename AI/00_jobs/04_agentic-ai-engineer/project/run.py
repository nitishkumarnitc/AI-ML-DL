"""
Sample project — Agentic AI Engineer
A small tool-using agent with FOUR tools (calculator, note lookup, a mock
web-search, and a unit converter), retry-on-tool-failure, short-term memory,
a 10-task eval harness scored pass/fail, and full JSON transcript logging --
the actual debugging artifact agent engineers rely on when a task fails in a
way that isn't obvious from the final answer alone.

The "LLM" here is a deterministic MOCK_PLANNER so the whole thing runs
instantly, offline, with no API key. Swap `call_llm` for a real OpenAI/
Anthropic/local model call and keep everything else (the loop, retries,
eval harness, transcript logging) unchanged -- that's the actual point of
this project: the *harness* is what's real.

Run:  python run.py
      python run.py --verbose                 (print each tool call as it happens)
      python run.py --log-file transcripts.json  (persist full traces for debugging)
Dependencies:
  - re (stdlib) -- parsing task text into tool-call decisions
  - random (stdlib) -- reproducible seeding
  - json (stdlib) -- transcript export
  - argparse (stdlib) -- CLI flags
  - (no third-party packages -- swap call sites for openai/anthropic SDKs to go live)
"""
import argparse
import json
import random
import re

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
NOTES = {"revenue_q1": 1.2, "revenue_q2": 1.5}
_flaky_calls = {"count": 0}

WEB_SEARCH_KB = {
    "population of france": "France's population is about 68 million.",
    "capital of japan": "The capital of Japan is Tokyo.",
    "speed of light": "The speed of light is about 299,792 km/s.",
}

UNIT_CONVERSIONS = {
    ("km", "miles"): lambda v: v * 0.621371,
    ("miles", "km"): lambda v: v / 0.621371,
    ("kg", "lbs"): lambda v: v * 2.20462,
    ("lbs", "kg"): lambda v: v / 2.20462,
    ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
    ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
}


def calculator(expression: str) -> str:
    try:
        return str(round(eval(expression, {"__builtins__": {}}), 4))
    except Exception as e:
        return f"error: {e}"


def note_lookup(key: str) -> str:
    # Deliberately flaky on the very first call ever, to exercise retry logic.
    _flaky_calls["count"] += 1
    if _flaky_calls["count"] == 1:
        raise ConnectionError("simulated transient lookup failure")
    if key not in NOTES:
        return "not found"
    return f"{NOTES[key]}"


def web_search(query: str) -> str:
    key = query.lower().strip()
    for k, v in WEB_SEARCH_KB.items():
        if k in key:
            return v
    return "no results found"


def unit_convert(arg: str) -> str:
    """arg format: 'value,from_unit,to_unit' e.g. '10,km,miles'"""
    try:
        value_s, from_u, to_u = [a.strip() for a in arg.split(",")]
        fn = UNIT_CONVERSIONS.get((from_u.lower(), to_u.lower()))
        if fn is None:
            return f"error: no conversion for {from_u} -> {to_u}"
        return f"{round(fn(float(value_s)), 3)} {to_u}"
    except Exception as e:
        return f"error: {e}"


TOOLS = {"calculator": calculator, "note_lookup": note_lookup,
          "web_search": web_search, "unit_convert": unit_convert}

_retry_log = []


def call_tool_with_retry(name, arg, retries=2):
    for attempt in range(retries + 1):
        try:
            result = TOOLS[name](arg)
            if attempt > 0:
                _retry_log.append((name, arg, attempt))
            return result, True
        except Exception as e:
            if attempt == retries:
                return f"tool '{name}' failed after {retries + 1} attempts: {e}", False


# ---------------------------------------------------------------------------
# Mock "LLM" planner -- swap this for a real call_llm(messages) in production.
# ---------------------------------------------------------------------------
KEY_ALIASES = {"q1": "revenue_q1", "q2": "revenue_q2", "q3": "revenue_q3"}


def mock_planner(task: str, fetched: dict):
    t = task.lower()

    # 1. unit conversion tasks
    m = re.search(r"convert\s+([\d.]+)\s*(km|miles|kg|lbs|celsius|fahrenheit)\s+to\s+(km|miles|kg|lbs|celsius|fahrenheit)", t)
    if m and "unit_convert_done" not in fetched:
        return ("TOOL", "unit_convert", f"{m.group(1)},{m.group(2)},{m.group(3)}")

    # 2. web search tasks
    if any(kw in t for kw in ["population of", "capital of", "speed of light"]) and "web_search_done" not in fetched:
        return ("TOOL", "web_search", task)

    # 3. revenue lookup + arithmetic tasks
    mentioned_keys = set()
    for alias, key in KEY_ALIASES.items():
        if alias in t or key in t:
            mentioned_keys.add(key)
    if "revenue_q3" in t or "revenue for q3" in t:
        mentioned_keys.add("revenue_q3")

    missing = [k for k in mentioned_keys if k not in fetched]
    if missing:
        return ("TOOL", "note_lookup", missing[0])

    if mentioned_keys:
        values = [str(fetched[k]) for k in sorted(mentioned_keys) if fetched[k] != "not found"]
        if not values:
            return ("FINAL", "not found")
        expr = values[0] if len(mentioned_keys) == 1 else " + ".join(values)
        m2 = re.search(r"multiply.*?by\s+(\d+)", task, re.I)
        if m2:
            expr = f"({expr}) * {m2.group(1)}"
        m3 = re.search(r"add\s+(\d+)", task, re.I)
        if m3:
            expr = f"({expr}) + {m3.group(1)}"
        return ("TOOL", "calculator", expr)

    # 4. plain arithmetic
    if re.match(r"^\s*[\d\.\s\+\-\*/\(\)]+\s*$", task):
        return ("TOOL", "calculator", task.strip().rstrip("?").strip())

    return ("FINAL", "I don't have enough information to answer that.")


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
def run_agent(task: str, max_steps: int = 6, verbose: bool = False):
    fetched = {}
    trace = []
    for step in range(max_steps):
        decision = mock_planner(task, fetched)
        action = decision[0]
        if action == "FINAL":
            if verbose:
                print(f"    step {step}: FINAL -> {decision[1]}")
            return decision[1], trace
        _, name, arg = decision
        result, ok = call_tool_with_retry(name, arg)
        if verbose:
            print(f"    step {step}: {name}({arg!r}) -> {result!r} (ok={ok})")
        trace.append({"step": step, "tool": name, "arg": arg, "result": result, "ok": ok})
        if name == "note_lookup":
            fetched[arg] = result if ok else "not found"
        elif name == "web_search":
            fetched["web_search_done"] = True
            return result, trace
        elif name == "unit_convert":
            fetched["unit_convert_done"] = True
            return result, trace
        elif name == "calculator":
            return result, trace
    return "FAILED: max steps exceeded", trace


# ---------------------------------------------------------------------------
# Eval harness -- 10 tasks covering all four tools, scored automatically
# ---------------------------------------------------------------------------
EVAL_TASKS = [
    {"task": "What was total revenue across Q1 and Q2?", "expects_substring": "2.7"},
    {"task": "Look up revenue_q1 and multiply it by 2.", "expects_substring": "2.4"},
    {"task": "What is revenue_q3?", "expects_substring": "not found"},
    {"task": "17 * 23", "expects_substring": "391"},
    {"task": "Look up revenue_q2, then add 1 to it.", "expects_substring": "2.5"},
    {"task": "What is the population of France?", "expects_substring": "68 million"},
    {"task": "What is the capital of Japan?", "expects_substring": "Tokyo"},
    {"task": "convert 10 km to miles", "expects_substring": "6.214"},
    {"task": "convert 100 celsius to fahrenheit", "expects_substring": "212"},
    {"task": "convert 5 kg to lbs", "expects_substring": "11.023"},
]


def run_eval(verbose: bool = False):
    results = []
    for t in EVAL_TASKS:
        if verbose:
            print(f"\n  task: {t['task']}")
        answer, trace = run_agent(t["task"], verbose=verbose)
        passed = t["expects_substring"] in str(answer)
        results.append({"task": t["task"], "answer": answer, "passed": passed,
                         "n_steps": len(trace), "trace": trace})
    return results


def main():
    parser = argparse.ArgumentParser(description="Tool-using agent + eval harness")
    parser.add_argument("--verbose", action="store_true", help="print every tool call as it happens")
    parser.add_argument("--log-file", default=None, help="write full JSON transcripts to this path")
    args = parser.parse_args()

    random.seed(0)
    print(f"tools available: {', '.join(TOOLS)}\n")
    results = run_eval(verbose=args.verbose)

    print(f"\n{'#':<3}{'task':<45}{'answer':<14}{'steps':<7}{'pass'}")
    for i, r in enumerate(results):
        print(f"{i:<3}{r['task']:<45}{str(r['answer'])[:12]:<14}{r['n_steps']:<7}{'PASS' if r['passed'] else 'FAIL'}")

    pass_rate = sum(r["passed"] for r in results) / len(results)
    print(f"\npass rate: {pass_rate:.0%}  ({sum(r['passed'] for r in results)}/{len(results)})")

    if _retry_log:
        for name, arg, attempt in _retry_log:
            print(f"\nNote: tool '{name}({arg})' failed on its first call (simulated transient "
                  f"error) and succeeded on retry attempt {attempt} -- the retry logic caught it "
                  f"transparently, which is why that task still passed.")

    if args.log_file:
        with open(args.log_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nfull transcripts (every tool call, argument, and result) written to {args.log_file} "
              f"-- this is the artifact you'd actually attach to a bug report when a task fails "
              f"in a way the final answer alone doesn't explain.")


if __name__ == "__main__":
    main()
