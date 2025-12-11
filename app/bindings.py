import logging

import inject
from inject import Binder
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.zal_importer.importers import OrganisationListImporter

from .addressing.addressing_service import AddressingAdapter
from .addressing.mock.mock_adapter import AddressingMockAdapter
from .addressing.repositories import KeyRepository
from .addressing.signing_service import SigningService
from .addressing.zal.zal_adapter import AddressingZalAdapter
from .config.models import AddressingAdapterType, Config, HealthcareAdapterType
from .db.db import Database
from .exceptions.config_exception import ConfigException
from .healthcarefinder.factory import HealthcareFinderAdapterFactory
from .healthcarefinder.healthcarefinder import HealthcareFinder
from .healthcarefinder.interface import HealthcareFinderAdapter
from .healthcarefinder.mock.adapter import MockHealthcareFinderAdapter
from .healthcarefinder.zorgab_mock.zorgab_mock import ZorgABMockHydrationAdapter
from .logger.factory import create_logger
from .version.models import VersionInfo
from .version.services import read_version_info


def configure_bindings(binder: Binder, config: Config) -> None:
    """
    Configure dependency bindings for the application.
    """
    binder.bind(Config, config)
    binder.bind(VersionInfo, read_version_info())

    __bind_logger(binder, config)
    __bind_db(binder, config)
    __bind_addressing_finder_adapter(binder, config)
    __bind_healthcare_finder(binder, config)
    __bind_healthcare_finder_adapter(binder, config)
    __bind_mock_healthcare_finder_adapter(binder, config)
    __bind_zorgab_mock_hydration_adapter(binder, config)
    __bind_signing_service_and_key_repository(binder, config)
    __bind_org_list_importer(binder, config)


def __bind_logger(binder: Binder, config: Config) -> logging.Logger:
    logger = create_logger(config)
    binder.bind(
        logging.Logger,
        logger,
    )
    return logger


def __bind_db(binder: Binder, app_config: Config) -> None:
    database = Database(dsn=app_config.database.dsn, logger=create_logger(app_config))
    binder.bind(Database, database)

    session_factory = sessionmaker(bind=database.engine)
    # scoped_session helps manage connections, transactions, and handles cleanup automatically.
    scoped_session_factory = scoped_session(session_factory)

    binder.bind(Session, scoped_session_factory)


def __bind_addressing_finder_adapter(binder: Binder, config: Config) -> None:
    if config.app.addressing_adapter == AddressingAdapterType.mock:
        binder.bind_to_constructor(
            AddressingAdapter,
            lambda: AddressingMockAdapter(
                sign_endpoints=config.signing.sign_endpoints, mock_base_url=config.app.mock_base_url
            ),
        )
    elif config.app.addressing_adapter == AddressingAdapterType.zal:
        binder.bind_to_constructor(
            AddressingAdapter,
            lambda: AddressingZalAdapter(sign_endpoints=config.signing.sign_endpoints),
        )
    else:
        raise ConfigException("Unknown addressing adapter")


def __bind_healthcare_finder(binder: Binder, config: Config) -> None:
    binder.bind_to_provider(
        HealthcareFinder,
        lambda: HealthcareFinder(allow_search_bypass=config.healthcarefinder.allow_search_bypass),
    )


def __bind_healthcare_finder_adapter(binder: Binder, config: Config) -> None:
    binder.bind_to_provider(
        HealthcareFinderAdapter,
        lambda: HealthcareFinderAdapterFactory().create(healthcare_adapter=config.app.healthcare_adapter),
    )


def __bind_mock_healthcare_finder_adapter(binder: Binder, config: Config) -> None:
    binder.bind_to_provider(
        MockHealthcareFinderAdapter,
        lambda: HealthcareFinderAdapterFactory().create(healthcare_adapter=HealthcareAdapterType.mock),
    )


def __bind_zorgab_mock_hydration_adapter(binder: Binder, config: Config) -> None:
    binder.bind_to_provider(
        ZorgABMockHydrationAdapter,
        lambda: ZorgABMockHydrationAdapter(mock_base_url=config.app.mock_base_url),
    )


def __bind_signing_service_and_key_repository(binder: Binder, config: Config) -> None:
    key_repository = KeyRepository(private_key_path=config.signing.private_key_path)  # type: ignore
    binder.bind(KeyRepository, key_repository)

    signing_service = SigningService(key_repository=key_repository)
    binder.bind(SigningService, signing_service)


def __bind_org_list_importer(binder: Binder, config: Config) -> None:
    binder.bind_to_constructor(
        OrganisationListImporter,
        lambda: OrganisationListImporter(
            signing_service=inject.instance(SigningService) if config.signing.sign_endpoints else None,
        ),
    )
