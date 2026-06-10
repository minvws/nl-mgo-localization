import logging
from typing import TypeAlias

import inject

from app.addressing.services import EndpointJWEWrapper
from app.db.repositories import EndpointRepository

logger = logging.getLogger(__name__)


EncryptedEndpoints: TypeAlias = dict[int, str]


class EncryptedEndpointProvider:
    @inject.autoparams("endpoint_repository", "endpoint_jwe_wrapper")
    def __init__(self, endpoint_repository: EndpointRepository, endpoint_jwe_wrapper: EndpointJWEWrapper) -> None:
        self.endpoint_repository = endpoint_repository
        self.endpoint_jwe_wrapper = endpoint_jwe_wrapper

    def get_all(
        self,
    ) -> EncryptedEndpoints:
        logger.info("Starting encrypted endpoint export")
        endpoints = self.endpoint_repository.find_all()
        logger.debug("Found %s endpoints to encrypt", len(endpoints))
        encrypted_endpoints: EncryptedEndpoints = {}

        for endpoint in endpoints:
            try:
                encrypted_endpoint = self.endpoint_jwe_wrapper.wrap(endpoint.url)
                encrypted_endpoints[endpoint.id] = encrypted_endpoint
            except Exception as e:
                raise RuntimeError(f"Failed to encrypt endpoint id={endpoint.id}") from e

        return encrypted_endpoints
