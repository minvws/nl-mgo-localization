from abc import ABC, abstractmethod
from pathlib import Path

from jwcrypto import jwk


class InvalidKeyError(Exception):
    pass


class KeyStoreRepository(ABC):  # pragma: no cover
    @abstractmethod
    def add_key_to_store(self, key_store_id: str, key: jwk.JWK) -> None: ...

    @abstractmethod
    def get_key_store(self, key_store_id: str) -> list[jwk.JWK]: ...

    """
    :raises KeyError: If key store does not exist or is empty.
    """

    def get_first_key_from_store(self, key_store_id: str) -> jwk.JWK:
        """
        :raises KeyError: If key store does not exist or is empty.
        """

        keys = self.get_key_store(key_store_id)
        return keys[0]


class FilesystemJWKStoreRepository(KeyStoreRepository):
    def __init__(self) -> None:
        self._key_stores: dict[str, list[jwk.JWK]] = {}

    def add_key_to_store(self, key_store_id: str, key: jwk.JWK) -> None:
        if self._key_stores.get(key_store_id) is None:
            self._key_stores[key_store_id] = [key]
        else:
            self._key_stores[key_store_id].append(key)

    def get_key_store(self, key_store_id: str) -> list[jwk.JWK]:
        if key_store_id not in self._key_stores:
            raise KeyError(f"No key store found with ID: {key_store_id}")

        if len(self._key_stores[key_store_id]) == 0:
            raise KeyError(f"No keys found in key store {key_store_id}")

        return self._key_stores[key_store_id]

    def add_pem_key_from_path(self, key_store_id: str, key_path: Path) -> None:
        with open(key_path, "rb") as key_file:
            key_data = key_file.read()

        try:
            key = jwk.JWK.from_pem(key_data)
        except Exception as exc:  # noqa: BLE001
            raise InvalidKeyError("Could not parse PEM formatted key as JWK ") from exc

        self.add_key_to_store(key_store_id, key)
