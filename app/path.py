import os


def project_root(*args: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", *args))
