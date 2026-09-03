# 08 — Coding & DSA

> At Principal level the coding bar is "clearly competent, clean, pragmatic" — not competitive-programming speed. Expect practical problems, maybe one medium algorithmic, and possibly an AI-flavored implementation. JD stresses DS/Algo + HLD/LLD, so don't skip fundamentals.

---

## 🎯 What to actually expect

1. **Practical / applied coding** — implement a rate limiter, LRU cache, a retry-with-backoff wrapper, a simple in-memory vector search, parse/transform data, a mini agent loop. **Most likely bucket for this role.**
2. **One medium DSA** — arrays/hashmaps/strings/intervals/graphs/heaps. Rarely hard-DP or obscure stuff at Principal.
3. **Python fluency + async** — since AI services are Python; async/concurrency is fair game.
4. **Code review / debugging** — they show you code, you find issues (Principal-flavored).

---

## 📋 Focused DSA list (highest ROI, ~2 hrs each block)

- **Hash maps / sets** — dedup, frequency, two-sum family, grouping. (Most common.)
- **Two pointers / sliding window** — subarray/substring, rate-window problems.
- **Heaps / priority queue** — top-k, merge k lists, streaming median. (Top-k ≈ retrieval reranking flavor.)
- **Intervals** — merge/insert/overlap.
- **Graphs / BFS-DFS / topological sort** — dependency resolution, agent/DAG execution order. **Very on-theme** (agent graphs, tool dependency).
- **Binary search** — on answer / on sorted data.
- **Stacks / queues** — parsing, monotonic stack.
- **Strings** — parsing, tokenizing (relevant to text processing).
- Light: **DP** (know the pattern: climbing stairs, coin change, LCS) but don't over-invest.
- **Trie** — autocomplete / prefix (relevant to search).

Skip: heavy DP, segment trees, advanced graph algos — unlikely for this role.

---

## 🐍 Python patterns to have at your fingertips

```python
# collections
from collections import defaultdict, Counter, deque
from heapq import heappush, heappop, nlargest, nsmallest

# top-k (reranking flavor)
nlargest(k, items, key=lambda x: x.score)

# LRU cache
from functools import lru_cache          # decorator
from collections import OrderedDict       # manual LRU for interviews

# async — LLM/tool calls are I/O bound
import asyncio
async def gather_calls(coros): return await asyncio.gather(*coros)
sem = asyncio.Semaphore(10)               # cap concurrency (provider rate limits)

# retry with backoff
async def with_retry(fn, retries=3, base=0.5):
    for i in range(retries):
        try: return await fn()
        except TransientError:
            if i == retries - 1: raise
            await asyncio.sleep(base * 2**i)   # exponential backoff (add jitter in prod)
```

**Async is a likely differentiator** — be ready to write concurrent-with-bounded-concurrency LLM calls (gather + semaphore), and explain why (I/O-bound, rate limits, backpressure).

---

## 🧪 Likely applied problems (practice writing these cleanly)

1. **Token-bucket / sliding-window rate limiter** — class with `allow(key) -> bool`. (Ties to [06](06_Distributed_Systems_Backend.md).)
2. **LRU cache** — `get`/`put` O(1) with OrderedDict or dict+DLL. Then: "make it a semantic cache" discussion.
3. **Retry wrapper with exponential backoff + jitter** — decorator/higher-order fn.
4. **Mini in-memory vector search** — cosine similarity, return top-k. Then discuss how it scales (ANN, HNSW).
5. **Simple agent loop** — `while not done and steps < budget:` reason → pick tool → execute → observe. Shows you understand [02](02_Agentic_AI_and_Orchestration.md) in code.
6. **Topological sort of a task/tool DAG** — execution order with cycle detection.
7. **Merge k sorted streams** (heap) — result aggregation flavor.
8. **Parse/stream JSON tokens / chunk text with overlap** — chunking flavor from [03](03_RAG_and_Retrieval.md).

---

## 🎙️ Live-coding tips (Principal edition)

- **Clarify inputs/outputs/constraints/edge cases before coding.** Restate the problem.
- **Talk while you code**, but don't narrate every keystroke — narrate *decisions*.
- **Start with the signature + a brute force**, state complexity, then optimize. Working > clever.
- **Name complexity** (time + space) unprompted.
- **Handle edge cases** (empty, nulls, duplicates, huge input, concurrency).
- **Write it clean** — good names, small functions, no premature abstraction. They're evaluating you as someone who sets the code bar.
- **Test it** — walk a small example, mention how you'd unit-test.
- **Connect to real systems** — "in prod I'd back this with Redis / add metrics here" earns Principal points.
- If stuck: say your approach out loud, ask for a hint gracefully — collaboration is a signal, not a weakness.

---

## ⏱️ Practice plan

- ~15–20 curated mediums across the categories above (2–3 days). Use the applied list first — it's the likeliest.
- 2–3 timed 45-min mock sessions, out loud.
- Rehearse the async-LLM-calls and agent-loop snippets until you can write them from memory.
