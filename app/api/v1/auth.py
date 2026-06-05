from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.core.config import settings
from app.core.security import create_auth_token, parse_auth_token
from app.schemas.auth import AuthCredentials, AuthResponse, AuthUserResponse
from app.services.users import (
    UserAlreadyExistsError,
    authenticate_user_async,
    create_user_async,
    get_user_by_id_async,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    credentials: AuthCredentials,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> AuthResponse:
    if not settings.auth_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled.",
        )

    try:
        user = await create_user_async(
            db,
            username=credentials.username,
            password=credentials.password,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        ) from exc

    _set_auth_cookie(response, user.id, user.username)
    return AuthResponse(user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: AuthCredentials,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
) -> AuthResponse:
    user = await authenticate_user_async(
        db,
        username=credentials.username,
        password=credentials.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    _set_auth_cookie(response, user.id, user.username)
    return AuthResponse(user=_user_response(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    _clear_auth_cookie(response)


@router.get("/me", response_model=AuthResponse)
async def me(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> AuthResponse:
    payload = parse_auth_token(request.cookies.get(settings.auth_cookie_name))
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    try:
        user_id = int(payload["sub"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        ) from exc

    user = await get_user_by_id_async(db, user_id)
    if user is None or not user.is_active or user.username != payload["username"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    return AuthResponse(user=_user_response(user))


def _set_auth_cookie(response: Response, user_id: int, username: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_auth_token(user_id, username),
        max_age=settings.auth_cookie_max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )


def _user_response(user) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
    )
