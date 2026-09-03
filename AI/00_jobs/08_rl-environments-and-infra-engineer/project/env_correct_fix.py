"""A correct fix: validate before mutating, and hold a lock across the whole
check-then-mutate so a concurrent call can never interleave inside it.
"""
import threading


class ReservationService:
    def __init__(self):
        self.inventory = {"widget": 10, "gadget": 3}
        self._lock = threading.Lock()

    def reserve(self, item: str, qty: int):
        with self._lock:
            if qty > self.inventory.get(item, 0):
                return 400, {"error": "insufficient stock"}
            self.inventory[item] -= qty
            return 200, {"remaining": self.inventory[item]}
