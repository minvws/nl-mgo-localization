from typing import Any

import inject

from app.addressing.models import ZalDataServiceResponse, ZalDataServiceRoleResponse
from app.addressing.signing_service import SigningService
from app.config.models import Config
from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.models import (
    Address,
    CType,
    GeoLocation,
    Identification,
    Organization,
    SearchRequest,
    SearchResponse,
)


class DemoHealthCareFinderAdapter(HealthcareFinderAdapter):
    @inject.autoparams("signing_service", "config")
    def __init__(self, signing_service: SigningService, config: Config):
        self.__signing_service = signing_service
        self.__config = config

    def __build_mock_url(self, endpoint: str) -> str:
        mock_base_url = self.__config.app.mock_base_url
        url = self.__signing_service.sign_endpoint(f"{mock_base_url}{endpoint}")

        return url

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        organizations: list[Organization] = []

        organizations.append(
            self.create_organization(self.get_ziekenhuis_de_ziekenboeg_data()),
        )
        organizations.append(
            self.create_organization(self.get_huisartsenpraktijk_de_huisarts_data()),
        )
        organizations.append(
            self.create_organization(self.get_rivm_data()),
        )
        organizations.append(
            self.create_organization(self.get_organization_without_dataservices_data()),
        )
        organizations.append(
            self.create_organization(self.get_apothecary_data()),
        )

        return SearchResponse(organizations=organizations)

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
                type=address_data.get("type", ""),
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
            data_service = ZalDataServiceResponse(
                id=data_service_data.get("id", "0"),
                name=data_service_data.get("name", ""),
                interface_versions=data_service_data.get("interface_versions", []),
                auth_endpoint=data_service_data.get("auth_endpoint", ""),
                token_endpoint=data_service_data.get("token_endpoint", ""),
                roles=self.__create_roles(roles_data=data_service_data.get("roles", [])),
            )
            data_services.append(data_service)
        return data_services

    def __create_roles(self, roles_data: list[dict[str, Any]]) -> list[ZalDataServiceRoleResponse]:
        roles = []
        for role_data in roles_data:
            role = ZalDataServiceRoleResponse(
                code=role_data.get("code", ""),
                resource_endpoint=role_data.get("resource_endpoint", ""),
            )
            roles.append(role)
        return roles

    def get_ziekenhuis_de_ziekenboeg_data(self) -> dict[str, Any]:
        return {
            "display_name": "Ziekenhuis Nieuw Juinen",
            "identification_type": "demo",
            "identification_value": "9999999",
            "addresses": [
                {
                    "active": True,
                    "address": "Ziekenhuisstraat 123A\n1000AB Amsterdam",
                    "city": "Amsterdam",
                    "country": "Nederland",
                    "geolocation": {"latitude": 12345.678, "longitude": 98765.432},
                    "postalcode": "1000AB",
                    "state": None,
                    "type": "physical",
                },
            ],
            "names": [
                {"full_name": "Ziekenhuis Nieuw Juinen", "preferred": True},
            ],
            "types": [
                {
                    "code": "hospital",
                    "display_name": "Ziekenhuis",
                    "type": "organization",
                }
            ],
            "data_services": [
                {
                    "id": "48",
                    "name": "Basisgegevens Zorg",
                    "interface_versions": ["2"],
                    "auth_endpoint": self.__build_mock_url("authorize"),
                    "token_endpoint": self.__build_mock_url("token"),
                    "roles": [
                        {
                            "code": "MM-3.0-BZB-FHIR",
                            "resource_endpoint": self.__build_mock_url("48"),
                        }
                    ],
                },
                {
                    "id": "51",
                    "name": "Documenten",
                    "interface_versions": ["2"],
                    "auth_endpoint": self.__build_mock_url("authorize"),
                    "token_endpoint": self.__build_mock_url("token"),
                    "roles": [
                        {
                            "code": "MM-3.0-PLB-FHIR",
                            "resource_endpoint": self.__build_mock_url("51"),
                        },
                        {
                            "code": "MM-3.0-PDB-FHIR",
                            "resource_endpoint": self.__build_mock_url("51"),
                        },
                    ],
                },
            ],
        }

    def get_huisartsenpraktijk_de_huisarts_data(self) -> dict[str, Any]:
        return {
            "display_name": "Huisartspraktijk Heideroosje",
            "identification_type": "demo",
            "identification_value": "1111111",
            "addresses": [
                {
                    "active": True,
                    "address": "Huisartsstraat 123A\n1000AB Rotterdam",
                    "city": "Rotterdam",
                    "country": "Nederland",
                    "geolocation": {"latitude": 12345.678, "longitude": 98765.432},
                    "postalcode": "1000AB",
                    "state": None,
                    "type": "physical",
                },
            ],
            "names": [
                {"full_name": "Huisartspraktijk Heideroosje", "preferred": True},
            ],
            "types": [
                {
                    "code": "hospital",
                    "display_name": "Ziekenhuis",
                    "type": "organization",
                }
            ],
            "data_services": [
                {
                    "id": "49",
                    "name": "Huisartsgegevens",
                    "interface_versions": ["2"],
                    "auth_endpoint": self.__build_mock_url("authorize"),
                    "token_endpoint": self.__build_mock_url("token"),
                    "roles": [
                        {
                            "code": "MM-3.0-HGB-FHIR",
                            "resource_endpoint": self.__build_mock_url("49"),
                        }
                    ],
                },
                {
                    "id": "51",
                    "name": "Documenten",
                    "interface_versions": ["2"],
                    "auth_endpoint": self.__build_mock_url("authorize"),
                    "token_endpoint": self.__build_mock_url("token"),
                    "roles": [
                        {
                            "code": "MM-3.0-PLB-FHIR",
                            "resource_endpoint": self.__build_mock_url("51"),
                        },
                        {
                            "code": "MM-3.0-PDB-FHIR",
                            "resource_endpoint": self.__build_mock_url("51"),
                        },
                    ],
                },
            ],
        }

    def get_rivm_data(self) -> dict[str, Any]:
        return {
            "display_name": "RIVM",
            "identification_type": "demo",
            "identification_value": "222222",
            "addresses": [
                {
                    "active": True,
                    "address": "Postbus 654, 2700AR Zoetermeer",
                    "city": "Zoetermeer",
                    "country": "Nederland",
                    "geolocation": {"latitude": 12345.678, "longitude": 98765.432},
                    "postalcode": "1000AB",
                    "state": None,
                    "type": "physical",
                },
            ],
            "names": [
                {"full_name": "RIVM", "preferred": True},
            ],
            "types": [
                {
                    "code": "hospital",
                    "display_name": "Ziekenhuis",
                    "type": "organization",
                }
            ],
            "data_services": [
                {
                    "id": "63",
                    "name": "Vaccinatiegegevens",
                    "interface_versions": ["2"],
                    "auth_endpoint": self.__build_mock_url("authorize"),
                    "token_endpoint": self.__build_mock_url("token"),
                    "roles": [
                        {
                            "code": "MM-1.0-VAR-FHIR",
                            "resource_endpoint": self.__build_mock_url("63"),
                        }
                    ],
                },
            ],
        }

    def get_organization_without_dataservices_data(self) -> dict[str, Any]:
        return {
            "display_name": "Fysiotherapiepraktijk De Toekomst",
            "identification_type": "",
            "identification_value": "",
            "addresses": [
                {
                    "active": True,
                    "address": "Utrechtseweg 10\r\n1020BD Amsterdam",
                    "city": "Amsterdam",
                    "country": "Nederland",
                    "geolocation": {"latitude": 12345.678, "longitude": 98765.432},
                    "postalcode": "1020AB",
                    "state": None,
                    "type": "physical",
                }
            ],
            "names": [{"full_name": "Fysiotherapiepraktijk De Toekomst", "preferred": True}],
            "types": [
                {
                    "code": "0400",
                    "display_name": "Fysiotherapeuten, niet nader gespecificeerd",
                    "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
                }
            ],
            "data_services": [],
        }

    def get_apothecary_data(self) -> dict[str, Any]:
        return {
            "display_name": "Apotheek Aanstalten",
            "identification_type": "",
            "identification_value": "",
            "addresses": [
                {
                    "active": True,
                    "address": "Apothekersweg 5\r\n1020BD Amsterdam",
                    "city": "Amsterdam",
                    "country": "Nederland",
                    "geolocation": {"latitude": 12345.678, "longitude": 98765.432},
                    "postalcode": "1020AB",
                    "state": None,
                    "type": "physical",
                }
            ],
            "names": [{"full_name": "Apotheek Aanstalten", "preferred": True}],
            "types": [
                {
                    "code": "0200",
                    "display_name": "Apothekers",
                    "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
                }
            ],
            "data_services": [],
        }
