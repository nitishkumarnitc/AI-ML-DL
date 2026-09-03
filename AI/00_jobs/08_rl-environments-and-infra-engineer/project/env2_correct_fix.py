"""A correct fix: remember EVERY idempotency key ever seen (not just the
most recent one), and short-circuit a repeat with the original result."""


class PaymentService:
    def __init__(self):
        self.charges = []
        self._seen = {}  # idempotency_key -> result, for ALL keys ever seen

    def charge(self, amount: float, idempotency_key: str):
        if idempotency_key in self._seen:
            return self._seen[idempotency_key]  # replay, no new charge
        self.charges.append((idempotency_key, amount))
        result = {"status": "charged", "amount": amount}
        self._seen[idempotency_key] = result
        return result

    def get_charge_count(self, idempotency_key: str) -> int:
        return sum(1 for k, _ in self.charges if k == idempotency_key)

    def get_total_charged(self) -> float:
        return sum(a for _, a in self.charges)
