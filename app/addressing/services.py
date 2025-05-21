from logging import Logger

import inject

from app.db.db import Database
from app.db.models import Endpoint
from app.db.repositories import EndpointRepository

from .schemas import EndpointSignatureRenewResultDTO
from .signing_service import SigningService


class EndpointSignatureRenewer:
    @inject.autoparams()
    def __init__(self, db: Database, signing_service: SigningService, logger: Logger):
        self.__db_session = db.get_db_session()
        self.__endpoint_repository: EndpointRepository = self.__db_session.get_repository(Endpoint)
        self.__signing_service = signing_service
        self.__logger = logger

    def renew(self) -> EndpointSignatureRenewResultDTO:
        result = EndpointSignatureRenewResultDTO()

        for endpoint in self.__endpoint_repository.find_all():
            existing_signature = endpoint.signature is not None

            try:
                endpoint.signature = self.__signing_service.generate_signature(endpoint.url)
            except Exception:
                self.__logger.exception(
                    "Failed to generate signature for endpoint (id: %d, url: %s)", endpoint.id, endpoint.url
                )
                result.increment_skipped()

                continue

            if existing_signature:
                result.increment_updated()
            else:
                result.increment_added()

        self.__db_session.commit()

        return result
