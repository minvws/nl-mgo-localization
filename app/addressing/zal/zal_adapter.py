import json

import inject

from app.addressing.models import (
    IdentificationType,
    ZalDataServiceResponse,
    ZalDataServiceRoleResponse,
    ZalSearchResponseEntry,
)
from app.addressing.services import EndpointJWEWrapper
from app.db.models import Organisation
from app.db.repositories import DataServiceRepository, OrganisationRepository
from app.zal_importer.enums import IdentifyingFeatureType


class AddressingZalAdapter:
    @inject.autoparams()
    def __init__(
        self,
        organisation_repository: OrganisationRepository,
        data_service_repository: DataServiceRepository,
        endpoint_jwe_wrapper: EndpointJWEWrapper,
    ) -> None:
        self.organisation_repository = organisation_repository
        self.data_service_repository = data_service_repository
        self.__endpoint_jwe_wrapper = endpoint_jwe_wrapper

    def search_by_medmij_name(self, name: str) -> ZalSearchResponseEntry | None:
        entry = self.organisation_repository.find_one_by_name(name)
        return self._convert_to_response(IdentificationType.medmij, name, entry)

    def search_by_ura(self, ura: str) -> ZalSearchResponseEntry | None:
        entry = self.organisation_repository.find_one_by_identifying_feature(IdentifyingFeatureType.URA, ura)
        return self._convert_to_response(IdentificationType.ura, ura, entry)

    def search_by_agb(self, agb: str) -> ZalSearchResponseEntry | None:
        entry = self.organisation_repository.find_one_by_identifying_feature(IdentifyingFeatureType.AGB, agb)
        return self._convert_to_response(IdentificationType.agbz, agb, entry)

    def search_by_hrn(self, hrn: str) -> ZalSearchResponseEntry | None:
        entry = self.organisation_repository.find_one_by_identifying_feature(IdentifyingFeatureType.HRN, hrn)
        return self._convert_to_response(IdentificationType.hrn, hrn, entry)

    def search_by_kvk(self, kvk: str) -> ZalSearchResponseEntry | None:
        entry = self.organisation_repository.find_one_by_identifying_feature(IdentifyingFeatureType.KVK, kvk)
        return self._convert_to_response(IdentificationType.kvk, kvk, entry)

    def _convert_to_response(
        self,
        id_type: IdentificationType,
        id_value: str,
        organisation: Organisation | None,
    ) -> ZalSearchResponseEntry | None:
        if organisation is None:
            return None

        dataservices = [
            ZalDataServiceResponse(
                id=data_service.external_id,
                name=data_service.name,
                interface_versions=(
                    json.loads(data_service.interface_versions) if data_service.interface_versions else []
                ),
                auth_endpoint=self.__endpoint_jwe_wrapper.wrap(data_service.auth_endpoint.url),
                token_endpoint=self.__endpoint_jwe_wrapper.wrap(data_service.token_endpoint.url),
                roles=[
                    ZalDataServiceRoleResponse(
                        code=system_role.code,
                        resource_endpoint=self.__endpoint_jwe_wrapper.wrap(system_role.resource_endpoint.url),
                    )
                    for system_role in data_service.roles
                ],
            )
            for data_service in self.data_service_repository.find_all_by_organisation(organisation.id)
        ]

        return ZalSearchResponseEntry(
            medmij_id=organisation.name,
            organization_type=organisation.type,
            id_type=id_type,
            id_value=id_value,
            dataservices=dataservices,
        )
