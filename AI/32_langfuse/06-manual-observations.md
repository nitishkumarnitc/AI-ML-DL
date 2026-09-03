# 06 · Manual Observations: Spans, Generations and Events

> ← [`05-the-observe-decorator.md`](05-the-observe-decorator.md) · **Next:** [`07-sessions-users-and-trace-attributes.md`](07-sessions-users-and-trace-attributes.md) →

---

`@observe` covers most cases. When the unit of work isn't a function — a loop body, a block inside a handler, a retry attempt, a `with` scope — you create observations directly.

---

## 1. The v4 API

One method, with the type as an argument:

```python
from langfuse import get_client

langfuse = get_client()

with langfuse.start_as_current_observation(
    as_type="span",
    name="process-request",
) as span:
    span.update(output="Processing complete")
```

And for a model call:

```python
with langfuse.start_as_current_observation(
    as_type="generation",
    name="llm-response",
    model="gpt-3.5-turbo",
) as generation:
    generation.update(output="Generated response")
```

> **Note the v4 shape**, because v2 and v3 material looks different (lesson 01 §3). There is one entry point — `start_as_current_observation` — and `as_type` selects `span` / `generation` / `event`, rather than separate `start_span()` and `start_generation()` methods. If an example you find online calls `langfuse.span(...)` or `langfuse.generation(...)`, it is v2.

### `start_as_current_*` vs `start_*`

The docs describe both shapes. The distinction is the one you'd expect from OpenTelemetry:

| Form | Behaviour |
|---|---|
| **`start_as_current_observation(...)`** | Creates the observation **and makes it the current context** — so anything called inside nests under it |
| **`start_observation(...)`** | Creates the observation **without** changing the current context — you hold the object and end it yourself |

**Use `start_as_current_*` by default.** Reach for the non-current form only when the observation's lifetime doesn't match a lexical block — a span that begins in one callback and ends in another, for instance. Then you own ending it, and forgetting to is how you get observations that never close.

---

## 2. The three types, in practice

### `span` — work with a duration

```python
with langfuse.start_as_current_observation(as_type="span", name="rerank") as span:
    span.update(input={"candidates": len(candidates)})
    reranked = cross_encoder.rerank(query, candidates)
    span.update(
        output={"kept": len(reranked)},
        metadata={"model": "bge-reranker-base", "dropped": len(candidates) - len(reranked)},
    )
```

### `generation` — a model call

```python
with langfuse.start_as_current_observation(
    as_type="generation",
    name="answer",
    model="gpt-4o-mini",
    model_parameters={"temperature": 0, "max_tokens": 512},
    input=messages,
) as gen:
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    gen.update(
        output=resp.choices[0].message.content,
        usage_details={
            "input": resp.usage.prompt_tokens,
            "output": resp.usage.completion_tokens,
        },
    )
```

> **Pass real usage numbers when you have them.** The provider tells you exactly how many tokens were consumed; that is better than any inference from the payload. If you are calling a self-hosted or unusual model that LangFuse cannot price, this is also where you would attach your own cost metadata — otherwise cost shows as zero and your economics dashboards quietly under-report.
>
> Attribute names for usage/cost vary across SDK versions. **Check the [Python SDK reference](https://python.reference.langfuse.com/langfuse) for your installed version** rather than trusting the exact keys here — this is precisely the kind of detail that moved between v2, v3 and v4.

### `event` — a point in time

The type people forget, and it is genuinely useful:

```python
with langfuse.start_as_current_observation(as_type="event", name="cache_hit") as ev:
    ev.update(metadata={"key": cache_key, "age_s": age})
```

Good uses — all things that *happened* rather than *took time*:

| Event | Why it belongs in the trace |
|---|---|
| `cache_hit` / `cache_miss` | Explains a latency outlier instantly |
| `guardrail_triggered` | The reason an answer looks truncated or refused |
| `fallback_engaged` | The reason a cheap model's output appeared on an expensive path |
| `retry` | Distinguishes one slow call from three fast failed ones |
| `rate_limited` | The reason for a latency spike that isn't your code |

> **A trace with events reads like a narrative; one without reads like a stopwatch.** When you open a 9-second trace and see `rate_limited` and two `retry` events, you are done — no hypothesis needed. That is the difference between data and an explanation.

---

## 3. Mixing decorators and manual observations

They share the same OTel context, so they compose freely:

```python
@observe(name="rag_pipeline")
def rag_pipeline(question: str) -> str:
    hits = retrieve(question)                      # @observe'd

    if not hits:
        with langfuse.start_as_current_observation(
            as_type="event", name="empty_retrieval"
        ) as ev:
            ev.update(metadata={"question": question})
        return "I don't have that information."

    for i, attempt_model in enumerate(["gpt-4o-mini", "gpt-4o"]):
        with langfuse.start_as_current_observation(
            as_type="generation", name=f"answer_attempt_{i}", model=attempt_model
        ) as gen:
            try:
                out = call_model(attempt_model, question, hits)
                gen.update(output=out)
                return out
            except RateLimited:
                gen.update(level="WARNING", status_message="rate limited, escalating")
                continue

    return "Service unavailable."
```

Two things this shows:

**Decorate the stable structure; open observations manually for the dynamic parts.** The pipeline shape is a function, so it's decorated. The retry loop's iterations aren't functions, so they're manual. Trying to force the loop into a decorated function would mean inventing a function that exists only to be decorated.

**`level` and `status_message` mark a degraded observation.** A rate-limited attempt is neither a success nor an unhandled error, and recording it as `WARNING` with a message makes the trace explain itself. Attribute availability varies by version — check the SDK reference.

---

## 4. When to go manual

| Situation | Use |
|---|---|
| A function is the unit of work | **`@observe`** — always prefer it |
| A block inside a function | Manual `span` |
| Loop iterations you want individually visible | Manual, in the loop body |
| A point-in-time fact | Manual **`event`** — no decorator equivalent |
| Wrapping a non-LangChain LLM SDK where you want full control of usage/cost | Manual `generation` |
| Lifetime crosses lexical scope (starts in one callback, ends in another) | `start_observation` (non-current) + explicit end |

> **Default to `@observe`.** Manual observations are more code, more to get wrong, and easy to leave unclosed. Reach for them when the unit of work genuinely isn't a function — which is a real category, just a smaller one than it first appears.

---

## Recap

- **One entry point in v4:** `start_as_current_observation(as_type=…)`. `langfuse.span(...)` / `.generation(...)` are v2.
- **`start_as_current_*`** sets the context so children nest; **`start_*`** doesn't and makes you end it yourself.
- `span` = duration · `generation` = model call (**pass real `usage_details`**) · `event` = point in time.
- **Events turn a stopwatch into a narrative** — `cache_miss`, `retry`, `rate_limited`, `guardrail_triggered`, `fallback_engaged`.
- Decorators and manual observations share OTel context and mix freely: **decorate the structure, open manually for the dynamic parts.**
- `level` / `status_message` mark degraded-but-not-failed work.
- **Verify usage/cost attribute names in the SDK reference for your version** — they moved across major versions.

---

## Self-check

1. Why is `start_observation` riskier than `start_as_current_observation`?
2. You have a 9-second trace and no idea why. Which observation type would most cheaply have told you, and give two concrete examples?
3. A retry loop runs three times. Decorator or manual, and why?
4. You call a self-hosted model. What must you attach yourself, and what breaks if you don't?

---

**Next:** [`07-sessions-users-and-trace-attributes.md`](07-sessions-users-and-trace-attributes.md) →
