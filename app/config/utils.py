from typing import Callable, List, TypeVar

T = TypeVar("T")


def lines_to_list(value: str, item_type: Callable[[str], T]) -> List[T]:
    """
    Convert a newline-separated string into a list.
    Each line is stripped and converted using `item_type`. Empty lines are ignored.
    """
    return [item_type(stripped_line) for raw_line in value.splitlines() if (stripped_line := raw_line.strip())]
