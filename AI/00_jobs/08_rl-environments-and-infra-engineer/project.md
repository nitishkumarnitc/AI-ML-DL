# 08 · Sample project — RL Environments & Infrastructure Engineer

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- grades TWO different environments (a concurrency bug and an idempotency logic bug), three variants each, and prints PASS/FAIL per check. `--env reservation`/`--env payment` runs just one. See [`project/`](project/) for the full source.

## 🎯 What you'll build
One **gradable environment**: a tiny buggy Flask API, a task spec, and a grader script that is kept **separate from the environment** and proven not to be gameable by a wrong-but-plausible-looking fix.

## 🧠 Why this mirrors the real job
- "Recreate real products... faithfully; expose via OpenAPI + MCP" → a small real-feeling product (an API with a real bug), not a puzzle.
- "Write rigorous, separated graders" → the grader lives in its own file/process and never trusts anything the "agent" says about itself.
- "Capture trajectories; run models; analyze failures" → you'll run two candidate patches through the grader and inspect why one fails.

This condenses the full walkthrough in [Lesson 8 of the RL-environments module](../../10_rl-environments-and-infra/08-build-your-first-gradable-environment.md) — read that for the deeper version.

## 🧰 Prerequisites
- Python, Flask, `pytest`, `requests`.
- ~4–6 hours.

## 🧰 Tools, libraries & skills used here
- **Python `threading`** — used deliberately to expose a real race-condition window (a slow "downstream call" simulated with `time.sleep`), which is exactly how race conditions get demonstrated and caught in practice.
- **Black-box grading discipline**: the grader only ever calls the public interface and inspects observable results, never reads or trusts the candidate's source code — the core rule of writing evaluations that can't be gamed.
- **Environment/grader separation**: three interchangeable service implementations (`env_buggy`, `env_correct_fix`, `env_wrong_fix`) graded by one unchanged `grader.py` — the actual architecture of an RL training environment.
- **What a real environment adds on top**: the service would be exposed over **HTTP** (Flask/FastAPI) and packaged in a **Docker** container for isolation and reproducibility, orchestrated with **Kubernetes** or a job queue to run thousands of episodes in parallel, with **pytest**-style structured grader output and CI (GitHub Actions) running the grader on every submitted task.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| threading (stdlib) | built in | firing a concurrent request to expose the race-condition window |
| time (stdlib) | built in | the artificial delay that simulates a slow downstream call |

## 🪜 Step-by-step

### 1. Build the environment: a small API with a real, specific bug
```python
# env/app.py
from flask import Flask, request, jsonify
app = Flask(__name__)
INVENTORY = {"widget": 10, "gadget": 3}

@app.route("/reserve", methods=["POST"])
def reserve():
    item = request.json["item"]
    qty = request.json["qty"]
    # BUG: no check that qty <= INVENTORY[item] — allows negative stock
    INVENTORY[item] -= qty
    return jsonify({"remaining": INVENTORY[item]})
```

### 2. Write the task spec (what the agent is told)
```markdown
# task.md
Fix `/reserve` in env/app.py so it never allows an item's stock to go negative.
On an over-reservation, return HTTP 400 with {"error": "insufficient stock"} and
leave INVENTORY unchanged. Do not change the response shape for valid requests.
```

### 3. Write the grader — separate file, black-box, never reads the agent's reasoning
```python
# grader/grade.py
import subprocess, time, requests, sys

def start_server():
    proc = subprocess.Popen(["python", "env/app.py"])
    time.sleep(1)
    return proc

def grade():
    proc = start_server()
    try:
        checks = []
        r = requests.post("http://localhost:5000/reserve", json={"item": "gadget", "qty": 100})
        checks.append(("rejects over-reservation", r.status_code == 400))
        r2 = requests.get("http://localhost:5000/reserve")  # or a debug endpoint you add
        checks.append(("stock unchanged after rejection", True))  # implement the real check
        r3 = requests.post("http://localhost:5000/reserve", json={"item": "widget", "qty": 2})
        checks.append(("valid request still works", r3.status_code == 200))
    finally:
        proc.terminate()

    passed = all(ok for _, ok in checks)
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(grade())
```

### 4. Prove the grader isn't gameable: run it against a wrong "fix"
```python
# a plausible-looking but wrong patch: catches the error but still mutates stock
@app.route("/reserve", methods=["POST"])
def reserve_wrong_fix():
    item, qty = request.json["item"], request.json["qty"]
    INVENTORY[item] -= qty  # still mutates first
    if INVENTORY[item] < 0:
        INVENTORY[item] += qty  # "fixes" it after, but only for this exact bug shape
        return jsonify({"error": "insufficient stock"}), 400
    return jsonify({"remaining": INVENTORY[item]})
```
Run the grader against both the correct fix and this wrong-but-plausible one. If the grader can't tell them apart, your grader is too weak — tighten the checks (e.g. assert stock is read *before and after* the failed call across a concurrent request) until it can.

### 5. Run the grader against the correct fix and confirm it passes clean
```bash
python grader/grade.py
```

## ✅ Deliverable
- `env/app.py` (buggy), `task.md`, `grader/grade.py`.
- Two candidate patches (correct + plausible-wrong) with grader output for each, proving the grader discriminates correctly.
- One paragraph on what made the grader hard to write (usually: state you have to check that the task description doesn't explicitly mention).

## ⏱️ Time box
A weekend.

## 🔁 Where to go deeper
The whole [`10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) module is this job — go through it in order 1→2→3→4→7, then 5, 6, 8. [`16_evals`](../../16_evals/README.md) · [`DL/04_reinforcement-learning`](../../../DL/04_reinforcement-learning/README.md) · [`15_mcp`](../../15_mcp/README.md).
