# 15 · Prompt Experimentation, Versioning and the Hub

> ← [`14-evaluation-datasets-and-annotation.md`](14-evaluation-datasets-and-annotation.md) · **Next:** [`16-feedback-and-collaboration.md`](16-feedback-and-collaboration.md) →

---

## Why prompts need their own tooling

Prompt engineering became its own discipline for a reason: **how much performance you can extract from an LLM depends heavily on how well the prompt is written.** For chatbots, RAG systems and agents alike, the prompt has to be on point.

Which raises an awkward question. You have Prompt A and Prompt B. **Which is better?**

The usual method is to paste both into ChatGPT, look at the two answers, and pick. That is not conclusive evidence of anything. You compared two samples from two non-deterministic distributions on one input, and you did it with your own preferences in the loop. Run it again and you might choose the other one.

> **The reframe that makes this tractable:** a prompt change is not a copy edit, it is a **code change to the most behaviour-defining component in your system** (lesson 01, Story B: one sentence rewired a loop). It therefore needs what code changes get — version control, a test suite, and a reviewable diff.

---

## Prompt experimentation

> **Prompt experimentation** in LangSmith lets you systematically test and compare different prompt versions. You can run **A/B tests across prompts on the same dataset**, track their performance against **evaluation metrics**, and record the outcomes. Results are stored over time, giving you a clear history of **which prompt variations worked best and under what conditions**.

Three components, and each replaces one weakness of the eyeball method:

| Component | Replaces |
|---|---|
| The **same dataset** for both prompts | One arbitrary input |
| **Evaluation criteria** (lesson 14) | Your subjective read |
| **Stored history** | Forgetting what you already tried |

That last one is underrated. Six months in, "did we already try being stricter about citations?" has an answer instead of a shrug.

Essentially: **A/B testing for prompts**, on a real test set, scored objectively, recorded.

---

## The Playground

**Prompt Engineering → Playground**, and the key control is **Compare**.

In it you can:

- Author a prompt.
- Supply an **output schema** (structured output).
- Attach **evaluation criteria**.
- **Test the same prompt across different models** — is `gpt-4o-mini` genuinely worse here, or were you paying for `gpt-4o` out of habit?
- Run it over a dataset and see per-example results side by side.

That model-comparison axis is worth using deliberately. Prompt quality and model choice interact: a well-specified prompt often lets a cheaper model match an expensive one, and the Playground is where you find out. On a high-volume endpoint that is not a small saving.

---

## Prompt versioning and the Hub

Two more capabilities:

**Versioning.** Store prompts in LangSmith with version history. Teammates collaborate on them. Every version is retrievable, so you can roll a prompt back without touching a deploy.

**LangChain Hub.** A place to host prompts, browse **public** prompts, and see how other people solved a prompting problem. Useful as a starting point rather than a final answer — a public prompt is tuned for someone else's data.

> **⭐ The decision the video doesn't make for you** *(added)*: should prompts live in your **repo** or in **LangSmith**?
>
> | | In the repo (a `.py` / `.jinja` / `.yaml` file) | In LangSmith |
> |---|---|---|
> | Reviewed in PRs alongside code | ✅ | ❌ (separate history) |
> | Rolls back with a `git revert` | ✅ | ❌ |
> | Non-engineers can edit | ❌ | ✅ |
> | Changes without a deploy | ❌ | ✅ (also the risk) |
> | One source of truth with the code that uses it | ✅ | ❌ |
>
> **Recommendation: repo by default.** A prompt is the highest-leverage line in your application, and it should go through the same review, the same tags, and the same rollback as any other line. Story B was a *prompt* change that cost 4× — you want that in a diff that someone approved.
>
> Use LangSmith-hosted prompts when a non-engineer genuinely owns the wording (a support lead tuning tone, a legal team maintaining a disclaimer) and the value of them editing without a deploy outweighs losing the atomic rollback. If you go that route, **pin a version in code** rather than pulling `latest`:
>
> ```python
> from langsmith import Client
> prompt = Client().pull_prompt("my-team/support-answer:a3f9c1d")   # pinned, not :latest
> ```
>
> Pulling `latest` at runtime means anyone with UI access can change production behaviour with no deploy, no review and no rollback path. That is not a feature.

---

## ⭐ Beyond the video — a prompt change workflow that holds up

*Added: how the pieces from lessons 06, 14 and 15 combine into a routine.*

```
1. Find a real failure          →  a trace where the app got it wrong (lesson 07)
2. Capture it                   →  Add to Dataset, with the CORRECT expected output (14)
3. Reproduce                    →  run the current prompt over the dataset; confirm it fails
4. Change one thing             →  edit the prompt. One variable at a time
5. Score                        →  evaluate(); compare experiments PER EXAMPLE
6. Check for collateral damage  →  did any previously-passing example break?
7. Ship with a version stamp    →  metadata={"prompt_version": "v4"} (lesson 06)
8. Watch                        →  monitor feedback + online eval by prompt_version (13, 16)
```

Step 6 is the one people skip and the one that matters most. An aggregate that improved while three passing cases broke is a **bad change** wearing a good number, and per-example comparison is the only way to see it.

Step 7 is what makes step 8 possible. Without `prompt_version` in metadata you cannot ask "is v4 worse than v3 in production?" — because production traces carry no record of which prompt produced them. Ten characters at write time.

### Change one thing at a time

The temptation is to fix the prompt, bump `k` from 4 to 8, and switch to `gpt-4o` in one go. If quality improves you don't know which change did it, and you may be paying for two changes when one was enough — or one helped while another hurt and they cancelled. One variable per experiment. Slower, and the only way to actually learn anything.

### Version prompts semantically

```python
PROMPTS = {
    "support_v1": "Answer the question.",
    "support_v2": "Answer the question using only the provided context.",
    "support_v3": ("Answer using ONLY the provided context. "
                   "If the context is insufficient, reply exactly: "
                   "'I don't have that information.' Cite the source section."),
}
```

Keep the old versions in the file. When v3 regresses, you roll forward to v4 with a one-line edit rather than reconstructing v2 from memory — and the file itself is a readable history of what you've learned about this task.

---

## Recap

- Comparing two prompts by eyeballing two outputs is **not evidence**: two samples, two non-deterministic distributions, one input, your preferences in the loop.
- A prompt change is a **code change to the most behaviour-defining component** in the system. Treat it accordingly.
- Prompt experimentation = **same dataset + evaluation criteria + stored history**.
- The **Playground → Compare** view also tests one prompt across **models** — often a cheaper model plus a better prompt beats an expensive model.
- **Keep prompts in the repo by default** — review, diff and atomic rollback are worth more than deploy-free edits. If hosted, **pin a version**, never pull `latest` in production.
- Workflow: real failure → dataset row → reproduce → change one thing → score → **check collateral damage** → version stamp → watch.
- Keep old prompt versions in the file. They're a history of what you learned.

---

## Self-check

1. Why is "I tried both in ChatGPT and B looked better" statistically empty? Name two separate flaws.
2. Which step in the workflow catches an aggregate improvement that's actually a bad change?
3. Give one situation where a LangSmith-hosted prompt genuinely beats a repo file, and the safeguard it requires.
4. Why is pulling `:latest` at runtime a production risk rather than a convenience?

---

**Next:** [`16-feedback-and-collaboration.md`](16-feedback-and-collaboration.md) →
