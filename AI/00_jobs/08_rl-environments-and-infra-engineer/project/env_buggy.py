"""The environment: a tiny inventory service with a real, specific bug.
BUG: reserve() never checks that qty <= current stock, so stock can go negative.
"""


class ReservationService:
    def __init__(self):
        self.inventory = {"widget": 10, "gadget": 3}

    def reserve(self, item: str, qty: int):
        self.inventory[item] -= qty  # BUG: no bounds check
        return 200, {"remaining": self.inventory[item]}
