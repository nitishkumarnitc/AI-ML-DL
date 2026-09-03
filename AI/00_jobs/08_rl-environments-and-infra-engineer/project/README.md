# Run it

```bash
python run.py                  # both environments
python run.py --env payment    # just the payment/idempotency environment
python run.py --env reservation
python run.py --help
```

No dependencies, runs instantly. Grades TWO different gradable environments with the same separate-grader discipline:

1. **Reservation service** — a concurrency/race-condition bug.
2. **Payment service** — a pure logic bug (idempotency): a "wrong fix" that only remembers the most-recent request key passes the easy retry test but fails when a different request arrives in between.

Each grader correctly PASSes only the real fix and FAILs both the buggy version and the plausible-but-wrong one.

Files: `env_*.py`/`grader.py` (reservation), `env2_*.py`/`grader2.py` (payment), `run.py` (orchestrator for both).

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
