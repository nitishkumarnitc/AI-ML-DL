"""A plausible-looking but WRONG fix: blocks the literal substring '..' in
the input. It stops the obvious '../../etc/passwd' attack -- but does
NOTHING against an absolute path, which needs no '..' at all and reaches
anywhere on the filesystem just as easily. This is exactly the kind of
narrow, string-matching "fix" a quick pass would wrongly accept.
"""
import os


class FileService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def read_user_file(self, filename: str) -> str:
        if ".." in filename:  # BUG: blocks one attack shape, not the underlying problem
            raise PermissionError(f"access outside sandbox denied: {filename}")
        path = os.path.join(self.base_dir, filename)
        with open(path) as f:
            return f.read()
