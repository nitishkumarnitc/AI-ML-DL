"""The environment: a tiny account service with a real, specific bug.
BUG: set_balance never checks caller_role at all -- any caller can act as admin.
"""


class AccountService:
    def __init__(self):
        self.users = {"alice": {"role": "user", "balance": 100},
                      "admin": {"role": "admin", "balance": 0}}

    def set_balance(self, user: str, balance: int, caller_role: str):
        self.users[user]["balance"] = balance  # BUG: no auth check
        return 200, dict(self.users[user])
