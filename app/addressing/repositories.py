from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


class InvalidPrivateKeyError(Exception):
    pass


class KeyRepository:
    def __init__(self, private_key_path: str) -> None:
        self.__private_key_path = private_key_path

    def load_private_key(self) -> ec.EllipticCurvePrivateKey:
        try:
            with open(self.__private_key_path, "rb") as key_file:
                key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                    backend=None,
                )
        except ValueError as e:
            raise InvalidPrivateKeyError("The loaded key is not an EllipticCurvePrivateKey") from e

        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise InvalidPrivateKeyError("The loaded key is not an EllipticCurvePrivateKey")

        return key
