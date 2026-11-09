"""FastAPI authentication and RBAC authorization dependencies.

Authentication rules:

* A valid ``Authorization: Bearer aep_...`` API key always yields its stored role.
* A missing or invalid credential yields HTTP 401 - except in ``development`` with
  ``ALLOW_ANONYMOUS_VIEWER=true``, where the caller receives the read-only VIEWER role.
* Anonymous callers never receive ADMIN or ENGINEER, and every mutating route rejects
  them regardless of environment (see :func:`require_role`).
"""

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session
from app.schemas.auth_api import AuthPrincipal, ServiceAccountRole
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService

bearer_scheme = HTTPBearer(auto_error=False)

_AUTH_CHALLENGE = {"WWW-Authenticate": "Bearer"}

logger = logging.getLogger(__name__)


def authenticate_bearer_token(session: Session, raw_token: str) -> AuthPrincipal:
    """Resolve an API key into a principal, or raise HTTP 401 if it is not valid."""
    token = raw_token.strip()
    record = AuthService(session).authenticate_key(token)
    if not record:
        # Log the first characters only, so an operator can correlate attempts without the secret.
        logger.warning("Rejected API key attempt (prefix=%s, length=%d)", token[:8], len(token))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked API key.",
            headers=_AUTH_CHALLENGE,
        )
    return AuthPrincipal(
        is_authenticated=True,
        key_id=record.key_id,
        workspace_id=record.workspace_id,
        role=ServiceAccountRole(record.role),
        name=record.name,
        is_service_account=True,
    )


def anonymous_principal(session: Session) -> AuthPrincipal:
    """Read-only VIEWER identity for anonymous development access."""
    default_ws = WorkspaceService(session).get_default_workspace()
    return AuthPrincipal(
        is_authenticated=False,
        key_id=None,
        workspace_id=default_ws.workspace_id,
        role=ServiceAccountRole.VIEWER,
        name="anonymous",
        is_service_account=False,
    )


def resolve_principal(session: Session, raw_token: str | None) -> AuthPrincipal:
    """Central credential resolution shared by REST, OTLP HTTP and OTLP gRPC entry points.

    Raises HTTPException(401) when no acceptable credential is presented.
    """
    if raw_token and raw_token.strip():
        return authenticate_bearer_token(session, raw_token)
    if settings.anonymous_access_enabled:
        return anonymous_principal(session)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide an API key as 'Authorization: Bearer <key>'.",
        headers=_AUTH_CHALLENGE,
    )


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> AuthPrincipal:
    """FastAPI dependency returning the caller's principal."""
    return resolve_principal(session, credentials.credentials if credentials else None)


def require_role(
    *allowed_roles: ServiceAccountRole,
    allow_anonymous: bool = False,
) -> Callable[[AuthPrincipal], AuthPrincipal]:
    """Build a dependency enforcing an RBAC tier.

    Anonymous principals are rejected with HTTP 401 unless ``allow_anonymous`` is set, which
    only the read-only VIEWER tier does. Mutating routes must never set it.
    """

    def role_checker(
        principal: Annotated[AuthPrincipal, Depends(get_current_principal)],
    ) -> AuthPrincipal:
        if not principal.is_authenticated and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication with an API key is required for this operation.",
                headers=_AUTH_CHALLENGE,
            )
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: role '{principal.role.value}' cannot perform this action.",
            )
        return principal

    return role_checker


def ensure_collector_principal(principal: AuthPrincipal) -> AuthPrincipal:
    """Trace ingestion (OTLP) requires an authenticated ADMIN or ENGINEER key."""
    if not principal.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication with an API key is required to ingest traces.",
            headers=_AUTH_CHALLENGE,
        )
    if principal.role not in (ServiceAccountRole.ADMIN, ServiceAccountRole.ENGINEER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: role '{principal.role.value}' cannot ingest OpenTelemetry traces.",
        )
    return principal


# Type aliases for dependency injection
CurrentPrincipal = Annotated[AuthPrincipal, Depends(get_current_principal)]
RequireAdmin = Annotated[AuthPrincipal, Depends(require_role(ServiceAccountRole.ADMIN))]
RequireEngineer = Annotated[
    AuthPrincipal,
    Depends(require_role(ServiceAccountRole.ADMIN, ServiceAccountRole.ENGINEER)),
]
RequireViewer = Annotated[
    AuthPrincipal,
    Depends(
        require_role(
            ServiceAccountRole.ADMIN,
            ServiceAccountRole.ENGINEER,
            ServiceAccountRole.VIEWER,
            allow_anonymous=True,
        )
    ),
]


# Dependency used by routers to protect every read endpoint. In production every caller
# must present a valid key; in development anonymous callers receive VIEWER only.
require_viewer = require_role(
    ServiceAccountRole.ADMIN,
    ServiceAccountRole.ENGINEER,
    ServiceAccountRole.VIEWER,
    allow_anonymous=True,
)
