"""A correct fix: allow-list check -- only the literal 'admin' role may act."""


class AccountService:
    def __init__(self):
        self.users = {"alice": {"role": "user", "balance": 100},
                      "admin": {"role": "admin", "balance": 0}}

    def set_balance(self, user: str, balance: int, caller_role: str):
        if caller_role != "admin":
            return 403, {"error": "forbidden"}
        self.users[user]["balance"] = balance
        return 200, dict(self.users[user])
