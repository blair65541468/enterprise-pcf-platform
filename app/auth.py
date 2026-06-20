from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles or "admin" in self.roles


bearer = HTTPBearer(auto_error=False)


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_user_id: str | None = Header(default=None),
    x_roles: str | None = Header(default=None),
) -> Principal:
    if settings.oidc_enabled:
        if not credentials or not settings.oidc_jwks_url:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
        jwks = jwt.PyJWKClient(settings.oidc_jwks_url)
        key = jwks.get_signing_key_from_jwt(credentials.credentials).key
        claims = jwt.decode(
            credentials.credentials,
            key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
        )
        raw_roles = claims.get("roles") or claims.get("realm_access", {}).get("roles", [])
        return Principal(str(claims["sub"]), frozenset(raw_roles))

    if not settings.local_auth_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication disabled")
    return Principal(
        subject=x_user_id or "local-user",
        roles=frozenset(r.strip() for r in (x_roles or "data_submitter,lca_reviewer,admin").split(",") if r.strip()),
    )


def require_role(role: str):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_role(role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role required: {role}")
        return principal

    return dependency

