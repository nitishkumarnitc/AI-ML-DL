# Claude Code Usage Optimization: Skills, MCPs, Model Calibration, and Cost Accounting

## 1. What We Are Building

A working Claude Code project that demonstrates the four levers that actually move the needle on cost and quality:

1. A **skill** that packages a repeatable procedure so Claude Code doesn't have to be re-taught it every session — plus a second skill showing how skills can call a helper script instead of doing everything in-prompt.
2. An **MCP configuration** with two servers (a hosted OAuth one and a local stdio one) so you see both connection patterns.
3. A **settings.json** model-routing policy so model choice is enforced by config, not memory.
4. A **cost-accounting toolkit** — a real parser for Anthropic's `usage` block, a batch-vs-interactive break-even calculator, and a working Python + curl example against the Message Batches API.

By the end you'll have one directory that actually runs: a skill you can trigger, an MCP server you can query, and a script that tells you, from real usage numbers, whether your last Claude Code session was cache-efficient or not.

---

## 2. Prerequisites

- Claude Code installed: `npm install -g @anthropic-ai/claude-code`, then `claude login` (or `ANTHROPIC_API_KEY` exported for API/script use).
- Python 3.9+ for the cost tooling (standard library only — no `pip install` needed).
- `curl` for the batch API example, or the `anthropic` Python package if you'd rather drive it from Python (`pip install anthropic`).
- Node.js available on `PATH` if you want the `npx`-based MCP server in Step 2 to work as written.

---

## 3. Project Setup

```text
claude_usage_optimization/
├── .claude/
│   ├── skills/
│   │   ├── changelog-entry/
│   │   │   └── SKILL.md
│   │   └── usage-report/
│   │       ├── SKILL.md
│   │       └── scripts/
│   │           └── summarize_usage.py
│   └── settings.json
├── .mcp.json
├── cost_calculator.py
├── batch_submit.py
└── README.md
```

Two things worth noting before we build this out:
- `.claude/skills/usage-report/scripts/` is a real, supported pattern — a skill can bundle scripts it invokes via `Bash`, so the skill's `SKILL.md` stays short and the actual logic lives in a testable file.
- `.claude/settings.json` is where project-level Claude Code config (permissions, model defaults) lives, checked into the repo so the whole team gets the same defaults.

---

## 4. Step-by-Step Implementation

### Step 1 — A skill for a real, opinionated writing task

**Goal:** Encode a task that's easy to get subtly wrong by hand every time — writing a changelog entry that's genuinely useful (not a restatement of the diff) — so it's done the same correct way every time.

**Files involved:** `.claude/skills/changelog-entry/SKILL.md`

**Implementation:**

```markdown
---
name: changelog-entry
description: Write a CHANGELOG.md entry from a git diff, PR title, or PR description. Triggers on "write a changelog entry", "update the changelog", "add a CHANGELOG line for this PR".
---

# Changelog Entry

## Input
A git diff, a PR title, or a short description of a change.

## Process
1. Read the diff/description and classify the change:
   - `Added` — new user-facing capability
   - `Changed` — behavior change to something that already existed
   - `Fixed` — bug fix
   - `Removed` — capability taken away
   - `Security` — a fix with security implications (call this out explicitly)
2. Write ONE line per distinct user-visible effect. If the diff has three
   unrelated effects, write three lines, not one line that lists all three.
3. Rules for the line itself:
   - Imperative mood: "Add X", not "Added X" or "This adds X".
   - Describe the *user-visible* effect, never internal implementation
     (no function names, no file paths, no "refactored X to use Y").
   - Max 15 words.
   - No marketing language ("blazing fast", "seamless") — state the fact.

## Output format
Return only the entry lines, nothing else:
```
- Added: <line>
- Fixed: <line>
```

## Example
Diff: adds retry-with-backoff to the HTTP client, fixes a null-pointer
crash when a response has no body.

Output:
```
- Added: Retry failed HTTP requests automatically with exponential backoff.
- Fixed: Crash when a server response has an empty body.
```
```

**Why:** The `description` field is Claude Code's entire discovery surface for a skill — it's matched against the user's request the same way a search index is matched against a query. Naming the exact trigger phrases ("write a changelog entry", "update the changelog") is what makes the skill actually fire instead of Claude Code answering the request from scratch each time, inconsistently. The worked example inside the skill body also matters: showing one correct input→output pair does more to fix format drift than another paragraph of prose rules would.

**Expected result:** Any phrasing close to "write a changelog entry for this" reliably produces the same format, classification, and level of detail — this is what "packaging a procedure once" actually buys you.

---

### Step 2 — A skill that delegates to a real script

**Goal:** Show the other half of the skill pattern — when a task needs actual computation (not just formatting judgment), the skill should call a script instead of asking the model to compute by hand.

**Files involved:** `.claude/skills/usage-report/SKILL.md`, `.claude/skills/usage-report/scripts/summarize_usage.py`

**Implementation — the script:**

```python
#!/usr/bin/env python3
"""
summarize_usage.py — turn a raw Anthropic usage log (JSON lines, one
`usage` object per API call) into a per-model cost + cache-efficiency report.

Usage:
    python3 summarize_usage.py usage_log.jsonl
"""
import json
import sys
from collections import defaultdict

PRICING = {
    # $ per million tokens. Verify against https://www.anthropic.com/pricing
    "claude-opus-4":   {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-4":  {"input": 3.00,  "output": 15.00, "cache_write": 3.75,  "cache_read": 0.30},
    "claude-haiku-4":   {"input": 0.80,  "output": 4.00,  "cache_write": 1.00,  "cache_read": 0.08},
}


def cost_of(model, usage):
    rates = PRICING[model]
    return (
        usage.get("input_tokens", 0) / 1e6 * rates["input"]
        + usage.get("output_tokens", 0) / 1e6 * rates["output"]
        + usage.get("cache_creation_input_tokens", 0) / 1e6 * rates["cache_write"]
        + usage.get("cache_read_input_tokens", 0) / 1e6 * rates["cache_read"]
    )


def cache_hit_rate(usage):
    cached = usage.get("cache_read_input_tokens", 0)
    fresh = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
    total = cached + fresh
    return cached / total if total else 0.0


def main(path):
    totals = defaultdict(lambda: {"calls": 0, "cost": 0.0, "cache_hits": []})

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            model = record["model"]
            usage = record["usage"]

            totals[model]["calls"] += 1
            totals[model]["cost"] += cost_of(model, usage)
            totals[model]["cache_hits"].append(cache_hit_rate(usage))

    print(f"{'Model':<20}{'Calls':>8}{'Cost':>12}{'Avg cache-hit':>16}")
    grand_total = 0.0
    for model, t in totals.items():
        avg_hit = sum(t["cache_hits"]) / len(t["cache_hits"]) if t["cache_hits"] else 0
        grand_total += t["cost"]
        print(f"{model:<20}{t['calls']:>8}{t['cost']:>12.4f}{avg_hit:>15.1%}")
    print(f"\nTotal spend: ${grand_total:.4f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: summarize_usage.py <usage_log.jsonl>")
    main(sys.argv[1])
```

**Implementation — the skill wrapper:**

```markdown
---
name: usage-report
description: Summarize Claude API usage/cost from a JSONL log of usage records. Triggers on "summarize my usage", "how much did this session cost", "cache hit rate report".
---

# Usage Report

1. Locate the usage log the user is referring to (ask for the path if
   ambiguous — do not guess a filename).
2. Run:
   ```
   python3 .claude/skills/usage-report/scripts/summarize_usage.py <path>
   ```
3. Present the table as-is, then add one sentence of interpretation:
   flag any model with an average cache-hit rate under 50% as a caching
   opportunity, and name the single most expensive model by total cost.
```

**Why:** Token math and aggregation are exactly the kind of task a model should *not* be doing by generating numbers from "reasoning" — it should run code and report the result. Bundling `summarize_usage.py` inside the skill folder keeps it version-controlled, testable on its own (`python3 summarize_usage.py test_log.jsonl`), and reusable outside Claude Code entirely, while `SKILL.md` stays a two-line instruction to run it and interpret the output.

**Expected result:** "Summarize my usage from today's log" produces a real, arithmetically correct table plus a one-line takeaway, not an approximated guess.

---

### Step 3 — Connect two MCP servers (hosted OAuth + local stdio)

**Goal:** See both real connection patterns MCP servers use, since Claude Code treats them identically once connected but the setup differs.

**Files involved:** `.mcp.json`

**Implementation:**

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
    },
    "filesystem-readonly": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/Documents/reference-docs"]
    }
  }
}
```

- `atlassian` is a **hosted, remote MCP server**: `mcp-remote` opens an SSE connection to Atlassian's own server and handles the OAuth browser redirect for you on first use — no credentials live in this file.
- `filesystem-readonly` is a **local stdio server**: Claude Code spawns it as a subprocess and talks to it over stdin/stdout, giving read access to a specific directory outside the project without needing Claude Code itself to have broader filesystem permissions.

Verify both with:

```bash
claude mcp list
```

which should print both servers with a connected status once you've completed the Atlassian OAuth prompt.

**Why:** These are the two shapes almost every MCP integration takes — remote+OAuth (Atlassian, Slack, most SaaS tools) and local+stdio (filesystem, a local database, an internal CLI wrapped as an MCP server). Knowing which one you're wiring up tells you what to debug when it fails: an OAuth problem for the first, a subprocess/argument problem for the second.

**Expected result:** Claude Code can call `getJiraIssue` / `getConfluencePage` tools live (remote), and can read files from `reference-docs/` as MCP resources (local) — both without you manually pasting content into the chat.

---

### Step 4 — Enforce model routing via settings, not memory

**Goal:** Make "use Sonnet by default, escalate to Opus deliberately" a checked-in policy rather than something everyone has to remember to type.

**Files involved:** `.claude/settings.json`

**Implementation:**

```json
{
  "model": "claude-sonnet-4-5",
  "permissions": {
    "allow": [
      "Bash(python3 .claude/skills/usage-report/scripts/summarize_usage.py:*)"
    ]
  }
}
```

Then in the project's `CLAUDE.md`, make the escalation rule explicit and legible to both humans and the model:

```markdown
## Model policy

Default model for this project is Sonnet (set in `.claude/settings.json`).
Switch to Opus with `/model opus` only for:
- Multi-file architectural decisions with real tradeoffs to weigh.
- Debugging a failure that has already resisted one Sonnet attempt.
- Anything explicitly marked high-stakes in the task description.

Switch back to Sonnet afterward — Opus is not the new default.
```

**Why:** `settings.json` is read on every Claude Code launch in this directory, so the default model is enforced for anyone who opens the project — not dependent on each person remembering to run `/model sonnet`. Writing the escalation rule into `CLAUDE.md` means the *model itself* also sees the policy (it's loaded into context), so it can proactively suggest "this looks like an Opus-tier task" rather than silently reasoning at reduced depth on something that needed more.

**Expected result:** New sessions start on Sonnet by default; Opus usage becomes a deliberate, visible decision instead of ambient default behavior.

---

### Step 5 — Compute real cost from a real `usage` block

**Goal:** Take one actual API response's `usage` object and get an exact dollar figure, broken down by component — not an estimate.

**Files involved:** `cost_calculator.py`

**Implementation:**

```python
#!/usr/bin/env python3
"""
cost_calculator.py — exact cost breakdown for one Anthropic API response.

Paste the `usage` block from a real response (from Claude Code's /cost
output, or the raw API JSON) to see exactly where the dollars went.
"""
from dataclasses import dataclass

PRICING = {
    "claude-opus-4":   {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "claude-sonnet-4":  {"input": 3.00,  "output": 15.00, "cache_write": 3.75,  "cache_read": 0.30},
    "claude-haiku-4":   {"input": 0.80,  "output": 4.00,  "cache_write": 1.00,  "cache_read": 0.08},
}


@dataclass
class CostBreakdown:
    input_cost: float
    output_cost: float
    cache_write_cost: float
    cache_read_cost: float

    @property
    def total(self):
        return self.input_cost + self.output_cost + self.cache_write_cost + self.cache_read_cost

    def report(self):
        lines = [
            f"  input tokens:        ${self.input_cost:.6f}",
            f"  output tokens:       ${self.output_cost:.6f}",
            f"  cache writes:        ${self.cache_write_cost:.6f}",
            f"  cache reads:         ${self.cache_read_cost:.6f}",
            f"  {'-'*35}",
            f"  total:               ${self.total:.6f}",
        ]
        return "\n".join(lines)


def breakdown(model: str, usage: dict) -> CostBreakdown:
    rates = PRICING[model]
    return CostBreakdown(
        input_cost=usage.get("input_tokens", 0) / 1e6 * rates["input"],
        output_cost=usage.get("output_tokens", 0) / 1e6 * rates["output"],
        cache_write_cost=usage.get("cache_creation_input_tokens", 0) / 1e6 * rates["cache_write"],
        cache_read_cost=usage.get("cache_read_input_tokens", 0) / 1e6 * rates["cache_read"],
    )


if __name__ == "__main__":
    # Example: a Claude Code turn with a large cached system prompt/CLAUDE.md
    # (cache_creation on the first call, cache_read on every call after).
    first_call = {
        "input_tokens": 400,
        "output_tokens": 250,
        "cache_creation_input_tokens": 9000,   # CLAUDE.md + skills cached here
        "cache_read_input_tokens": 0,
    }
    later_call = {
        "input_tokens": 400,
        "output_tokens": 300,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 9000,        # same context, now cheap
    }

    print("First call (cache miss):")
    print(breakdown("claude-sonnet-4", first_call).report())

    print("\nLater call (cache hit):")
    print(breakdown("claude-sonnet-4", later_call).report())
```

Running it:

```bash
python3 cost_calculator.py
```

```text
First call (cache miss):
  input tokens:        $0.001200
  output tokens:       $0.003750
  cache writes:        $0.033750
  cache reads:         $0.000000
  -----------------------------------
  total:               $0.038700

Later call (cache hit):
  input tokens:        $0.001200
  output tokens:       $0.004500
  cache writes:        $0.000000
  cache reads:         $0.002700
  -----------------------------------
  total:               $0.008400
```

**Why:** This example is deliberately built around the same 9,000 tokens of context (a `CLAUDE.md` + loaded skills, say) treated two ways: paid once at the cache-write rate (1.25× input) on the first call, then paid on every later call at the cache-read rate (0.1× input) instead of full input price. The later call is roughly **4.6× cheaper** than it would be if that context were resent as fresh input every turn — which is the actual mechanism behind "caching saves money," made concrete instead of asserted.

**Expected result:** You can paste in any real `usage` block and immediately see which of the four components is driving cost, and whether your session is actually benefiting from caching or paying full price every turn because the cached prefix keeps changing (e.g., if `CLAUDE.md` or the skill set is edited mid-session, invalidating the cache).

---

### Step 6 — Submit a batch job and know when it's worth it

**Goal:** Move a real, latency-tolerant workload (bulk document summarization) off the interactive API and onto the Message Batches API at half price.

**Files involved:** `batch_submit.py`

**Implementation:**

```python
#!/usr/bin/env python3
"""
batch_submit.py — submit a batch of summarization requests, then poll
for completion. Requires: pip install anthropic
"""
import time
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

documents = [
    {"id": "doc-1", "text": "..."},   # replace with real document text
    {"id": "doc-2", "text": "..."},
]

requests = [
    {
        "custom_id": doc["id"],
        "params": {
            "model": "claude-sonnet-4-5",
            "max_tokens": 512,
            "messages": [
                {"role": "user", "content": f"Summarize in 3 bullet points:\n\n{doc['text']}"}
            ],
        },
    }
    for doc in documents
]

batch = client.messages.batches.create(requests=requests)
print(f"Submitted batch {batch.id}, status: {batch.processing_status}")

while True:
    batch = client.messages.batches.retrieve(batch.id)
    if batch.processing_status == "ended":
        break
    print(f"...still processing ({batch.processing_status}), checking again in 30s")
    time.sleep(30)

for result in client.messages.batches.results(batch.id):
    print(f"{result.custom_id}: {result.result.type}")
    if result.result.type == "succeeded":
        print(result.result.message.content[0].text)
```

**A break-even rule for "should this be a batch job?":**

```python
def should_batch(is_latency_tolerant: bool, needs_response_within_minutes: bool) -> bool:
    """
    Batch API: ~50% of interactive price, results within a variable
    window (typically well under the 24h SLA ceiling).
    Use it whenever nothing downstream is blocked waiting on the response.
    """
    if needs_response_within_minutes:
        return False  # interactive API — Claude Code always falls in this bucket
    return is_latency_tolerant


# A live chat session, or Claude Code itself: never batch.
# A nightly job that summarizes yesterday's 5,000 support tickets: always batch.
```

**Why:** Claude Code is inherently interactive — every batch job would block the very conversation it's part of, so the batch API is never the right tool *inside* a Claude Code session. It becomes relevant the moment you're writing a script or pipeline *around* Claude that has no live user waiting on the result: bulk summarization, offline evals, dataset labeling. The price difference (roughly half of standard input/output pricing) is real and stacks with prompt caching if your batch requests also share a long, stable prefix.

**Expected result:** A workload correctly identified as batch-eligible now costs about half what running the same requests through the interactive API would — with the tradeoff being that you get results on a job-completion timeline, not turn-by-turn.

---

## 5. Errors and Debugging

**Error:** `claude mcp list` shows the `atlassian` server as configured but with no tools available.
**Cause:** The OAuth handshake `mcp-remote` needs hasn't completed — common the first time a project opens in a new machine, or in any non-interactive/headless run where there's no browser to redirect to.
**Fix:** Open an interactive Claude Code session in this directory and run `/mcp` to trigger and complete the browser auth flow once; it persists after that. Don't attempt this from a cron job or CI runner — it has no browser to complete the redirect.
**Lesson:** Remote OAuth-based MCP servers are environment-dependent. A script that works on your laptop can silently lose that server in a scheduled/headless context.

**Error:** `summarize_usage.py` throws `KeyError` on `record["usage"]`.
**Cause:** The JSONL log has a line that isn't a full API response object — often a partial/streamed chunk logged by mistake, which has a different shape than the final message's `usage` block.
**Fix:** Log only the final response object per call (or specifically its `usage` field), not intermediate streaming events.
**Lesson:** Streaming responses emit multiple event types; only the final `message_delta`/`message_stop` event carries the authoritative `usage` totals for that call.

**Error:** Cache-hit rate in the usage report stays near 0% even though the same `CLAUDE.md` and skills are loaded every turn.
**Cause:** Something in the cached prefix is changing between calls — a timestamp, a dynamically-injected value, or an edited file — which invalidates the cache and forces a fresh `cache_creation` on every turn instead of a `cache_read`.
**Fix:** Keep anything volatile (current time, request IDs) *after* the stable, cacheable prefix in the prompt structure, never inside it.
**Lesson:** Prompt caching works on an exact-prefix match; a single changed token anywhere before the cache boundary invalidates the entire cached block, not just the changed part.

**Error:** `batch_submit.py` result for a given `custom_id` has `result.type == "errored"`.
**Cause:** One request in the batch hit a per-request error (e.g., an oversized document exceeding context, or a malformed `messages` array) — batch failures are per-item, not per-batch.
**Fix:** Inspect `result.result.error` for that `custom_id` and resubmit only the failed items in a follow-up batch; don't resubmit the whole batch.
**Lesson:** The Message Batches API isolates failures per request — a bad document in a 5,000-item batch doesn't sink the other 4,999.

---

## 6. Final Files

**`.claude/skills/changelog-entry/SKILL.md`** — see Step 1 in full above.

**`.claude/skills/usage-report/SKILL.md`** and **`.claude/skills/usage-report/scripts/summarize_usage.py`** — see Step 2 in full above.

**`.mcp.json`**

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"]
    },
    "filesystem-readonly": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/you/Documents/reference-docs"]
    }
  }
}
```

**`.claude/settings.json`**

```json
{
  "model": "claude-sonnet-4-5",
  "permissions": {
    "allow": [
      "Bash(python3 .claude/skills/usage-report/scripts/summarize_usage.py:*)"
    ]
  }
}
```

**`cost_calculator.py`** — see Step 5 in full above.

**`batch_submit.py`** — see Step 6 in full above.

---

## 7. Running the Project

```bash
# 1. Open the project — skill + MCP + settings load automatically
cd claude_usage_optimization
claude

# 2. Confirm MCP servers are connected
claude mcp list

# 3. Inside Claude Code, trigger each skill
#    "write a changelog entry for this diff: <paste diff>"
#    "summarize my usage from usage_log.jsonl"

# 4. Run the cost tooling directly, outside Claude Code
python3 cost_calculator.py
python3 .claude/skills/usage-report/scripts/summarize_usage.py usage_log.jsonl

# 5. Submit a real batch job (requires: pip install anthropic)
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
python3 batch_submit.py
```

---

## 8. Testing

- **`changelog-entry` skill:** feed it a diff with two unrelated changes and confirm you get two separate bullet lines, correctly classified — a single merged line means the skill's "one line per effect" rule didn't apply.
- **`usage-report` skill:** build a tiny 2-line `usage_log.jsonl` by hand with known token counts, run `summarize_usage.py` directly, and hand-check the printed cost against the `cost_of()` math — this validates the script independent of Claude Code.
- **MCP servers:** `claude mcp list` should show both servers as connected; ask a question that requires a live Jira lookup and confirm the answer reflects current ticket state, not a guess.
- **`cost_calculator.py`:** the two example calls in Step 5 should print a cache-hit total noticeably lower than the cache-miss total for the same context size — if they're roughly equal, the cache-read rate in `PRICING` is misconfigured.
- **`batch_submit.py`:** submit a 2-item batch, confirm both `custom_id`s come back in `results()`, and verify at least one via `result.result.type == "succeeded"`.

---

## 9. Common Mistakes

1. **Vague skill descriptions.** If `description` doesn't name the actual phrases people use, the skill silently never triggers — there's no error, it just doesn't fire.
2. **Doing arithmetic in the prompt instead of in a script.** Token/cost totals should come from `summarize_usage.py`-style code, not from the model "computing" them in natural language.
3. **Letting a volatile value sit before the cacheable prefix.** One changed token before the cache boundary (a timestamp, a request ID) invalidates the whole cached block and quietly kills your cache-hit rate.
4. **Defaulting to Opus.** Set the default in `settings.json` to Sonnet and make Opus an explicit `/model opus` escalation, not the ambient choice.
5. **Trying to batch something with a live user waiting on it.** Batch is for pipelines with no one blocked on the response — never for a Claude Code session itself.
6. **Resubmitting an entire batch after one item errors.** Batch failures are per-`custom_id`; only resubmit the failed ones.

---

## 10. Final Explanation

Skills and MCP servers extend *capability*: a skill encodes a procedure once (with a script doing any real computation) so it's applied consistently instead of re-derived every session; an MCP server gives Claude Code live tool access to systems like Atlassian, or to a scoped local filesystem, instead of manual copy-pasting. `settings.json` and `CLAUDE.md` turn *model choice* into an enforced default with a deliberate, visible escalation path, rather than a habit everyone has to remember. And the cost tooling — `cost_calculator.py` and `summarize_usage.py` — makes *spend* legible by breaking every call into its four real components (input, output, cache-write, cache-read) instead of treating "cost" as one number, which is also what tells you, concretely, whether prompt caching is actually working in a given session. `batch_submit.py` extends the same cost discipline outside Claude Code: any pipeline you build on the API that isn't blocking on a live user is a candidate for half-price batch processing. Together these four pieces are the whole toolkit for running Claude Code capably *and* cheaply, instead of picking one at the expense of the other.
