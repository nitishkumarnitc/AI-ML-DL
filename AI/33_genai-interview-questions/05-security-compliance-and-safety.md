# 05 · Security, compliance, and safety

> ← [`04-production-cost-latency-and-monitoring.md`](04-production-cost-latency-and-monitoring.md) · **Index:** [`README.md`](README.md) · **Next:** [`06-agentic-ai-and-mcp.md`](06-agentic-ai-and-mcp.md) →

---

## Q14 — How do you build a HIPAA-compliant GenAI app for a hospital?

The pipeline given, in order:

**1. Use a HIPAA-compliant provider path** — e.g. Azure OpenAI under a **BAA (Business Associate Agreement)**, or a self-hosted model. **Never use the public OpenAI API without a BAA in place** — this is stated as an absolute, not a preference.

**2. De-identify data before it ever reaches the LLM** — strip name, ID, address, and any other identifying field *before* the data is sent.

**3. Encrypt everything in transit** — TLS, AES-256.

**4. Implement audit logs** — who accessed what data, and when.

**5. Apply output filters** — scan the LLM's response before returning it to the user.

### What a BAA actually is (explained in the transcript)

A **Business Associate Agreement** is a formal agreement your company signs with the cloud provider (e.g. Microsoft, for Azure OpenAI) that legally covers how patient data can be processed through their service. Using the *public* OpenAI API — without going through a cloud provider's BAA-covered offering — is explicitly called out as **the wrong choice** for anything handling patient data, because there's no such agreement in place.

### The worked example

> A hospital wants AI to summarize patient notes for doctors. The pipeline: **strip patient name/ID from the notes** (using something like Azure's PII-detection/redaction service) → **send the de-identified notes to Azure OpenAI under the BAA** → **get the summary back** → **re-insert the patient's name only for the authorized doctor viewing it**, after the AI step is done. The name never touches the model.

---

## Q15 — How do you prevent sensitive data from leaking through an LLM?

Four layers, and this is explicitly the **same four-layer defensive shape** used again in the prompt-injection answer (Q18) — worth noticing as a reusable pattern rather than four separate techniques:

| Layer | What it does |
|---|---|
| **Input filtering** | Scan every user query *before* it reaches the LLM, looking for attempts to extract sensitive data. This is also called **jailbreak detection** — validate the query before it's ever passed to the model |
| **Context filtering** | Mask sensitive fields (account numbers, SSNs) *inside the retrieved documents* before they're sent to the LLM as context |
| **Output filtering** | Use regex or an ML classifier to check the LLM's **output** for leaks before it's ever returned to the user |
| **Audit trail** | Log every request for later review |

### The worked example

> A bank's chatbot is asked: *"Can you list the five customers with the highest loan amount?"* Without protection, the LLM could actually answer with real customer names. **With input filtering**, the query itself is flagged as a privacy-violating request and blocked *before* it reaches the model. The bot replies: *"I can't share information about specific customers."*

---

## Q16 — How do you implement role-based access control (RBAC) in a RAG system?

The mechanism: **attach role/access metadata to every document at indexing time.**

```
INDEXING TIME
  Every document gets tagged with metadata: which role can access it
  (e.g. "manager", "HR", "engineering"), and its access level.

QUERY TIME
  The user's identity comes from their auth token (JWT) — NEVER from
  the request body. The system extracts the user's role from the
  server-side-verified JWT, then filters retrieval results to only
  documents whose access-level metadata matches or is below the
  user's own access level.
```

> **The critical rule, stated as an absolute:** *"Never let the role come from the user's request body — always extract it from the server-side JWT/auth token."* Trusting a client-supplied role field is the exact vulnerability this whole design exists to prevent.

Additionally: even after retrieval is properly filtered, the final LLM-generation step should be instructed to **only use the provided (already-filtered) context** and not infer or draw on anything outside it.

> **The analogy:** *"Like a building with key cards — each card only opens certain doors. Even if you sneak into a restricted area, a metadata check (the sensor) catches you."*

### The worked example — the failure case

> An HR chatbot **accidentally let a junior employee ask "what is the CEO's salary?"** and it returned the actual answer — because **role-based filtering wasn't correctly implemented**. The fix: tag every salary document with an access level (e.g. "admin only"), so a query from a junior employee's role is filtered out **before** it ever reaches generation. **"This is the classic security mistake — pull identity from the JWT token, never from the request body."**

---

## Q17 — How do you handle PII (Personally Identifiable Information) in training data?

**1. Scan all training data with a PII-detection tool** (named examples: Microsoft's and AWS's PII-scanning services).

**2. Mask/remove the identifying fields** — names, emails, phone numbers, addresses — replacing them with consistent placeholders (e.g. every instance of a name becomes `[NAME]`, consistently, not just deleted).

**3. Manually spot-check ~1%** of the data to verify the automated scan actually caught everything.

**4. Run an extraction attack against your own fine-tuned model** to test whether PII can still be extracted from it, even after the training data was cleaned — because a model can sometimes memorize and regurgitate training examples even if the raw dataset looked clean.

> **The analogy:** *"Like preparing a case study for a class — you change all names, locations, and dates before sharing a real patient's story, so that even if students discuss the case study, no one can identify the real patient. AI training data needs the exact same treatment."*

---

## Q18 — How do you defend an LLM app against prompt injection?

**Four layers** (the same shape as Q15's data-leak defence, applied to a different threat):

| Layer | What it does |
|---|---|
| **Input wrapping** | Put the user's raw input inside a clear delimiter (e.g. XML tags), and explicitly instruct the LLM to treat that content **as data, not as instructions** |
| **Input classification** | Use a separate, small LLM to detect injection attempts *before* the main model call happens |
| **Isolation** | Keep the system prompt and user input structurally separate — don't let user text blend into the instruction layer |
| **Output monitoring** | Use guardrail tooling to catch anything that made it through anyway |

Named example of a real guardrail tool category: purpose-built LLM guardrail products that different companies build or buy for this specific layer.

---

## Q19 — How would you ensure compliance auditors can verify what your AI is doing?

**Log everything, and log it richly.**

- Use something like Azure App Insights (or LangSmith/Langfuse-class tooling) to capture logs
- Store logs in something like S3 or blob storage for retention
- Build compliance **dashboards** (e.g. Grafana) on top of the stored logs

### The concrete test given

> A compliance team asks: *"Show us all AI-generated loan-related decisions given to customer X in 2025."* If your logging captures **user ID, request ID, prompt, response, retrieved document, and model version** for every call, you can answer that within five minutes. **Without logging, you cannot answer it at all.**

---

## Q20 — How do you handle a data-residency requirement — "data can't leave the country"?

Three options, in order:

**1. Regional deployment.** Use a cloud provider's region-specific offering — e.g. Azure OpenAI's India region, AWS Bedrock in-region — so the data literally never crosses a border. (Noted honestly: as of the recording, not every country has full regional coverage from every provider — "there are very few chances," so check availability first.)

**2. Self-hosted open-source models**, run entirely inside the required jurisdiction — a hybrid approach for sensitive workloads that must stay in-country.

**3. A combination** — sensitive workloads self-hosted locally, less-sensitive workloads on regional cloud.

### The worked example

> An Indian bank wants to use ChatGPT-style AI, but customer data **cannot leave India per RBI regulation**. Solution: **deploy in a South-India cloud region under a contract that guarantees data stays in-country**, and use a self-hosted Llama-based model as backup/fallback for anything that can't go through the regional cloud path.

---

## Q23 — Your AI gives an offensive response that goes viral. How do you respond?

A crisis-response sequence, in order:

**1. Disable the feature within the hour** — don't wait, don't debate, shut it down fast.

**2. Post a public apology** acknowledging it was a mistake.

**3. Trace the root cause** through your logs.

**4. Implement guardrails** to prevent recurrence.

**5. Add the offensive case to your regression test suite** (see [Q24](03-debugging-rag-and-evaluating-it.md)) so it's caught automatically before any future deploy.

### The historical example given

> **Microsoft's Tay chatbot (2016)** became racist within 24 hours of launch, after users deliberately manipulated it through repeated interactions. Microsoft shut it down quickly and apologized publicly. The presenter contrasts this with how modern frontier labs now build in **multiple safety layers before launch** — RLHF, Constitutional AI, and content classifiers — specifically citing **Anthropic's "safety first" positioning with Claude** as the modern standard the industry moved toward *because of* incidents like Tay.

**Interview framing:** "Always say transparency first, fix second. Show you understand AI ethics and PR — not just the engineering fix."

---

> ← [`04-production-cost-latency-and-monitoring.md`](04-production-cost-latency-and-monitoring.md) · **Index:** [`README.md`](README.md) · **Next:** [`06-agentic-ai-and-mcp.md`](06-agentic-ai-and-mcp.md) →
