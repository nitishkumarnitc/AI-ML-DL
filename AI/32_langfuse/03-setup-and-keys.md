# 03 · Setup: Keys, Regions and the Client

> ← [`02-core-concepts-and-data-model.md`](02-core-concepts-and-data-model.md) · **Next:** [`04-self-hosting.md`](04-self-hosting.md) →

---

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install langfuse
```

Verify the major version before anything else — lesson 01 §3 explains why this is the first command, not an afterthought:

```bash
pip show langfuse | grep -i version
```

This folder assumes **v4**. If you are on v2, the code here will not run and you should upgrade or read the versioned docs for your line.

---

## 2. Get keys

**Cloud:** sign up, create an organization, create a project, then **Settings → API Keys → Create**.

You get a **pair**:

| Key | Prefix | Nature |
|---|---|---|
| **Public key** | `pk-lf-…` | Identifies the project. Not a secret in the strict sense |
| **Secret key** | `sk-lf-…` | **Is** a secret. Shown once |

> **Why a pair, when LangSmith has one key?** Because the public key is designed to be usable from contexts where it will be visible — a browser SDK submitting user feedback, for instance. Ingestion is authenticated with the pair together, and the split lets some flows carry only the public half. Treat `sk-lf-` exactly as you would any API secret; the "public" in public key does not extend to it.

**Self-hosted:** same flow inside your own instance. See [`04-self-hosting.md`](04-self-hosting.md).

---

## 3. Environment variables

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

OPENAI_API_KEY=sk-...
```

| Variable | Notes |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Required |
| `LANGFUSE_SECRET_KEY` | Required |
| `LANGFUSE_BASE_URL` | **This is the current name.** Older material says `LANGFUSE_HOST` — see lesson 01 §3 |

```bash
echo ".env" >> .gitignore
```

Same discipline as [`../30_langsmith/03-setup-and-environment.md`](../30_langsmith/03-setup-and-environment.md): **a key that has ever been visible is a key to rotate.** Rotation takes seconds; a leaked secret key against a project with your customers' prompts in it does not.

### Regions — pick deliberately, because the key is bound to it

LangFuse cloud runs in several regions, each a **separate instance with its own keys and its own OTLP endpoint**:

| Region | Base URL |
|---|---|
| EU (default) | `https://cloud.langfuse.com` |
| US | `https://us.cloud.langfuse.com` |
| Japan | `https://jp.cloud.langfuse.com` |
| HIPAA | `https://hipaa.cloud.langfuse.com` |

> **A key from one region will not work against another**, and the failure is an auth error rather than anything that names the real problem. If keys look right and nothing ingests, check this before anything else.
>
> The HIPAA instance existing at all is worth noticing: it is the hosted answer to the healthcare case that [`../28_ai-system-design-by-industry/04_healthcare_clinical_ai/`](../28_ai-system-design-by-industry/04_healthcare_clinical_ai/) is built around. If you need a BAA, that is the path — and if you need the data never to leave your network at all, lesson 04.

---

## 4. The client

```python
from dotenv import load_dotenv
load_dotenv()

from langfuse import get_client

langfuse = get_client()
```

`get_client()` returns a **singleton**. Call it wherever you need the client rather than threading one through your call graph.

Explicit construction, when config comes from somewhere other than the environment:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    base_url="https://cloud.langfuse.com",
)
```

> **One behaviour worth knowing before it confuses you.** The docs state: *"If you create multiple `Langfuse` instances with the same `public_key`, the singleton instance is reused and new arguments are ignored."*
>
> So a second `Langfuse(...)` with a different `base_url` but the same public key **silently keeps the first configuration.** If you are trying to point one process at two instances — say, mirroring to a self-hosted instance during a migration — this will quietly not do what you wrote. Different keys, or separate processes.

### It sets up OpenTelemetry for you

Per the docs, *"the Python SDK automatically sets up OpenTelemetry when initializing the client"*, and the spans it creates are **native OTel spans** with LangFuse conveniences added.

That is the whole architecture in one sentence, and it explains three things you will otherwise find surprising:

1. **Context propagation is OTel context propagation** — so it follows `await` and `asyncio` tasks, and does *not* follow a bare `threading.Thread`. Exactly the caveat from [`../30_langsmith/09-one-trace-not-two.md`](../30_langsmith/09-one-trace-not-two.md), for the same underlying reason.
2. **Nesting comes free** from the OTel context, which is why `@observe` needs no wiring (lesson 05).
3. **It coexists with OTel instrumentation you already run** rather than competing with it (lesson 09).

---

## 5. Flush before exit

```python
langfuse.flush()
```

The docs mark this **required for short-lived applications** so events are sent before the process ends.

Same failure as [`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md) §3, same shape, and it bites in the same places:

- AWS Lambda / Cloud Functions — the runtime freezes the moment you return
- CLI tools and cron jobs
- CI test runs
- Containers with a short `SIGTERM` grace period
- Notebook kernels restarted mid-flight

```python
def handler(event, context):
    result = run_pipeline(event["question"])
    langfuse.flush()          # block until sent
    return result
```

FastAPI:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app):
    yield
    get_client().flush()

app = FastAPI(lifespan=lifespan)
```

> **The tell is intermittently-missing traces** — mostly present, occasionally absent, no pattern. It is almost always this, and it is very easy to spend an afternoon debugging it as an auth or configuration problem.

---

## 6. Smoke-test the pipe

Prove ingestion works before you write anything real.

```python
# 00_smoke_test.py
from dotenv import load_dotenv
load_dotenv()

from langfuse import get_client, observe

langfuse = get_client()

@observe()
def hello(name: str) -> str:
    return f"hello {name}"

print(hello("world"))
langfuse.flush()
```

```bash
python 00_smoke_test.py
```

Open your project → **Tracing** → one trace named `hello`.

### If it isn't there, check in this order

| # | Check | How |
|---|---|---|
| 1 | Keys are loaded | `python -c "import os;print(os.getenv('LANGFUSE_PUBLIC_KEY'))"` |
| 2 | `.env` was found | `print(load_dotenv())` → `True` |
| 3 | **Region matches the key** | US key against the EU default URL fails |
| 4 | `LANGFUSE_BASE_URL`, not `LANGFUSE_HOST` | The rename from lesson 01 §3 |
| 5 | Process exited before flush | Add `langfuse.flush()` |
| 6 | SDK major version | `pip show langfuse` — v2 code against v4, or vice versa |

---

## Recap

- `pip install langfuse`, then **check the major version first**.
- Keys come as a **pair**: `pk-lf-` (public) and `sk-lf-` (secret, shown once). Both are needed; treat the secret as a secret.
- `LANGFUSE_BASE_URL` — **not** `LANGFUSE_HOST`.
- **Regions are separate instances.** A key is bound to one; mismatches fail as auth errors.
- `get_client()` returns a **singleton**, and a second construction with the same public key **silently ignores new arguments**.
- The SDK **is** OpenTelemetry — which is why context follows `await` but not raw threads.
- **`flush()` before a short-lived process exits**, or lose the tail of your traces.
- Smoke-test first, and know the six-step checklist.

---

**Next:** [`04-self-hosting.md`](04-self-hosting.md) →
