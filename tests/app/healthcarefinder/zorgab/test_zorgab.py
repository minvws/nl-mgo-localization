from logging import Logger
from typing import Any

import pytest
import requests
from pydantic import ValidationError
from pytest_mock import MockerFixture
from requests import RequestException, Response, Session

from app.healthcarefinder.models import Organization, SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.zorgab import ApiError, ZorgABAdapter


class TestZorgABAdapter:
    def __bundle_data(self) -> dict[str, Any]:  # type: ignore[explicit-any]
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Organization",
                        "id": "org1",
                        "meta": {"lastUpdated": "2024-05-05T10:00:00Z"},
                        "name": "Test Organization",
                    }
                }
            ],
        }

    @pytest.mark.parametrize(
        "last_updated",
        [
            "2024-05-05T10:00:00Z",
            "2024-05-05T10:00:00+01:00",
        ],
    )
    def test_search_organizations_parses_lastupdated_with_and_without_timezone(
        self, mocker: MockerFixture, last_updated: str
    ) -> None:
        logger = mocker.Mock()
        hydration_service = mocker.Mock()
        hydration_service.hydrate_to_organization.return_value = mocker.Mock(spec=Organization)
        adapter = ZorgABAdapter(
            base_url="https://zorgab.test/",
            hydration_service=hydration_service,
            logger=logger,
            suppress_hydration_errors=False,
        )

        fake_response = mocker.Mock(spec=Response)
        fake_response.status_code = 200
        fake_response.json.return_value = self.__bundle_data()
        mocker.patch.object(requests.Session, "get", return_value=fake_response)

        request = SearchRequest(name="huisarts", city="Amsterdam")
        search_response = adapter.search_organizations(request)

        assert isinstance(search_response, SearchResponse)
        assert hydration_service.hydrate_to_organization.call_count == 1
        assert search_response.organizations[0] is hydration_service.hydrate_to_organization.return_value

    def test_search_organizations_logs_and_reraises_hydration_error(self, mocker: MockerFixture) -> None:
        suppress_hydration_errors = False

        logger = mocker.Mock()
        hydration_service = mocker.Mock()
        hydration_service.hydrate_to_organization.side_effect = ValueError("Hydration failed!")
        adapter = ZorgABAdapter(
            base_url="https://zorgab.test/",
            hydration_service=hydration_service,
            logger=logger,
            suppress_hydration_errors=suppress_hydration_errors,
        )

        fake_response = mocker.Mock(spec=Response)
        fake_response.status_code = 200
        fake_response.json.return_value = self.__bundle_data()
        mocker.patch.object(requests.Session, "get", return_value=fake_response)

        request = SearchRequest(name="huisarts", city="Amsterdam")
        with pytest.raises(ValueError, match="Hydration failed!"):
            adapter.search_organizations(request)

        logger.warning.assert_called_once_with(
            "Error while trying to hydrate an organization (suppress_hydration_errors=%s)",
            suppress_hydration_errors,
            exc_info=True,
        )

    def test_search_organizations_logs_and_suppresses_hydration_error(self, mocker: MockerFixture) -> None:
        suppress_hydration_errors = True

        logger = mocker.Mock()
        hydration_service = mocker.Mock()
        hydration_service.hydrate_to_organization.side_effect = ValueError("Hydration failed!")
        adapter = ZorgABAdapter(
            base_url="https://zorgab.test/",
            hydration_service=hydration_service,
            logger=logger,
            suppress_hydration_errors=suppress_hydration_errors,
        )

        fake_response = mocker.Mock(spec=Response)
        fake_response.status_code = 200
        fake_response.json.return_value = self.__bundle_data()
        mocker.patch.object(requests.Session, "get", return_value=fake_response)

        request = SearchRequest(name="huisarts", city="Amsterdam")
        adapter.search_organizations(request)

        logger.warning.assert_called_once_with(
            "Error while trying to hydrate an organization (suppress_hydration_errors=%s)",
            suppress_hydration_errors,
            exc_info=True,
        )

    def test_search_organizations_logs_fhir_non_compliant_data(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock()
        hydration_service = mocker.Mock()
        adapter = ZorgABAdapter(
            base_url="https://zorgab.test/",
            hydration_service=hydration_service,
            logger=logger,
            suppress_hydration_errors=False,
        )

        invalid_bundle_data = {"resourceType": "non-compliant"}

        fake_response = mocker.Mock(spec=Response)
        fake_response.status_code = 200
        fake_response.json.return_value = invalid_bundle_data
        mocker.patch.object(requests.Session, "get", return_value=fake_response)

        request = SearchRequest(name="huisarts", city="Amsterdam")

        with pytest.raises(ValueError):
            adapter.search_organizations(request)

        logger.warning.assert_called_once()
        assert "ZorgAB API returned FHIR non-compliant data" in logger.warning.call_args[0][0]

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
            suppress_hydration_errors=False,
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
        ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )
        with pytest.raises(ValidationError):
            SearchRequest(name=name, city=city)

    def test_session_initialization(self, mocker: MockerFixture) -> None:
        session_init_spy = mocker.spy(Session, "__init__")
        ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )

        assert session_init_spy.call_count == 1

    def test_incorrect_status_code(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock(Logger)
        mock_session = mocker.Mock()
        response = Response()
        response.status_code = 418
        mock_session.get.return_value = response
        mocker.patch("requests.Session", return_value=mock_session)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=logger,
            suppress_hydration_errors=False,
        )

        with pytest.raises(ApiError) as exception_info:
            adapter.search_organizations(SearchRequest(name="foo", city="bar"))

        assert "Unexpected status code" in str(exception_info.value)
        logger.error.assert_any_call(
            "Incorrect status code returned from ZorgAB API: 'https://example.org/fhir/Organization'"
        )

    def test_connection_error(self, mocker: MockerFixture) -> None:
        logger = mocker.Mock(Logger)
        mock_session = mocker.Mock()
        request_exception = RequestException("Connection refused")
        mock_session.get.side_effect = request_exception
        mocker.patch("requests.Session", return_value=mock_session)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=logger,
            suppress_hydration_errors=False,
        )

        with pytest.raises(ApiError) as exception_info:
            adapter.search_organizations(SearchRequest(name="foo", city="bar"))

        assert "Error while trying to call" in str(exception_info.value)
        logger.error.assert_any_call(
            "Error while trying to call the external ZorgAB API: %s",
            request_exception,
        )

    def test_incorrect_parameters(self, mocker: MockerFixture) -> None:
        ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )

        with pytest.raises(ValidationError):
            SearchRequest(name="", city="")

    def test_verify_connection_success(self, mocker: MockerFixture) -> None:
        mock_session = mocker.Mock()
        response = Response()
        response.status_code = 200
        mock_session.get.return_value = response
        mocker.patch("requests.Session", return_value=mock_session)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )

        assert adapter.verify_connection() is True

    def test_verify_connection_failure(self, mocker: MockerFixture) -> None:
        mock_session = mocker.Mock()
        response = Response()
        response.status_code = 404
        mock_session.get.return_value = response
        mocker.patch("requests.Session", return_value=mock_session)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )

        assert adapter.verify_connection() is False

    def test_verify_connection_request_exception(self, mocker: MockerFixture) -> None:
        mock_session = mocker.Mock()
        request_exception = RequestException("Connection refused")
        mock_session.get.side_effect = request_exception
        mocker.patch("requests.Session", return_value=mock_session)

        adapter = ZorgABAdapter(
            "https://example.org",
            hydration_service=mocker.Mock(),
            logger=mocker.Mock(Logger),
            suppress_hydration_errors=False,
        )

        assert adapter.verify_connection() is False
