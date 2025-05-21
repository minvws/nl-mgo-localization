from pathlib import Path

import inject

from app.addressing.models import IdentificationType, ZalSearchResponseEntry
from app.addressing.signing_service import SigningService


class AddressingMockAdapter:
    @inject.autoparams()
    def __init__(self, sign_endpoints: bool, signing_service: SigningService) -> None:
        self.__should_sign_endpoints = sign_endpoints
        self.__signing_service = signing_service

    def search_by_medmij_name(self, name: str) -> ZalSearchResponseEntry | None:
        return self.__search(name, IdentificationType.medmij)

    def search_by_ura(self, ura: str) -> ZalSearchResponseEntry | None:
        return self.__search(ura, IdentificationType.ura)

    def search_by_agb(self, agb: str) -> ZalSearchResponseEntry | None:
        return self.__search(agb, IdentificationType.agbz)

    def search_by_hrn(self, hrn: str) -> ZalSearchResponseEntry | None:
        return self.__search(hrn, IdentificationType.hrn)

    def search_by_kvk(self, kvk: str) -> ZalSearchResponseEntry | None:
        return self.__search(kvk, IdentificationType.kvk)

    def __search(self, value: str, id_type: IdentificationType) -> ZalSearchResponseEntry:
        json = self.__read_json("response.json")

        entry = ZalSearchResponseEntry.model_validate_json(json)
        entry.id_value = value
        entry.id_type = id_type

        return self.__sign_endpoints(entry) if self.__should_sign_endpoints else entry

    def __read_json(self, filename: str) -> str:
        path = Path(__file__).parent / filename

        with open(path) as json_file:
            return json_file.read()

    def __sign_endpoints(self, entry: ZalSearchResponseEntry) -> ZalSearchResponseEntry:
        for data_services in entry.dataservices:
            data_services.auth_endpoint = self.__signing_service.sign_endpoint(data_services.auth_endpoint)
            data_services.token_endpoint = self.__signing_service.sign_endpoint(data_services.token_endpoint)

            for role in data_services.roles:
                role.resource_endpoint = self.__signing_service.sign_endpoint(role.resource_endpoint)

        return entry
