from typing import Callable

import pytest
from faker import Faker
from pytest_mock import MockerFixture

from app.addressing.constants import SIGNATURE_PARAM_NAME
from app.addressing.mock.mock_adapter import AddressingMockAdapter
from app.addressing.models import ZalSearchResponseEntry
from app.addressing.signing_service import SigningService


class TestAddressingMockAdapter:
    @pytest.mark.parametrize(
        "search_method",
        [
            (AddressingMockAdapter.search_by_medmij_name),
            (AddressingMockAdapter.search_by_ura),
            (AddressingMockAdapter.search_by_agb),
            (AddressingMockAdapter.search_by_hrn),
            (AddressingMockAdapter.search_by_kvk),
        ],
    )
    def test_search_returns_signed_endpoints(
        self,
        search_method: Callable[[AddressingMockAdapter, str], ZalSearchResponseEntry],
        faker: Faker,
        mocker: MockerFixture,
    ) -> None:
        search_value = faker.company()
        signature = faker.hexify(faker.text())
        mock_base_url = faker.uri()

        signing_query_string = f"{SIGNATURE_PARAM_NAME}={signature}"

        signing_service = mocker.Mock(SigningService)
        signing_service.sign_endpoint.side_effect = lambda endpoint: f"{endpoint}?{signing_query_string}"

        mock_adapter = AddressingMockAdapter(
            sign_endpoints=True, mock_base_url=mock_base_url, signing_service=signing_service
        )
        entry: ZalSearchResponseEntry = search_method(mock_adapter, search_value)

        signing_service.sign_endpoint.assert_called()

        assert all(
            data_service.auth_endpoint.endswith(f"?{signing_query_string}")
            and data_service.token_endpoint.endswith(f"?{signing_query_string}")
            for data_service in entry.dataservices
        )
        assert all(
            role.resource_endpoint.endswith(f"?{signing_query_string}")
            for data_service in entry.dataservices
            for role in data_service.roles
        )

    @pytest.mark.parametrize(
        "search_method",
        [
            (AddressingMockAdapter.search_by_medmij_name),
            (AddressingMockAdapter.search_by_ura),
            (AddressingMockAdapter.search_by_agb),
            (AddressingMockAdapter.search_by_hrn),
            (AddressingMockAdapter.search_by_kvk),
        ],
    )
    def test_no_endpoints_signed(
        self,
        search_method: Callable[[AddressingMockAdapter, str], ZalSearchResponseEntry],
        faker: Faker,
        mocker: MockerFixture,
    ) -> None:
        search_value = faker.company()
        mock_base_url = faker.uri()

        signing_service = mocker.Mock(SigningService)

        mock_adapter = AddressingMockAdapter(
            sign_endpoints=False, mock_base_url=mock_base_url, signing_service=signing_service
        )
        search_method(mock_adapter, search_value)

        signing_service.sign_endpoint.assert_not_called()
