from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.addressing.repositories import InvalidPrivateKeyError, KeyRepository


class TestKeyRepository:
    @pytest.fixture
    def private_key_pem(self, tmp_path: Path) -> Path:
        private_key = ec.generate_private_key(ec.SECP256R1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path = tmp_path / "private_key.pem"
        with open(key_path, "wb") as key_file:
            key_file.write(pem)
        return key_path

    def test_load_private_key_success(self, private_key_pem: str) -> None:
        repo = KeyRepository(str(private_key_pem))
        key = repo.load_private_key()
        assert isinstance(key, ec.EllipticCurvePrivateKey)

    def test_load_private_key_invalid_format(self, tmp_path: Path) -> None:
        invalid_key_path = tmp_path / "invalid_key.pem"
        with open(invalid_key_path, "wb") as key_file:
            key_file.write(b"invalid key data")

        repo = KeyRepository(str(invalid_key_path))
        with pytest.raises(InvalidPrivateKeyError, match="The loaded key is not an EllipticCurvePrivateKey"):
            repo.load_private_key()

    def test_load_private_key_is_not_ec_key(self, tmp_path: Path) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path = tmp_path / "private_key.pem"
        with open(key_path, "wb") as key_file:
            key_file.write(pem)

        repo = KeyRepository(str(key_path))
        with pytest.raises(InvalidPrivateKeyError, match="The loaded key is not an EllipticCurvePrivateKey"):
            repo.load_private_key()
