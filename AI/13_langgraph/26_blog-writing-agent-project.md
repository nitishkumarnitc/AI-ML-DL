# Video 26 — AI Agent that Plans, Researches & Writes Blogs Automatically (project)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `Ou_v9lk0rxg`
> **Watch:** https://www.youtube.com/watch?v=Ou_v9lk0rxg

## 🎯 Overview
This is a full end-to-end **project** video building a **planning agent** — an agent that does not jump straight to the answer but first produces a structured plan and then executes it step by step. The concrete use case is a **blog-writing agent**: give it a topic and it plans the blog's sections, optionally **researches** the topic online (Tavily), writes each section in parallel (orchestrator–worker pattern), and stitches everything into a Markdown blog with auto-generated **images** (Gemini). It is built in four progressive stages and finished with a Streamlit GUI.

## 🧠 Key Concepts

### Planning agents
> *A planning agent is an AI agent that does not immediately jump to an answer or act. Instead it first creates a structured plan of what needs to be done and then executes that plan step by step.*

Earlier agents in the playlist jumped directly to the task (e.g. evaluating a UPSC essay the moment it arrived). For complex tasks — building a website, writing a detailed blog — jumping straight in risks missing things. A planning agent works in **two phases**:
1. **Plan** — understand the task and break it down into subtasks.
2. **Execute** — carry out all the subtasks.

Blog writing is a good fit: planning the sections first yields a more complete, coherent blog than writing blind.

### The orchestrator–worker pattern
The **orchestrator** (a.k.a. **planner**) reads the topic and produces a **Plan**: the blog title plus a list of **Task** objects, one per section. Because the number of sections is not known ahead of time, a **fan-out** step uses LangGraph's **`Send` API** to dynamically spawn one **worker** per task. Each worker has its own LLM and writes its section **in parallel**. A **reducer** then stitches all sections together.

### The full architecture (final version)
```
START → topic
      → Router (LLM): needs_research? mode? search queries?
          ├─ needs_research = True  → Research (Tavily) → Orchestrator/Planner
          └─ needs_research = False → Orchestrator/Planner
      → Orchestrator/Planner: builds Plan (title + list of section Tasks)
      → Fan-out (Send API): 1 worker per Task
      → Worker × N (parallel): each writes one section (may use research evidence)
      → Reducer (subgraph): merge sections → decide images → generate & place images → file
      → END
```
- **Router** — an LLM router that decides whether internet research is needed for the topic. If yes, it also **generates the search queries**. It returns a `RouterDecision` with `needs_research` (bool), `mode` (`closed_book` / `hybrid` / `open_book`), and `queries` (list).
  - **closed_book** — evergreen topic, no research (e.g. *self-attention*).
  - **hybrid** — mostly evergreen but needs up-to-date examples/tools (e.g. *open-source LLMs*).
  - **open_book** — volatile, needs heavy research (e.g. *top AI news of the week*).
- **Research node** — for each query does a **Tavily** search (a search engine for LLMs), standardizes each raw result into an **`EvidenceItem`** (title, url, published_at, source, snippet), and collects them into an **`EvidencePack`** stored in state.
- **Orchestrator/Planner** — builds the `Plan`; when research exists, it considers the evidence while planning.
- **Reducer** — becomes a 3-node **subgraph** once images are added.

## 🔧 Code / Implementation

### Stage 1 schemas — Plan and Task
```python
from typing import List
from pydantic import BaseModel, Field

class Task(BaseModel):
    id: int
    title: str
    brief: str = Field(description="What to cover in this section")

class Plan(BaseModel):
    blog_title: str
    tasks: List[Task]
```
Each `Task` describes one section; the `Plan` holds the title plus a list of tasks.

### Stage 1 state
```python
import operator
from typing import TypedDict, Annotated

class BlogState(TypedDict):
    topic: str                                    # from the user
    plan: Plan                                    # from the orchestrator
    sections: Annotated[List[str], operator.add]  # each worker appends its section (reducer)
    final: str                                    # final merged blog
```
`sections` uses the `operator.add` reducer so every parallel worker's output merges into one list.

### Stage 1 orchestrator
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4.1-mini")

def orchestrator(state: BlogState):
    planner = llm.with_structured_output(Plan)     # force output into a Plan object
    plan = planner.invoke([
        SystemMessage(content="Create a blog plan with 5 to 7 sections on the following topic."),
        HumanMessage(content=state["topic"]),
    ])
    return {"plan": plan}
```

### Stage 1 fan-out (the `Send` API) + worker
```python
from langgraph.types import Send

def fan_out(state: BlogState):
    # one Send per task -> N workers spawned dynamically
    return [
        Send("worker", {"task": task, "topic": state["topic"], "plan": state["plan"]})
        for task in state["plan"].tasks
    ]

def worker(payload):
    task, topic, plan = payload["task"], payload["topic"], payload["plan"]
    response = llm.invoke([
        SystemMessage(content="Write one clean markdown section."),
        HumanMessage(content=(
            f"Blog title: {plan.blog_title}\n"
            f"Topic (from user): {topic}\n"
            f"Section title: {task.title}\n"
            f"What to cover: {task.brief}\n"
            "Return only the section content in markdown."
        )),
    ])
    return {"sections": [response.content]}
```
The worker is given not just its own task but the **whole plan** so it can write a coherent section aware of the overall structure.

### Stage 1 reducer + graph
```python
from langgraph.graph import StateGraph, START, END

def reducer(state: BlogState):
    title = state["plan"].blog_title
    body = "\n".join(state["sections"])            # stitch sections, separated by newlines
    final = f"# {title}\n{body}"                    # '#' -> markdown heading for the title
    with open("blog.md", "w") as f:
        f.write(final)
    return {"final": final}

builder = StateGraph(BlogState)
builder.add_node("orchestrator", orchestrator)
builder.add_node("worker", worker)
builder.add_node("reducer", reducer)

builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", fan_out, ["worker"])  # orchestrator -> N workers
builder.add_edge("worker", "reducer")
builder.add_edge("reducer", END)

app = builder.compile()
app.invoke({"topic": "Write a blog on self attention"})
```
Stage 1 produces a decent **text-only** blog (no research, no images).

**First improvement (still stage 1):** make the Pydantic models richer and the system prompts far more elaborate. The `Task` grows a `goal` (one sentence describing what the reader should understand after the section), `bullets` (3–5 concrete non-overlapping sub-points), `target_words`, and a `type` (`intro` / `core` / `examples` / `checklist`); the `Plan` gains `audience` and `tone`. Just adding detailed schemas + prompts noticeably improves quality (code blocks, summaries, deeper explanations).

### Stage 2 — research with a Router + Tavily
```python
from typing import Literal, Optional

class RouterDecision(BaseModel):
    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    queries: List[str] = []          # generated only when research is needed (3–10 queries)

def router(state):
    router_llm = llm.with_structured_output(RouterDecision)
    decision = router_llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),   # "You are a routing module for a technical blog planner..."
        HumanMessage(content=state["topic"]),
    ])
    return {"needs_research": decision.needs_research,
            "mode": decision.mode,
            "queries": decision.queries}

def route_next(state):
    return "research" if state["needs_research"] else "orchestrator"
```

Tavily setup: create an account at **tavily.com**, get an API key, put it in your `.env`. Then:
```python
from langchain_community.tools.tavily_search import TavilySearchResults

tavily = TavilySearchResults(max_results=2)     # results per query is configurable
results = tavily.invoke("ChatGPT version releases and updates from 2022 to 2026")
# -> list of {title, url, content}
```

Evidence schemas + research node:
```python
class EvidenceItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None
    source: str
    snippet: str                       # the result's content

class EvidencePack(BaseModel):
    items: List[EvidenceItem]          # a collection of EvidenceItem objects

def research(state):
    raw_results = []
    for query in state["queries"]:                       # e.g. 5 queries
        raw_results += tavily.invoke(query)              # ~6 results each -> ~30 items
    # de-duplicate by URL, keep only items with a non-empty URL, standardize into EvidenceItems
    evidence_pack = build_evidence_pack(raw_results)     # -> EvidencePack
    return {"evidence": evidence_pack}
```
The planner and workers then receive the `EvidencePack` and use it while writing. For evergreen topics the evidence is empty.

### Stage 3 — images (reducer becomes a subgraph)
The whole graph is unchanged up to the reducer. Images require the reducer to do **three** things, so it is refactored into a subgraph of three nodes: **`merge_content` → `decide_images` → `generate_and_place_images`**.

```python
class ImageSpec(BaseModel):
    placeholder: str          # marker inserted into the markdown
    filename: str             # where the image will be saved
    prompt: str               # prompt to send to the image model
    size: str
    quality: str

class GlobalImagePlan(BaseModel):
    markdown_with_placeholders: str     # the blog text with [[IMAGE_x]] placeholders
    images: List[ImageSpec]             # one ImageSpec per placeholder
```

- **`merge_content`** — stitch all worker sections into a single markdown *string* (not yet a file).
- **`decide_images`** — send that markdown to an LLM (prompt: *"You are an expert technical editor. Decide if image diagrams are needed. Max 3 images; each image should materially improve understanding — diagram, flow, table-like visual…"*). It returns a `GlobalImagePlan`: the markdown with placeholders **plus** an `ImageSpec` per placeholder.
- **`generate_and_place_images`** — for each `ImageSpec`, call the Gemini image API via a helper, save the bytes to an `images/` folder, and replace the placeholder with the file path. Finally write the complete markdown file (now text + images).

Gemini setup: get an API key from **Google AI Studio** (`ai.studio` → *Get API key* → *Create API key*), and put `GOOGLE_API_KEY` in `.env`. The instructor's cost for ~30–40 generated blogs was only about **₹135**, but the key must be kept private.

### Stage 4 — GUI
The GUI is built entirely in **Streamlit** (the easiest way to make a Python GUI). The backend (all code up to and including the compiled `app`) is placed in a `.py` file and simply **imported** into the Streamlit file, then run with `streamlit run <file>.py`. The Streamlit layout itself was vibe-coded via ChatGPT from a clear spec — the real work is the agent backend, not the front end.

## 🪜 Step-by-Step Walkthrough
1. **Stage 1 — basic agent:** define `Plan`/`Task` schemas and state; build orchestrator → fan-out (`Send`) → parallel workers → reducer; produce a text-only blog. Then upgrade the schemas and prompts for quality.
2. **Stage 2 — research:** add an LLM `router` (`needs_research` / `mode` / `queries`), a `research` node using Tavily, and `EvidenceItem`/`EvidencePack` schemas; feed evidence to the planner and workers.
3. **Stage 3 — images:** convert the reducer into a subgraph (`merge_content` → `decide_images` → `generate_and_place_images`); add `GlobalImagePlan`/`ImageSpec`; generate images with Gemini and inject them at placeholders.
4. **Stage 4 — GUI:** wrap the compiled backend in a Streamlit app.

## ⚠️ Gotchas & Tips
- **Plan first, then execute** — for complex generative tasks this beats jumping straight to output.
- Use the **`Send` API** to fan out a dynamic (data-dependent) number of workers; you don't know the section count until the plan exists.
- Pass the **whole plan** to each worker so parallel sections stay coherent.
- **Elaborate Pydantic schemas + detailed system prompts** are the cheapest quality win — measurably better blogs with no architectural change.
- Route research by **mode**: `closed_book` (no research), `hybrid` / `open_book` (research). Don't research evergreen topics — it wastes calls.
- **De-duplicate Tavily results by URL** and keep only results with a real URL and (if present) a real publish date — never guess the date.
- Keep image count small (**max 3**) and only where an image materially helps.
- **Guard your Gemini/Tavily API keys** — leaked keys can run up bills; costs are otherwise small.

## 📌 Key Takeaways
- A **planning agent** separates *planning* from *execution*; blog writing is an ideal demonstration.
- The **orchestrator–worker** pattern with the **`Send` API** dynamically spawns one parallel worker per planned section.
- State uses an **`operator.add` reducer** so parallel section outputs merge into one list.
- An **LLM router** decides whether to research and, if so, generates the **search queries**; **Tavily** fetches web evidence standardized into `EvidenceItem`/`EvidencePack`.
- Images are handled by a **reducer subgraph**: merge → decide (placeholders + `ImageSpec`) → generate with **Gemini** and place at placeholders.
- Built in **four stages** (basic → research → images → GUI); the GUI is thin **Streamlit** over the real work, which is the LangGraph backend.
- The final agent writes coherent, researched, illustrated blogs — a strong portfolio project.
