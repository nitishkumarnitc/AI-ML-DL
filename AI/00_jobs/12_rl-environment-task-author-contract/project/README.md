# Run it

```bash
python run.py                  # both authored tasks
python run.py --task auth      # just the auth-bypass task
python run.py --task path      # just the path-traversal task
python run.py --help
```

No dependencies, runs instantly. TWO vendor-style task submissions covering different bug classes:

1. **Auth bypass** — deny-list vs allow-list logic bug.
2. **Path traversal** — a naive `..`-substring "fix" that blocks the obvious attack but misses the absolute-path bypass entirely (uses a real temp-directory sandbox with `tempfile`).

Each grader correctly PASSes only the real fix and FAILs both the buggy version and the plausible-but-wrong one — plus a submission note for each task.

Files: `task.md` (both briefs), `env_*.py`/`grader.py` (task 1), `env_path_*.py`/`grader_path.py` (task 2), `run.py` (orchestrator for both).

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
