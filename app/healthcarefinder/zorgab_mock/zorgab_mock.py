from logging import Logger
from pathlib import Path

import inject

from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.models import (
    Address,
    CType,
    Organization,
    SearchRequest,
    SearchResponse,
)
from app.healthcarefinder.zorgab.models import OrganizationModel, OrganizationsModel


class ZorgABMockHydrationAdapter(HealthcareFinderAdapter):
    @inject.autoparams()
    def __init__(self, logger: Logger):
        self.__logger = logger

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        self.__logger.info("Searching Hydrated ZorgAB mock with %s" % search.model_dump_json())

        json: str = self._get_json_mock_response()
        decoded_organizations: OrganizationsModel = OrganizationsModel.model_validate_json(json)

        if not decoded_organizations.root:
            return None

        organizations: list[Organization] = []

        for decoded_organization in decoded_organizations.root:
            organizations.append(
                Organization(
                    medmij_id=None,
                    display_name=decoded_organization.displayName,
                    addresses=self.__get_address(decoded_organization=decoded_organization),
                    identification="ura:1234567890",
                    types=self.__get_types(decoded_organization=decoded_organization),
                )
            )

        return SearchResponse(organizations=organizations)

    def __get_address(self, decoded_organization: OrganizationModel) -> list[Address]:
        # We have to "convert" from ZorgAB address to search response address. Even though
        # they are the same, we don't want to expose the ZorgAB address to the outside world.
        if decoded_organization.addresses:
            address = Address.model_validate_json(decoded_organization.addresses[0].model_dump_json())
            return [address]
        return []

    def __get_types(self, decoded_organization: OrganizationModel) -> list[CType]:
        types = []
        for type in decoded_organization.types:
            types.append(
                CType(
                    code=type.code,
                    display_name=type.displayName,
                    type=type.type,
                )
            )
        return types

    def _get_json_mock_response(self) -> str:
        return self._get_json_from_file("zorgab_response_001.json")

    def _get_json_from_file(self, filename: str) -> str:
        path = Path(__file__).parent / filename
        with open(path) as json_file:
            json = json_file.read()
        return json
