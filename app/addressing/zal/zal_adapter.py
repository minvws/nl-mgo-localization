import json

import inject

from app.addressing.models import (
    IdentificationType,
    ZalDataServiceResponse,
    ZalDataServiceRoleResponse,
    ZalSearchResponseEntry,
)
from app.addressing.schemas import SignedUrl
from app.db.db import Database
from app.db.models import DataService, Endpoint, Organisation
from app.db.repositories import DataServiceRepository, OrganisationRepository
from app.zal_importer.enums import IdentifyingFeatureType


class AddressingZalAdapter:
    @inject.autoparams("db")
    def __init__(self, db: Database, sign_endpoints: bool) -> None:
        self.__db = db
        self.__should_sign_endpoints = sign_endpoints

        session = self.__db.get_db_session()
        self.organisation_repository: OrganisationRepository = session.get_repository(Organisation)
        self.data_service_repository: DataServiceRepository = session.get_repository(DataService)

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
                interface_versions=json.loads(data_service.interface_versions)
                if data_service.interface_versions
                else [],
                auth_endpoint=self.__get_endpoint_url(data_service.auth_endpoint),
                token_endpoint=self.__get_endpoint_url(data_service.token_endpoint),
                roles=[
                    ZalDataServiceRoleResponse(
                        code=system_role.code,
                        resource_endpoint=self.__get_endpoint_url(system_role.resource_endpoint),
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

    def __get_endpoint_url(self, endpoint: Endpoint) -> str:
        if not self.__should_sign_endpoints or endpoint.signature is None:
            return endpoint.url

        return str(SignedUrl.create(url=endpoint.url, signature=endpoint.signature))
