"""A plausible-looking but WRONG fix: dedupes against only the MOST RECENT
idempotency key, not every key ever seen. It passes the obvious test
(immediately retry the same request twice -> charged once), but fails as
soon as a DIFFERENT request happens in between and the original key comes
back around -- exactly what happens in production when a client retries a
timed-out request after other traffic has already been processed.
"""


class PaymentService:
    def __init__(self):
        self.charges = []
        self._last_key = None  # BUG: only remembers the single most recent key

    def charge(self, amount: float, idempotency_key: str):
        if idempotency_key == self._last_key:
            return {"status": "charged", "amount": amount}  # replay (looks right for the easy case)
        self.charges.append((idempotency_key, amount))
        self._last_key = idempotency_key
        return {"status": "charged", "amount": amount}

    def get_charge_count(self, idempotency_key: str) -> int:
        return sum(1 for k, _ in self.charges if k == idempotency_key)

    def get_total_charged(self) -> float:
        return sum(a for _, a in self.charges)
