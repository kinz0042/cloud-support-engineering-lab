"""JWT verification against generated RSA keys; skipped without optional dependencies."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    jwt = None

from app.oauth_gateway import AuthInvalid, AuthUnavailable, TokenVerifier


@unittest.skipUnless(jwt, 'PyJWT and cryptography are not installed')
class JWTVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public = cls.private.public_key()

    def setUp(self):
        self.verifier = TokenVerifier('https://issuer.example/realm', 'relay-api', 'https://issuer.example/jwks')
        self.verifier.client = Mock()
        self.verifier.client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.public)
        now = int(time.time())
        self.claims = {'iss': 'https://issuer.example/realm', 'aud': 'relay-api',
                       'sub': 'synthetic-client', 'iat': now, 'exp': now + 300, 'tenant_id': 'acme'}

    def signed(self, claims=None):
        return jwt.encode(claims or self.claims, self.private, algorithm='RS256', headers={'kid':'test-key'})

    def test_valid_signature_and_claims(self):
        self.assertEqual(self.verifier.validate(self.signed())['tenant_id'], 'acme')

    def test_wrong_issuer_audience_expiry_and_missing_exp_are_rejected(self):
        for change in ({'iss': 'https://evil.example'}, {'aud': 'other-api'}, {'exp': int(time.time())-10}, {'exp': None}):
            with self.subTest(change=change):
                claims = {**self.claims, **change}
                if change == {'exp': None}:
                    del claims['exp']
                with self.assertRaises(AuthInvalid):
                    self.verifier.validate(self.signed(claims))

    def test_tampered_signature_rejected(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(self.claims, other, algorithm='RS256', headers={'kid':'test-key'})
        with self.assertRaises(AuthInvalid):
            self.verifier.validate(token)

    def test_unavailable_identity_is_distinguished_from_invalid_token(self):
        self.verifier.client.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError('unavailable')
        with self.assertRaises(AuthUnavailable):
            self.verifier.validate(self.signed())
