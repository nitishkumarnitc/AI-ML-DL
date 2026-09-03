# Run it

```bash
python run.py
python run.py --verbose                       # print every tool call as it happens
python run.py --log-file transcripts.json      # persist full traces for debugging
python run.py --help
```

No dependencies, runs instantly. A tool-using agent with FOUR tools (calculator, note lookup, mock web-search, unit converter), retry-on-failure, and a 10-task eval harness scored pass/fail automatically. `--verbose` shows every tool call live; `--log-file` writes the full step-by-step JSON transcript for every task, the actual artifact you'd attach to a bug report.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
