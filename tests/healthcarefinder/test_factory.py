from typing import Any

import pytest

from app.addressing.addressing_service import AddressingService
from app.config.models import HealthcareAdapterType
from app.exceptions.config_exception import ConfigException
from app.healthcarefinder.factory import HealthcareFinderAdapterFactory
from app.healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter
from app.healthcarefinder.zorgab_mock.zorgab_mock import ZorgABMockHydrationAdapter
from tests.utils import configure_bindings


class TestFactory:
    @pytest.mark.parametrize(
        "adapter_type, expected",
        [
            (HealthcareAdapterType.zorgab, ZorgABAdapter),
            (HealthcareAdapterType.mock_zorgab_hydrated, ZorgABMockHydrationAdapter),
            (HealthcareAdapterType.mock, MockHealthcareFinderAdapter),
        ],
    )
    def test_returns_correct_healthcare_adapter(self, adapter_type: Any, expected: Any, mocker: Any) -> None:
        mock_addressing_service = mocker.Mock(AddressingService)
        configure_bindings(
            lambda binder: binder.bind(
                AddressingService,
                mock_addressing_service,
            )
        )

        factory = HealthcareFinderAdapterFactory()
        adapter = factory.create(adapter_type)

        assert isinstance(adapter, expected)

    def test_throws_config_exception_for_invalid_adapter_type(self, mocker: Any) -> None:
        mock_addressing_service = mocker.Mock(AddressingService)
        configure_bindings(
            lambda binder: binder.bind(
                AddressingService,
                mock_addressing_service,
            )
        )
        factory = HealthcareFinderAdapterFactory()

        mock_healthcare_adapter_type = mocker.patch("app.config.models.HealthcareAdapterType")
        mock_healthcare_adapter_type.__getitem__.return_value = "invalid"

        with pytest.raises(ConfigException):
            factory.create(mock_healthcare_adapter_type)
