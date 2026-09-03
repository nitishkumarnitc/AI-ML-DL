"""Black-box grader for the path-traversal task. Sets up a real temp
directory with an allowed file inside the sandbox and a secret file
OUTSIDE it, then tries three access patterns: normal, '../' traversal, and
an absolute-path bypass (the one narrow string-matching fixes miss).
"""
import os
import tempfile


def grade(service_cls) -> list:
    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        sandbox_dir = os.path.join(tmp, "sandbox")
        os.makedirs(sandbox_dir)
        with open(os.path.join(sandbox_dir, "allowed.txt"), "w") as f:
            f.write("this file is meant to be readable")
        secret_path = os.path.join(tmp, "secret.txt")
        with open(secret_path, "w") as f:
            f.write("TOP SECRET -- should never be readable via the file service")

        service = service_cls(sandbox_dir)

        try:
            content = service.read_user_file("allowed.txt")
            checks.append(("reads an in-sandbox file normally", "readable" in content))
        except Exception:
            checks.append(("reads an in-sandbox file normally", False))

        try:
            service.read_user_file("../secret.txt")
            checks.append(("blocks '../' traversal to the secret file", False))
        except (PermissionError, OSError):
            checks.append(("blocks '../' traversal to the secret file", True))

        try:
            service.read_user_file(secret_path)  # absolute path -- no '..' needed at all
            checks.append(("blocks an ABSOLUTE-PATH bypass to the secret file", False))
        except (PermissionError, OSError):
            checks.append(("blocks an ABSOLUTE-PATH bypass to the secret file", True))

    return checks


def report(checks: list) -> bool:
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    return all(ok for _, ok in checks)
