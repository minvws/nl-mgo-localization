from logging import Logger

import inject

from app.addressing.addressing_service import AddressingService
from app.config.models import Config, HealthcareAdapterType
from app.exceptions.config_exception import ConfigException
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from app.healthcarefinder.zorgab.hydration_service import HydrationService
from app.healthcarefinder.zorgab.zorgab import ZorgABAdapter
from app.healthcarefinder.zorgab_mock.zorgab_mock import ZorgABMockHydrationAdapter


class HealthcareFinderAdapterFactory:
    @inject.autoparams("addressing_service", "logger", "config")
    def __init__(self, addressing_service: AddressingService, logger: Logger, config: Config):
        self.__addressing_service = addressing_service
        self.__logger = logger
        self.__config = config

    def create(
        self,
        healthcare_adapter: HealthcareAdapterType,
    ) -> HealthcareFinderAdapter:
        match healthcare_adapter:
            case HealthcareAdapterType.zorgab:
                zorgab_adapter: ZorgABAdapter = self._get_zorgab_adapter()
                return zorgab_adapter

            case HealthcareAdapterType.mock_zorgab_hydrated:
                mocked_hydration_adapter: HealthcareFinderAdapter = ZorgABMockHydrationAdapter()
                return mocked_hydration_adapter

            case HealthcareAdapterType.mock:
                mock_healthcarefinder_adapter: HealthcareFinderAdapter = MockHealthcareFinderAdapter()
                return mock_healthcarefinder_adapter

            case _:
                raise ConfigException("Unknown healthcarefinder adapter")

    def _get_zorgab_adapter(
        self,
    ) -> ZorgABAdapter:
        return ZorgABAdapter(
            base_url=self.__config.zorgab.base_url,
            mtls_cert_file=self.__config.zorgab.mtls_cert_file,
            mtls_key_file=self.__config.zorgab.mtls_key_file,
            mtls_chain_file=self.__config.zorgab.mtls_chain_file,
            proxy=self.__config.zorgab.proxy,
            hydration_service=HydrationService(self.__addressing_service),
            logger=self.__logger,
        )
