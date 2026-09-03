"""Black-box grader for the payment-idempotency environment. Deliberately
interleaves a DIFFERENT request between two retries of the same one, since
that's the exact production scenario ("only remembers the last key") fails.
"""


def grade(service) -> list:
    checks = []

    service.charge(10, "req-A")
    service.charge(10, "req-A")  # immediate retry -- the easy case
    checks.append(("immediate retry of the same key charges only once",
                    service.get_charge_count("req-A") == 1))

    service.charge(5, "req-B")  # a different request arrives in between
    service.charge(10, "req-A")  # req-A comes back around (e.g. a delayed retry)

    checks.append(("a delayed retry after OTHER traffic still charges only once",
                    service.get_charge_count("req-A") == 1))
    checks.append(("the unrelated request was charged normally",
                    service.get_charge_count("req-B") == 1))
    checks.append(("total charged reflects exactly 2 real charges (A once, B once), not 3",
                    service.get_total_charged() == 15))

    return checks


def report(checks: list) -> bool:
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return all(ok for _, ok in checks)
