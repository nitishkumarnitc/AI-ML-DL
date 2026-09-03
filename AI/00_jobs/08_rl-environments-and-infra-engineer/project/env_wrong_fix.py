"""A plausible-looking but WRONG fix: mutates first, "corrects" after the
fact, with no lock. Every single-request test passes -- the final response
and end state both look right. But there is a real window, while the
artificial delay runs, where stock is transiently invalid and a concurrent
reader can observe it. This is exactly the patch a weak grader would pass.
"""
import time


class ReservationService:
    def __init__(self):
        self.inventory = {"widget": 10, "gadget": 3}

    def reserve(self, item: str, qty: int):
        self.inventory[item] -= qty  # mutates first...
        time.sleep(0.3)  # ...simulates a slow downstream call (e.g. a real DB write)
        if self.inventory[item] < 0:
            self.inventory[item] += qty  # ...then "fixes" it after the fact
            return 400, {"error": "insufficient stock"}
        return 200, {"remaining": self.inventory[item]}
