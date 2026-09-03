# 03 · Setup: Account, Keys and Environment

> ← [`02-what-langsmith-is-and-what-it-records.md`](02-what-langsmith-is-and-what-it-records.md) · **Next:** [`04-project-trace-run.md`](04-project-trace-run.md) →

---

Setup is short. Do it once and every later lesson runs.

---

## 1. Project scaffold

```bash
mkdir langsmith-masterclass && cd langsmith-masterclass
python -m venv myenv
source myenv/bin/activate          # macOS / Linux
# myenv\Scripts\activate           # Windows
```

`requirements.txt`:

```text
langchain
langchain-openai
langchain-community
langchain-core
langgraph
langsmith
python-dotenv
pypdf
faiss-cpu
duckduckgo-search
requests
```

```bash
pip install -r requirements.txt
```

> **Note on package layout.** Modern LangChain is split: `langchain-core` (interfaces, runnables), `langchain-openai` (the OpenAI integration), `langchain-community` (third-party loaders and tools), `langchain` (the convenience layer). Import from the *specific* package — `from langchain_openai import ChatOpenAI`, not `from langchain.chat_models import ChatOpenAI`. The old paths still resolve but emit deprecation warnings and will eventually stop.
>
> `langsmith` is a **standalone SDK**. You need it explicitly for `@traceable` (lesson 08), `Client`, and `evaluate` (lesson 14) — it is not re-exported by `langchain`.

---

## 2. Get a LangSmith API key

1. Sign up at **`smith.langchain.com`**.
2. **Settings → API Keys → `+`**.
3. Give it a description (e.g. `langsmith personal project`).
4. Key type: **Personal Access Token**.
5. Set an expiry, or leave it as never.
6. **Copy the key now** — it is shown once.

---

## 3. The `.env` file

```bash
# ---- model provider ----
OPENAI_API_KEY=sk-...

# ---- LangSmith ----
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=LangSmith Demo
```

| Variable | Effect if missing / wrong |
|---|---|
| `LANGCHAIN_TRACING_V2` | Not `true` → **nothing is traced at all**. This is the master switch and the first thing to check when traces don't appear. |
| `LANGCHAIN_ENDPOINT` | Which LangSmith instance to send to. `https://api.smith.langchain.com` for US cloud. |
| `LANGCHAIN_API_KEY` | Wrong → traces are dropped **silently** (see lesson 02, §Beyond). Nothing in your app will complain. |
| `LANGCHAIN_PROJECT` | Missing → traces land in a project called `default`. Present → that project is **created automatically** if it doesn't exist. |

Load it at the top of every script:

```python
from dotenv import load_dotenv
load_dotenv()
```

`load_dotenv()` must run **before** you construct any LangChain object, because the tracer reads the environment at construction time.

### Add `.env` to `.gitignore` now, not later

```bash
echo ".env" >> .gitignore
echo "myenv/" >> .gitignore
```

The video's author notes on camera that he deletes his keys after recording. Take the lesson: **a key that has ever been visible is a burned key.** If you paste one into a screenshot, a chat window, a commit or a video, revoke it and issue a new one. Rotation is thirty seconds; a leaked key with billing attached is not.

---

## 4. ⭐ Beyond the video — the variables were renamed

*Added, and worth knowing because you will meet both spellings in the wild and in the docs.*

The `LANGCHAIN_*` names in the video are the **legacy** spellings. When LangSmith became usable independently of LangChain, the variables were renamed to `LANGSMITH_*`:

| Legacy (used in the video) | Current | Notes |
|---|---|---|
| `LANGCHAIN_TRACING_V2=true` | `LANGSMITH_TRACING=true` | The `_V2` suffix was always an artefact |
| `LANGCHAIN_API_KEY` | `LANGSMITH_API_KEY` | |
| `LANGCHAIN_ENDPOINT` | `LANGSMITH_ENDPOINT` | |
| `LANGCHAIN_PROJECT` | `LANGSMITH_PROJECT` | |

**Both work** — the legacy names are honoured as aliases. Two practical rules:

1. **Prefer `LANGSMITH_*`** in new code.
2. **Never set both** for the same setting. If they disagree, which one wins is a detail you should not have to reason about at 2 a.m.

Recommended `.env` going forward:

```bash
OPENAI_API_KEY=sk-...

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=LangSmith Demo
```

> **EU data residency.** If you need EU-region storage, sign up on the EU instance and set `LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`. The key and the endpoint must match the region — a US key against the EU endpoint fails, silently, in the usual way.

---

## 5. Verify the setup in ten seconds

Before you write anything real, prove the pipe works:

```python
# 00_smoke_test.py
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

resp = ChatOpenAI(model="gpt-4o-mini").invoke("Say OK and nothing else.")
print(resp.content)
```

```bash
python 00_smoke_test.py
```

Then open `smith.langchain.com` → **Tracing Projects** → `LangSmith Demo`. One trace should be there.

### If it isn't — check in this order

| # | Check | How |
|---|---|---|
| 1 | Tracing switch is on | `python -c "import os;print(os.getenv('LANGSMITH_TRACING'), os.getenv('LANGCHAIN_TRACING_V2'))"` — one must print `true` (the string, not `True`) |
| 2 | `.env` was actually found | `load_dotenv()` returns `True` if it read a file. `print(load_dotenv())` |
| 3 | Right project | You may be staring at `default` while traces land in `LangSmith Demo` |
| 4 | Key is valid and region-matched | Re-copy from Settings; confirm US key ↔ US endpoint |
| 5 | Process exited too fast | Rare for a script that awaited a response, but see `wait_for_all_tracers()` in lesson 17 |

Nothing in your application will tell you which of these is wrong — tracing fails silently by design. Work the list.

---

## Recap

- venv → `pip install -r requirements.txt` → LangSmith account → Personal Access Token → `.env`.
- `LANGCHAIN_TRACING_V2` / `LANGSMITH_TRACING` is the **master switch**; without `true` nothing happens.
- `LANGCHAIN_PROJECT` / `LANGSMITH_PROJECT` **auto-creates** the project.
- `load_dotenv()` before constructing LangChain objects.
- The variables were **renamed** `LANGCHAIN_*` → `LANGSMITH_*`; both work, prefer the new ones, never set both.
- `.env` in `.gitignore` on day one. A key that has been seen is a key to rotate.
- Smoke-test the pipe before writing anything real, and know the five-step failure checklist.

---

**Next:** [`04-project-trace-run.md`](04-project-trace-run.md) →
