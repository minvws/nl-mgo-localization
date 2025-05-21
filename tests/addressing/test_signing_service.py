import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pytest_mock import MockerFixture

from app.addressing.constants import SIGNATURE_PARAM_NAME
from app.addressing.repositories import InvalidPrivateKeyError, KeyRepository
from app.addressing.signing_service import (
    PrivateKeyNotLoadedError,
    SigningService,
)


@pytest.fixture
def private_key_pem() -> bytes:
    """Generate a valid EC private key in PEM format."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture
def private_key_path() -> str:
    """Provide a mock path for the private key file."""
    return "path/to/private_key.pem"


@pytest.fixture
def key_repository(mocker: MockerFixture, private_key_pem: bytes) -> KeyRepository:
    """Mock the KeyRepository to return the generated private key."""
    mock_repo = mocker.Mock(spec=KeyRepository)
    mock_repo.load_private_key.return_value = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
        backend=None,
    )
    return mock_repo  # type: ignore


def test_load_private_key_invalid_type(
    mocker: MockerFixture,
) -> None:
    """
    Ensure InvalidPrivateKeyError is raised for non-EC keys.
    Verifies that only EllipticCurvePrivateKey types are accepted.
    """
    mock_repo = mocker.Mock(spec=KeyRepository)
    mock_repo.load_private_key.side_effect = InvalidPrivateKeyError("The loaded key is not an EllipticCurvePrivateKey")

    service = SigningService(mock_repo)
    with pytest.raises(
        InvalidPrivateKeyError,
        match="The loaded key is not an EllipticCurvePrivateKey",
    ):
        service.ensure_private_key_loaded()


def test_sign_endpoint(
    key_repository: KeyRepository,
) -> None:
    """
    Ensure an endpoint is correctly signed.
    Verifies that the signature is appended to the URL.
    """
    service = SigningService(key_repository)
    signed_endpoint = service.sign_endpoint("https://example.com/api/resource")
    assert f"{SIGNATURE_PARAM_NAME}=" in signed_endpoint


def test_generate_signature_invalid_private_key(
    key_repository: KeyRepository,
) -> None:
    """
    Ensure TypeError is raised with an invalid private key type.
    Verifies that the service handles invalid key types properly.
    """
    key_repository.load_private_key.return_value = "invalid key"  # type: ignore
    service = SigningService(key_repository)
    service.ensure_private_key_loaded()

    with pytest.raises(TypeError):
        service.generate_signature("https://example.com/api/resource")


def test_sign_endpoint_with_query(
    key_repository: KeyRepository,
) -> None:
    """
    Ensure an endpoint with existing query parameters is correctly signed.
    Verifies that the signature is appended as an additional parameter.
    """
    service = SigningService(key_repository)
    signed_endpoint = service.sign_endpoint("https://example.com/api/resource?param=value")
    assert f"&{SIGNATURE_PARAM_NAME}=" in signed_endpoint


def test_sign_endpoint_no_private_key(
    mocker: MockerFixture,
) -> None:
    """
    Ensure PrivateKeyNotLoadedError is raised when signing without loading the private key.
    Verifies that the service does not attempt to sign without a loaded key.
    """
    mock_repo = mocker.Mock(spec=KeyRepository)
    mock_repo.load_private_key.side_effect = PrivateKeyNotLoadedError("Private key not loaded")
    service = SigningService(mock_repo)
    with pytest.raises(PrivateKeyNotLoadedError, match="Private key not loaded"):
        service.sign_endpoint("https://example.com/api/resource")


def test_invalid_key_type(
    mocker: MockerFixture,
) -> None:
    """
    Ensure InvalidPrivateKeyError is raised with an invalid key type in the file.
    Verifies that only valid EllipticCurvePrivateKey types are accepted.
    """
    mock_repo = mocker.Mock(spec=KeyRepository)
    mock_repo.load_private_key.side_effect = InvalidPrivateKeyError("The loaded key is not an EllipticCurvePrivateKey")
    service = SigningService(key_repository=mock_repo)
    with pytest.raises(InvalidPrivateKeyError):
        service.ensure_private_key_loaded()
