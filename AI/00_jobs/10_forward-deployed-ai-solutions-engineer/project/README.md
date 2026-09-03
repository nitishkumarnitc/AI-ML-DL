# Run it

```bash
python run.py                              # scripted demo across 5 repair orders
python run.py --interactive                # live session CLI (pick an RO, chat)
python run.py --interactive --log-file session.json
```

No dependencies, runs instantly. A draft-reply generator across FIVE repair orders that never invents a price/date not in the note, an escalation-detection heuristic (angry-sounding messages skip the draft and route to a human instead), a guardrail stress test, and the assumptions/follow-up-questions deliverable. `--interactive` runs a live session CLI with JSON transcript logging.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
