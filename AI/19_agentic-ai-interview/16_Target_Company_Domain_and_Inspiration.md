# 16 — Target Company: Domain Deep‑Dive, Project Mapping & Inspiration

> Goal: walk in sounding like someone who **already understands the target company's business and its AI**, and who can connect your real current‑employer/RAG work to their world *honestly*. Everything here is public info (sources omitted here on purpose — see note at the bottom), memorize the numbers, but say "as I understand it / roughly" for figures, since they move.
>
> ⚠️ **Integrity note:** Use this to demonstrate *genuine* knowledge and *genuine* enthusiasm. Reference **their** products/metrics as public facts, and map **your** real projects to their problems. Do **not** claim you've used their products or invent personal experience with them — a Principal loop will catch it, and authenticity is your strongest card.

---

## 🏦 The target company in 90 seconds (know this cold)

- **Who:** an India‑based debt‑markets fintech unicorn (rebranded to its current name in **June 2022** from an earlier corporate identity), founded **2020** by its CEO — "freeing the flow of finance between borrowers, lenders, and investors." Backed by top‑tier VC investors (per the JD).
- **Scale (public):** **₹1,40,000 Cr+** debt facilitated · **17,000+** enterprises · **6,200+** investors & lenders · collections cost reduced **~57%**.
- **Thesis:** be the **credit infrastructure layer** for the whole debt lifecycle — origination → underwriting/risk → marketplace → servicing → collections → data.

### The product family (map each to a "what does an agent do here?")
| Product line | What it is | Obvious agentic‑AI surface |
|---|---|---|
| **Loan origination marketplace** | Corporate loan origination marketplace | Deal‑matching, document extraction, term‑sheet drafting |
| **Co‑lending marketplace** | Bank↔NBFC co‑lending marketplace | Rule/eligibility reasoning, reconciliation agents |
| **Fixed‑income investing** | Fixed‑income / bond investing | Research assistants, disclosure/prospectus RAG |
| **Securitisation management** | Securitisation management (RBI 2021 compliant) | Pool structuring, covenant/compliance checks |
| **Supply‑chain finance** | Supply‑chain finance | Invoice extraction, anomaly/fraud detection |
| **Real‑estate / infra financing** | Real‑estate / infra financing | Project‑doc RAG, risk memos |
| **Flagship agentic‑AI collections product** | **Agentic‑AI debt collections** (see below) | **This is the crown jewel for your role** |
| **Corporate data / risk‑intelligence product** | Corporate data / risk intelligence | Entity resolution, KG‑backed risk RAG |

### 🌐 What their institutional markets platform is (the one named in your JD)
It's the **institutional debt capital markets marketplace** — the two‑sided platform connecting **borrowers/issuers** with **lenders/investors** for bonds, securitised pools, co‑lending, and supply‑chain finance (network of **750+** lenders/investors). Frame it as: *"a regulated, document‑heavy, two‑sided transaction platform where speed of match and correctness of every instrument/covenant is money and compliance."* That framing lets every AI answer land with the right constraints.

---

## 🤖 Their flagship collections product — study this the most (it *is* your role, already shipped)

**"India's largest end‑to‑end debt collections platform powered by Agentic AI."** (It's a subsidiary/brand of the target company.) This is the single most relevant thing at the target company for a **Principal Engineer (Agentic AI)** — the interviewers will love that you found it.

**Public data points (reference as "as reported"):**
- AI agents **analyze borrower behavior, predict default risk, and orchestrate tailored interventions**.
- Manages **5.5 Cr+ monthly accounts**, protects **8.9 Cr+ borrowers** from becoming NPAs, helping lenders avoid **₹50,000 Cr+** in expected credit losses.
- **Reduced operational costs up to ~57%**; cut **bounce rates 25–30%**; PSU banks reported recoveries **up ~60%**.
- **60+ financial institutions**; growing **MENA presence (DIFC)**; a notable payments/collections partnership; built an **AI‑driven compliance framework** for collections (with an industry self‑regulatory body) — collections in India is heavily regulated (RBI fair‑practices, no harassment).

**Why this is your gift:** it's *literally the same shape as your current‑employer BDC agents* — an agent that **engages a person over messaging, reasons over their context/history, decides the next best action, and stays inside compliance guardrails**, at massive multi‑tenant scale. You've built that pattern; they've productized it for debt. That's your bridge.

---

## 🔗 Your projects → their problems (the mapping that wins)

Use these as *analogies*, not claims of prior debt experience. Pattern‑match your real architecture onto their domain out loud — that's exactly what a Principal does on day one.

| Your real work (docs 15) | Their analogue | The one‑liner to say |
|---|---|---|
| **Sales BDC supervisor** — LLM‑routed multi‑agent, dual‑input contract, ContextVar isolation, hybrid memory | **Collections orchestration** — pick next‑best borrower intervention across channels | "My BDC supervisor is structurally a collections orchestrator: same multi‑agent routing, same per‑customer memory, same channel actions — swap 'book a service appointment' for 'negotiate a repayment plan'." |
| **Guardrails: nova guards + deterministic fact injection + Responder exit gate + price disclaimers** | **RBI fair‑practice / compliance guardrails on every borrower message** | "I already enforce a compliance gate on every outbound string with post‑hoc disclaimer injection — for collections that becomes the fair‑practices/consent guardrail, and it's non‑negotiable." |
| **Service MCP migration** — dual‑transport shared contract, schema‑validated tool calls, trusted‑identity headers | **Tool‑augmented agents over their core (Java/Spring Boot) services** | "MCP is exactly how I'd let AI agents safely call your existing enterprise services without each team hardcoding integrations — with identity from trusted context, never the model." |
| **RagApp** — citations, delete‑correctness, forced‑retrieval, config‑versioned prompts, two‑loop eval | **Fixed‑income / securitisation document RAG** — prospectuses, covenants, RBI directions | "For fixed‑income and securitisation docs, my page‑level citation + 'delete = privacy property' + abstention‑tested eval design is the template — in debt markets a hallucinated covenant is a legal event." |
| **Bedrock AgentCore LTM + circuit breaker + rate limiter; tiered nano routing; async callback + tracing** | **Fault‑tolerant, cost‑efficient AI platform at transaction scale** | "The reliability + cost primitives are domain‑agnostic — circuit breakers, token‑bucket limits, tiered models, one trace per conversation — I bring those on day one." |
| **Config‑driven agent registry (reused across both repos)** | **The JD's "platform abstractions/SDKs for multiple product teams"** | "I've built the 'add an agent = register a config' platform twice; that's the SDK I'd give your different product lines and collections team so they don't each reinvent orchestration/eval/guardrails." |

---

## ❓ Company‑specific questions & how to answer

Rehearse these — they blend domain + your JD strengths. (Full model answers for generic versions live in [11a–11d]; these are the *company‑flavored* versions.)

1. **"Design an agent that helps an investor evaluate a bond/pool on the markets platform."**
   → Retrieval over the offer doc + issuer financials (RAG w/ **citations**, hybrid search for exact covenant terms), a **risk‑summary agent**, **explicit abstention** on anything not in the docs, human sign‑off before any recommendation, full audit trail. Emphasize: *"in regulated investing I bias to constrained tool‑augmented workflow + citations over open‑ended autonomy — correctness and auditability beat cleverness."*

2. **"How would you build the next generation of the collections agent?"**
   → Per‑borrower **memory** (your LTM insight‑extractor), **next‑best‑action** planning (risk score × channel × propensity), a hard **compliance guardrail gate** (RBI fair practices, consent, time‑of‑day, no‑harassment) that fails *closed*, **LLM‑as‑judge + human review** on sensitive messages, and cost‑tiered models (nano for triage, larger for negotiation). Tie each piece to your real code.

3. **"An LLM in a lending/collections path is non‑deterministic and slow — how do you make it safe?"**
   → (A likely reliability‑focused panelist's kind of question.) Deterministic guardrails around the LLM, timeouts + retries + circuit breaker + fallback model, human‑in‑the‑loop on financial actions, idempotent tool calls, and *never let the model set identity/amounts* — those come from trusted context (cite your `_mcp_context` pattern).

4. **"Debt‑market data is sensitive and India‑regulated. What changes in your AI design?"**
   → Data residency (India), PII masking + log redaction (you do this), auditability (per‑conversation traces + SAE codes + citations), RBI/consent guardrails, and delete‑correctness as a *privacy property* (cite RagApp ADR‑16). This is the answer that separates you from a generic AI engineer.

5. **"Build vs buy: LangGraph? a vector DB? a collections model?"**
   → Your framework (doc 11d): buy commodity infra, build your differentiation. "Their moat is the debt‑lifecycle data and network, not orchestration plumbing — so I'd standardize on LangGraph + MCP + a managed vector store, and invest build effort in the eval/guardrail/domain layers where correctness is the product."

6. **"How do you evaluate a collections/lending agent — you can't A/B test harassing customers."**
   → Offline golden sets with **mandatory abstention + compliance‑violation rows**, LLM‑as‑judge for tone/compliance, shadow mode before live, human review queue, and online sampled groundedness — the two‑loop design from RagApp's eval proposal, hardened for regulation.

---

## 💡 "Why them?" / your inspiration narrative (make it yours)

Interviewers can smell a generic "I love fintech." Ground it in your **real trajectory**. Spine to personalize:

> "I've spent the last few years building production **agentic AI on regulated, revenue‑critical, high‑stakes workflows** — service and sales agents where a wrong answer costs a customer or breaks a compliance rule. I kept hitting the same hard, interesting problems: making non‑deterministic LLMs safe inside transactional systems, orchestrating multiple agents reliably, and building the eval/guardrail platform so *other* teams can move fast. **This is that exact problem at a higher stakes and bigger scale** — debt markets are the most document‑heavy, audit‑critical, regulated place to apply agentic AI, and **their flagship collections product already proves agents move the needle** there (recoveries up, costs down, at 5+ crore accounts a month). The chance to set the AI‑engineering bar for that platform, hands‑on and partnering with the CTO, is the most compelling version of the work I'm already doing."

**Personalize before the loop — insert your genuine reasons:**
- A specific moment your agent work made you care about *reliability/safety* over demos: 🟡 `[real anecdote]`
- Why *debt/credit* specifically resonates (access to finance, India credit gap, a personal/family/regional angle): 🟡 `[your honest reason]`
- Why *now* / why Principal: 🟡 `[your growth reason — bigger blast radius, platform ownership]`

**Your "I did my homework" name‑drops (verify current titles first):** their flagship product's agentic collections; a senior industry leader's public stance on **agentic AI in BFSI**; that the role partners with the **CTO**; their AWS‑heavy stack (SageMaker/Data Lake). Sprinkle 1–2 naturally; don't recite a list.

---

## 📊 Quick‑reference data points (for credible, specific examples)

Keep these in your back pocket; deploy 2–3 per conversation, hedged as "as I understand it":
- The company: ₹1,40,000 Cr+ debt · 17,000+ enterprises · 6,200+ lenders/investors · ~57% collections cost cut · founded 2020 · rebranded to current name June 2022 · led by its CEO.
- Flagship collections product: 5.5 Cr+ monthly accounts · 8.9 Cr+ borrowers protected · ₹50,000 Cr+ credit losses avoided · bounce rates −25–30% · PSU recoveries +~60% · 60+ FIs · MENA/DIFC.
- Product lines: loan origination, co‑lending, fixed‑income investing, securitisation (RE/infra), supply‑chain finance, real‑estate/infra financing, collections, corporate risk‑data product.
- Regulatory hooks to name‑check: **RBI Master Directions 2021** (securitisation of standard assets), RBI **fair‑practices code** for collections, co‑lending guidelines, KYC/AML, data residency (India).
- Stack: AWS (ECS, Fargate, RDS, Aurora, CloudWatch, **SageMaker**, Data Lake); core **Java/Spring Boot**; AI services **Python/Node/TS**.

---

## 📚 Sources
Public-info sources (startup‑news coverage, the company's own blog/press, and LinkedIn) were used to compile the figures above and are intentionally omitted here since they'd directly identify the company. Re‑verify current numbers/titles the day before the interview.
