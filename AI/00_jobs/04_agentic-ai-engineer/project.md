# 04 · Sample project — Agentic AI Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- runs the real agent (now 4 tools) against a 10-task eval harness and prints the pass/fail table. `--verbose` shows every tool call live; `--log-file` dumps full JSON transcripts. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A small **tool-using agent** ("research assistant": calculator + note-lookup + mock web-search + unit converter) with short-term memory, retry-on-tool-failure logic, full transcript logging, and a **10-task eval harness** that scores it pass/fail — reliability proof, not just a demo.

## 🧠 Why this mirrors the real job
- "Design agent loops: planning, reasoning, tool/function calling, memory, reflection, retries" → every one of those is a named step below.
- "Make agents reliable in production: guardrails, evals... failure recovery" → the eval harness and retry logic *are* the job, not an afterthought.
- "Ship a real multi-step agent... with an eval harness proving reliability" is this repo's own "how to stand out" advice for this role — this project is exactly that.

## 🧰 Prerequisites
- Python + an LLM with function/tool calling (OpenAI, Anthropic, or a local model via Ollama that supports tool calls).
- ~4–6 hours.

## 🧰 Tools, libraries & skills used here
- **Pure Python stdlib** — the agent loop, tool dispatch, and retry logic are hand-written so the control flow (plan → act → observe → repeat) is fully visible, with no framework hiding the steps.
- **Design patterns**: a `TOOLS` registry (name → function), a retry wrapper with bounded attempts, and an eval harness that scores outcomes automatically instead of eyeballing transcripts.
- **What a real agent stack adds on top**: an actual LLM for planning (OpenAI/Anthropic function-calling, or a local model via Ollama), an orchestration framework (**LangGraph**, **CrewAI**, or the **OpenAI/Anthropic Agents SDK**) for more complex branching/looping, the **MCP** (Model Context Protocol) for standardized tool wiring across many tools, and tracing tools (**LangSmith**, **Langfuse**) to inspect long agent runs in production.
- **Core skill**: treating reliability as a first-class deliverable — the retry logic and eval harness *are* the engineering, not scaffolding around it.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| re (stdlib) | built in | parsing the mock planner's task text into tool calls |
| random (stdlib) | built in | seeding for reproducible runs |

## 🪜 Step-by-step

### 1. Define 2–3 tools
```python
def calculator(expression: str) -> str:
    try:
        return str(eval(expression, {"__builtins__": {}}))
    except Exception as e:
        return f"error: {e}"

NOTES = {"revenue_q1": "Revenue Q1 was $1.2M.", "revenue_q2": "Revenue Q2 was $1.5M."}

def note_lookup(key: str) -> str:
    return NOTES.get(key, "not found")

TOOLS = {"calculator": calculator, "note_lookup": note_lookup}
```

### 2. The agent loop — plan, call tool, observe, repeat
```python
import json

def run_agent(task: str, max_steps: int = 5, memory: list = None):
    memory = memory or []
    messages = [
        {"role": "system", "content": "You solve tasks step by step. Use tools when needed. "
                                       "When done, reply with FINAL: <answer>."},
        *memory,
        {"role": "user", "content": task},
    ]
    for step in range(max_steps):
        response = call_llm_with_tools(messages, list(TOOLS.keys()))  # your LLM client call
        if response.startswith("FINAL:"):
            return response.removeprefix("FINAL:").strip(), messages
        tool_name, tool_arg = parse_tool_call(response)  # your parsing logic
        result = call_tool_with_retry(tool_name, tool_arg)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "tool", "content": result})
    return "FAILED: max steps exceeded", messages
```

### 3. Retry logic for flaky tools
```python
def call_tool_with_retry(tool_name, arg, retries=2):
    for attempt in range(retries + 1):
        try:
            return TOOLS[tool_name](arg)
        except Exception as e:
            if attempt == retries:
                return f"tool '{tool_name}' failed after {retries+1} attempts: {e}"
```

### 4. Memory across turns
Keep the last N `(user, agent)` exchanges and pass them back into `memory` on the next call — enough to answer "what did I just ask you?" without unbounded context growth.

### 5. Build the eval harness — 5 tasks, scored automatically
```python
EVAL_TASKS = [
    {"task": "What was total revenue across Q1 and Q2?", "expects_substring": "2.7"},
    {"task": "Look up revenue_q1 and multiply it by 2.", "expects_substring": "2.4"},
    {"task": "What is revenue_q3?", "expects_substring": "not found"},  # tests honest failure
    {"task": "What is 17 * 23?", "expects_substring": "391"},
    {"task": "Look up revenue_q2, then add 100000 to it.", "expects_substring": "1.6"},
]

def run_eval():
    results = []
    for t in EVAL_TASKS:
        answer, trace = run_agent(t["task"])
        passed = t["expects_substring"] in answer
        results.append({"task": t["task"], "answer": answer, "passed": passed, "n_steps": len(trace)})
    pass_rate = sum(r["passed"] for r in results) / len(results)
    return pass_rate, results
```

### 6. Look at the failures, not just the score
For every failing task, read the message trace: did it call the wrong tool, misparse a result, or give up too early? That failure taxonomy is the actual engineering signal.

## ✅ Deliverable
- Agent code + `EVAL_TASKS` + a run showing pass rate (aim to explain, not just report, any failures).
- A short "failure modes" list: what broke, why, and the one change that would fix it.

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
[`05_multi-agent-frameworks`](../../05_multi-agent-frameworks/README.md) · [`13_langgraph`](../../13_langgraph/README.md) — real orchestration frameworks instead of a hand-rolled loop · [`15_mcp`](../../15_mcp/README.md) — standardized tool protocol · [`14_memory`](../../14_memory/README.md) · [`16_evals`](../../16_evals/README.md).
