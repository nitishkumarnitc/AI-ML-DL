# Run it

```bash
python run.py
python run.py --report-file redteam_report.md   # export findings as a markdown table
python run.py --help
```

No dependencies, runs instantly. FIVE prompt-injection/jailbreak attacks (direct override, tool abuse, formatting trick, roleplay jailbreak, base64-encoding trick) against a naive email agent — all succeed. The same five against a defended agent — all neutralized. `--report-file` exports a real markdown red-team report.

Full write-up, what to look for, and how to extend it: [../project.md](../project.md).
