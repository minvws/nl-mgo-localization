import inject

from app.addressing.constants import ENDPOINT_JWE_EXPIRATION_SECONDS
from app.addressing.repositories import KeyStoreRepository

from .factories import EndpointJWEFactory, EndpointJWTFactory


class EndpointJWEWrapper:
    @inject.autoparams("jwt_factory", "jwe_factory", "key_repository")
    def __init__(
        self,
        jwt_factory: EndpointJWTFactory,
        jwe_factory: EndpointJWEFactory,
        key_repository: KeyStoreRepository,
    ) -> None:
        self.__jwt_factory = jwt_factory
        self.__jwe_factory = jwe_factory
        self.__key_repository = key_repository

    def wrap(self, endpoint: str) -> str:
        jwt_key = self.__key_repository.get_first_key_from_store(EndpointJWTFactory.JWT_KEY_LABEL)
        jwe_key = self.__key_repository.get_first_key_from_store(EndpointJWEFactory.JWE_KEY_LABEL)

        jwt = self.__jwt_factory.build(
            endpoint=endpoint, signing_key=jwt_key, expiration_seconds=ENDPOINT_JWE_EXPIRATION_SECONDS
        )

        jwt_string = jwt.serialize()
        jwe = self.__jwe_factory.encrypt(payload=jwt_string, encryption_key=jwe_key)
        jwe_string: str = jwe.serialize(compact=True)

        return jwe_string
