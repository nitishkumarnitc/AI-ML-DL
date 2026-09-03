# Run it

```bash
python run.py                                          # full 10-question eval + cost log + multi-turn demo
python run.py --ask "Do gift cards expire?"            # one-off question
python run.py --interactive                            # multi-turn REPL with memory
python run.py --json-out results.json                  # export eval + cost log
python run.py --help
```

No dependencies, runs instantly. A RAG feature over a 10-doc corpus (local bag-of-words retrieval, structured extractive answers), with per-query latency/cost logging, a 10-question eval set, an out-of-scope guardrail probe, AND a multi-turn memory demo showing a follow-up question ("what about international?") get rewritten using the prior question so retrieval still finds the right doc.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
