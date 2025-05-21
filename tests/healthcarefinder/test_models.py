import pytest

from app.healthcarefinder.models import Identification, SearchRequest


class TestSearchRequest:
    def test_it_trims_whitespace_off_off_the_search_request(self) -> None:
        search_request = SearchRequest(city=" 123 ", name=" 456 ")
        assert search_request.city == "123"
        assert search_request.name == "456"


class TestIdentification:
    @pytest.mark.parametrize(
        "type, value, expected_type, expected_value",
        [
            (None, "123", None, "123"),
            ("random_type", None, "random_type", None),
            ("random_type", "123", "random_type", "123"),
            (None, None, None, None),
        ],
    )
    def test_identification_validation(
        self, type: str | None, value: str | None, expected_type: str | None, expected_value: str | None
    ) -> None:
        if type is None and value is None:
            with pytest.raises(ValueError):
                Identification()  # type: ignore
        else:
            identification = Identification(identification_type=type, identification_value=value)
            assert identification.identification_type == expected_type
            assert identification.identification_value == expected_value

    def test_identification_to_str(self) -> None:
        type: str = "type"
        value: str = "123"
        identification = Identification(identification_type=type, identification_value=value)

        assert str(identification) == f"{type}:{value}"
