# Video 21 — Human in the Loop (HITL) using LangGraph

> **Series:** Agentic AI using LangGraph (CampusX) · **Video ID:** `xxqZzVZ4gE0`
> **Watch:** https://www.youtube.com/watch?v=xxqZzVZ4gE0

## 🎯 Overview
Human-in-the-Loop (HITL) is a design approach in which a human is deliberately inserted at critical points of an AI workflow to supervise, approve, correct, or guide the model's output. This video first builds the theory — why autonomous agentic systems still need humans — and then shows exactly how LangGraph implements HITL using two functions: `interrupt` and `Command`. It closes with two runnable examples (a trivial approval gate and a more realistic stock-buying chatbot) so the pattern sticks.

## 🧠 Key Concepts

### What HITL is and why it exists
Agentic AI systems are built for **autonomy** — letting repetitive work (e.g., customer support at Swiggy/Zomato) run without human involvement. But today's LLMs (the "brain" of these systems) are not developed enough to handle every situation safely. HITL puts a **human checkpoint inside the AI pipeline** so that important decisions are not made autonomously by the model. Rule of thumb from the instructor: build any real AI system today and there is a ~99% chance you will need HITL somewhere.

Two primary reasons HITL exists:

1. **The LLM isn't perfect (assist the agent).** The model may misinterpret the user's goal, face an ambiguous query, or hallucinate. Classic example: *"Book flight tickets for next Friday."* If today is Monday, "next Friday" is ambiguous (this week's Friday vs. next week's). Instead of guessing, the agent pauses and asks the human to clarify.
2. **Accountability.** No matter how powerful an AI becomes, it cannot be held accountable — only a human can. For high-stakes actions (auto-replying to email as Gmail, making a payment) a human must confirm before the action fires, so responsibility stays with a person, not the model.

### Benefits of adding HITL
- **Accuracy improves.** Example: an invoice is scanned and the model reads ₹1,000 as ₹1,20,000. A confirmation step lets the human catch and correct the amount before payment.
- **Safety increases.** Example: "delete files I haven't used in 30 days" — the agent asks before deleting the 10 files that actually belong to the current project.
- **Ethical alignment.** Example: an angry customer message gets a logically-correct but cold reply; a human agent tells the model to add empathy so it matches company values.
- **Net result: a better user experience** — the more you use human + AI synergy, the better the output.

### The four common HITL integration patterns
1. **Approval / Action pattern (most common).** Before a crucial action (payment, important email, deleting files from a server), ask the human yes/no. Proceed only on "yes."
2. **Output review / edit pattern.** A research or social-media agent drafts content; a human reviews before it is posted, refining if needed.
3. **Ambiguity clarification pattern.** When the agent is confused (the "next Friday" case), it asks the human to disambiguate.
4. **Escalation pattern.** The agent works until it decides a case is beyond it, then escalates to a human agent — common in customer support ("Would you like to talk to a human executive?").

### How HITL works in LangGraph (conceptual walkthrough)
The instructor uses a **social-media manager agent** that researches a tweet for a topic (e.g., "GenAI") and then posts it. The workflow graph is: `START → research → post → END`. Two parts exist: a **frontend** and a LangGraph **backend**.

The entire mechanism rests on **two functions: `interrupt` and `Command`**, plus a **checkpointer** for saving state. When execution reaches a node containing `interrupt`, LangGraph:

1. **Pauses** the running execution at that node.
2. **Saves the current state** (e.g., `topic`, `draft`) via the checkpointer (an in-memory saver or SQLite/DB).
3. **Prepares a message** for the human (e.g., "I prepared this draft. Should I post it?").
4. **Sends that message out** of the graph to the frontend.

On the frontend the flow is: receive the interrupt message → show it to the user → collect the user's yes/no input → send it back to the backend by **calling `invoke` again, this time passing a `Command`** that carries the decision. LangGraph then loads the saved state from the checkpointer and **resumes execution from exactly the same node** where it paused, routing to post or reject accordingly, then reaching `END`.

Key mental model: a normal graph is invoked **once**. A HITL graph is invoked **once per human input required**, because the graph pauses, persists, and resumes.

## 🔧 Code / Implementation

### Example 1 — A minimal approval gate (Jupyter notebook)
A deliberately "stupid" example: the user asks a question, but before sending it to the LLM the graph interrupts and asks the user to confirm. Only on approval does the LLM answer.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()
llm = ChatOpenAI()

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

def chat_node(state: ChatState):
    # This node is ALSO the HITL node.
    # interrupt() prepares the payload the frontend needs and pauses execution.
    decision = interrupt({
        "type": "approval",
        "reason": "Confirm before querying the LLM",
        "question": state["messages"][-1].content,
        "instruction": "Approve (yes) or reject (no) sending this to the LLM?",
    })

    # We expect the frontend to resume with a dict like {"approved": "yes"/"no"}
    if decision["approved"] == "no":
        return {"messages": [AIMessage(content="Not approved")]}

    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

# HITL REQUIRES a checkpointer, because the graph pauses and its state must be saved.
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

**First invoke (frontend calls the graph the first time):**

```python
config = {"configurable": {"thread_id": "1"}}
initial_state = {"messages": [{"role": "user",
                 "content": "Explain gradient descent in very simple terms"}]}

result = app.invoke(initial_state, config=config)
# result now contains an "__interrupt__" key holding the payload we put inside interrupt()
```

**Show the interrupt to the user, collect input, resume with `Command`:**

```python
interrupt_payload = result["__interrupt__"]        # extract the message
user_input = input(str(interrupt_payload))          # e.g. "yes" or "no"

final = app.invoke(
    Command(resume={"approved": user_input}),        # key MUST match what the node reads
    config=config,                                   # same thread_id resumes the same run
)
print(final)
```

If the user sends `no`, the final AI message is `Not approved`. If `yes`, the LLM answer is returned. Note the resume payload key (`approved`) must match the key the node reads from `decision`.

### Example 2 — A realistic stock-trading chatbot with HITL on a risky tool
A normal chatbot with two tools: `get_stock_price` (real API-style lookup) and `purchase_stocks` (a **dummy** tool standing in for a real payment/brokerage integration). Without HITL, "purchase 10 stocks" executes silently — dangerous and unaccountable. With HITL, the purchase tool asks for approval first.

```python
from langgraph.types import interrupt
from langchain_core.tools import tool

@tool
def get_stock_price(symbol: str) -> str:
    """Return the current stock price for a company symbol."""
    # ... hits a stock-price API (same tool shown in earlier videos) ...
    return "The current stock price is $278"

@tool
def purchase_stocks(symbol: str, quantity: int) -> str:
    """Purchase a given quantity of shares for a company (DUMMY)."""
    # HITL lives INSIDE the tool, not in a separate node.
    decision = interrupt(f"Approve buying {quantity} shares of {symbol}? (yes/no)")

    # Here the frontend resumes with a plain STRING ("yes"/"no"), not a dict.
    if isinstance(decision, str) and decision.strip().lower() == "yes":
        return f"Purchase successful: bought {quantity} shares of {symbol}"
    return f"status: cancelled — did not buy {quantity} shares of {symbol}"

llm_with_tools = llm.bind_tools([get_stock_price, purchase_stocks])
```

The frontend is a CLI `while` loop (no UI). On each turn it invokes the graph; if the returned `__interrupt__` is not empty, the risky tool was triggered, so it shows the message, reads the user's yes/no, and re-invokes with `Command(resume="yes"/"no")` — this time resuming a **string** straight into the tool.

```python
config = {"configurable": {"thread_id": "1"}}
while True:
    user_msg = input("You: ")
    result = app.invoke({"messages": [("user", user_msg)]}, config=config)

    interrupt_val = result.get("__interrupt__")
    if interrupt_val:                       # risky purchase tool paused execution
        print(interrupt_val)                # "Approve buying 10 shares of Apple? (yes/no)"
        decision = input("Approve? (yes/no): ")
        result = app.invoke(Command(resume=decision), config=config)

    print(result["messages"][-1].content)
```

Observed behaviour: `get_stock_price` runs freely, but `purchase_stocks` always pauses with *"Approve buying 10 shares of Apple? yes/no"*; "yes" places the order, "no" declines it.

## 🪜 Step-by-Step Walkthrough
1. Identify the node/tool where a human decision is required (payment, post, delete, etc.).
2. Inside that node/tool, call `interrupt(payload)` with everything the frontend needs to show the user.
3. Compile the graph **with a checkpointer** (`InMemorySaver`, or a DB in production).
4. Frontend calls `graph.invoke(initial_state, config={"configurable": {"thread_id": ...}})`.
5. LangGraph pauses at `interrupt`, saves state, and returns an `__interrupt__` payload.
6. Frontend extracts the payload, shows it, and collects the human's decision.
7. Frontend re-invokes with `graph.invoke(Command(resume=decision), config=<same thread_id>)`.
8. LangGraph reloads state from the checkpointer and resumes from the exact paused node, routing on the decision until `END`.

## ⚠️ Gotchas & Tips
- **A checkpointer is mandatory for HITL** — pausing means the state must be persisted somewhere to be reloaded on resume.
- **Always re-use the same `thread_id`** across the initial invoke and the resume, or LangGraph cannot find the paused run.
- **The resume payload shape must match what the node reads.** Example 1 resumes a dict (`{"approved": ...}`); Example 2 resumes a plain string. Keep the producer and consumer in agreement.
- **HITL can live inside a tool, not just a node** — in the trading example the decision-making happens inside `purchase_stocks`.
- **You invoke once per human input.** Unlike a normal graph (one invoke), a HITL graph needs an extra invoke (with `Command`) for every pause.
- The examples ran in a notebook/CLI, but you can add a real UI (e.g., Streamlit) on top of the same backend.

## 📌 Key Takeaways
- HITL = a human checkpoint inside an AI pipeline so critical decisions aren't made autonomously.
- It exists for two reasons: LLMs aren't perfect (assistance) and only humans provide accountability.
- Four common patterns: approval/action, output review/edit, ambiguity clarification, escalation.
- Benefits: better accuracy, safety, ethical alignment, and overall user experience.
- LangGraph implements HITL with just two functions: `interrupt` (pause + emit payload) and `Command(resume=...)` (resume with the human's decision).
- A checkpointer + consistent `thread_id` are required so the graph can pause, persist, and resume from the same node.
- The resume value can be a dict or a string — it just has to match what the interrupting node expects.
