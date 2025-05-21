import base64
from typing import Optional

import inject
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from app.addressing.constants import SIGNATURE_PARAM_NAME
from app.addressing.repositories import KeyRepository

"""
This service signs endpoints to ensure their authenticity.
The public key is shared with the DVP Proxy, allowing it to verify that each endpoint was signed by this app.
"""


class PrivateKeyNotLoadedError(Exception):
    pass


class SigningService:
    @inject.autoparams()
    def __init__(self, key_repository: KeyRepository) -> None:
        self.__key_repository = key_repository
        self.__private_key: Optional[ec.EllipticCurvePrivateKey] = None

    def ensure_private_key_loaded(self) -> None:
        if self.__private_key is None:
            self.__private_key = self.__key_repository.load_private_key()

    def sign_endpoint(self, endpoint: str) -> str:
        self.ensure_private_key_loaded()

        encoded_signature = self.generate_signature(endpoint)

        delimiter = "&" if "?" in endpoint else "?"
        return f"{endpoint}{delimiter}{SIGNATURE_PARAM_NAME}={encoded_signature}"

    def generate_signature(self, endpoint: str) -> str:
        self.ensure_private_key_loaded()

        if not isinstance(self.__private_key, ec.EllipticCurvePrivateKey):
            raise TypeError("Private key is not of type EllipticCurvePrivateKey")

        signature = self.__private_key.sign(
            endpoint.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )

        return base64.urlsafe_b64encode(signature).decode("utf-8")
