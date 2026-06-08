from app.core.config import settings
from app.core.database import SessionLocal
from app.services.users import UserAlreadyExistsError, create_user


def main() -> None:
    with SessionLocal() as db:
        admin_user_state = _ensure_admin_user(db)

    print(f"admin_user={admin_user_state}")


def _ensure_admin_user(db) -> str:
    if not settings.admin_username or not settings.admin_password:
        return "not_configured"

    try:
        create_user(
            db,
            username=settings.admin_username,
            password=settings.admin_password,
        )
    except UserAlreadyExistsError:
        return "exists"
    return "created"


if __name__ == "__main__":
    main()
