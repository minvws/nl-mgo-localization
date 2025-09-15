from logging import Logger
from typing import Any, List

import inject

from app.addressing.models import ZalDataServiceResponse, ZalDataServiceRoleResponse
from app.addressing.signing_service import SigningService
from app.config.models import Config
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.mock.fixtures import (
    INTEROPLAB_DATASERVICES,
    HealthOrganizationFixtures,
    QualificationDataServiceFixtures,
)
from app.healthcarefinder.models import (
    Address,
    CType,
    GeoLocation,
    Identification,
    Organization,
    SearchRequest,
    SearchResponse,
)


class MockHealthcareFinderAdapter(HealthcareFinderAdapter):
    @inject.autoparams()
    def __init__(self, signing_service: SigningService, logger: Logger, config: Config):
        self.__signing_service = signing_service
        self.__logger = logger
        self.__config = config

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        """
        This method is used to form a collection of organizations. The organizations are created using the
        fixtures provided in the HealthOrganizationFixtures class. It also creates qualification organizations,
        which are made up of only one data service, so the implementation of the data service can be verified.

        """
        self.__logger.info("LOAD search using mock with %s" % search.model_dump_json())
        organizations: list[Organization] = []

        # Add interoplab organization, which has "real" dataservices
        organizations.append(self.__get_interoplab_organization())

        # Add basic organizations
        organizations.append(self.create_organization(HealthOrganizationFixtures.ORGANIZATION_WITH_DATASERVICES))
        organizations.append(self.create_organization(HealthOrganizationFixtures.ORGANIZATION_WITHOUT_DATASERVICES))
        organizations.append(
            self.create_organization(HealthOrganizationFixtures.ORGANIZATION_WITH_UNSUPPORTED_DATASERVICE)
        )

        # Add qualification organizations
        organizations.extend(self.__get_qualification_organizations())

        return SearchResponse(organizations=organizations)

    def __get_interoplab_organization(self) -> Organization:
        dataservices = [
            {
                "id": interoplab_dataservice["id"],
                "name": interoplab_dataservice["name"],
                "interface_versions": ["2"],
                "auth_endpoint": "https://dva-inlog.interoplab.eu/ontwikkel/verplicht/oauth2/authorize",
                "token_endpoint": "https://dva.interoplab.eu/ontwikkel/verplicht/oauth2/token",
                "roles": [
                    {
                        "code": interoplab_dataservice["code"],
                        "resource_endpoint": "https://dva.interoplab.eu/ontwikkel/verplicht/fhir/",
                    }
                ],
            }
            for interoplab_dataservice in INTEROPLAB_DATASERVICES
        ]

        organization = HealthOrganizationFixtures.ORGANIZATION_WITH_INTEROPLAB_DATASERVICE
        organization["data_services"] = dataservices
        return self.create_organization(organization)

    def __get_qualification_organizations(self) -> List[Organization]:
        organizations: list[Organization] = []

        for data_service in QualificationDataServiceFixtures:
            organization = HealthOrganizationFixtures.QUALIFICATION_ORGANIZATION_BASE
            organization["display_name"] = "Kwalificatie Medmij: " + data_service.name
            organization["identification_type"] = "urn:oid:2.16.840.1.113883"
            organization["identification_value"] = ("Kwalificatie Medmij: " + data_service.name).replace(" ", "_")
            organization["addresses"] = [{"address": "Kwalificatiestraat " + data_service.name, "type": "work"}]
            organization["data_services"] = [data_service.value]
            organizations.append(self.create_organization(organization))

        return organizations

    def create_organization(self, data: dict[str, Any]) -> Organization:
        addresses = self.__create_addresses(data.get("addresses", []))
        types = self.__create_types(data.get("types", []))
        data_services = self.__create_data_services(data.get("data_services", []))

        id_type = data.get("identification_type", "")
        id_value = data.get("identification_value", "")

        identification = Identification(identification_type=id_type, identification_value=id_value)

        return Organization(
            medmij_id=None,
            display_name=data.get("display_name", ""),
            identification=str(identification),
            addresses=addresses,
            types=types,
            data_services=data_services,
        )

    def __create_addresses(self, addresses_data: list[dict[str, Any]]) -> list[Address]:
        addresses = []
        for address_data in addresses_data:
            address = Address(
                active=address_data.get("active", False),
                address=address_data.get("address", ""),
                city=address_data.get("city", ""),
                country=address_data.get("country", ""),
                geolocation=self.__create_geolocation(address_data.get("geolocation", {})),
                postalcode=address_data.get("postalcode", ""),
                state=address_data.get("state", ""),
            )
            addresses.append(address)
        return addresses

    def __create_geolocation(self, geolocation_data: dict[str, Any]) -> GeoLocation:
        return GeoLocation(
            latitude=geolocation_data.get("latitude", 0.0), longitude=geolocation_data.get("longitude", 0.0)
        )

    def __create_types(self, types_data: list[dict[str, Any]]) -> list[CType]:
        types = []
        for type_data in types_data:
            ctype = CType(
                code=type_data.get("code", ""),
                display_name=type_data.get("display_name", ""),
                type=type_data.get("type", ""),
            )
            types.append(ctype)
        return types

    def __create_data_services(self, data_services_data: list[dict[str, Any]]) -> list[ZalDataServiceResponse]:
        data_services = []
        for data_service_data in data_services_data:
            auth_endpoint = data_service_data.get("auth_endpoint", "")
            token_endpoint = data_service_data.get("token_endpoint", "")

            if "{{MOCK_URL}}" in auth_endpoint:
                auth_endpoint = auth_endpoint.replace("{{MOCK_URL}}", self.__config.app.mock_base_url)

            if "{{MOCK_URL}}" in token_endpoint:
                token_endpoint = token_endpoint.replace("{{MOCK_URL}}", self.__config.app.mock_base_url)

            if self.__config.signing.sign_endpoints:
                auth_endpoint = self.__signing_service.sign_endpoint(auth_endpoint)
                token_endpoint = self.__signing_service.sign_endpoint(token_endpoint)

            data_service = ZalDataServiceResponse(
                id=data_service_data.get("id", "0"),
                name=data_service_data.get("name", ""),
                interface_versions=data_service_data.get("interface_versions", []),
                auth_endpoint=auth_endpoint,
                token_endpoint=token_endpoint,
                roles=self.__create_roles(roles_data=data_service_data.get("roles", [])),
            )
            data_services.append(data_service)
        return data_services

    def __create_roles(self, roles_data: list[dict[str, Any]]) -> list[ZalDataServiceRoleResponse]:
        roles = []
        for role_data in roles_data:
            resource_endpoint = role_data.get("resource_endpoint", "")
            if "{{MOCK_URL}}" in resource_endpoint:
                resource_endpoint = resource_endpoint.replace("{{MOCK_URL}}", self.__config.app.mock_base_url)

            if self.__config.signing.sign_endpoints:
                resource_endpoint = self.__signing_service.sign_endpoint(resource_endpoint)

            role = ZalDataServiceRoleResponse(
                code=role_data.get("code", ""),
                resource_endpoint=resource_endpoint,
            )
            roles.append(role)
        return roles
