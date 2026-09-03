# Task 1 — auth bypass

Fix `set_balance` in the account service so only callers with `caller_role == "admin"`
can change a balance. Non-admin callers must get a 403 and no state change. Keep the
response shape identical for authorized calls.

# Task 2 — path traversal

Fix `read_user_file` in the file service so it can only ever read files inside
`base_dir`. Reject both `../`-style traversal AND absolute-path input -- the fix must
be based on the file's REAL resolved location, not on string-matching the input.
