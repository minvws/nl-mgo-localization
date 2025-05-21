import pytest
import requests
from pytest_mock import MockerFixture
from requests.models import Response

from app.healthcarefinder.models import Organization, SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter


class TestZorgABAdapter:
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
        )

        bundle_data = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 1,
            "entry": [
                {
                    "resource": {
                        "resourceType": "Organization",
                        "id": "org1",
                        "meta": {"lastUpdated": last_updated},
                        "name": "Test Organization",
                    }
                }
            ],
        }

        fake_response = mocker.Mock(spec=Response)
        fake_response.status_code = 200
        fake_response.json.return_value = bundle_data
        mocker.patch.object(requests.Session, "get", return_value=fake_response)

        request = SearchRequest(name="huisarts", city="Amsterdam")
        search_response = adapter.search_organizations(request)

        assert isinstance(search_response, SearchResponse)
        assert hydration_service.hydrate_to_organization.call_count == 1
        assert search_response.organizations[0] is hydration_service.hydrate_to_organization.return_value
