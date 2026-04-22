import argparse
import sys
from typing import Any, Protocol


def print_progress_bar(progress: int, total: int) -> None:
    if total == 0:
        total = 1
        progress = 1

    bar_length = 40
    block = int(round(bar_length * progress / total))
    text = f"\rProgress: [{'#' * block + '-' * (bar_length - block)}] {progress}/{total}"
    sys.stdout.write(text)
    sys.stdout.flush()


class SubParsers(Protocol):
    """Wrapper class used to prevent having to type hint private (_prefixed) argparse types."""

    def add_parser(self, name: str, **kwargs: Any) -> argparse.ArgumentParser: ...  # type: ignore[explicit-any]
