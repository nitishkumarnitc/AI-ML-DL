# AI-ML Notes

My personal study notes on machine learning, deep learning, and LLM/agentic-AI engineering.

Mostly written-up notes in Markdown (~570 files), plus 72 Jupyter notebooks in the deep-learning
foundations folder. Sources are course playlists (largely CampusX), papers, docs, and my own
working-through of problems — each folder's README says where its material came from.

This is a working notebook, not a course. Depth is uneven: some folders are careful multi-lesson
write-ups, others are rough notes I haven't come back to.

---

## Layout

Four top-level areas: classical **ML**, **DL** (frameworks and architectures), **AI** (the LLM and
agentic-AI application stack), and **Shared** for material that isn't specific to one of them —
MLOps applies to classical and deep models alike, and LoRA/QLoRA is a DL technique that's equally
central to LLM work.

Each subfolder has its own README with a detailed index. Start there rather than here.

```
AI-ML/
│
├── ML/                                            # Classical machine learning
│   ├── 01_intro-and-foundations/                  #   NumPy, Pandas, stats, feature engineering
│   ├── 02_machine-learning/                       #   Regression, classification, ensembles, unsupervised, recsys
│   └── 03_ml-interview-prep/                      #   ML interview prep
│
├── DL/                                            # Deep learning
│   ├── 01_deep-learning-foundations/              #   ANN/DNN, TensorFlow, PyTorch, CNNs, transfer learning,
│   │                                              #   object detection, RNNs, transformers, autoencoders
│   │                                              #   (31 notebooks — the notebook-heavy part of the repo)
│   ├── 02_pytorch/                                #   CampusX "Practical Deep Learning using PyTorch" notes
│   ├── 03_tensorflow/                             #   TensorFlow / Keras notes (PyTorch-parallel mirror)
│   └── 04_reinforcement-learning/                 #   RL notes
│
├── AI/                                            # LLM & agentic-AI application stack
│   ├── 00_jobs/                                   #   Job postings → the lesson paths that cover them
│   ├── 01_prompt-engineering/                     #   Prompting: techniques, reasoning, structured output
│   ├── 02_fine-tuning-and-alignment/              #   SFT, PEFT, RLHF, DPO; when to fine-tune vs RAG
│   ├── 03_llm-security-and-guardrails/            #   OWASP LLM Top 10, injection, guardrails
│   ├── 04_llm-serving-and-inference-optimization/ #   vLLM, KV-cache, batching, quantization
│   ├── 05_multi-agent-frameworks/                 #   AutoGen, CrewAI, OpenAI Agents SDK, topologies
│   ├── 06_vector-databases/                       #   ANN (HNSW/IVF/PQ), DB comparison, hybrid search
│   ├── 07_graph-rag/                              #   Knowledge graphs, Microsoft GraphRAG
│   ├── 08_multimodal-ai/                          #   VLMs, image gen, voice agents, multimodal RAG
│   ├── 09_a2a-protocol/                           #   Agent-to-Agent interop (A2A vs MCP)
│   ├── 10_rl-environments-and-infra/              #   RL environments & infra for frontier-agent training/eval
│   ├── 11_langchain/                              #   LangChain fundamentals
│   ├── 12_rag/                                    #   RAG building blocks
│   ├── 13_langgraph/                              #   Agentic AI using LangGraph
│   ├── 14_memory/                                 #   Agent memory
│   ├── 15_mcp/                                    #   Model Context Protocol
│   ├── 16_evals/                                  #   LLM evaluation — 16 lessons
│   ├── 17_claude-code/                            #   Claude Code notes
│   ├── 18_ragapp/                                 #   Reusable agent stack — system design docs
│   ├── 19_agentic-ai-interview/                   #   Agentic-AI interview prep
│   ├── 20_data-engineering-for-rag/               #   RAG ingestion — connectors, parsing, chunking, freshness
│   ├── 21_ai-system-design-deep-dives/            #   10 AI system designs — HLD + LLD each
│   ├── 22_transformer-and-gpt-architecture/       #   Transformer & GPT internals — attention, blocks, KV cache
│   ├── 23_ai-coding-agents-and-code-eval/         #   Coding-agent landscape + evaluating AI-generated code
│   ├── 24_xgboost/                                #   XGBoost from first principles — similarity/gain, regularization
│   ├── 25_reinforcement-learning/                 #   RL fundamentals through to RLHF
│   ├── 26_ml-evaluation-metrics/                  #   MAE/RMSE, R², confusion matrix, precision/recall/F1, ROC
│   ├── 27_ai-platform-system-design/              #   AI platform system design
│   ├── 28_ai-system-design-by-industry/           #   12 industry AI systems — requirements + HLD + LLD + production
│   ├── 29_model-training-system-design/           #   3 training-side systems — experiment platform, post-training,
│   │                                              #   distributed training
│   ├── 30_langsmith/                              #   LangSmith — observability & evaluation, 18 lessons
│   ├── 31_forward-deployed-engineer/              #   Forward-deployed engineering — the demo-to-production gap
│   └── 32_langfuse/                               #   LangFuse — open-source, self-hostable alternative, 13 lessons
│
└── Shared/                                        # Cross-cutting
    ├── 01_lora-qlora/                             #   LoRA/QLoRA fine-tuning
    ├── 02_mlops/                                  #   MLOps
    ├── 03_llmops/                                 #   LLMOps — shipping & operating LLM/agent apps
    ├── 04_cloud-ai-platforms/                     #   Bedrock, Vertex, Azure, IaC
    └── 05_llm-training-pipeline/                  #   End-to-end LLM training pipeline
```

---

## Where to start

Depends what you're after:

| If you want | Go to |
|---|---|
| Classical ML from the ground up | [`ML/01_intro-and-foundations/`](ML/01_intro-and-foundations/) → [`ML/02_machine-learning/`](ML/02_machine-learning/) |
| Neural nets, hands-on with notebooks | [`DL/01_deep-learning-foundations/`](DL/01_deep-learning-foundations/) |
| PyTorch specifically | [`DL/02_pytorch/`](DL/02_pytorch/) |
| To build things with LLMs | [`AI/11_langchain/`](AI/11_langchain/) → [`AI/12_rag/`](AI/12_rag/) → [`AI/13_langgraph/`](AI/13_langgraph/) |
| To know whether an LLM app works | [`AI/16_evals/`](AI/16_evals/) → [`AI/30_langsmith/`](AI/30_langsmith/) or [`AI/32_langfuse/`](AI/32_langfuse/) |
| To run one in production | [`Shared/03_llmops/`](Shared/03_llmops/) |
| System-design practice | [`AI/28_ai-system-design-by-industry/`](AI/28_ai-system-design-by-industry/) (12 worked designs) |
| Interview prep | [`AI/00_jobs/`](AI/00_jobs/) · [`AI/19_agentic-ai-interview/`](AI/19_agentic-ai-interview/) · [`ML/03_ml-interview-prep/`](ML/03_ml-interview-prep/) |

The AI folders are numbered but not strictly sequential — most stand alone. The exceptions say so in
their own README (`30_langsmith` assumes `11_langchain` and `13_langgraph`, for instance).

---

## Running the notebooks

Only [`DL/01_deep-learning-foundations/`](DL/01_deep-learning-foundations/) has a substantial number
of notebooks. Everything else is Markdown you can just read.

```bash
git clone https://github.com/nitishkumarnitc/AI-ML-DL.git
cd AI-ML
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

There's no repo-wide `requirements.txt` — dependencies differ too much between folders. Install what
a given notebook imports, or start from:

```bash
pip install jupyter numpy pandas matplotlib seaborn scikit-learn
pip install tensorflow torch torchvision          # as needed
pip install transformers                           # for the BERT/transformer notebooks
```

```bash
jupyter notebook
```

Code in the `AI/` folders is illustrative — snippets inside notes, not runnable projects. Where a
folder does have working code it says so and lists its own dependencies.

---

## Tools these notes cover

Python 3.8+ · NumPy · Pandas · Matplotlib · Seaborn · scikit-learn · XGBoost · TensorFlow 2.17 ·
Keras · PyTorch · OpenCV · HuggingFace Transformers · LangChain · LangGraph · LangSmith · FAISS ·
vLLM · TensorFlow Lite · ONNX

---

## Notes on the notes

- **Sources are credited per folder.** Most of the AI and DL material is worked up from course
  playlists — CampusX especially — with the source video linked per lesson.
- **Written from transcripts, not summaries.** Where a lesson came from a video, it was written
  after reading the full transcript. Anything I added beyond the source is marked inline.
- **Numbers in the system-design folders are labelled.** Assumptions are tagged as assumptions;
  arithmetic is shown so it can be checked.
- **Some folders overlap.** `21_`, `27_`, `28_` and `29_` all cover system design from different
  angles; each README says which is deeper for a given topic.

---

For my own reference. Corrections welcome via issues.
