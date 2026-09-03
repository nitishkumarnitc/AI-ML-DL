"""The grader: separate from the environment, black-box, never trusts the
candidate's code. Deliberately includes a role the task brief never named,
to catch a deny-list-instead-of-allow-list bug.
"""


def grade(service) -> list:
    checks = []

    status, _ = service.set_balance("alice", 999999, caller_role="user")
    checks.append(("blocks the 'user' role (explicitly named in the task)", status == 403))
    checks.append(("state unchanged after a 'user' rejection", service.users["alice"]["balance"] == 100))

    status2, body2 = service.set_balance("alice", 500, caller_role="admin")
    checks.append(("allows the 'admin' role", status2 == 200 and service.users["alice"]["balance"] == 500))
    service.users["alice"]["balance"] = 100  # reset for the next check

    # The real check: a role the task brief never explicitly named. An
    # allow-list blocks this correctly; a deny-list (blocking only "user")
    # wrongly lets it through.
    status3, _ = service.set_balance("alice", 777777, caller_role="guest")
    checks.append(("blocks an unnamed non-admin role ('guest') -- allow-list, not deny-list",
                    status3 == 403 and service.users["alice"]["balance"] == 100))

    return checks


def report(checks: list) -> bool:
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return all(ok for _, ok in checks)
