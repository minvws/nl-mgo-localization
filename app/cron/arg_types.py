from argparse import ArgumentTypeError
from collections.abc import Callable
from enum import Enum
from typing import Generic, TypeVar, cast

T = TypeVar("T")


class ListType(Generic[T]):
    """
    Argparse type for parsing comma-separated values into a list.

    Supports:
    - Enum classes
    - Any callable that accepts a single string argument

    Example:
        parser.add_argument("--colors", type=ListType(ColorEnum))
        # Input: "red,blue" -> [ColorEnum.RED, ColorEnum.BLUE]
    """

    def __init__(self, item_type: Callable[[str], T]) -> None:
        self.item_type = item_type

    def __call__(self, raw_input: str) -> list[T]:
        """Parse a comma-separated string into a list of a given type."""
        parsed_values: list[T] = []

        for raw_item in raw_input.split(","):
            item = raw_item.strip()
            if not item:
                continue

            try:
                parsed_values.append(self.item_type(item))
            except ValueError as err:
                raise self.__raise_type_error(item) from err

        return parsed_values

    def __raise_type_error(self, invalid_item: str) -> ArgumentTypeError:
        if self._is_enum():
            enum_type = cast(type[Enum], self.item_type)
            valid_options = ", ".join(e.value for e in enum_type)
            return ArgumentTypeError(f"Invalid value '{invalid_item}'. Valid options: {valid_options}")

        return ArgumentTypeError(f"Invalid value '{invalid_item}'")

    def _is_enum(self) -> bool:
        return isinstance(self.item_type, type) and issubclass(self.item_type, Enum)
