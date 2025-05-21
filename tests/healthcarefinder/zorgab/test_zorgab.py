from logging import Logger

import pytest
from pytest_mock import MockerFixture
from requests import RequestException, Response, Session

from app.healthcarefinder.models import SearchRequest
from app.healthcarefinder.zorgab.zorgab import ApiError, BadSearchParams, ZorgABAdapter


class TestZorgAb:
    @pytest.mark.parametrize(
        "name, city, expected",
        [
            ("foo", "bar", "name=foo&address-city=bar"),
            ("foo", "'s-Hertogenbosch", "name=foo&address-city=%27%27s-Hertogenbosch"),
            ("foo", "&foobar=1", "name=foo&address-city=%26foobar%3D1"),
        ],
    )
    def test_fhir_search_params_valid(
        self,
        mocker: MockerFixture,
        name: str,
        city: str,
        expected: str,
    ) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )
        search = SearchRequest(name=name, city=city)
        assert expected == adapter.create_fhir_search(search)

    @pytest.mark.parametrize(
        "name, city",
        [
            ("foo", ""),
            ("", ""),
            ("  ", "bar"),
        ],
    )
    def test_fhir_search_params_invalid(
        self,
        mocker: MockerFixture,
        name: str,
        city: str,
    ) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )
        search = SearchRequest(name=name, city=city)
        with pytest.raises(ValueError):
            adapter.create_fhir_search(search)

    def test_session_initialization(self, mocker: MockerFixture) -> None:
        session_init_spy = mocker.spy(Session, "__init__")
        ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )

        assert session_init_spy.call_count == 1

    def test_incorrect_status_code(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock(Logger)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=logger,
        )

        response = Response()
        response.status_code = 418
        session_mock = mocker.Mock(spec=Session)
        session_mock.get = mocker.Mock(return_value=response)

        with pytest.raises(ApiError) as exception_info:
            adapter.search_organizations(SearchRequest(name="foo", city="bar"))

        assert "Unexpected status code" in str(exception_info.value)

        logger.error.assert_any_call(
            "Incorrect status code returned from ZorgAB API: 'https://example.org/fhir/Organization'"
        )

    def test_connection_error(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock(Logger)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=logger,
        )

        request_exception = RequestException("Connection refused")
        mocker.patch("requests.Session.get", side_effect=request_exception)

        with pytest.raises(ApiError) as exception_info:
            adapter.search_organizations(SearchRequest(name="foo", city="bar"))

        assert "Error while trying to call" in str(exception_info.value)

        logger.error.assert_any_call(
            "Error while trying to call the external ZorgAB API: %s",
            request_exception,
        )

    def test_incorrect_parameters(self, mocker: MockerFixture) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )

        with pytest.raises(BadSearchParams):
            adapter.search_organizations(SearchRequest(name="", city=""))

    def test_verify_connection_success(self, mocker: MockerFixture) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )

        response = Response()
        response.status_code = 200
        mocker.patch("requests.Session.get", return_value=response)

        assert adapter.verify_connection() is True

    def test_verify_connection_failure(self, mocker: MockerFixture) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )

        response = Response()
        response.status_code = 404
        session_mock = mocker.Mock(spec=Session)
        session_mock.get = mocker.Mock(return_value=response)

        assert adapter.verify_connection() is False

    def test_verify_connection_request_exception(self, mocker: MockerFixture) -> None:
        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
        )

        request_exception = RequestException("Connection refused")
        session_mock = mocker.Mock(spec=Session)
        session_mock.get = mocker.Mock(side_effect=request_exception)

        assert adapter.verify_connection() is False
