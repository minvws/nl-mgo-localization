from pathlib import Path

import pytest
from jwcrypto import jwk

from app.addressing.repositories import FilesystemJWKStoreRepository, InvalidKeyError


def test_add_key_to_store_creates_and_appends() -> None:
    repository = FilesystemJWKStoreRepository()
    key_one = jwk.JWK.generate(kty="oct", size=256)
    key_two = jwk.JWK.generate(kty="oct", size=256)

    repository.add_key_to_store("store-1", key_one)
    repository.add_key_to_store("store-1", key_two)

    keys = repository.get_key_store("store-1")

    assert keys[0] == key_one
    assert keys[1] == key_two
    assert len(keys) == 2


def test_get_key_store_missing_raises() -> None:
    repository = FilesystemJWKStoreRepository()

    with pytest.raises(KeyError):
        repository.get_key_store("missing")


def test_get_key_store_empty_list_raises() -> None:
    repository = FilesystemJWKStoreRepository()
    repository._key_stores["empty"] = []

    with pytest.raises(KeyError):
        repository.get_key_store("empty")


def test_get_first_key_from_store_returns_first() -> None:
    repository = FilesystemJWKStoreRepository()
    key_one = jwk.JWK.generate(kty="oct", size=256)
    key_two = jwk.JWK.generate(kty="oct", size=256)

    repository.add_key_to_store("store-2", key_one)
    repository.add_key_to_store("store-2", key_two)

    assert repository.get_first_key_from_store("store-2") == key_one


def test_add_pem_key_from_path_success(tmp_path: Path) -> None:
    repository = FilesystemJWKStoreRepository()
    key = jwk.JWK.generate(kty="RSA", size=2048)
    pem_bytes = key.export_to_pem(private_key=True, password=None)
    pem_path = tmp_path / "key.pem"
    pem_path.write_bytes(pem_bytes)

    repository.add_pem_key_from_path("store-3", pem_path)

    keys = repository.get_key_store("store-3")

    assert len(keys) == 1


def test_add_pem_key_from_path_invalid_raises(tmp_path: Path) -> None:
    repository = FilesystemJWKStoreRepository()
    invalid_path = tmp_path / "invalid.pem"
    invalid_path.write_bytes(b"not-a-pem")

    with pytest.raises(InvalidKeyError):
        repository.add_pem_key_from_path("store-4", invalid_path)
