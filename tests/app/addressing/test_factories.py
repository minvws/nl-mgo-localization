import json
import time

import pytest
from jwcrypto import jwe, jwk, jws, jwt

from app.addressing.constants import JWE_CONTENT_ENC, JWE_KEY_MANAGEMENT_ALG, JWS_ALG, URL_CLAIM_NAME
from app.addressing.factories import EndpointJWEFactory, EndpointJWTFactory


@pytest.fixture()
def signing_key() -> jwk.JWK:
    return jwk.JWK.generate(kty="EC", crv="P-256")


@pytest.fixture()
def encryption_key() -> jwk.JWK:
    return jwk.JWK.generate(kty="RSA", size=2048)


@pytest.fixture()
def wrong_signing_key() -> jwk.JWK:
    return jwk.JWK.generate(kty="EC", crv="P-256")


@pytest.fixture()
def wrong_encryption_key() -> jwk.JWK:
    return jwk.JWK.generate(kty="RSA", size=2048)


class TestEndpointJWTFactory:
    def test_build_creates_signed_jwt_with_correct_claims(self, signing_key: jwk.JWK) -> None:
        factory = EndpointJWTFactory()
        endpoint = "https://example.com/fhir"
        expiration_seconds = 3600

        before_creation = int(time.time())
        signed_token = factory.build(endpoint, signing_key, expiration_seconds)
        after_creation = int(time.time())

        token_string = signed_token.serialize()
        assert isinstance(token_string, str)
        assert len(token_string) > 0

        verified_token = jwt.JWT(jwt=token_string, key=signing_key)
        claims = json.loads(verified_token.claims)

        assert claims[URL_CLAIM_NAME] == endpoint
        assert before_creation <= claims["iat"] <= after_creation
        assert claims["exp"] == claims["iat"] + expiration_seconds

    def test_jwt_verification_fails_with_wrong_key(self, signing_key: jwk.JWK, wrong_signing_key: jwk.JWK) -> None:
        factory = EndpointJWTFactory()
        endpoint = "https://example.com/fhir"

        signed_token = factory.build(endpoint, signing_key, expiration_seconds=3600)
        token_string = signed_token.serialize()

        with pytest.raises(jws.InvalidJWSSignature):
            jwt.JWT(jwt=token_string, key=wrong_signing_key)

    def test_jwt_uses_correct_algorithm(self, signing_key: jwk.JWK) -> None:
        factory = EndpointJWTFactory()
        endpoint = "https://example.com/fhir"

        signed_token = factory.build(endpoint, signing_key, expiration_seconds=3600)

        header = signed_token.token.jose_header
        assert header["alg"] == JWS_ALG

    @pytest.mark.parametrize("expiration_seconds", [60, 3600, 86400, 2592000])
    def test_jwt_respects_expiration_seconds(self, signing_key: jwk.JWK, expiration_seconds: int) -> None:
        factory = EndpointJWTFactory()
        endpoint = "https://example.com/fhir"

        before_creation = int(time.time())
        signed_token = factory.build(endpoint, signing_key, expiration_seconds)
        after_creation = int(time.time())

        token_string = signed_token.serialize()
        verified_token = jwt.JWT(jwt=token_string, key=signing_key)
        claims = json.loads(verified_token.claims)

        exp_claim = claims["exp"]
        iat_claim = claims["iat"]

        assert exp_claim - iat_claim == expiration_seconds
        assert before_creation <= iat_claim <= after_creation

    def test_jwt_verification_fails_when_expired(self, signing_key: jwk.JWK) -> None:
        factory = EndpointJWTFactory()
        endpoint = "https://example.com/fhir"

        signed_token = factory.build(endpoint, signing_key, expiration_seconds=1)
        token_string = signed_token.serialize()

        time.sleep(2)

        verified_token = jwt.JWT(jwt=token_string, key=signing_key)
        claims = json.loads(verified_token.claims)
        exp_claim = claims["exp"]
        now = int(time.time())

        assert exp_claim < now


class TestEndpointJWEFactory:
    def test_encrypt_creates_jwe(self, encryption_key: jwk.JWK) -> None:
        factory = EndpointJWEFactory()
        payload = "test payload"

        jwe_envelope = factory.encrypt(payload, encryption_key)

        jwe_string = jwe_envelope.serialize(compact=True)
        assert isinstance(jwe_string, str)
        assert len(jwe_string) > 0

    def test_encrypted_jwe_can_be_decrypted_to_original_payload(self, encryption_key: jwk.JWK) -> None:
        factory = EndpointJWEFactory()
        original_payload = "https://example.com/fhir/endpoint"

        jwe_envelope = factory.encrypt(original_payload, encryption_key)
        jwe_string = jwe_envelope.serialize(compact=True)

        decrypted_jwe = jwe.JWE()
        decrypted_jwe.deserialize(jwe_string)
        decrypted_jwe.decrypt(encryption_key)
        decrypted_payload = decrypted_jwe.payload.decode("utf-8")

        assert decrypted_payload == original_payload

    def test_jwe_decryption_fails_with_wrong_key(self, encryption_key: jwk.JWK, wrong_encryption_key: jwk.JWK) -> None:
        factory = EndpointJWEFactory()
        payload = "test payload"

        jwe_envelope = factory.encrypt(payload, encryption_key)
        jwe_string = jwe_envelope.serialize(compact=True)

        decrypted_jwe = jwe.JWE()
        decrypted_jwe.deserialize(jwe_string)
        with pytest.raises(jwe.InvalidJWEData):
            decrypted_jwe.decrypt(wrong_encryption_key)

    def test_jwe_uses_correct_algorithms(self, encryption_key: jwk.JWK) -> None:
        factory = EndpointJWEFactory()
        payload = "test payload"

        jwe_envelope = factory.encrypt(payload, encryption_key)

        protected_header = jwe_envelope.jose_header
        assert protected_header["alg"] == JWE_KEY_MANAGEMENT_ALG
        assert protected_header["enc"] == JWE_CONTENT_ENC

    def test_jwe_handles_special_characters(self, encryption_key: jwk.JWK) -> None:
        factory = EndpointJWEFactory()
        special_payload = "https://example.com/fhir?param=value&special=äöü€@#"

        jwe_envelope = factory.encrypt(special_payload, encryption_key)
        jwe_string = jwe_envelope.serialize(compact=True)

        decrypted_jwe = jwe.JWE()
        decrypted_jwe.deserialize(jwe_string)
        decrypted_jwe.decrypt(encryption_key)
        decrypted_payload = decrypted_jwe.payload.decode("utf-8")

        assert decrypted_payload == special_payload


class TestEndpointJWTAndJWEIntegration:
    def test_full_endpoint_wrapping_roundtrip(self, signing_key: jwk.JWK, encryption_key: jwk.JWK) -> None:
        jwt_factory = EndpointJWTFactory()
        jwe_factory = EndpointJWEFactory()

        original_endpoint = "https://example.com/fhir/R4"
        expiration_seconds = 3600

        signed_jwt = jwt_factory.build(original_endpoint, signing_key, expiration_seconds)
        jwt_string = signed_jwt.serialize()

        jwe_envelope = jwe_factory.encrypt(jwt_string, encryption_key)
        jwe_string = jwe_envelope.serialize(compact=True)

        decrypted_jwe = jwe.JWE()
        decrypted_jwe.deserialize(jwe_string)
        decrypted_jwe.decrypt(encryption_key)
        decrypted_jwt_string = decrypted_jwe.payload.decode("utf-8")

        verified_jwt = jwt.JWT(jwt=decrypted_jwt_string, key=signing_key)
        claims = json.loads(verified_jwt.claims)

        assert claims[URL_CLAIM_NAME] == original_endpoint

    def test_roundtrip_with_multiple_endpoints(self, signing_key: jwk.JWK, encryption_key: jwk.JWK) -> None:
        jwt_factory = EndpointJWTFactory()
        jwe_factory = EndpointJWEFactory()

        endpoints = [
            "https://example.com/fhir/R4",
            "https://other-system.org/api/v1/fhir",
            "https://localhost:8080/test",
        ]

        for original_endpoint in endpoints:
            signed_jwt = jwt_factory.build(original_endpoint, signing_key, 3600)
            jwt_string = signed_jwt.serialize()
            jwe_envelope = jwe_factory.encrypt(jwt_string, encryption_key)
            jwe_string = jwe_envelope.serialize(compact=True)

            decrypted_jwe = jwe.JWE()
            decrypted_jwe.deserialize(jwe_string)
            decrypted_jwe.decrypt(encryption_key)
            decrypted_jwt_string = decrypted_jwe.payload.decode("utf-8")
            verified_jwt = jwt.JWT(jwt=decrypted_jwt_string, key=signing_key)
            claims = json.loads(verified_jwt.claims)

            assert claims[URL_CLAIM_NAME] == original_endpoint
