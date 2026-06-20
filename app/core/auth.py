from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.request_context import actor_var


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles or "admin" in self.roles


bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_user_id: str | None = Header(default=None),
    x_roles: str | None = Header(default=None),
) -> Principal:
    if settings.oidc_enabled:
        if not credentials or not settings.oidc_jwks_url:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
        try:
            key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(
                credentials.credentials
            ).key
            claims = jwt.decode(
                credentials.credentials,
                key,
                algorithms=["RS256", "ES256"],
                audience=settings.oidc_audience,
                issuer=settings.oidc_issuer,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token",
            ) from exc
        raw_roles = claims.get("roles") or claims.get("realm_access", {}).get("roles", [])
        principal = Principal(str(claims["sub"]), frozenset(raw_roles))
    else:
        if not settings.local_auth_enabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication disabled",
            )
        principal = Principal(
            subject=x_user_id or "local-user",
            roles=frozenset(
                role.strip()
                for role in (x_roles or "data_submitter,lca_reviewer,admin").split(",")
                if role.strip()
            ),
        )
    actor_var.set(principal.subject)
    return principal


def require_role(role: str):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}",
            )
        return principal

    return dependency
