# Agentic AI using LangGraph — Study Notes

Detailed developer study notes generated from the transcripts of the CampusX
[**Agentic AI using LangGraph**](https://www.youtube.com/playlist?list=PLKnIA16_RmvYsvB8qkUQuJmJNuiCUJFPL)
playlist (28 videos).

Each note follows a consistent template: **Overview → Key Concepts → Code / Implementation → Step-by-Step Walkthrough → Gotchas & Tips → Key Takeaways**.

## 📁 Folder structure

```
Langgraph/
├── README.md          ← this index
├── 01_intro-playlist-overview.md ... 28_self-rag.md   ← 28 detailed markdown notes (one per video)
└── transcripts/       ← raw fetched transcripts (source material)
```

## 📚 Index

### Foundations — what & why
| # | Topic | Notes |
|---|-------|-------|
| 01 | Playlist intro / tutorial overview | [01_intro-playlist-overview.md](01_intro-playlist-overview.md) |
| 02 | Generative AI vs Agentic AI | [02_generative-ai-vs-agentic-ai.md](02_generative-ai-vs-agentic-ai.md) |
| 03 | What is Agentic AI? | [03_what-is-agentic-ai.md](03_what-is-agentic-ai.md) |
| 04 | LangChain vs LangGraph | [04_langchain-vs-langgraph.md](04_langchain-vs-langgraph.md) |
| 05 | LangGraph core concepts (State, Nodes, Edges, Reducers) | [05_langgraph-core-concepts.md](05_langgraph-core-concepts.md) |

### Workflow patterns
| # | Topic | Notes |
|---|-------|-------|
| 06 | Sequential workflows | [06_sequential-workflows.md](06_sequential-workflows.md) |
| 07 | Parallel workflows | [07_parallel-workflows.md](07_parallel-workflows.md) |
| 08 | Conditional workflows (routing) | [08_conditional-workflows.md](08_conditional-workflows.md) |
| 09 | Iterative / looping workflows | [09_iterative-workflows.md](09_iterative-workflows.md) |

### Building chatbots + persistence
| # | Topic | Notes |
|---|-------|-------|
| 10 | Build a chatbot (messages + `add_messages`) | [10_build-a-chatbot.md](10_build-a-chatbot.md) |
| 11 | Persistence & time travel (checkpointers, threads) | [11_persistence-and-time-travel.md](11_persistence-and-time-travel.md) |
| 12 | Chatbot UI with Streamlit | [12_chatbot-ui-streamlit.md](12_chatbot-ui-streamlit.md) |
| 13 | Streaming responses | [13_streaming.md](13_streaming.md) |
| 14 | Resume-chat feature (like ChatGPT threads) | [14_resume-chat-feature.md](14_resume-chat-feature.md) |
| 15 | LangGraph + SQLite (DB-backed checkpointer) | [15_langgraph-sqlite.md](15_langgraph-sqlite.md) |

### Observability
| # | Topic | Notes |
|---|-------|-------|
| 16 | LangSmith crash course | [16_langsmith-crash-course.md](16_langsmith-crash-course.md) |
| 17 | Observability in LangGraph (LangSmith integration) | [17_observability-langsmith-integration.md](17_observability-langsmith-integration.md) |

### Tools, MCP & RAG
| # | Topic | Notes |
|---|-------|-------|
| 18 | Tools in LangGraph (`@tool`, `bind_tools`, `ToolNode`) | [18_tools-in-langgraph.md](18_tools-in-langgraph.md) |
| 19 | Build an MCP client with LangGraph | [19_mcp-client.md](19_mcp-client.md) |
| 20 | RAG using LangGraph | [20_rag-using-langgraph.md](20_rag-using-langgraph.md) |

### Control & composition
| # | Topic | Notes |
|---|-------|-------|
| 21 | Human in the loop (HITL) | [21_human-in-the-loop.md](21_human-in-the-loop.md) |
| 22 | Subgraphs | [22_subgraphs.md](22_subgraphs.md) |

### Memory
| # | Topic | Notes |
|---|-------|-------|
| 23 | How LLMs "remember" (stateless models + context) | [23_llm-memory-explained.md](23_llm-memory-explained.md) |
| 24 | Short-term memory | [24_short-term-memory.md](24_short-term-memory.md) |
| 25 | Long-term memory (`BaseStore`, semantic search) | [25_long-term-memory.md](25_long-term-memory.md) |

### Projects & advanced RAG
| # | Topic | Notes |
|---|-------|-------|
| 26 | Blog-writing agent (plan → research → write) | [26_blog-writing-agent-project.md](26_blog-writing-agent-project.md) |
| 27 | Corrective RAG (CRAG) | [27_corrective-rag-crag.md](27_corrective-rag-crag.md) |
| 28 | Self-RAG | [28_self-rag.md](28_self-rag.md) |

---

*Notes are grounded strictly in the video transcripts. Auto-generated (Hindi + English) captions
were cleaned into English; code blocks were reconstructed from what each video demonstrated.*
