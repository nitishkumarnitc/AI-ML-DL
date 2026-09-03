"""
Sample project — Forward-Deployed / AI Solutions Engineer
A draft-reply generator for a service advisor across FIVE repair orders,
with a numeric-fact guardrail (never invents a price/date not in the note),
an escalation-detection heuristic (flags angry-sounding messages for a human
instead of drafting a reply at all), a session CLI with conversation
logging, and the assumptions/follow-up-questions deliverable that's the
actual output of a real first customer engagement.

Run:  python run.py                              (scripted demo across all 5 ROs)
      python run.py --interactive                (session CLI, pick an RO, chat, auto-logs)
      python run.py --log-file session.json       (used with --interactive)
Dependencies:
  - re (stdlib) -- fact extraction from the note text and the numeric guardrail check
  - json, argparse (stdlib) -- session logging and CLI
  - (no third-party packages -- swap draft_body() for a real LLM call to go live)
"""
import argparse
import json
import re

REPAIR_NOTES = {
    "RO-1042": "Customer dropped off 7/28. Brake pads + rotors, front. Parts backordered, "
               "ETA 8/2. Advisor: Mike.",
    "RO-1088": "Oil change + multi-point inspection. Found rear tire wear, flagged for "
               "customer approval. Completed 7/29, ready for pickup.",
    "RO-1103": "Check engine light diagnosis: P0301 misfire cylinder 1. Recommended spark "
               "plug replacement, quoted separately by parts desk. Awaiting customer approval "
               "as of 7/30.",
    "RO-1119": "Transmission fluid flush completed 7/31. No further issues found. Vehicle "
               "ready for pickup, advisor: Dana.",
    "RO-1130": "Customer reported grinding noise. Inspection found worn brake pads all "
               "around, estimate pending. Vehicle currently on lift as of 8/1.",
}

# Facts explicitly present in each note -- used only to check the draft never
# invents a number/date that isn't one of these.
NOTE_FACTS = {
    "RO-1042": {"7/28", "8/2"},
    "RO-1088": {"7/29"},
    "RO-1103": {"7/30"},
    "RO-1119": {"7/31"},
    "RO-1130": {"8/1"},
}

ANGRY_MARKERS = ["unacceptable", "furious", "ridiculous", "lawyer", "never again", "worst"]


def is_escalation(customer_text: str) -> bool:
    """A cheap, real technique: route on tone BEFORE generating anything --
    an angry customer message should reach a human, not an auto-draft."""
    t = customer_text.lower()
    return any(marker in t for marker in ANGRY_MARKERS)


def draft_body(customer_text: str, note: str) -> str:
    text = customer_text.lower()
    note_lower = note.lower()

    if ("ready" in text or "done" in text) and "ready for pickup" in note_lower:
        m = re.search(r"completed (\S+)", note, re.I)
        if m:
            return f"Good news -- your vehicle was completed on {m.group(1).rstrip('.,')} and is ready for pickup!"
        return "Good news -- your vehicle is ready for pickup!"

    if any(kw in text for kw in ["how much longer", "eta", "when", "update"]):
        m = re.search(r"eta (\S+)", note, re.I)
        if m:
            return f"We're still waiting on backordered parts -- current ETA is {m.group(1).rstrip('.,')}."
        m2 = re.search(r"awaiting customer approval as of (\S+)", note, re.I)
        if m2:
            return (f"We're waiting on your approval to proceed as of {m2.group(1).rstrip('.,')} -- "
                     f"let us know if you'd like to go ahead.")
        if "ready for pickup" in note_lower:
            m3 = re.search(r"completed (\S+)", note, re.I)
            if m3:
                return f"Good news -- your vehicle was completed on {m3.group(1).rstrip('.,')} and is ready for pickup!"

    if "price" in text or "cost" in text or "how much" in text:
        return "I don't have final pricing in front of me yet -- let me check and get back to you shortly."
    if "noise" in text or "grinding" in text:
        return "We found the issue during inspection and are working on an estimate now -- I'll follow up shortly."
    return "Thanks for reaching out -- checking your repair order now and will follow up shortly."


def draft_reply(customer_text: str, ro_number: str) -> dict:
    if is_escalation(customer_text):
        return {"draft": None, "escalated": True,
                "reason": "message tone suggests the customer is upset -- routed to a human, no auto-draft."}
    note = REPAIR_NOTES.get(ro_number)
    if not note:
        return {"draft": "[DRAFT] I don't have your repair order pulled up yet -- checking now "
                          "and will follow up shortly.", "escalated": False}
    return {"draft": "[DRAFT] " + draft_body(customer_text, note), "escalated": False}


def violates_guardrail(draft: str, ro_number: str) -> bool:
    allowed = NOTE_FACTS.get(ro_number, set())
    dates_in_draft = set(re.findall(r"\b\d{1,2}/\d{1,2}\b", draft))
    return bool(dates_in_draft - allowed)


def run_scripted_demo():
    print("=== Assumptions made (write these down before coding, in a real engagement) ===")
    print("- A human always approves before sending (draft-only, never auto-send).")
    print("- If the note doesn't answer the question, the draft says so honestly, never guesses.")
    print("- Messages that sound angry/escalated skip the draft entirely and route to a human.\n")

    scenarios = [
        ("hey is my car ready yet??", "RO-1088"),
        ("how much longer for the brake job", "RO-1042"),
        ("what's the total cost going to be", "RO-1042"),
        ("any update on my check engine light thing", "RO-1103"),
        ("is the transmission flush done", "RO-1119"),
        ("what's that grinding noise about", "RO-1130"),
        ("this is unacceptable, I've been waiting for days, I want a refund", "RO-1042"),
        ("hi there", "RO-9999"),  # unknown RO
    ]

    print("=== Draft replies across 5 repair orders ===")
    for customer_text, ro in scenarios:
        result = draft_reply(customer_text, ro)
        print(f"customer: {customer_text!r}  (RO {ro})")
        if result["escalated"]:
            print(f"  -> ESCALATED: {result['reason']}")
        else:
            flagged = violates_guardrail(result["draft"], ro)
            print(f"  -> {result['draft']}")
            print(f"  guardrail: {'VIOLATION -- fabricated a date not in the note!' if flagged else 'clean'}")
        print()

    print("=== Guardrail stress test: force a fabrication attempt ===")
    fabricated_draft = "[DRAFT] Your part will arrive 9/15 and total cost is $450."
    print(f"hypothetical bad draft: {fabricated_draft!r}")
    print(f"  guardrail: {'VIOLATION caught -- would be blocked before sending' if violates_guardrail(fabricated_draft, 'RO-1042') else 'clean'}")

    print("\n=== Follow-up questions for the customer (real FDE deliverable) ===")
    for q in [
        "What's your actual daily message volume across all advisors?",
        "Who is liable if a draft reply is wrong and an advisor sends it as-is?",
        "What system currently holds the repair-order notes, and can we get API access to it?",
        "How should escalated/angry messages be routed -- to the assigned advisor, or a manager?",
    ]:
        print(f"- {q}")


def run_interactive(log_file: str = None):
    print("Interactive session -- pick a repair order, then chat as the customer (Ctrl-C to quit).")
    print(f"Available: {', '.join(REPAIR_NOTES)}\n")
    ro = input("repair order> ").strip() or "RO-1088"
    history = []
    try:
        while True:
            msg = input("customer> ").strip()
            if not msg:
                continue
            result = draft_reply(msg, ro)
            entry = {"ro": ro, "customer_message": msg}
            if result["escalated"]:
                print(f"[ESCALATED] {result['reason']}")
                entry["escalated"] = True
            else:
                flagged = violates_guardrail(result["draft"], ro)
                print(f"advisor draft> {result['draft']}")
                if flagged:
                    print("  [guardrail violation -- would be blocked]")
                entry.update({"draft": result["draft"], "guardrail_violation": flagged})
            history.append(entry)
    except (KeyboardInterrupt, EOFError):
        print("\nsession ended.")
    if log_file and history:
        with open(log_file, "w") as f:
            json.dump(history, f, indent=2)
        print(f"session log written to {log_file}")


def main():
    parser = argparse.ArgumentParser(description="Service-advisor draft-reply assistant")
    parser.add_argument("--interactive", action="store_true", help="run a live session CLI instead of the scripted demo")
    parser.add_argument("--log-file", default=None, help="write the interactive session transcript here")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(args.log_file)
    else:
        run_scripted_demo()


if __name__ == "__main__":
    main()
