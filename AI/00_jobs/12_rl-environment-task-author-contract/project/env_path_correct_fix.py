"""A correct fix: resolve the REAL absolute path and verify it's still
inside base_dir -- this catches '../' traversal AND an absolute-path
bypass, because it checks the final resolved location, not the input string.
"""
import os


class FileService:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.realpath(base_dir)

    def read_user_file(self, filename: str) -> str:
        candidate = os.path.realpath(os.path.join(self.base_dir, filename))
        if os.path.commonpath([candidate, self.base_dir]) != self.base_dir:
            raise PermissionError(f"access outside sandbox denied: {filename}")
        with open(candidate) as f:
            return f.read()
