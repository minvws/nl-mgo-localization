from argparse import ArgumentTypeError
from enum import Enum
from typing import Any, List, Type

import pytest
from pytest_mock import MockerFixture

from app.cron.arg_types import ListType


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestListType:
    @pytest.mark.parametrize(
        "parser_cls,parser_type,input_str,expected",
        [
            (ListType[int], int, "1,2,3", [1, 2, 3]),
            (ListType[int], int, " 10 , 20 , 30 ", [10, 20, 30]),
            (ListType[int], int, "", []),
            (ListType[int], int, " , , ", []),
            (ListType[str], str, "a,b,c", ["a", "b", "c"]),
            (ListType[str], str, " x , y , z ", ["x", "y", "z"]),
            (ListType[str], str, "a,,b, ,c", ["a", "b", "c"]),
            (ListType[str], str, "", []),
            (ListType[str], str, " , , ", []),
            (ListType[Color], Color, "red,green", [Color.RED, Color.GREEN]),
            (ListType[Color], Color, "blue", [Color.BLUE]),
        ],
    )
    def test_parses_values_correctly(  # type: ignore[explicit-any]
        self,
        parser_cls: Type[ListType[Any]],
        parser_type: Type[Any],
        input_str: str,
        expected: List[Any],
    ) -> None:
        parser = parser_cls(parser_type)
        result = parser(input_str)
        assert result == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("a,,b, ,c", ["a", "b", "c"]),
            ("", []),
            (" , , ", []),
        ],
    )
    def test_skips_empty_items(self, input_str: str, expected: List[str]) -> None:
        parser = ListType[str](str)
        result = parser(input_str)
        assert result == expected

    def test_callable_parser(self, mocker: MockerFixture) -> None:
        def to_upper(value: str) -> str:
            return value.upper()

        mock_callable = mocker.Mock(side_effect=to_upper)
        parser = ListType[str](mock_callable)

        result = parser("a,b,c")
        assert result == ["A", "B", "C"]
        assert mock_callable.call_count == 3
        mock_callable.assert_any_call("a")
        mock_callable.assert_any_call("b")
        mock_callable.assert_any_call("c")

    def test_invalid_int_raises(self) -> None:
        parser = ListType[int](int)

        with pytest.raises(ArgumentTypeError) as exc:
            parser("1,2,notanint")

        assert "Invalid value 'notanint'" in str(exc.value)

    def test_invalid_enum_raises(self) -> None:
        parser = ListType[Color](Color)

        with pytest.raises(ArgumentTypeError) as exc:
            parser("red,yellow")

        msg = str(exc.value)
        assert "Invalid value 'yellow'" in msg
        assert "Valid options: red, green, blue" in msg

    def test_value_error_wrapped_as_argument_type_error(self) -> None:
        def value_error_parser(value: str) -> int:
            if value == "bad":
                raise ValueError("cannot parse")
            return int(value)

        parser = ListType[int](value_error_parser)
        assert parser("1,2") == [1, 2]

        with pytest.raises(ArgumentTypeError) as exc:
            parser("1,bad,3")

        assert "Invalid value 'bad'" in str(exc.value)

    def test_other_exceptions_propagate(self) -> None:
        def failing_parser(value: str) -> int:
            if value == "fail":
                raise RuntimeError("boom")

            return int(value)

        parser = ListType[int](failing_parser)
        assert parser("1,2") == [1, 2]

        with pytest.raises(RuntimeError) as exc:
            parser("1,fail,3")

        assert str(exc.value) == "boom"
