"""A plausible-looking but WRONG fix: a deny-list instead of an allow-list.
It correctly blocks the one role the task description happened to mention
("user") and correctly allows "admin" -- so it passes an obvious 2-case test.
But it's an inverted-logic bug: ANY role that isn't literally "user" is
treated as authorized, including "guest", "hacker", or a typo. This is
exactly the kind of patch a narrow grader (testing only user/admin) would
wrongly pass.
"""


class AccountService:
    def __init__(self):
        self.users = {"alice": {"role": "user", "balance": 100},
                      "admin": {"role": "admin", "balance": 0}}

    def set_balance(self, user: str, balance: int, caller_role: str):
        if caller_role.lower() == "user":  # BUG: deny-list instead of allow-list
            return 403, {"error": "forbidden"}
        self.users[user]["balance"] = balance
        return 200, dict(self.users[user])
