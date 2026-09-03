# Video 06 — Sequential Workflows in LangGraph (Video 5)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `bAWujyAl1Kk`
> **Watch:** https://www.youtube.com/watch?v=bAWujyAl1Kk

## 🎯 Overview
This is the first **hands-on** video in the series. After all the theory, we install LangGraph and build our first working graphs. The focus is **sequential (linear) workflows** — where tasks are connected one after another with no branching or parallel paths. Two goals: (1) learn the basic LangGraph coding syntax, and (2) be able to build any linear workflow yourself. Three examples are built: a non-LLM BMI calculator, a simple single-call LLM Q&A, and a two-call prompt-chaining blog generator.

## 🧠 Key Concepts

### Setup & installation
Create a folder (e.g. `langgraph-tutorials`), open it in VS Code, create and activate a **virtual environment** (`my_env`), and install the libraries. LangChain is installed alongside LangGraph because **any LLM-related component** (chat models, prompt templates, document loaders, text splitters) comes from LangChain — LangGraph handles the workflow, LangChain handles the LLM pieces. They work **hand in hand**.

```bash
python -m venv my_env
my_env\Scripts\activate            # activate the venv
pip install langgraph
pip install langchain
pip install langchain-openai       # to use OpenAI models
pip install python-dotenv          # to read environment variables
```

Work is done inside **Jupyter notebooks** (`.ipynb`) rather than plain `.py` files, because notebooks let you **visualize** the compiled graph inline. (Later projects will use `.py` files.)

### The fixed build pattern (5 steps)
Every LangGraph workflow follows the same recipe:
1. **Define the State** — a class inheriting `TypedDict`, listing each data point (key) and its type.
2. **Create the graph object** — `StateGraph(YourState)`.
3. **Add nodes** — `graph.add_node("name", function)`.
4. **Add edges** — `graph.add_edge(...)`, including `START` and `END`.
5. **Compile** (`graph.compile()`) to validate structure, then **execute** with `.invoke(initial_state)`.

### Node = Python function that takes and returns State
Each node is a Python function that receives the graph's **state object** as input and returns a state object. Inside it: read the values it needs from state, do the work, write results back (a **partial update**), and return the state. The node name and its underlying function name can differ.

### State carries everything end-to-end
Because the state flows through and evolves across all nodes, at the end you can access **every** intermediate value (title, outline, content), not just the final result — a concrete advantage over plain LangChain chains, where you'd only get the last step's output.

## 🔧 Code / Implementation

### Example 1 — BMI Calculator (non-LLM, single node)
```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. State
class BMIState(TypedDict):
    weight_kg: float
    height_m: float
    bmi: float
    category: str          # added in the extension below

# node function
def calculate_bmi(state: BMIState) -> BMIState:
    weight = state['weight_kg']
    height = state['height_m']
    bmi = weight / (height ** 2)
    state['bmi'] = round(bmi, 2)      # partial update
    return state

def label_bmi(state: BMIState) -> BMIState:
    bmi = state['bmi']
    if bmi < 18.5:
        state['category'] = "Underweight"
    elif bmi < 25:
        state['category'] = "Normal"
    elif bmi < 30:
        state['category'] = "Overweight"
    else:
        state['category'] = "Obese"
    return state

# 2. graph
graph = StateGraph(BMIState)

# 3. nodes
graph.add_node("calculate_bmi", calculate_bmi)
graph.add_node("label_bmi", label_bmi)

# 4. edges (sequential)
graph.add_edge(START, "calculate_bmi")
graph.add_edge("calculate_bmi", "label_bmi")
graph.add_edge("label_bmi", END)

# 5. compile + execute
workflow = graph.compile()

initial_state = {'weight_kg': 80, 'height_m': 1.73}
final_state = workflow.invoke(initial_state)
print(final_state)
```
The first version had only `calculate_bmi`; the extension adds a second node `label_bmi` to classify the person, requiring a new `category` key in state and one extra node + edge — demonstrating how easy it is to lengthen a linear chain.

**Visualizing the graph** (works in Jupyter, taken from the LangGraph docs):
```python
from IPython.display import Image
Image(workflow.get_graph().draw_mermaid_png())
```

### Example 2 — Simple LLM Q&A (single LLM call)
```python
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import TypedDict
from dotenv import load_dotenv

load_dotenv()                 # reads OPENAI_API_KEY from .env
model = ChatOpenAI()

class LLMState(TypedDict):
    question: str
    answer: str

def llm_qa(state: LLMState) -> LLMState:
    question = state['question']
    prompt = f"Answer the following question: {question}"
    answer = model.invoke(prompt).content     # .content = the text
    state['answer'] = answer
    return state

graph = StateGraph(LLMState)
graph.add_node("llm_qa", llm_qa)
graph.add_edge(START, "llm_qa")
graph.add_edge("llm_qa", END)
workflow = graph.compile()

final_state = workflow.invoke({'question': 'How far is the moon from the earth?'})
print(final_state['answer'])
```
The point here is only to show how **LangChain and LangGraph work together**; a single LLM call in a linear graph is admittedly overkill ("using a sledgehammer to crack a nut"), but it teaches the pattern.

### Example 3 — Prompt Chaining (blog generator, two LLM calls)
```python
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from typing import TypedDict
from dotenv import load_dotenv

load_dotenv()
model = ChatOpenAI()

class BlogState(TypedDict):
    title: str
    outline: str
    content: str

def create_outline(state: BlogState) -> BlogState:
    title = state['title']
    prompt = f"Generate a detailed outline for a blog on the topic: {title}"
    outline = model.invoke(prompt).content
    state['outline'] = outline
    return state

def create_blog(state: BlogState) -> BlogState:
    title = state['title']
    outline = state['outline']
    prompt = f"Write a detailed blog on the title '{title}' using the following outline:\n{outline}"
    content = model.invoke(prompt).content
    state['content'] = content
    return state

graph = StateGraph(BlogState)
graph.add_node("create_outline", create_outline)
graph.add_node("create_blog", create_blog)
graph.add_edge(START, "create_outline")
graph.add_edge("create_outline", "create_blog")
graph.add_edge("create_blog", END)
workflow = graph.compile()

final_state = workflow.invoke({'title': 'Rise of AI in India'})
print(final_state['outline'])
print(final_state['content'])
```
This is **prompt chaining**: two nodes, each calling the LLM in sequence (topic → outline → blog). Because state persists, the final result exposes `title`, `outline`, **and** `content` — all still accessible at the end.

## 🪜 Step-by-Step Walkthrough
1. Install `langgraph`, `langchain`, `langchain-openai`, `python-dotenv` in a fresh virtual env.
2. Confirm imports work: `from langgraph.graph import StateGraph` (install `ipykernel` if prompted).
3. Define a `TypedDict` **State** for the workflow's data points.
4. Create `StateGraph(State)`.
5. Write node functions (each takes state, updates it, returns state) and register them with `add_node`.
6. Wire them with `add_edge`, starting from `START` and ending at `END`.
7. `compile()` the graph into a runnable, store it (e.g. `workflow`).
8. Optionally visualize with the mermaid-PNG snippet in Jupyter.
9. Build an `initial_state` dict and call `workflow.invoke(initial_state)`; read the `final_state`.

## ⚠️ Gotchas & Tips
- Put the OpenAI key in a **`.env`** file and load it with `load_dotenv()`; never hardcode it.
- LLM responses are objects — use **`.content`** to get the text string.
- Node **name** and the **function** it points to can be different names.
- Use **Jupyter notebooks** so you can render/visualize the compiled graph inline (the visualization code doesn't work in plain `.py` files).
- For purely linear work LangGraph is overkill; its true power shows with complex/branching/parallel workflows — these simple examples exist only to teach syntax.
- **Homework given:** extend the prompt-chaining example with a third `evaluate` node that prompts "Based on this outline, rate my blog" and returns an integer score — requires updating both the State and the graph.

## 📌 Key Takeaways
- First practical video: install LangGraph + LangChain + langchain-openai + python-dotenv in a venv; code in Jupyter notebooks.
- **LangChain supplies LLM components; LangGraph orchestrates the workflow** — they're used together.
- Every workflow = **State (`TypedDict`) → StateGraph → add_node → add_edge (START…END) → compile → invoke**.
- A **node is a Python function** that reads state, does a **partial update**, and returns state.
- Built three sequential examples: **BMI calculator** (non-LLM), **single-call Q&A**, and **prompt chaining** (outline → blog).
- Because **State persists and evolves**, all intermediate values remain accessible at the end — an advantage over LangChain chains.
- Visualize compiled graphs in Jupyter with `workflow.get_graph().draw_mermaid_png()`.
