import logging

import inject
from inject import Binder
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.addressing.factories import EndpointJWEFactory, EndpointJWTFactory
from app.benchmark.zorgab.benchmark import (
    BenchmarkOutputWriter,
    BenchmarkQueryLoader,
    DefaultBenchmarkQueryLoader,
    FileLoader,
    JsonFileOutputWriter,
)
from app.db.repositories import DbEndpointRepository, EndpointRepository
from app.search_indexation.constants import (
    ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME,
    SEARCH_INDEX_OUTPUT_DIR,
    SEARCH_INDEX_OUTPUT_FILENAME,
    SEARCH_INDEX_TEMP_DIR,
)
from app.search_indexation.repositories import (
    EncryptedEndpointsFileRepository,
    EncryptedEndpointsRepository,
    MockEndpointsRepository,
    MockOrganizationsFileRepo,
    SearchIndexFileRepository,
    SearchIndexRepository,
)
from app.search_indexation.services import MockOrganizationsMerger
from app.zorgab_scraper.config import IdentifierSource, ZorgABScraperConfig
from app.zorgab_scraper.services import (
    AgbCsvIdentifierRepository,
    IdentifierProvider,
    ZaklXmlIdentifierRepository,
)

from .addressing.addressing_service import AddressingAdapter
from .addressing.mock.mock_adapter import AddressingMockAdapter
from .addressing.repositories import FilesystemJWKStoreRepository, KeyStoreRepository
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
from .normalization.services import DutchGridTransformerFactory, GeoCoordinateService
from .version.models import VersionInfo
from .version.services import read_version_info


def configure_bindings(binder: Binder, config: Config) -> None:
    """
    Configure dependency bindings for the application.
    """
    binder.bind(Config, config)
    binder.bind(VersionInfo, read_version_info())

    __bind_logger(binder, config)
    __bind_zorgab_scraper_config(binder, config)
    __bind_db(binder, config)
    __bind_addressing_finder_adapter(binder, config)
    __bind_healthcare_finder(binder, config)
    __bind_healthcare_finder_adapter(binder, config)
    __bind_mock_healthcare_finder_adapter(binder, config)
    __bind_zorgab_mock_hydration_adapter(binder, config)
    __bind_geo_coordinate_service(binder)
    __bind_benchmark_services(binder)
    __bind_identifier_provider(binder)
    __bind_key_repository(binder, config)
    __bind_search_index_repositories(binder, config)
    __bind_endpoint_repository(binder, config)
    __bind_mock_organization_services(binder, config)


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
                mock_base_url=config.app.mock_base_url,
            ),
        )
    elif config.app.addressing_adapter == AddressingAdapterType.zal:
        binder.bind_to_constructor(
            AddressingAdapter,
            lambda: AddressingZalAdapter(),
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


def __bind_key_repository(binder: Binder, config: Config) -> None:
    key_store_repository = FilesystemJWKStoreRepository()

    key_store_repository.add_pem_key_from_path(EndpointJWTFactory.JWT_KEY_LABEL, config.jwe.signing_private_key_path)
    key_store_repository.add_pem_key_from_path(EndpointJWEFactory.JWE_KEY_LABEL, config.jwe.encryption_public_key_path)

    binder.bind(KeyStoreRepository, key_store_repository)


def __bind_geo_coordinate_service(binder: Binder) -> None:
    binder.bind_to_constructor(
        GeoCoordinateService,
        lambda: GeoCoordinateService(dutch_grid_transformer=DutchGridTransformerFactory().create_transformer()),
    )


def __bind_benchmark_services(binder: Binder) -> None:
    binder.bind_to_provider(
        BenchmarkQueryLoader,
        lambda: DefaultBenchmarkQueryLoader(
            file_loader=inject.instance(FileLoader),
            config=inject.instance(Config),
        ),
    )
    binder.bind_to_provider(
        BenchmarkOutputWriter,
        lambda: JsonFileOutputWriter(),
    )


def __bind_zorgab_scraper_config(binder: Binder, config: Config) -> None:
    binder.bind_to_constructor(
        ZorgABScraperConfig,
        lambda: config.zorgab_scraper,
    )


def __bind_identifier_provider(binder: Binder) -> None:
    binder.bind_to_constructor(
        IdentifierProvider,
        lambda: IdentifierProvider(
            repositories={
                IdentifierSource.zakl_xml: ZaklXmlIdentifierRepository(),  # pylint: disable=no-value-for-parameter
                IdentifierSource.agb_csv: AgbCsvIdentifierRepository(),  # pylint: disable=no-value-for-parameter
            }
        ),  # pylint: disable=no-value-for-parameter
    )


def __bind_search_index_repositories(binder: Binder, config: Config) -> None:
    binder.bind_to_constructor(
        SearchIndexRepository,
        lambda: SearchIndexFileRepository(
            output_path=SEARCH_INDEX_OUTPUT_DIR / SEARCH_INDEX_OUTPUT_FILENAME,
            temp_path=SEARCH_INDEX_TEMP_DIR,
        ),
    )

    binder.bind_to_constructor(
        EncryptedEndpointsRepository,
        lambda: EncryptedEndpointsFileRepository(
            output_path=SEARCH_INDEX_OUTPUT_DIR / ENCRYPTED_ENDPOINTS_OUTPUT_FILENAME,
            temp_path=SEARCH_INDEX_TEMP_DIR,
        ),
    )


def __bind_endpoint_repository(binder: Binder, config: Config) -> None:
    def provide_endpoint_repository() -> EndpointRepository:
        repository: EndpointRepository = DbEndpointRepository()

        if config.search_indexation.include_mock_organizations:
            repository = MockEndpointsRepository(
                endpoint_repository=repository,
                dva_mock_url=config.app.mock_base_url,
            )

        return repository

    binder.bind_to_constructor(
        EndpointRepository,
        provide_endpoint_repository,
    )


def __bind_mock_organization_services(binder: Binder, config: Config) -> None:
    binder.bind_to_constructor(
        MockOrganizationsFileRepo,
        lambda: MockOrganizationsFileRepo(
            mock_organizations_path=config.search_indexation.mock_organizations_path,
            mock_addressing_path=config.search_indexation.mock_addressing_path,
        ),
    )

    binder.bind_to_constructor(
        MockOrganizationsMerger,
        lambda: MockOrganizationsMerger(
            should_include_mock_organizations=config.search_indexation.include_mock_organizations,
        ),
    )
