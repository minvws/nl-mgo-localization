from __future__ import annotations

import json
import time

from jwcrypto import jwe, jwk, jwt

from app.addressing.constants import JWE_CONTENT_ENC, JWE_KEY_MANAGEMENT_ALG, JWS_ALG, URL_CLAIM_NAME


class EndpointJWTFactory:
    """Create signed JWTs for endpoint URLs."""

    JWT_KEY_LABEL = "endpoint_jwt_signing_key"

    def build(self, endpoint: str, signing_key: jwk.JWK, expiration_seconds: int) -> jwt.JWT:
        now = int(time.time())
        claims = {URL_CLAIM_NAME: endpoint, "iat": now, "exp": now + expiration_seconds}

        signed_token = jwt.JWT(header={"alg": JWS_ALG}, claims=claims)
        signed_token.make_signed_token(signing_key)

        return signed_token


class EndpointJWEFactory:
    """Encrypt payloads into compact JWEs."""

    JWE_KEY_LABEL = "endpoint_jwe_encryption_key"

    def encrypt(self, payload: str, encryption_key: jwk.JWK) -> jwe.JWE:
        jwe_envelope = jwe.JWE(
            plaintext=payload.encode("utf-8"),
            protected=json.dumps({"alg": JWE_KEY_MANAGEMENT_ALG, "enc": JWE_CONTENT_ENC}),
        )

        jwe_envelope.add_recipient(encryption_key)

        return jwe_envelope
