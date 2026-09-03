# Video 09 — Iterative Workflows in LangGraph (Video 8)

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `7CbSqrovcsE`
> **Watch:** https://www.youtube.com/watch?v=7CbSqrovcsE

## 🎯 Overview
This video introduces the fourth type of LangGraph workflow — **iterative (looping) workflows** — after sequential, parallel, and conditional workflows covered earlier. An iterative workflow repeatedly cycles between two or more nodes to progressively *improve* a result. The concept is taught through a real, practical use case: an automated system that generates a social-media post (a tweet) on a given topic, evaluates its quality, and keeps optimizing it in a loop until it is good enough. Crucially, the video shows that loops in LangGraph are created simply by manipulating edges.

## 🧠 Key Concepts

### The four workflow types
By this point the series has covered:
1. **Sequential** — tasks run one after another in a linear order.
2. **Parallel** — multiple tasks run at the same time.
3. **Conditional** — one of several possible tasks is chosen based on a condition.
4. **Iterative / Looping (this video)** — the workflow cycles between nodes to refine an output. This becomes very common once you build more complex, real-world workflows.

### The real-world use case: auto-generating quality tweets
The instructor wants to automate posting on platforms like X/Twitter. The problem with naively asking an LLM to "write me a tweet" is that the **first-pass output is usually mediocre** — repetitive, low value. To fix this, you build a *generate → evaluate → optimize* loop so the content is iteratively improved before a human ever sees it.

The narrowed-down task: generate a **funny and original tweet** for the **X (Twitter)** platform on any given topic.

### The three components of the loop
1. **Generator (LLM)** — takes the topic and produces a tweet. Ideally a model with strong writing ability (e.g., GPT-4.5); in the demo GPT-4o is used.
2. **Evaluator (LLM)** — judges the generated tweet against a strict evaluation rubric and returns **two things**: a verdict (`approved` / `needs_improvement`) *and* written feedback. It should follow instructions faithfully (demo uses GPT-4o-mini).
3. **Optimizer (LLM)** — takes the tweet *plus* the evaluator's feedback and rewrites an improved version, which is sent **back to the evaluator**. Demo uses GPT-4o.

The loop runs between **evaluate ↔ optimize** until the evaluator approves (or a max-iteration cap is hit). In a real system, an approved post would go to a **human-in-the-loop** for final sign-off and then be published via an API call.

### Why a max-iteration guard is essential
The evaluator/optimizer loop can get stuck **infinitely** — e.g., if the evaluation criteria are too strict or the LLM is not capable enough, the evaluator keeps rejecting and the optimizer keeps producing new rejects. To break out, the state carries a `max_iteration` limit (here `5`) alongside an `iteration` counter. When iterations exceed the cap, the loop is forced to stop.

### Structured output for the evaluator
So the evaluator always returns a predictable shape (verdict + feedback), it uses **structured output** via a Pydantic schema bound to the LLM with `.with_structured_output(...)`.

### How loops are actually built in LangGraph
The key takeaway: **you create a loop simply by manipulating edges.** A normal edge from `optimize` back to `evaluate` (combined with the conditional edge out of `evaluate`) is what forms the cycle. Nothing special is required beyond wiring the edges.

## 🔧 Code / Implementation

### State definition
```python
from typing import TypedDict, Literal, Annotated
import operator
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

# Three LLMs (in a real project, pick specialised models per task)
generator_llm = ChatOpenAI(model="gpt-4o")
evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
optimizer_llm = ChatOpenAI(model="gpt-4o")

class TweetState(TypedDict):
    topic: str
    tweet: str
    evaluation: Literal["approved", "needs_improvement"]
    feedback: str
    iteration: int
    max_iteration: int
    # history (added later in the video)
    tweet_history: Annotated[list[str], operator.add]
    feedback_history: Annotated[list[str], operator.add]
```

### Structured-output schema for the evaluator
```python
class TweetEvaluation(BaseModel):
    evaluation: Literal["approved", "needs_improvement"] = Field(
        ..., description="Final evaluation result."
    )
    feedback: str = Field(..., description="Feedback for the tweet.")
```

### Generate node
```python
def generate_tweet(state: TweetState):
    messages = [
        SystemMessage(content="You are a funny and clever Twitter influencer."),
        HumanMessage(content=f"""
Write a short, original and hilarious tweet on the topic: {state['topic']}.

Rules:
- Do NOT use question-answer format.
- Max 280 characters.
- Use observational humour, irony, sarcasm, cultural references.
- Think in meme logic, punchlines, relatable takes.
- Use simple day-to-day English.
""")
    ]
    response = generator_llm.invoke(messages).content
    return {"tweet": response, "tweet_history": [response]}
```

### Evaluate node (structured output)
```python
def evaluate_tweet(state: TweetState):
    messages = [
        SystemMessage(content="You are a ruthless, no-laughs-given Twitter critic. "
                              "You evaluate tweets based on humour, originality, "
                              "virality and tweet format."),
        HumanMessage(content=f"""
Evaluate the following tweet: {state['tweet']}

Criteria:
1. Originality — is it fresh, or have you seen it 100 times?
2. Humour
3. Punchiness
4. Virality potential
5. Format

Auto-reject if the tweet:
- is in question-answer format
- exceeds 280 characters
- uses traditional/setup jokes

Respond ONLY in structured format:
- evaluation: 'approved' or 'needs_improvement'
- feedback: one paragraph with strengths and weaknesses.
""")
    ]
    structured_evaluator_llm = evaluator_llm.with_structured_output(TweetEvaluation)
    response = structured_evaluator_llm.invoke(messages)
    return {
        "evaluation": response.evaluation,
        "feedback": response.feedback,
        "feedback_history": [response.feedback],
    }
```

### Optimize node (increments the iteration counter)
```python
def optimize_tweet(state: TweetState):
    messages = [
        SystemMessage(content="You punch up tweets for virality and humour "
                              "based on given feedback."),
        HumanMessage(content=f"""
Improve the tweet based on this feedback: {state['feedback']}

Topic: {state['topic']}
Original tweet: {state['tweet']}

Rewrite it as a short, viral-worthy tweet. Avoid Q&A style and stay under 280 characters.
""")
    ]
    response = optimizer_llm.invoke(messages).content
    iteration = state['iteration'] + 1
    return {
        "tweet": response,
        "iteration": iteration,
        "tweet_history": [response],
    }
```

### Conditional routing function
```python
def route_evaluation(state: TweetState):
    if state['evaluation'] == "approved" or state['iteration'] >= state['max_iteration']:
        return "approved"
    else:
        return "needs_improvement"
```

### Wiring the graph (edges create the loop)
```python
graph = StateGraph(TweetState)

graph.add_node("generate", generate_tweet)
graph.add_node("evaluate", evaluate_tweet)
graph.add_node("optimize", optimize_tweet)

graph.add_edge(START, "generate")
graph.add_edge("generate", "evaluate")

graph.add_conditional_edges("evaluate", route_evaluation, {
    "approved": END,
    "needs_improvement": "optimize",
})

graph.add_edge("optimize", "evaluate")   # <-- this back-edge creates the loop

workflow = graph.compile()
```

### Running it
```python
initial_state = {
    "topic": "Indian Railways",
    "iteration": 1,       # first iteration
    "max_iteration": 5,
}
result = workflow.invoke(initial_state)

# Inspect intermediate tweets/feedback
for tweet in result["tweet_history"]:
    print(tweet)
```

## 🪜 Step-by-Step Walkthrough
1. Define three LLMs: generator, evaluator, optimizer.
2. Define `TweetState` with `topic`, `tweet`, `evaluation`, `feedback`, `iteration`, `max_iteration`.
3. Write `generate_tweet` — builds a system+human prompt and returns the generated tweet.
4. Write `evaluate_tweet` — uses a Pydantic schema + `.with_structured_output()` to return a verdict and feedback.
5. Write `optimize_tweet` — rewrites the tweet from feedback and increments `iteration`.
6. Write `route_evaluation` — the decision function for the conditional edge.
7. Add nodes `generate`, `evaluate`, `optimize`.
8. Add edges: `START → generate`, `generate → evaluate`, conditional `evaluate → END | optimize`, and `optimize → evaluate` (the loop-closing edge).
9. Compile and visualise; the diagram shows the evaluate↔optimize cycle.
10. Invoke with an initial state and inspect the result.
11. (Improvement) Add `tweet_history` and `feedback_history` with `operator.add` reducers to keep a running log of every tweet and its feedback.

## ⚠️ Gotchas & Tips
- **Reducer for history lists:** to keep a history of tweets/feedback across iterations without overwriting, annotate the list fields with a reducer (`Annotated[list[str], operator.add]`) and always **append as a list** (`[response]`) so items merge instead of replacing.
- **Max-iteration cap prevents infinite loops.** Without it, a strict evaluator + weak model can cycle forever.
- **Watch the routing/state key names.** The instructor hit a bug because the state key was `max_iteration` (singular) but the code referenced `iterations` — mismatched names throw errors.
- **A subtle silent bug:** an invalid model name (`gpt-40` vs `gpt-4o`) in the optimizer didn't error initially *because control flow never reached the optimizer* (the tweet kept getting approved on the first try). Errors in never-executed branches stay hidden.
- **To actually see multiple iterations**, use a weaker model (e.g., GPT-4o-mini) or a harder-to-satisfy prompt so the first tweet gets rejected and the loop engages.
- Prompt quality drives outcome quality: the more precisely you describe the evaluation criteria, the better the final result.

## 📌 Key Takeaways
- Iterative/looping workflows repeatedly cycle between nodes to **progressively improve** an output.
- The pattern here is **Generate → Evaluate → Optimize**, looping evaluate↔optimize until approval or a cap.
- The evaluator returns both a **verdict and feedback**; use **structured output** (Pydantic + `.with_structured_output`) to guarantee shape.
- The optimizer improves the content using the feedback and **increments the iteration counter**.
- Always include a **max-iteration guard** to break out of potentially infinite loops.
- In LangGraph, **loops are made by adding a back-edge** — you're just manipulating edges, nothing more.
- Use **reducer-annotated list fields** to accumulate history (tweets, feedback) across iterations.
- This workflow will later be extended with tools and human-in-the-loop.
