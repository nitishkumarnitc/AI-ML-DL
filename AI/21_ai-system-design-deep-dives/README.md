# 17 — Top 10 System Design Deep-Dives (Full HLD + LLD)

> Complements [07](../19_agentic-ai-interview/07_System_Design_HLD_LLD.md) (framework + skeleton, for speed in the room) and [11c](../19_agentic-ai-interview/11c_Answers_Systems_and_Design.md) (short spoken answers). This folder is built for *depth* in prep: **one file per problem**, and every file carries a full **HLD** (scope, architecture, component choices + why, NFRs, failure modes, capacity) **and** a full **LLD** (data models, API contracts, core algorithms/sequence diagrams, state machines, edge cases).
>
> **Mix, deliberately:** files 01–04 are agentic-AI-native (the core of the loop). Files 05–10 are all still **AI/ML system design**, pulled from domains adjacent to agentic RAG — classical ML decisioning, ML-driven ranking, graph/entity-resolution, adversarial ML/AI-security, and computer vision — reframed inside the debt-markets domain. A Principal AI loop tests whether your systems thinking generalizes across the *whole* AI stack, not just LLM orchestration; files 07 and 08 deliberately favor a classical model over an LLM, and knowing *when not* to reach for one is itself a signal.

## Files

| # | File | One-line prompt |
| --- | --- | --- |
| 01 | [01_agentic_ai_platform.md](01_agentic_ai_platform.md) | Design the platform that lets any product team stand up an agent, end to end. |
| 02 | [02_document_intelligence_agent.md](02_document_intelligence_agent.md) | Design an agent that extracts terms/covenants from loan and bond agreements. |
| 03 | [03_agentic_collections.md](03_agentic_collections.md) | Design a real-time, multi-channel, compliance-gated borrower-engagement agent. |
| 04 | [04_agent_eval_guardrail_platform.md](04_agent_eval_guardrail_platform.md) | Design the system that decides whether an agent change is safe to ship, and keeps it that way in prod. |
| 05 | [05_fraud_anomaly_detection.md](05_fraud_anomaly_detection.md) | Design real-time fraud scoring for loan applications, explainably, at scale. |
| 06 | [06_prompt_injection_defense.md](06_prompt_injection_defense.md) | Design the defense so a malicious ingested document can't hijack an agent. |
| 07 | [07_marketplace_matching_ranking.md](07_marketplace_matching_ranking.md) | Design the matching/ranking engine for a two-sided institutional debt marketplace. |
| 08 | [08_credit_risk_scoring_engine.md](08_credit_risk_scoring_engine.md) | Design a real-time credit-risk decision engine that can explain every rejection. |
| 09 | [09_kyc_entity_resolution_graph.md](09_kyc_entity_resolution_graph.md) | Design entity resolution + fraud-ring detection over a graph of borrowers/guarantors. |
| 10 | [10_cv_kyc_liveness.md](10_cv_kyc_liveness.md) | Design a computer-vision KYC pipeline: liveness, face-match, document-forgery detection. |

## How to rehearse this set

For each file, practice the **three-sentence compression** before you open it: (1) the one architectural choice that matters most, (2) the alternative you rejected and why, (3) the failure mode you'd volunteer unprompted. Then open the file and check your compression against the HLD's "why" table — if you can defend every row against "but why not X instead," move to the LLD and do the same for the data model and the core algorithm. The tables are ammunition for follow-ups, not the opening answer.

## Further reading — real-world designs to compare against

Read one or two of these fully before the loop, not all of them — the goal is to say "I'd design it the way X does, for the same reason," not to recite the article.

| File | Real-world reference | Why it's relevant |
| --- | --- | --- |
| 06 — Prompt-injection defense | [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/); [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) | OWASP's GenAI project names the same dual-LLM / privilege-separation pattern used in file 06. |
| 10 — CV/biometric KYC | [Facial Liveness Detection — Mitek](https://www.miteksystems.com/blog/facial-liveness-detection); [Liveness Detection Guide — Sumsub](https://sumsub.com/blog/face-liveness-detection/) | Two identity-verification vendors' writeups on the same liveness-first, defense-in-depth pipeline shape used in file 10. |
| 05, 08 — Feature store (fraud + credit scoring) | [Meet Michelangelo: Uber's ML Platform](https://www.uber.com/en-CA/blog/michelangelo-machine-learning-platform/); [Palette Meta Store Journey](https://www.uber.com/us/en/blog/palette-meta-store-journey/) | The reference implementation of "one feature store shared across many models" — the justification reused across files 05, 07, and 08. |
| 09 — Graph-based fraud-ring detection | [Graph databases for fraud detection & analytics — Neo4j](https://neo4j.com/use-cases/fraud-detection/) | Covers the same blocking → graph traversal → community-detection shape used in file 09. |
| 07 — Marketplace matching/ranking | [Reinforcement Learning for Modeling Marketplace Balance — Uber](https://www.uber.com/us/en/blog/reinforcement-learning-for-modeling-marketplace-balance/); [Airbnb Relevance Team Publications](https://sites.google.com/view/airbnb-relevance-publications/home) | Real two-sided marketplaces solving the same candidate-generation-then-ranking problem as file 07. |
