import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.core.config import settings
from app.core.security import parse_auth_token
from app.services.users import get_user_by_id_async


api_token_auth = HTTPBearer(auto_error=False)


async def require_api_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(api_token_auth),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    if not settings.api_token:
        return

    if _has_valid_bearer_token(credentials):
        return

    if await _has_valid_admin_cookie(request, db):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _has_valid_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> bool:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return False
    return bool(settings.api_token) and hmac.compare_digest(
        credentials.credentials,
        settings.api_token,
    )


async def _has_valid_admin_cookie(request: Request, db: AsyncSession) -> bool:
    payload = parse_auth_token(request.cookies.get(settings.auth_cookie_name))
    if payload is None:
        return False

    try:
        user_id = int(payload["sub"])
    except ValueError:
        return False

    user = await get_user_by_id_async(db, user_id)
    return bool(user and user.is_active and user.username == payload["username"])
