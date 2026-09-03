"""The grader: separate from the environment, black-box (only calls the
service's public interface, never reads its source), and never trusts the
candidate's code -- only its observable behavior.

In a real deployment the service would sit behind an HTTP API (Flask/FastAPI)
and the grader would speak HTTP, as described in project.md. Here the grader
calls the same public interface in-process via plain method calls -- the
grading logic and what it proves are identical either way.
"""
import threading
import time


def grade(service, item: str = "gadget", stock: int = 3) -> list:
    checks = []

    # Check 1: a single over-reservation must be rejected with 400.
    status, _ = service.reserve(item, 100)
    checks.append(("rejects a single over-reservation with status 400", status == 400))

    # Check 2: stock must be back to its starting value after the rejection.
    checks.append((f"stock for '{item}' unchanged after rejection (expected {stock})",
                    service.inventory.get(item) == stock))

    # Check 3: a valid request still succeeds.
    status2, _ = service.reserve("widget", 1)
    checks.append(("a valid request still succeeds (200)", status2 == 200))
    service.reserve("widget", -1)  # restore

    # Check 4 (the real one): during a slow over-reservation attempt, a
    # concurrent reader must never observe a transiently negative/invalid
    # stock value. This is the check a "mutate then revert, no lock" patch
    # fails, even though every single-request check above passes it.
    seen_bad_state = {"flag": False}

    def slow_over_reserve():
        service.reserve(item, 100)

    t = threading.Thread(target=slow_over_reserve)
    t.start()
    time.sleep(0.05)  # let the slow request get past its mutation, before its revert
    mid_flight_value = service.inventory.get(item, 0)
    if mid_flight_value < 0:
        seen_bad_state["flag"] = True
    t.join()

    checks.append(("no concurrent reader ever observes negative/invalid stock",
                    not seen_bad_state["flag"]))

    return checks


def report(checks: list) -> bool:
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return all(ok for _, ok in checks)
