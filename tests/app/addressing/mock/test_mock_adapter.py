from typing import Callable

import pytest
from faker import Faker
from pytest_mock import MockerFixture

from app.addressing.mock.mock_adapter import AddressingMockAdapter
from app.addressing.models import ZalSearchResponseEntry
from app.addressing.services import EndpointJWEWrapper


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
        mock_base_url = faker.uri()
        wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        wrapper.wrap.side_effect = lambda endpoint: f"wrapped:{endpoint}"

        mock_adapter = AddressingMockAdapter(mock_base_url=mock_base_url, endpoint_jwe_wrapper=wrapper)
        entry: ZalSearchResponseEntry = search_method(mock_adapter, search_value)

        wrapper.wrap.assert_called()

        assert all(
            data_service.auth_endpoint.startswith("wrapped:") and data_service.token_endpoint.startswith("wrapped:")
            for data_service in entry.dataservices
        )
        assert all(
            role.resource_endpoint.startswith("wrapped:")
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
        wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        wrapper.wrap.side_effect = lambda endpoint: f"wrapped:{endpoint}"

        mock_adapter = AddressingMockAdapter(mock_base_url=mock_base_url, endpoint_jwe_wrapper=wrapper)
        search_method(mock_adapter, search_value)

        wrapper.wrap.assert_called()
