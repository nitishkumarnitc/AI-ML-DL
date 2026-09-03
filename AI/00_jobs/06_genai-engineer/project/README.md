# Run it

```bash
python run.py
python run.py --k 5              # retrieve/score top-5 instead of top-3
python run.py --help
```

No dependencies, runs instantly. A RAG chatbot with SENTENCE-LEVEL chunking (10 docs -> 25 chunks) over an internal-wiki-style corpus, measured recall@k/MRR/precision@k against a 15-query labeled set, plus TWO guardrail types: a scope-refusal guardrail (out-of-scope questions) and a PII-redaction guardrail (scrubs emails/extensions out of an otherwise-correct answer).

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
