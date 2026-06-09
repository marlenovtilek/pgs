from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import create_auth_token, parse_auth_token
from app.services.users import authenticate_user, get_user_by_id


class PGSAdminAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        if not username or not password:
            raise LoginFailed("Неверный логин или пароль")

        with SessionLocal() as db:
            user = authenticate_user(db, username=username, password=password)

        if user is None:
            raise LoginFailed("Неверный логин или пароль")

        response.set_cookie(
            key=settings.auth_cookie_name,
            value=create_auth_token(user.id, user.username),
            max_age=settings.auth_cookie_max_age if remember_me else None,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
        )
        return response

    async def logout(self, request: Request, response: Response) -> Response:
        response.delete_cookie(
            key=settings.auth_cookie_name,
            httponly=True,
            secure=settings.auth_cookie_secure,
            samesite="lax",
        )
        return response

    async def is_authenticated(self, request: Request) -> bool:
        payload = parse_auth_token(request.cookies.get(settings.auth_cookie_name))
        if payload is None:
            return False

        try:
            user_id = int(payload["sub"])
        except ValueError:
            return False

        with SessionLocal() as db:
            user = get_user_by_id(db, user_id)
            if user is None or not user.is_active or user.username != payload["username"]:
                return False
            request.state.user = {
                "id": user.id,
                "username": user.username,
            }
        return True

    def get_admin_user(self, request: Request) -> AdminUser | None:
        user = getattr(request.state, "user", None)
        if user is None:
            return None
        return AdminUser(username=user["username"])
