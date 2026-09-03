# 06 — Distributed Systems & Backend

> JD: Kafka, Redis, Kubernetes, AWS (EKS, MSK, RDS), low-latency inference, high-throughput APIs, cost reduction. This is your foundation — and the round where you differentiate from "AI-only" candidates. **Bring numbers.**

---

## 🟥 Kafka (event-driven AI services)

**Core concepts (crisp):** topics → partitions (unit of parallelism + ordering), producers, consumers, **consumer groups** (scale-out + rebalancing), offsets, brokers, replication factor, ISR. **Ordering is per-partition only** — pick partition keys deliberately.

**Delivery semantics:** at-most-once / at-least-once / **exactly-once** (idempotent producer + transactions). Default reality = at-least-once → **make consumers idempotent**.

**AI-specific Kafka patterns (tie to the role):**
- **Async inference / decoupling** — request events → topic → inference workers consume → results topic. Decouples spiky LLM latency from the request path; smooths load; natural backpressure.
- **Re-indexing pipeline** — doc-change events → embedding workers → vector store (see [03](03_RAG_and_Retrieval.md)).
- **Agent orchestration via events** — long-horizon steps as events enable durability, replay, and audit (every step is an immutable event → aligns with fintech auditability).
- **Fan-out** — one event → multiple consumers (eval logging, monitoring, downstream triggers).

**Principal-level concerns:** partition strategy & hot partitions, consumer lag monitoring, poison-pill / DLQ handling, schema evolution (**Schema Registry**, Avro/Protobuf), rebalancing storms, throughput vs latency (batching, `linger.ms`), retention/compaction. On AWS: **MSK** (managed Kafka).

**Backpressure story:** LLM calls are slow + rate-limited. Kafka buffers; consumers pull at sustainable rate; scale consumers on lag; DLQ for repeated failures; cap concurrency to respect provider rate limits.

---

## 🟦 Redis (low-latency layer)

Use cases (pick the right one per scenario):
- **Semantic cache** — cache LLM responses keyed by embedding similarity; huge cost/latency win for repeated/similar queries. Also exact-match prompt cache.
- **Rate limiting** — token bucket / sliding window per user/tenant (protect provider quotas + cost).
- **Session / conversation memory** — short-term agent state, chat history, with TTL.
- **Vector search** — Redis as a vector store (RediSearch) for low-latency retrieval when you want one system.
- **Distributed locks / dedup / idempotency keys** — coordinate workers, dedupe events.
- **Queues / streams** — Redis Streams for lighter-weight eventing than Kafka.

**Trade-offs to volunteer:** eviction policy (LRU/LFU), persistence (RDB vs AOF) vs pure cache, cluster mode + sharding, memory pressure, cache invalidation (the hard problem — TTL + event-driven invalidation), semantic-cache staleness/false-hit risk (a near-miss returning a wrong cached answer is dangerous in fintech → tune similarity threshold conservatively).

---

## ⚡ Low-latency LLM inference (they named it)

Levers (know each):
- **Serving stack:** vLLM / TGI / TensorRT-LLM — **continuous batching**, **PagedAttention** (KV-cache mgmt), tensor parallelism.
- **KV cache** — the dominant memory/latency factor in generation; prefix caching reuses shared prompt prefixes (system prompts, few-shots).
- **Quantization** — INT8/FP8/4-bit for throughput + memory (accuracy trade-off).
- **Speculative decoding** — small draft model proposes, big model verifies → lower latency.
- **Streaming** — stream tokens for perceived latency (TTFT matters as much as total).
- **Routing / model cascade** — cheap/small model first, escalate to big only when needed; route by task complexity.
- **Semantic caching** — skip inference entirely for repeats (Redis).
- **Batching** — throughput vs latency trade-off; continuous batching gets both.
- **Prompt compression / shorter context** — fewer tokens = faster + cheaper.

**Metrics vocabulary:** **TTFT** (time-to-first-token), **TPOT/ITL** (inter-token latency), throughput (tokens/sec, req/sec), p95/p99. Optimize the one the product cares about (chat → TTFT; batch → throughput).

**Self-host vs API decision:** self-host (open model) for cost at scale, data residency, latency control, customization; API for speed-to-value, best quality, no ops. → build-vs-buy ([09](09_Leadership_and_Behavioral.md)).

---

## ☸️ Kubernetes / AWS

- **EKS** — orchestration; for GPU inference: node groups with GPU instances, autoscaling (HPA on custom metrics like queue depth/GPU util, **KEDA** on Kafka lag, Karpenter/cluster-autoscaler for nodes), scale-to-zero for spiky workloads.
- **GPU cost control** — spot for batch/eval, right-sizing, bin-packing, scale on real demand signals not CPU, share GPUs (MIG / fractional), off-hours scale-down. **This is your "reduced AWS spend" story — quantify it.**
- **MSK** (Kafka), **RDS** (Postgres — pgvector option), **OpenSearch** (hybrid search), **S3** (docs/data lake), **Bedrock** (managed foundation models — you have experience; relevant for a hosted-model path), **SQS/SNS/EventBridge** (lighter eventing), **ElastiCache** (Redis).
- **Reliability:** multi-AZ, health checks, graceful shutdown (drain in-flight LLM calls), circuit breakers on provider APIs, timeouts + retries with jittered backoff, bulkheads.

---

## 🏗️ High-throughput API design

- Async/non-blocking (FastAPI + async, or Node) — LLM calls are I/O-bound; don't block workers.
- **Streaming responses** (SSE/websockets) for LLM output.
- **Long-running work** → accept + return job id + poll/webhook, or push through Kafka (don't hold HTTP connections for 30s agent runs).
- Idempotency keys, rate limiting (Redis), auth/tenancy, request validation, graceful degradation (fallback model / cached answer on overload).
- Timeouts + retries + circuit breakers around every model/tool call.

---

## 🎙️ Likely questions + scaffolds

- **"Design an async event-driven inference service."** → API accepts request → publish to Kafka → inference workers (K8s, autoscaled on lag via KEDA) consume → call model (vLLM or Bedrock) → results topic → callback/websocket to client. Redis semantic cache in front. Backpressure via consumer pull + concurrency cap. DLQ for failures. Metrics: lag, TTFT, cost/req. → also [07](07_System_Design_HLD_LLD.md).
- **"How did you reduce latency / AWS cost?"** → (your real story) + generalizable levers: semantic caching (X% hit → Y% fewer calls), model routing/cascade, continuous batching, right-sizing GPUs + spot + autoscale-on-lag, prompt compression. **Give before/after numbers.**
- **"Exactly-once vs at-least-once for inference events?"** → at-least-once + idempotent consumers is usually right (idempotency key in Redis/DB, dedupe on it); exactly-once via Kafka transactions costs throughput — justify only when duplicate side-effects are unacceptable (e.g., don't double-charge / double-post a ledger entry).
- **"Redis for LLM caching — risks?"** → semantic cache false hits (conservative similarity threshold, especially fintech), staleness (TTL + event invalidation), memory/eviction. Never semantic-cache anything whose answer depends on live/private state without keying on it.
- **"Kafka consumer lag is growing — what do you do?"** → check: slow consumer (scale out / optimize / increase concurrency within rate limits), hot partition (repartition/rekey), poison pill (DLQ), downstream (model rate limit → this is backpressure working; add capacity or degrade gracefully). Alert on lag, autoscale on it.
