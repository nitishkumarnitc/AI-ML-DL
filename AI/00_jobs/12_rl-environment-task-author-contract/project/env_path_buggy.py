"""Second authored task -- a DIFFERENT bug class: path traversal. A naive
file-serving function that joins user input directly onto a base directory
with no containment check, so '../../etc/passwd'-style input (or an
absolute path) escapes the intended sandbox entirely.
"""
import os


class FileService:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def read_user_file(self, filename: str) -> str:
        path = os.path.join(self.base_dir, filename)  # BUG: no containment check
        with open(path) as f:
            return f.read()
