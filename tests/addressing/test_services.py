from base64 import b64encode
from os import urandom

from faker import Faker
from pytest import fixture
from pytest_mock import MockerFixture, MockType

from app.addressing.services import EndpointSignatureRenewer
from app.db.models import Endpoint


class EndpointSignatureRenewerMocks:
    def __init__(
        self,
        endpoint_signature_renewer: EndpointSignatureRenewer,
        session: MockType,
        endpoint_repository: MockType,
        signing_service: MockType,
    ):
        self.endpoint_signature_renewer = endpoint_signature_renewer
        self.session = session
        self.endpoint_repository = endpoint_repository
        self.signing_service = signing_service


class TestEndpointSignatureRenewer:
    @fixture
    def mocks(self, mocker: MockerFixture) -> EndpointSignatureRenewerMocks:
        mock_endpoint_repository = mocker.Mock()
        mock_signing_service = mocker.Mock()
        mock_logger = mocker.Mock()
        mock_session = mocker.Mock()

        endpoint_signature_renewer = EndpointSignatureRenewer(
            endpoint_repository=mock_endpoint_repository,
            session=mock_session,
            signing_service=mock_signing_service,
            logger=mock_logger,
        )

        return EndpointSignatureRenewerMocks(
            endpoint_signature_renewer=endpoint_signature_renewer,
            session=mock_session,
            endpoint_repository=mock_endpoint_repository,
            signing_service=mock_signing_service,
        )

    def __create_fake_signature(self) -> str:
        return b64encode(urandom(32)).decode("utf-8")

    def test_renew_adds_and_updates_signatures(self, faker: Faker, mocks: EndpointSignatureRenewerMocks) -> None:
        mocks.endpoint_repository.find_all.return_value = [
            endpoint1 := Endpoint(id=123, signature=None, url=faker.url()),
            endpoint2 := Endpoint(id=456, signature=self.__create_fake_signature(), url=faker.url()),
        ]
        mocks.signing_service.generate_signature.side_effect = [
            signature1 := self.__create_fake_signature(),
            signature2 := self.__create_fake_signature(),
        ]

        result = mocks.endpoint_signature_renewer.renew()

        assert result.added == 1
        assert result.updated == 1
        assert result.skipped == 0
        assert endpoint1.signature == signature1
        assert endpoint2.signature == signature2

        mocks.session.commit.assert_called_once()

    def test_renew_skips_endpoint_if_signature_generation_fails(
        self, faker: Faker, mocks: EndpointSignatureRenewerMocks
    ) -> None:
        assert mocks.signing_service is not None

        mocks.endpoint_repository.find_all.return_value = [
            Endpoint(id=123, signature=None, url=faker.url()),
            Endpoint(id=456, signature=None, url=faker.url()),
        ]
        mocks.signing_service.generate_signature.side_effect = [
            Exception("Signature generation failed"),
            self.__create_fake_signature(),
        ]

        result = mocks.endpoint_signature_renewer.renew()

        assert result.added == 1
        assert result.updated == 0
        assert result.skipped == 1

        mocks.session.commit.assert_called_once()
