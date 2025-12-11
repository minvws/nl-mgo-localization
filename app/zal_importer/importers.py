import json
from abc import ABC, abstractmethod
from datetime import datetime
from logging import Logger
from typing import Any
from xml.etree.ElementTree import Element

import inject
from sqlalchemy.orm import Session

from app.addressing.signing_service import SigningService
from app.cron.utils import print_progress_bar
from app.db.models import Organisation
from app.db.repositories import (
    DataServiceRepository,
    EndpointRepository,
    IdentifyingFeatureRepository,
    OrganisationRepository,
    SystemRoleRepository,
)
from app.xml.exceptions import CouldNotTraverse
from app.xml.services import ElementTraverser
from app.zal_importer.exceptions import CouldNotImportOrganisations

from .enums import IdentifyingFeatureType, OrganisationType


class OrganisationImporter(ABC):
    @abstractmethod
    def process_xml(self, traverser: ElementTraverser) -> None:
        pass  # pragma: no cover

    def _create_import_reference(self, traverser: ElementTraverser) -> str:
        import_datetime = datetime.fromisoformat(traverser.get_nested_text("Tijdstempel"))
        serial_number = traverser.get_nested_text("Volgnummer")

        return f"{int(import_datetime.timestamp())}{serial_number.zfill(6)}"


class OrganisationListImporter(OrganisationImporter):
    @inject.autoparams()
    def __init__(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        system_role_repository: SystemRoleRepository,
        endpoint_repository: EndpointRepository,
        session: Session,
        logger: Logger,
        signing_service: SigningService | None = None,
    ) -> None:
        self.__organisation_repository = organisation_repository
        self.__data_service_repository = data_service_repository
        self.__system_role_repository = system_role_repository
        self.__endpoint_repository = endpoint_repository
        self.__session = session
        self.__logger = logger
        self.__signing_service = signing_service

    def process_xml(self, traverser: ElementTraverser) -> None:
        import_reference = self._create_import_reference(traverser)

        if self.__organisation_repository.has_one_by_import_ref(import_reference):
            raise CouldNotImportOrganisations.because_import_reference_exists(import_reference)

        self.__logger.info(f"Start import: type = {traverser.get_root_element_name()}, reference = {import_reference}")

        try:
            self.__process_xml(traverser, import_reference)
            self.__session.commit()
            self.__logger.info("Successfully imported data with reference = %s", import_reference)
        except Exception as e:
            self.__session.rollback()
            self.__logger.error("Failed to import data with reference = %s: %s", import_reference, e)
            raise e

    def __process_xml(self, traverser: ElementTraverser, import_reference: str) -> None:
        elements = traverser.get_nested_elements(name="Zorgaanbieders/Zorgaanbieder")
        total_elements = len(elements)
        for progress, organisation_element in enumerate(elements):
            print_progress_bar(progress, total_elements)

            organisation = self.__organisation_repository.create(
                import_ref=import_reference,
                **self.__extract_organisation_data(traverser, organisation_element),
            )

            for data_service_element in traverser.get_nested_elements(
                name="Interfaceversies/Interfaceversie/Gegevensdiensten/Gegevensdienst",
                root=organisation_element,
            ):
                data_service = self.__data_service_repository.create(
                    organisation_id=organisation.id,
                    **self.__extract_data_service_data(traverser, data_service_element),
                )

                for system_role_element in traverser.get_nested_elements(
                    name="Systeemrollen/Systeemrol", root=data_service_element
                ):
                    self.__system_role_repository.create(
                        data_service_id=data_service.id,
                        **self.__extract_system_role_data(traverser, system_role_element),
                    )

    def __extract_organisation_data(self, traverser: ElementTraverser, organisation_element: Element) -> dict[str, Any]:
        return {
            "name": traverser.get_nested_text("Zorgaanbiedernaam", organisation_element),
            "type": OrganisationType(traverser.get_nested_text("Aanbiedertype", organisation_element)),
        }

    def __extract_data_service_data(self, traverser: ElementTraverser, data_service_element: Element) -> dict[str, Any]:
        auth_endpoint_url = traverser.get_nested_text(
            "AuthorizationEndpoint/AuthorizationEndpointuri", data_service_element
        )
        token_endpoint_url = traverser.get_nested_text("TokenEndpoint/TokenEndpointuri", data_service_element)

        return {
            "external_id": traverser.get_nested_text("GegevensdienstId", data_service_element),
            "auth_endpoint_id": self.__find_or_create_endpoint(auth_endpoint_url),
            "token_endpoint_id": self.__find_or_create_endpoint(token_endpoint_url),
        }

    def __extract_system_role_data(self, traverser: ElementTraverser, system_role_element: Element) -> dict[str, Any]:
        resource_endpoint_url = traverser.get_nested_text("ResourceEndpoint/ResourceEndpointuri", system_role_element)

        return {
            "code": traverser.get_nested_text("Systeemrolcode", system_role_element),
            "resource_endpoint_id": self.__find_or_create_endpoint(resource_endpoint_url),
        }

    def __find_or_create_endpoint(self, url: str) -> int:
        signature = self.__signing_service.generate_signature(url) if self.__signing_service is not None else None
        endpoint = self.__endpoint_repository.find_one_by_url(url)

        if endpoint is None:
            return self.__endpoint_repository.create(url=url, signature=signature).id

        endpoint.signature = signature

        return endpoint.id


class OrganisationJoinListImporter(OrganisationImporter):
    @inject.autoparams()
    def __init__(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        identifying_feature_repository: IdentifyingFeatureRepository,
        session: Session,
        logger: Logger,
    ) -> None:
        self.__organisation_repository = organisation_repository
        self.__data_service_repository = data_service_repository
        self.__identifying_feature_repository = identifying_feature_repository
        self.__session = session
        self.__logger = logger

    def process_xml(self, traverser: ElementTraverser) -> None:
        import_reference = self._create_import_reference(traverser)

        if self.__identifying_feature_repository.has_one_by_import_ref(import_reference):
            raise CouldNotImportOrganisations.because_import_reference_exists(import_reference)

        self.__logger.info(f"Start import: type = {traverser.get_root_element_name()}, reference = {import_reference}")

        try:
            self.__process_xml(traverser, import_reference)
            self.__session.commit()
            self.__logger.info("Successfully imported data with reference = %s", import_reference)
        except Exception as e:
            self.__session.rollback()
            self.__logger.error("Failed to import data with reference = %s: %s", import_reference, e)
            raise e

    def __process_xml(self, traverser: ElementTraverser, import_reference: str) -> None:
        elements = traverser.get_nested_elements(name="Zorgaanbieders/Zorgaanbieder")
        total_elements = len(elements)
        for progress, organisation_element in enumerate(elements):
            print_progress_bar(progress, total_elements)
            organisation = self.__get_organisation(traverser, organisation_element)

            if organisation is None:
                continue

            for identifying_feature_element in traverser.get_nested_elements(
                name="IdentificerendeKenmerken/IdentificerendKenmerk",
                root=organisation_element,
            ):
                self.__identifying_feature_repository.create(
                    organisation_id=organisation.id,
                    import_ref=import_reference,
                    **self.__extract_identifying_feature_data(
                        traverser=traverser,
                        identifying_feature_element=identifying_feature_element,
                    ),
                )

            for data_service_element in traverser.get_nested_elements(
                name="Gegevensdiensten/Gegevensdienst",
                root=organisation_element,
            ):
                data_service_external_id, data_service_name = self.__extract_data_service_data(
                    traverser, data_service_element
                )
                data_service = self.__data_service_repository.find_one_by_organisation_and_external_id(
                    organisation_id=organisation.id,
                    external_id=data_service_external_id,
                )

                if data_service is None:
                    self.__logger.warning(
                        "No DataService found for organisation %s with external ID '%s'",
                        organisation.id,
                        data_service_external_id,
                    )
                    continue

                data_service.name = data_service_name
                data_service.interface_versions = json.dumps(
                    self.__extract_interface_versions(traverser=traverser, data_service_element=data_service_element)
                )

    def __get_organisation(self, traverser: ElementTraverser, organisation_element: Element) -> Organisation | None:
        organisation_name = traverser.get_nested_text("Zorgaanbiedernaam", organisation_element)
        organisation = self.__organisation_repository.find_one_by_name(organisation_name)

        if organisation is None:
            self.__logger.warning(f"No Organisation found with name '{organisation_name}'")

        return organisation

    def __extract_data_service_data(
        self, traverser: ElementTraverser, data_service_element: Element
    ) -> tuple[str, str]:
        return (
            traverser.get_nested_text("GegevensdienstId", data_service_element),
            traverser.get_nested_text("Weergavenaam", data_service_element),
        )

    def __extract_identifying_feature_data(
        self, traverser: ElementTraverser, identifying_feature_element: Element
    ) -> dict[str, Any]:
        type_element = traverser.get_child_element(identifying_feature_element)
        tag_name = ElementTraverser.decompose_tag(type_element)[0]

        if not type_element.text:
            raise CouldNotTraverse.because_text_is_empty(type_element.tag)

        return {
            "type": IdentifyingFeatureType(tag_name),
            "value": type_element.text,
        }

    def __extract_interface_versions(self, traverser: ElementTraverser, data_service_element: Element) -> list[str]:
        interface_versions = map(
            lambda e: traverser.get_child_element(e).text,
            traverser.get_nested_elements("Interfaceversies/Interfaceversie", data_service_element),
        )

        return [interface_version for interface_version in interface_versions if interface_version]
