from base64 import b64encode
from os import urandom

from app.addressing.constants import SIGNATURE_PARAM_NAME
from app.addressing.schemas import SignedUrl


class TestSignedUrl:
    def test_create_handles_url_without_existing_query_params(self) -> None:
        signature = self.__create_fake_signature()
        signed_url = SignedUrl.create("http://example.com", signature)

        assert str(signed_url) == f"http://example.com?{SIGNATURE_PARAM_NAME}={signature}"

    def test_create_handles_url_with_existing_query_params(self) -> None:
        signature = self.__create_fake_signature()
        signed_url = SignedUrl.create("http://example.com?foo=bar", signature)

        assert str(signed_url) == f"http://example.com?foo=bar&{SIGNATURE_PARAM_NAME}={signature}"

    def test_create_handles_url_with_existing_signature_query_param(self) -> None:
        original_signature = self.__create_fake_signature()
        new_signature = self.__create_fake_signature()
        signed_url = SignedUrl.create(
            f"http://example.com?{SIGNATURE_PARAM_NAME}={original_signature}&foo=bar", new_signature
        )

        assert str(signed_url) == f"http://example.com?foo=bar&{SIGNATURE_PARAM_NAME}={new_signature}"

    def __create_fake_signature(self) -> str:
        return b64encode(urandom(32)).decode("utf-8")
