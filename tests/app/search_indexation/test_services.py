import pytest
from pytest_mock import MockerFixture

from app.addressing.services import EndpointJWEWrapper
from app.db.models import Endpoint
from app.search_indexation.services import EncryptedEndpointProvider


class TestEncryptedEndpointProvider:
    def test_get_all_encrypts_all_endpoints(self, mocker: MockerFixture) -> None:
        endpoint_repository = mocker.Mock()
        endpoint_repository.find_all.return_value = [
            Endpoint(id=1, url="https://example.com/auth"),
            Endpoint(id=2, url="https://example.com/token"),
        ]
        endpoint_jwe_wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        endpoint_jwe_wrapper.wrap.side_effect = lambda url: f"encrypted:{url}"

        provider = EncryptedEndpointProvider(
            endpoint_repository=endpoint_repository,
            endpoint_jwe_wrapper=endpoint_jwe_wrapper,
        )
        result = provider.get_all()

        assert result == {
            1: "encrypted:https://example.com/auth",
            2: "encrypted:https://example.com/token",
        }

    def test_get_all_raises_when_encryption_fails(self, mocker: MockerFixture) -> None:
        endpoint_repository = mocker.Mock()
        endpoint_repository.find_all.return_value = [
            Endpoint(id=42, url="https://fail.example.com"),
        ]
        endpoint_jwe_wrapper = mocker.Mock(spec=EndpointJWEWrapper)
        endpoint_jwe_wrapper.wrap.side_effect = Exception("encryption failure")

        provider = EncryptedEndpointProvider(
            endpoint_repository=endpoint_repository,
            endpoint_jwe_wrapper=endpoint_jwe_wrapper,
        )

        with pytest.raises(RuntimeError, match="Failed to encrypt endpoint id=42"):
            provider.get_all()
