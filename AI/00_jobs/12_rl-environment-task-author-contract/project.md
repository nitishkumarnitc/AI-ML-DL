# 12 · Sample project — RL Environment / Task Author (contract)

← back to [job description](README.md) · [jobs hub](../README.md)

> ▶ **Run the real code:** `python project/run.py` (instant, no deps) -- grades TWO authored tasks (auth bypass + path traversal, using a real temp-directory sandbox), three variants each, and prints PASS/FAIL per check plus both submission notes. `--task auth`/`--task path` runs just one. See [`project/`](project/) for the full source.

## 🎯 What you'll build
A single **task submission package** built to a vendor-style spec: a tiny repo with an injected known bug, a task brief, a grader, and a written submission explaining your engineering decisions — the exact deliverable format for this contract work.

## 🧠 Why this mirrors the real job
- "Build a reproducible environment + task + separate grader that meets a spec, and submit it" → you'll work from a spec, not from your own idea of what's interesting.
- "Common brief: inject/expose a known bug or CVE... that a model must find and patch" → the task below is that exact brief.
- "Explain your engineering decisions clearly in writing; iterate on reviewer feedback" → the submission writeup is graded as part of the deliverable, same as in real vendor review.

## 🧰 Prerequisites
- Whatever backend language you're fastest in.
- ~5–6 hours (throughput matters in this work — track your own time).

## 🧰 Tools, libraries & skills used here
- **Working from a terse, ambiguous spec** — filling the gaps with a documented assumption (see the submission note in the output) instead of guessing silently, which is what separates an accepted submission from a rejected one.
- **An adversarial grader-design mindset**: the grader deliberately tests a role (`"guest"`) the task brief never named, to catch a deny-list-vs-allow-list logic bug that an obvious 2-case test would miss — this is the actual skill vendors pay for.
- **Python `threading`/plain classes** standing in for a real service + HTTP grader, so the grading logic itself is the focus.
- **What a real submission adds on top**: the service is usually exposed over **HTTP** (Flask/FastAPI) inside a small Git repo, the grader runs **headlessly** via a CLI/CI pipeline the vendor platform controls, and the whole package (repo + task.md + grader + README) gets reviewed by a human before being accepted into a training corpus — the same review loop the vendor platforms (Mercor, Turing, Surge, Scale) run at scale.

## 📦 Dependencies

| Library | Install | Used for |
|---|---|---|
| sys (stdlib) | built in | process exit code so CI can detect a grading failure |

## 🪜 Step-by-step

### 1. Read the (self-issued) spec first
```markdown
# SPEC
Deliverable: one gradable task in a small (<300 line) web service.
Requirement: inject a *specific, realistic* bug class (pick one: SQL injection,
path traversal, missing auth check, race condition on shared state).
The task must be solvable by reading the repo alone — no external context needed.
Grader must run headless, in under 30s, and output PASS/FAIL + a reason.
```
Real vendor specs are this terse — filling the gaps with sound judgment *is* the job.

### 2. Build the tiny repo with the injected bug
```python
# app.py — missing auth check on a sensitive endpoint (pick your own bug class if you prefer)
from flask import Flask, request, jsonify
app = Flask(__name__)
USERS = {"alice": {"role": "user", "balance": 100}, "admin": {"role": "admin", "balance": 0}}

@app.route("/admin/set_balance", methods=["POST"])
def set_balance():
    # BUG: no check that the caller is actually an admin
    user = request.json["user"]
    USERS[user]["balance"] = request.json["balance"]
    return jsonify(USERS[user])
```

### 3. Write the task brief the model/worker will see
```markdown
# task.md
Fix `/admin/set_balance` in app.py so only requests where `request.json["caller_role"] == "admin"`
can change a balance. Non-admin callers must get HTTP 403 and no state change. Keep the response
shape identical for authorized calls.
```

### 4. Write the grader — and make it actually rigorous
```python
# grader.py
import subprocess, time, requests, sys

def grade():
    proc = subprocess.Popen(["python", "app.py"])
    time.sleep(1)
    try:
        checks = []
        before = requests.get("http://localhost:5000/debug/users").json()  # add a debug read endpoint
        r = requests.post("http://localhost:5000/admin/set_balance",
                           json={"user": "alice", "balance": 999999, "caller_role": "user"})
        checks.append(("rejects non-admin caller", r.status_code == 403))
        after = requests.get("http://localhost:5000/debug/users").json()
        checks.append(("state unchanged after rejection", before == after))
        r2 = requests.post("http://localhost:5000/admin/set_balance",
                            json={"user": "alice", "balance": 500, "caller_role": "admin"})
        checks.append(("admin call still works", r2.status_code == 200))
    finally:
        proc.terminate()
    passed = all(ok for _, ok in checks)
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(grade())
```

### 5. Stress-test your own grader with a wrong "fix"
Write a patch that checks `caller_role` but forgets to also block the state mutation on rejection (mutate-then-check, like in the [RL Environments project](../08_rl-environments-and-infra-engineer/project.md)). If your grader still says PASS, tighten it.

### 6. Write the submission note
This is the part contractors skip and get rejected for. Cover:
- Why you chose this bug class.
- Any assumption you made where the spec was silent.
- One edge case your grader deliberately does **not** cover, and why (scope, not laziness).

## ✅ Deliverable
`app.py` (buggy), `task.md`, `grader.py`, your wrong-fix stress test + result, and the submission note. Time yourself — this reflects the throughput reality of output-based pay.

## ⏱️ Time box
One evening (aim for under 4 hours once you've done the [RL Environments project](../08_rl-environments-and-infra-engineer/project.md) once — reusable skeletons are the whole point).

## 🔁 Where to go deeper
[`10_rl-environments-and-infra`](../../10_rl-environments-and-infra/README.md) Lessons [1](../../10_rl-environments-and-infra/01-the-role-and-the-frontier-lab-customer.md)→[2](../../10_rl-environments-and-infra/02-rl-environments-for-agents.md)→[3](../../10_rl-environments-and-infra/03-engineering-high-fidelity-environments.md)→[5](../../10_rl-environments-and-infra/05-designing-rigorous-graders.md)→[8](../../10_rl-environments-and-infra/08-build-your-first-gradable-environment.md) · [`03_llm-security-and-guardrails`](../../03_llm-security-and-guardrails/README.md).
