import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import auth


class FakeSigningKey:
    key = "public-key"


class FakeJwksClient:
    def get_signing_key_from_jwt(self, token):
        assert token == "token"
        return FakeSigningKey()


def test_oidc_principal_uses_cached_jwks_client(monkeypatch):
    monkeypatch.setattr(auth.settings, "oidc_enabled", True)
    monkeypatch.setattr(auth.settings, "oidc_jwks_url", "https://identity.example/jwks")
    monkeypatch.setattr(auth.settings, "oidc_issuer", "https://identity.example")
    monkeypatch.setattr(auth, "_jwks_client", lambda _url: FakeJwksClient())
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *_args, **_kwargs: {
            "sub": "oidc-user",
            "realm_access": {"roles": ["lca_reviewer"]},
        },
    )

    principal = auth.get_principal(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        x_user_id=None,
        x_roles=None,
    )

    assert principal.subject == "oidc-user"
    assert principal.has_role("lca_reviewer")


def test_oidc_rejects_missing_and_invalid_tokens(monkeypatch):
    monkeypatch.setattr(auth.settings, "oidc_enabled", True)
    monkeypatch.setattr(auth.settings, "oidc_jwks_url", "https://identity.example/jwks")
    with pytest.raises(HTTPException, match="Bearer token required"):
        auth.get_principal(credentials=None, x_user_id=None, x_roles=None)

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: FakeJwksClient())

    def invalid(*_args, **_kwargs):
        raise jwt.InvalidTokenError("invalid")

    monkeypatch.setattr(jwt, "decode", invalid)
    with pytest.raises(HTTPException, match="Invalid bearer token"):
        auth.get_principal(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
            x_user_id=None,
            x_roles=None,
        )
