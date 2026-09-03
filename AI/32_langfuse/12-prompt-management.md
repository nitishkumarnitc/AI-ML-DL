# 12 · Prompt Management

> ← [`11-datasets-and-experiments.md`](11-datasets-and-experiments.md) · **Next:** [`13-production-and-choosing.md`](13-production-and-choosing.md) →

---

A prompt is not copy. It is **the most behaviour-defining component in your application** — Story B was one sentence added for quality reasons that turned a single pass into a loop and quadrupled cost. So prompts need versioning, review and rollback, exactly like code.

LangFuse's prompt management is a genuinely good implementation of this, with one caching design decision worth understanding properly.

---

## 1. Create

```python
langfuse.create_prompt(
    name="movie-critic",
    type="text",
    prompt="As a {{criticlevel}} movie critic, do you like {{movie}}?",
    labels=["production"],
)
```

**Creating with an existing name adds a new version rather than overwriting.** Versions are immutable and accumulate — so there is always a previous version to roll back to, which is the whole point.

Prompts can equally be created and edited in the UI, which is the case for hosting them here at all (§5).

---

## 2. Fetch and compile

```python
prompt = langfuse.get_prompt("movie-critic")            # the `production` version
compiled = prompt.compile(criticlevel="expert", movie="Dune 2")
```

`{{variable}}` placeholders, filled by `compile(**kwargs)`.

JS/TS:

```typescript
const prompt = await langfuse.prompt.get("movie-critic");
const compiled = prompt.compile({ criticlevel: "expert", movie: "Dune 2" });
```

---

## 3. Labels — how you deploy a prompt without deploying code

By default `get_prompt(name)` fetches the version labelled **`production`**. There is also a **`latest`** label.

That indirection is the deployment mechanism:

```
version 1  ──────────────
version 2  ── [production]      ← what your app is serving
version 3  ── [latest]          ← being tested
version 4                       ← draft
```

Move the `production` label to version 3 and every running instance picks it up on its next fetch. No deploy, no restart.

```python
prompt = langfuse.get_prompt("movie-critic")                  # production
prompt = langfuse.get_prompt("movie-critic", label="latest")  # latest
prompt = langfuse.get_prompt("movie-critic", version=3)       # pinned
```

Custom labels let you stage: `staging`, `canary`, `experiment-a`.

> **⚠️ And this is also the risk, stated plainly.** "Change production behaviour with no deploy" is the feature and the hazard in one sentence. Anyone with UI access can alter what your application does, with **no PR, no review, no CI, and no `git revert`**.
>
> Recall Story B: the ₹2-per-report regression was a *prompt* change made for good reasons. In a repo it would have been a diff someone approved. Via a label move it is a UI click with no reviewer.
>
> So: **treat moving the `production` label as a deploy.** Restrict who can do it, require a reason, and know how to move it back. If your organisation would not let someone push to `main` unreviewed, it should not let them move this label unreviewed either — it is the same power.

---

## 4. Caching, and the availability argument

> The SDKs **cache prompts client-side** after the first retrieval, serving them from memory with no additional latency. **If LangFuse becomes unavailable, cached prompts continue functioning.**

This matters more than it sounds. Fetching a prompt over the network on every request would put your observability vendor **on your application's critical path** — a dependency you emphatically do not want. The cache means:

| | Effect |
|---|---|
| Steady state | Zero added latency; served from memory |
| LangFuse unreachable | Your app **keeps working** on the cached prompt |
| Label moved | Picked up on the next refresh, not instantly |

That last row is the trade: propagation is eventual, not immediate. Fine — and worth knowing when you move a label and wonder why behaviour hasn't changed yet.

### The cold-start gap

The docs reference a **"guaranteed availability"** approach for production-critical deployments: the failure case the cache does not cover is an instance starting up with an **empty cache** while LangFuse is unreachable. Then there is nothing to serve.

The defence is a **fallback prompt in your code** — so the application can always start:

```python
FALLBACK = (
    "Answer ONLY from the provided context. "
    "If the context is insufficient, say you don't know."
)

def get_system_prompt() -> str:
    try:
        return langfuse.get_prompt("support-system").compile()
    except Exception:
        logger.warning("langfuse prompt fetch failed; using in-code fallback")
        return FALLBACK
```

> **Check the current docs for the built-in fallback argument** — the SDK exposes support for this and I would rather point you at the reference than name a parameter I did not verify. The *pattern* is the point: **your application must be able to start when your observability platform is down.** A hosted prompt store that can prevent a deploy from booting has turned a nice-to-have into a hard dependency, which is the opposite of what you wanted.
>
> And keep the fallback **conservative** — the safest version of the prompt, not the cleverest. It is what runs during an incident.

---

## 5. Linking prompts to generations

The docs recommend linking prompts to traces so you can *"analyze performance by prompt version"*. The implementation specifics were not on the page I read — **check the prompt-management docs for the exact linking argument** on generation creation.

The *reason* is worth stating regardless, because it is the payoff for the whole feature:

```
prompt version 2  →  1,240 traces  ·  avg faithfulness 0.79  ·  $0.0004/trace
prompt version 3  →    980 traces  ·  avg faithfulness 0.88  ·  $0.0011/trace
```

That table is the question you actually want answered — **did v3 help, and what did it cost?** — and it requires the prompt version to be attached to the generations it produced. Without the link you have prompt versions in one place and quality scores in another and no join between them.

Failing that, put it in metadata yourself, per lesson 07:

```python
metadata={"prompt_version": "support_v3"}
```

Cruder, and it works. **What is not acceptable is having no record at all**, because then "is the new prompt worse in production?" is unanswerable — production traces carry no evidence of which prompt produced them, and traces are immutable so you cannot backfill it.

---

## 6. ⭐ Repo or platform? The decision, with a recommendation

The question lesson 15 of the LangSmith folder asks, and the answer is the same here because it is not really about the tool.

| | Prompt in the repo | Prompt in LangFuse |
|---|---|---|
| Reviewed in a PR alongside code | ✅ | ❌ separate history |
| Rolls back with `git revert` | ✅ | ❌ (label move — recoverable, but not atomic with code) |
| Non-engineers can edit | ❌ | ✅ |
| Changes without a deploy | ❌ | ✅ — **and that is the risk** |
| One source of truth with the code using it | ✅ | ❌ |
| A/B test versions with traffic | ❌ awkward | ✅ labels |
| Survives the platform being down | ✅ | ⚠️ needs cache + fallback |

**Recommendation: repo by default.** A prompt is the highest-leverage line in your application and should go through the same review, the same tags and the same rollback as any other line. Story B is the argument.

**Use LangFuse-hosted prompts when a non-engineer genuinely owns the wording** — a support lead tuning tone, a legal team maintaining a disclaimer, a domain expert refining a rubric — and the value of them editing without a deploy outweighs losing atomic rollback with code. That is a real and common situation; it is just narrower than the feature's convenience suggests.

If you go that route:

- **Pin a version in production**, not `latest`:
  ```python
  prompt = langfuse.get_prompt("support-system", version=7)
  ```
  Pulling `latest` at runtime means anyone with UI access can change production behaviour with no review and no rollback path. That is not a feature.
- **Restrict who can move the `production` label**, and treat it as a deploy.
- **Keep an in-code fallback** so the app can boot without the platform.
- **Record the version on the generation**, so §5's table is possible.

---

## Recap

- `create_prompt` adds a **new immutable version**; same name never overwrites.
- `get_prompt(name)` → the **`production`**-labelled version. `label=` and `version=` override.
- `compile(**kwargs)` fills `{{placeholders}}`.
- **Labels are the deployment mechanism** — move `production` and running instances pick it up. **Treat that as a deploy**, because it is one, without the review.
- **Client-side caching** means zero steady-state latency and continued operation when LangFuse is down; propagation is eventual.
- **Keep a conservative in-code fallback** for the cold-start-while-unreachable case. Your app must boot without your observability platform.
- **Link prompts to generations** (or at minimum record `prompt_version` in metadata) or "is v3 better in production?" is unanswerable forever.
- **Repo by default; hosted when a non-engineer owns the wording.** If hosted, **pin the version** — never `latest` in production.

---

## Self-check

1. What are the two faces of "change the prompt without a deploy"?
2. Client-side caching gives you two distinct benefits and one trade-off. Name all three.
3. Which failure does caching *not* protect against, and what covers it?
4. Why is pulling `latest` in production a risk rather than a convenience?
5. You want to know whether prompt v3 is better than v2 in production. What must have been recorded, and why can't you add it later?

---

**Next:** [`13-production-and-choosing.md`](13-production-and-choosing.md) →
