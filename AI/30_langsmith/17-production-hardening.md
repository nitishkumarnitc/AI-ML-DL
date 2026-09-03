# 17 · Production Hardening: PII, Sampling, Flushing, Cost

> ← [`16-feedback-and-collaboration.md`](16-feedback-and-collaboration.md) · **Next:** [`18-llmops-and-where-this-fits.md`](18-llmops-and-where-this-fits.md) →

---

## ⭐ This lesson is added

The video is a tutorial: it enables tracing with defaults and works through examples, which is exactly right for learning. It does not cover what changes when the same configuration meets real users, real data and real volume — that's deferred to a future LLMOps course.

This lesson covers it, because the defaults that are perfect for learning are **wrong in four specific ways** for production, and one of them is a data-protection problem rather than an engineering inconvenience.

| # | Default | Why it's wrong in production |
|---|---|---|
| 1 | Full payloads uploaded | Every prompt, document and completion leaves your process — **including personal data** |
| 2 | 100% of traces sampled | At scale this is a real bill and a lot of noise |
| 3 | Async batched upload | Short-lived processes exit before flushing and lose traces |
| 4 | Tracing failures swallowed | You may believe you have observability when you don't |

---

## 1. PII and sensitive data

### The problem, stated plainly

Lesson 02 established that LangSmith records inputs and outputs **in full**, and that this is deliberate — the payload *is* the diagnostic signal.

Now consider what is actually in those payloads for a real application:

| Application | What lands in the trace |
|---|---|
| HR policy chatbot (Story C) | Employee questions about their own salary, notice period, medical leave |
| Support assistant | Customer names, emails, order numbers, complaint text |
| Clinical or insurance assistant | Health information |
| Document RAG | **The full text of every retrieved chunk**, whatever is in your corpus |
| Résumé tailor (Story A) | Complete résumés — names, addresses, employment history |

All of it, by default, sent to and stored by a third-party service.

> **This is a data-protection question, not a preference.** Under GDPR, DPDP, HIPAA or an enterprise DPA, "we send full user inputs to a US SaaS vendor for debugging" is a processing activity that needs a legal basis, a data-processing agreement, and usually a residency answer. Nobody will tell you this at `pip install` time. **Decide it before you enable tracing in production, not after an audit.**

### The controls, weakest to strongest

**Blunt global switches:**

```bash
LANGSMITH_HIDE_INPUTS=true      # inputs replaced with a placeholder
LANGSMITH_HIDE_OUTPUTS=true     # outputs replaced with a placeholder
```

Effective and cheap, but they remove almost all diagnostic value. You keep latency, tokens, cost, structure and errors — and lose the ability to answer "what did the retriever return?" This is the right setting for a *high-risk* service where the mechanical metrics alone are worth having.

**Programmatic masking — the middle path, and usually the right one:**

```python
import re
from langsmith import Client

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")
PAN   = re.compile(r"[A-Z]{5}\d{4}[A-Z]")          # India PAN, as an example

def scrub(text: str) -> str:
    text = EMAIL.sub("<email>", text)
    text = PHONE.sub("<phone>", text)
    return PAN.sub("<pan>", text)

def mask(payload: dict) -> dict:
    return {k: scrub(v) if isinstance(v, str) else v for k, v in payload.items()}

client = Client(hide_inputs=mask, hide_outputs=mask)
```

You keep the shape and most of the content — enough to debug — while identifiers are gone before anything is transmitted.

**Per-function surgical control** (lesson 08):

```python
@traceable(name="answer_ticket", process_inputs=lambda i: {**i, "customer_email": "<redacted>"})
def answer_ticket(customer_email: str, question: str): ...
```

Best of the three where you can apply it, because it is *specific*: you name exactly the field that is sensitive rather than blanket-hiding everything.

**Architectural — don't put it in the payload:**

The cleanest fix is not a redaction rule; it is not having the data in the trace at all. Pass an **opaque handle** where you currently pass content:

```python
# ❌ the patient's record text is now in your trace, forever
answer = chain.invoke({"question": q, "record": patient_record_text})

# ✅ the trace holds a reference; the content is resolved inside, unlogged
answer = chain.invoke({"question": q, "record_id": "rec_8f21"})
```

You lose the ability to see the record in the trace. In a regulated domain that is the *point*: the trace tells you which record was used and how long it took, and the record itself never leaves your boundary. (This is the same pattern as the opaque citation handles in [`AI/28_ai-system-design-by-industry/04_healthcare_clinical_ai/`](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/).)

**Metadata discipline:** lesson 06 said identifiers, never content. Restated because it's the most common leak. `user_id="u_8812"` is fine. `user_email="…"` is a leak you wrote yourself into a field you designed.

**Region and deployment:**

```bash
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com     # EU residency
```

And for the strictest requirements, LangSmith can be **self-hosted** inside your own infrastructure (an Enterprise-plan option, deployed via Helm/Docker) so no trace data leaves your network at all. If your answer to "can customer text go to a SaaS vendor?" is a hard no, self-hosting or an open-source alternative (LangFuse, Phoenix — lesson 01, §6) is the honest path rather than redacting until the traces are useless.

---

## 2. Sampling

At a thousand traces a day, trace everything. At ten million, don't.

```bash
LANGSMITH_TRACING_SAMPLING_RATE=0.1        # ~10% of traces
```

But a **uniform** rate is a blunt instrument: it discards the same 90% of your failures as your successes, and failures are what you wanted. Sample by *interest* instead:

```python
import random
from langsmith.run_helpers import tracing_context

def should_trace(request) -> bool:
    if request.is_internal_test:      return True    # always
    if request.tenant in BIG_ACCOUNTS: return True   # always
    if request.user_flagged_last_turn: return True   # they're already unhappy
    return random.random() < 0.05                    # 5% background sample

with tracing_context(enabled=should_trace(request)):
    answer = chain.invoke(request.question)
```

Three rules that make sampling survivable:

1. **Never sample out errors.** If you can detect failure before deciding, always trace it. A sampled-away exception is the one trace you needed.
2. **Sample by session, not by request.** A conversation with turns 2 and 5 traced and 1, 3, 4 missing is nearly unreadable. Hash the `session_id` and keep whole conversations.
3. **Record the sample rate in metadata.** `metadata={"sample_rate": 0.05}` — otherwise every count you compute from traces is wrong by an unknown factor, and someone will eventually multiply by the wrong number in a capacity plan.

---

## 3. Flushing — the bug that eats your evidence

Uploads are **batched and asynchronous** so tracing stays off your request path (lesson 02). The consequence: a process that exits promptly can exit **before the batch is sent**, and those traces are gone.

Bites you in exactly the places you'd rather it didn't:

- AWS Lambda / Cloud Functions — the runtime freezes the instant you return
- CLI tools and cron jobs
- CI test runs
- Containers with a short `SIGTERM` grace period
- Notebook kernels restarted mid-flight

### The fix

```python
from langchain_core.tracers.langchain import wait_for_all_tracers

def handler(event, context):
    result = chain.invoke(event["question"])
    wait_for_all_tracers()          # block until traces are shipped
    return result
```

For the standalone SDK:

```python
from langsmith import Client
client = Client()
# … work …
client.flush()
```

FastAPI:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    yield
    wait_for_all_tracers()          # on shutdown

app = FastAPI(lifespan=lifespan)
```

> **The tell:** intermittently missing traces — mostly present, sometimes absent, with no pattern you can find. Almost always this. Debugging it as an auth or configuration problem can burn a whole afternoon.

---

## 4. Failure modes to know before they cost you an afternoon

| Symptom | Cause | Check |
|---|---|---|
| **No traces at all** | Master switch off | `LANGSMITH_TRACING` / `LANGCHAIN_TRACING_V2` must be the **string** `true` |
| **No traces, config looks right** | Bad key, or key/region mismatch | Re-copy the key; confirm US key ↔ US endpoint |
| **Traces in the wrong project** | `os.environ` set before `load_dotenv()` (lesson 06) | Order of those two lines |
| **Intermittently missing traces** | Not flushed on exit | Add `wait_for_all_tracers()` |
| **Two traces where you wanted one** | No active parent (lesson 09) | Wrap in `@traceable` or `with trace(...)` |
| **Some steps missing** | Not runnables, not decorated (lesson 07) | `@traceable` |
| **Run stuck "running"** | Generator abandoned mid-iteration, or process died mid-run | Drain generators fully |
| **Costs show as zero** | Custom or self-hosted model LangSmith can't price | Attach token counts and your own cost metadata |

> **The meta-lesson: tracing fails silently by design.** An observability outage must never take down your application, which is correct — and means **you will not be told**. So: add a startup assertion (`assert Client().info` or a single test trace at boot), and put the traffic-floor alert from lesson 13 in place. Otherwise you can be flying blind for a week while believing you're instrumented, and you'll find out during the incident where you needed it.

---

## 5. What tracing costs

Two costs, and people usually only think about the first.

### Money

LangSmith bills per trace, with a free developer allowance and paid tiers above it; retention comes in a shorter base tier and a longer extended tier at a higher per-trace price. **Check current pricing before you commit** — the numbers move and I won't quote figures that will be stale.

The shape of the decision is stable, though:

```
traces/month  =  requests/month  ×  sampling rate
cost/month    ≈  traces/month    ×  per-trace price(retention tier)
```

Two levers: **sampling rate** and **retention tier**. A useful default is a *low* background sample at *long* retention (so you can investigate something from six weeks ago) plus *100%* of errors and flagged sessions. Sampling everything at long retention is the expensive combination, and rarely the informative one.

### Latency and reliability

Upload is async and off the critical path, so the direct latency cost is near zero. Two indirect costs remain:

- **Serialisation.** Very large payloads (a 40 MB base64 image, an entire document) cost real CPU to serialise. Trim with `process_inputs` (lesson 08).
- **Memory.** Buffered batches hold payloads in memory. High-throughput, large-payload workloads should sample rather than buffer.

---

## 6. The production checklist

Before enabling tracing on a service with real users:

**Data protection**
- [ ] Someone has answered: **is it lawful to send this payload to this vendor?**
- [ ] PII masking in place (`hide_inputs`/`hide_outputs` callables or `process_inputs`), or content replaced by opaque handles
- [ ] Metadata audited: identifiers only, no content, no emails
- [ ] Region/residency correct, or self-hosted
- [ ] Trace-link sharing policy agreed (lesson 16)

**Correctness of the instrumentation**
- [ ] Startup assertion that tracing is actually working
- [ ] `wait_for_all_tracers()` on every short-lived entry point
- [ ] Traffic-floor alert (lesson 13) — catches silent instrumentation loss
- [ ] `run_name`, `tags` and `metadata` set: `env`, `git_sha`, `prompt_version`, `tenant`, `session_id`
- [ ] Startup/index-build traces kept **out** of request traces (lesson 09)

**Volume and cost**
- [ ] Sampling rate chosen; **errors and flagged sessions never sampled out**
- [ ] Sampling by **session**, not request
- [ ] `sample_rate` recorded in metadata
- [ ] Retention tier chosen deliberately
- [ ] Oversized payloads trimmed

**Closing the loop**
- [ ] Feedback endpoint returning and accepting `run_id` (lesson 16)
- [ ] Golden dataset exists; CI gated on it (lesson 14)
- [ ] Alerts routed by severity, thresholds on **percentiles** (lesson 13)

---

## Recap

- **Four defaults change for production:** full payloads · 100% sampling · async upload · silent failures.
- **PII is a legal question, decided before launch.** Controls, weakest to strongest: `HIDE_INPUTS`/`HIDE_OUTPUTS` → `Client(hide_inputs=fn)` → per-function `process_inputs` → **opaque handles instead of content** → region/self-host.
- Metadata: **identifiers, never content.**
- Sample by **interest, not uniformly**. Never sample out errors. Sample by **session**. Record the rate.
- **Flush on exit** — `wait_for_all_tracers()`. Intermittently missing traces are almost always this.
- **Tracing fails silently by design**, so add a startup assertion and a traffic-floor alert.
- Cost levers: **sampling rate × retention tier**. Low background sample, long retention, 100% of errors.
- Run the checklist before enabling tracing on a service with real users.

---

## Self-check

1. Name the strongest PII control here and the diagnostic capability you give up for it.
2. Uniform 10% sampling. Why is that worse than it looks, and what's the single most important exception?
3. Traces appear most of the time and vanish occasionally, with no pattern. First hypothesis?
4. Why does "tracing fails silently" require *two* separate safeguards, and what are they?
5. Which two levers set your LangSmith bill, and which combination is expensive without being informative?

---

**Next:** [`18-llmops-and-where-this-fits.md`](18-llmops-and-where-this-fits.md) →
