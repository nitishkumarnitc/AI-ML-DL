"""A second environment, a different bug CLASS entirely: a payment service
with no idempotency handling at all -- retrying the same request (e.g. after
a network timeout, a very common real trigger) charges the customer twice.
"""


class PaymentService:
    def __init__(self):
        self.charges = []  # list of (idempotency_key, amount)

    def charge(self, amount: float, idempotency_key: str):
        self.charges.append((idempotency_key, amount))  # BUG: no dedup at all
        return {"status": "charged", "amount": amount}

    def get_charge_count(self, idempotency_key: str) -> int:
        return sum(1 for k, _ in self.charges if k == idempotency_key)

    def get_total_charged(self) -> float:
        return sum(a for _, a in self.charges)
