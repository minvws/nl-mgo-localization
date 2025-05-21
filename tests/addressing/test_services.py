from base64 import b64encode
from os import urandom
from typing import TypeAlias

from faker import Faker
from pytest import fixture
from pytest_mock import MockerFixture, MockType

from app.addressing.services import EndpointSignatureRenewer
from app.db.models import Endpoint

MocksType: TypeAlias = tuple[EndpointSignatureRenewer, MockType, MockType, MockType | None]


class TestEndpointSignatureRenewer:
    @fixture
    def mocks(self, mocker: MockerFixture) -> MocksType:
        mock_db = mocker.Mock()
        mock_db_session = mocker.Mock()
        mock_endpoint_repository = mocker.Mock()
        mock_signing_service = mocker.Mock()

        mock_db.get_db_session.return_value = mock_db_session
        mock_db_session.get_repository.return_value = mock_endpoint_repository

        endpoint_signature_renewer = EndpointSignatureRenewer(
            db=mock_db, signing_service=mock_signing_service, logger=mocker.Mock()
        )

        return endpoint_signature_renewer, mock_db_session, mock_endpoint_repository, mock_signing_service

    def __create_fake_signature(self) -> str:
        return b64encode(urandom(32)).decode("utf-8")

    def test_renew_adds_and_updates_signatures(self, mocker: MockerFixture, faker: Faker, mocks: MocksType) -> None:
        endpoint_signer, mock_db_session, mock_endpoint_repository, mock_signing_service = mocks
        assert mock_signing_service is not None

        mock_endpoint_repository.find_all.return_value = [
            endpoint1 := Endpoint(id=123, signature=None, url=faker.url()),
            endpoint2 := Endpoint(id=456, signature=self.__create_fake_signature(), url=faker.url()),
        ]
        mock_signing_service.generate_signature.side_effect = [
            signature1 := self.__create_fake_signature(),
            signature2 := self.__create_fake_signature(),
        ]

        result = endpoint_signer.renew()

        assert result.added == 1
        assert result.updated == 1
        assert result.skipped == 0
        assert endpoint1.signature == signature1
        assert endpoint2.signature == signature2

        mock_db_session.commit.assert_called_once()

    def test_renew_skips_endpoint_if_signature_generation_fails(self, faker: Faker, mocks: MocksType) -> None:
        endpoint_signer, mock_db_session, mock_endpoint_repository, mock_signing_service = mocks
        assert mock_signing_service is not None

        mock_endpoint_repository.find_all.return_value = [
            Endpoint(id=123, signature=None, url=faker.url()),
            Endpoint(id=456, signature=None, url=faker.url()),
        ]
        mock_signing_service.generate_signature.side_effect = [
            Exception("Signature generation failed"),
            self.__create_fake_signature(),
        ]

        result = endpoint_signer.renew()

        assert result.added == 1
        assert result.updated == 0
        assert result.skipped == 1

        mock_db_session.commit.assert_called_once()
