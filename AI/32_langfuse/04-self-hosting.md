# 04 · Self-Hosting — the Reason Most Teams Are Here

> ← [`03-setup-and-keys.md`](03-setup-and-keys.md) · **Next:** [`05-the-observe-decorator.md`](05-the-observe-decorator.md) →

---

Lesson 01 named this as the headline difference. This lesson is what it actually costs, because "self-hostable" on a landing page and "we run this in production" are separated by four stateful services.

---

## 1. What you are agreeing to run

LangFuse self-hosted is **two application containers plus four stateful backing services**:

```
┌─────────────────────┐   ┌─────────────────────┐
│   LangFuse Web      │   │  LangFuse Worker    │
│   UI + APIs         │   │  async event        │
│   (ingestion entry) │   │  processing         │
└──────────┬──────────┘   └──────────┬──────────┘
           │                          │
    ┌──────┴──────────────────────────┴──────┐
    │                                         │
┌───▼────────┐ ┌──────────┐ ┌────────────┐ ┌─▼──────────────┐
│ PostgreSQL │ │ClickHouse│ │Redis/Valkey│ │ S3 / blob      │
│            │ │          │ │            │ │ storage        │
│transactional│ │traces,   │ │queue +     │ │raw events,     │
│  data       │ │observ-   │ │cache       │ │multi-modal     │
│             │ │ations,   │ │            │ │inputs, exports │
│             │ │scores    │ │            │ │                │
└─────────────┘ └──────────┘ └────────────┘ └────────────────┘
```

Per the docs, each has a distinct job:

| Component | Role (docs' wording) |
|---|---|
| **PostgreSQL** | *"The main database for transactional workloads"* — projects, users, prompts, config |
| **ClickHouse** | *"High-performance OLAP database which stores traces, observations, and scores"* |
| **Redis / Valkey** | *"Used for queue and cache operations"* |
| **S3 / blob storage** | *"Object storage to persist all incoming events, multi-modal inputs, and large exports"* |

> **The ClickHouse row is the one to notice.** Traces are an append-heavy, analytically-queried workload — "p95 latency by prompt version over 30 days across 40M observations" is an OLAP query, not an OLTP one. Postgres alone would not do it at volume, which is why the architecture is split rather than simple.
>
> The practical consequence: **if your organisation has no ClickHouse operational experience, that is the real cost of self-hosting**, not the LangFuse containers. Backups, upgrades, disk growth and query tuning for ClickHouse are the parts that will actually take your time.

### ⚠️ The requirement that will bite you

> *"All infrastructure components (ClickHouse and Postgres) **must** run with their timezone set to UTC."*

Non-UTC configurations **cause query failures**. Worth writing into your deployment checklist rather than discovering from a broken dashboard, because the symptom (queries failing or returning wrong windows) does not point at a timezone.

---

## 2. Docker Compose — for evaluation, not production

```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up
```

Then `http://localhost:3000` — or `http://<instance-ip>:3000` on a VM. Create an account in the UI, make a project, take the keys, and point lesson 03's `.env` at it:

```bash
LANGFUSE_BASE_URL=http://localhost:3000
```

### Change the secrets

The docs are explicit: *"All sensitive lines are marked with `# CHANGEME`"* in `docker-compose.yml`, and *"make sure to select long, random passwords for all secrets."*

```bash
grep -n "CHANGEME" docker-compose.yml
```

Do that before it is reachable by anything but your laptop. A default-credentialled observability stack holds every prompt and every retrieved document your app has processed.

### The stated limitations — read these before planning on it

| Limitation (docs) | Consequence |
|---|---|
| *"lacks high-availability, scaling capabilities, and backup functionality"* | A node loss is an outage **and** potentially data loss |
| *"does not support horizontal scaling without an additional Load Balancer"* | Single instance |
| Scaling is **vertical only** | More throughput means a bigger VM |
| MinIO (the default blob store) *"is not accessible from outside the Docker network for direct uploads"* | Breaks flows needing direct client uploads |

> **The docs recommend Kubernetes for production**, and that recommendation should be taken at face value. Docker Compose is the right way to evaluate LangFuse in an afternoon and the wrong way to depend on it — "no backup functionality" is not a caveat you engineer around after the fact.

---

## 3. Licensing — what I can and cannot tell you

**What the docs say:** the core self-hosting is open source; *"some add-on features require a license key"*; some features are marked **"(EE)"** for Enterprise Edition.

**What I am not going to do** is enumerate the split from memory. The overview page I read does not list it, and a wrong list here is worse than no list — you would plan around a feature that turns out to be gated, or self-host to avoid a cost that was never charged.

**So: check the licensing page for any feature you intend to depend on**, and specifically before you commit an architecture to it. The features most worth verifying, because they are the ones teams assume:

- SSO / SAML enforcement
- Fine-grained RBAC beyond basic roles
- Data retention policies and automated deletion
- Audit logs
- Annotation-queue capabilities at scale

Nor does the overview page give **minimum resource requirements** (CPU, memory, disk). Size ClickHouse from your own expected trace volume and payload sizes — lesson 13 has the arithmetic shape — rather than from a number I would be inventing.

---

## 4. When self-hosting is right, and when it is theatre

The honest version, because self-hosting has a real ongoing cost and is sometimes chosen for reasons that do not survive examination.

### Genuinely right

| Situation | Why |
|---|---|
| **Trace payloads legally cannot leave your infrastructure** | The case from lesson 01. Masking is damage limitation; this is the answer |
| **A customer DPA forbids sub-processors** for this data class | Not negotiable by engineering |
| **Air-gapped or heavily network-restricted environment** | No hosted option works |
| **You want no vendor dependency on a load-bearing tool** | Legitimate long-horizon reasoning |
| **Trace volume makes per-unit cloud pricing worse than running it** | Do the arithmetic; at high volume this flips |

### Usually theatre

| Situation | Why it doesn't hold |
|---|---|
| "Self-hosting is cheaper" | Four stateful services plus ClickHouse expertise plus on-call is rarely cheaper than a SaaS bill until real volume |
| "We prefer to own our data" as a stance | If nothing in policy or contract requires it, you have bought an operational burden with a feeling |
| "It's open source so it's free" | The licence is free. Running it is not |
| To avoid a procurement conversation | You have moved the cost from procurement to your own on-call rota, and hidden it |

> **The test I would apply:** can you name the specific policy, regulation or contract clause that forbids the hosted option? If yes, self-host and budget the ClickHouse work honestly. If no, use the cloud — and note that a **regional or HIPAA instance** (lesson 03) satisfies a large share of residency requirements without you running anything.
>
> That middle option is the one most often missed: the choice is not binary between "US SaaS" and "our own Kubernetes".

---

## 5. If you do self-host, the operational shortlist

Not exhaustive, and each item is a real piece of work:

- [ ] **Kubernetes**, not Compose, for anything depended upon
- [ ] **UTC on ClickHouse and Postgres** — the hard requirement above
- [ ] All `CHANGEME` secrets replaced with long random values
- [ ] **Backups for Postgres *and* ClickHouse**, and a *tested restore* — an untested backup is a belief
- [ ] ClickHouse disk-growth monitoring and a retention policy, because trace volume grows with your app's success
- [ ] TLS termination and authentication in front of the web container
- [ ] SSO wired up if your org requires it — **verify whether it needs a licence key**
- [ ] Upgrade path rehearsed; schema migrations across two databases are not automatic
- [ ] A named owner. An unowned observability stack fails silently and is discovered during the incident it was meant to help with

> That last item is the one that actually determines whether this works. **A self-hosted observability platform that nobody owns is worse than no observability platform**, because the team believes it is instrumented. Same structural point as [`../30_langsmith/17-production-hardening.md`](../30_langsmith/17-production-hardening.md) §4: tracing fails silently by design, so someone has to be responsible for noticing.

---

## Recap

- Self-hosted LangFuse = **2 app containers + Postgres + ClickHouse + Redis/Valkey + blob storage**.
- **ClickHouse is there because traces are an OLAP workload** — and if your org has no ClickHouse experience, that is the true cost of self-hosting.
- **Postgres and ClickHouse must run in UTC**, or queries fail.
- `git clone` + `docker compose up` + port 3000 gets you evaluating in minutes; replace every `CHANGEME`.
- Compose has **no HA, no horizontal scaling and no backups** — the docs recommend Kubernetes for production and mean it.
- **Licensing:** open-source core, some add-ons need a key, some features marked (EE). Verify the specific features you depend on; I am not guessing the split.
- Self-host when a **named policy, regulation or contract** requires it. Otherwise the regional/HIPAA cloud instances are the option people forget.
- If you self-host: tested restores for both databases, retention policy, and **a named owner**.

---

## Self-check

1. Why does LangFuse need ClickHouse in addition to Postgres?
2. Which single infrastructure setting will silently break your dashboards, and on which two components?
3. Name three things Docker Compose does not give you that production needs.
4. A colleague argues self-hosting is cheaper. What do you ask them?
5. What is the middle option between hosted-US-SaaS and running your own Kubernetes?

---

**Next:** [`05-the-observe-decorator.md`](05-the-observe-decorator.md) →
