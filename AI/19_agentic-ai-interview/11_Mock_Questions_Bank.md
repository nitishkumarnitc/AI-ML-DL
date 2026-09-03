# 11 — Mock Questions Bank (120+)

> Rehearse **out loud**. For each, know your 60–120 second answer. Deep-dive files linked. ⭐ = high probability given the JD.
>
> 📝 **Model answers:** Q1–34 → [11a](11a_Answers_Agentic_and_RAG.md) · Q35–59 → [11b](11b_Answers_LLMOps_and_FineTuning.md) · Q60–88 → [11c](11c_Answers_Systems_and_Design.md) · Q89–122 → [11d](11d_Answers_Coding_Leadership_Domain.md)

---

## A. Agentic AI & Orchestration → [02](02_Agentic_AI_and_Orchestration.md)

1. ⭐ Walk me through a multi-agent system you built end-to-end.
2. ⭐ LangGraph vs AutoGen — when each? Why would you pick one for us?
3. ⭐ When should you NOT use an agent?
4. Single-agent vs multi-agent — how do you decide?
5. ⭐ How do you stop an agent from looping / blowing up cost?
6. Explain ReAct vs plan-and-execute vs reflection. Trade-offs?
7. ⭐ How do you make a long-horizon agent reliable? Failure modes?
8. How do you handle tool errors mid-workflow?
9. Design a tool interface. What makes a tool "agent-friendly"?
10. Tool selection breaks with 100 tools — fix it.
11. ⭐ How do you make an agent auditable for a regulator?
12. What's MCP and why does it matter for an agent platform?
13. How do you checkpoint/resume a long agent workflow?
14. How do you test/eval an agent's decision *trajectory*, not just output?
15. Supervisor vs hierarchical vs pipeline multi-agent — when each?
16. How would you design the agent SDK product teams build on?
17. Human-in-the-loop — where do you insert gates and why?
18. How do you manage agent memory (short vs long term)?

## B. RAG & Retrieval → [03](03_RAG_and_Retrieval.md)

19. ⭐ Design RAG over 10M loan documents.
20. ⭐ Why hybrid search (BM25 + vector)? How do you fuse results?
21. ⭐ Explain reranking. Where does it help most?
22. Chunking strategies — which for legal/financial docs and why?
23. ⭐ What is GraphRAG and when is a knowledge graph worth it?
24. Vector search returns garbage — debug methodology.
25. ⭐ How do you evaluate a RAG system (retrieval + generation)?
26. HyDE, multi-query, contextual retrieval — explain and when.
27. How do you keep an index fresh with millions of changing docs?
28. How do you prevent cross-tenant document leakage?
29. Embedding model selection — how do you choose/evaluate?
30. How do you handle tables and structured data in RAG?
31. When is fine-tuning better than RAG?
32. How do you enforce citations / groundedness?
33. Vector DB choice (OpenSearch vs pgvector vs Qdrant vs Pinecone) — trade-offs?
34. How do you do metadata filtering at scale?

## C. LLMOps, Eval, Guardrails → [04](04_LLMOps_Eval_Guardrails.md)

35. ⭐ How do you own/build an agent evaluation framework?
36. ⭐ How do you catch hallucinations in production?
37. ⭐ Design guardrails for an agent reading borrower docs.
38. LLM-as-judge — how, and what can go wrong?
39. ⭐ How do you build trust with compliance/regulators?
40. What do you log/trace for an LLM system? Which metrics/dashboards?
41. Eval passes but prod quality drops — why and how to fix?
42. How do you version prompts/models/configs? CI/CD for LLM systems?
43. Prompt injection — how do you defend a doc-reading agent?
44. How do you build a golden dataset + regression suite?
45. Shadow vs canary vs A/B for LLM deploys?
46. How do you measure/monitor cost per request/user/feature?
47. What is model/data drift for LLMs and how do you detect it?
48. Explainability for an AI-influenced credit decision — what do you produce?
49. How do you handle a production hallucination incident?
50. How do you calibrate an LLM to abstain / say "I don't know"?

## D. Fine-Tuning & Alignment → [05](05_FineTuning_and_Alignment.md)

51. ⭐ Fine-tune vs RAG vs prompt — decision framework.
52. Explain LoRA and QLoRA. When each?
53. How would you fine-tune for a regulated financial task?
54. RLHF vs DPO — differences and when?
55. How do you serve many fine-tuned variants cost-efficiently?
56. Catastrophic forgetting — what is it and how avoid?
57. How do you build a fine-tuning dataset (quality, synthetic, PII)?
58. How do you evaluate whether a fine-tune actually helped?
59. Frontier API model vs self-hosted open model — how decide?

## E. Distributed Systems & Backend → [06](06_Distributed_Systems_Backend.md)

60. ⭐ Design an async event-driven inference service (Kafka).
61. ⭐ How did you reduce latency / AWS cost? (numbers!)
62. Kafka delivery semantics — exactly-once vs at-least-once for inference?
63. Kafka consumer lag is growing — diagnose and fix.
64. Redis for LLM systems — use cases and risks (semantic cache pitfalls)?
65. ⭐ How do you achieve low-latency LLM inference? (vLLM, KV cache, batching, spec decoding)
66. TTFT vs throughput — what do you optimize and when?
67. Design GPU autoscaling on K8s for spiky inference load.
68. How do you control GPU cost on AWS?
69. Backpressure when the LLM provider rate-limits you?
70. Partition strategy / hot partitions in Kafka?
71. How do you design a high-throughput streaming LLM API?
72. Circuit breakers, timeouts, retries around model calls — how?
73. Bedrock vs self-hosted — trade-offs?
74. Idempotency for event-driven side-effects (e.g., ledger writes)?
75. Schema evolution in Kafka (Schema Registry)?

## F. System Design (HLD/LLD) → [07](07_System_Design_HLD_LLD.md)

76. ⭐ Design the company's agentic AI platform end-to-end.
77. ⭐ Design a document-intelligence agent for loan agreements.
78. Design a collections/support agent for borrowers.
79. ⭐ Design the agent evaluation platform.
80. Design a low-latency RAG API at 10k QPS.
81. Design the model gateway (routing/fallback/rate-limit/cost).
82. Design the tool registry + governance layer.
83. Design agent state schema + checkpointing.
84. Design a guardrail middleware pipeline (LLD).
85. Design multi-tenant isolation for an AI platform.
86. Design idempotent inference event processing.
87. Capacity/cost estimate for X users/docs/QPS — do the math.
88. How would you make this fault-tolerant / handle provider outage?

## G. Coding / DSA → [08](08_Coding_and_DSA.md)

89. Implement a token-bucket / sliding-window rate limiter.
90. Implement an LRU cache (O(1)).
91. Implement retry-with-exponential-backoff (+ jitter).
92. Concurrent LLM calls with bounded concurrency (async + semaphore).
93. Mini in-memory vector search (cosine, top-k) — then scale it.
94. A minimal agent loop with a step budget.
95. Topological sort of a tool/task DAG (+ cycle detection).
96. Merge k sorted streams (heap).
97. Chunk text with overlap / stream-parse tokens.
98. Top-k frequent elements.
99. Group anagrams / frequency map problem.
100. Sliding-window max / longest substring variants.
101. Given code, find the bugs / review it.

## H. Leadership & Behavioral → [09](09_Leadership_and_Behavioral.md)

102. ⭐ Why this company / why this role?
103. Why leave your current role?
104. ⭐ Most complex system you've built — trade-offs and your decisions?
105. ⭐ A technical decision you got wrong — what you learned?
106. ⭐ How do you act as a "technical multiplier"?
107. ⭐ Build vs buy — framework + a real example.
108. How do you set direction across teams that don't report to you?
109. ⭐ First 90 days here — what's your plan?
110. How do you handle disagreement with a senior/exec?
111. How do you mentor senior/lead engineers?
112. Prioritize limited GPU budget across three teams.
113. Tell me about leading an architecture review that changed direction.
114. How do you stay current with AI?
115. A time you shipped under ambiguity / 0→1.
116. How do you balance hands-on coding with leadership?
117. A time you influenced without authority.
118. How do you say "no" to a stakeholder?

## I. Domain / Fintech → [01](01_Company_and_Role_Strategy.md), [10](10_Questions_to_Ask_and_Redflags.md)

119. What's unique about building AI for regulated debt/financial markets?
120. How do you handle PII/compliance/data residency in AI systems?
121. Where would AI add the most value in a debt marketplace? (Have an opinion.)
122. What are the risks of autonomous agents in financial workflows, and how do you mitigate?

---

### 🔥 The 20 you MUST nail (if short on time)
2, 5, 7, 11, 19, 20, 25, 35, 36, 37, 39, 51, 60, 61, 65, 76, 79, 102, 104, 106, 107, 109.
