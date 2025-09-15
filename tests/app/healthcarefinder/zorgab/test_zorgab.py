from typing import Any, Dict

import pytest
import requests
from pytest_mock import MockerFixture
from requests.models import Response

from app.healthcarefinder.models import Organization, SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter


class TestZorgABAdapter:
    def __bundle_data(self) -> Dict[str, Any]:
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Organization",
                        "id": "org1",
                        "meta": {"lastUpdated": "2024-05-05T10:00:00"},
                        "name": "Test Organization",
                    }
                }
            ],
        }

    @pytest.mark.parametrize(
        "last_updated",
        [
            "2024-05-05T10:00:00",
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
