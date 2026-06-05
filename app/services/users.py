from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


class UserAlreadyExistsError(Exception):
    pass


def normalize_username(username: str) -> str:
    return username.strip().lower()


def create_user(db: Session, *, username: str, password: str) -> User:
    normalized_username = normalize_username(username)
    existing_user = get_user_by_username(db, normalized_username)
    if existing_user is not None:
        raise UserAlreadyExistsError(normalized_username)

    user = User(
        username=normalized_username,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def create_user_async(db: AsyncSession, *, username: str, password: str) -> User:
    normalized_username = normalize_username(username)
    existing_user = await get_user_by_username_async(db, normalized_username)
    if existing_user is not None:
        raise UserAlreadyExistsError(normalized_username)

    user = User(
        username=normalized_username,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username_async(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(User.username == normalize_username(username))
    )
    return result.scalar_one_or_none()


def get_user_by_username(db: Session, username: str) -> User | None:
    result = db.execute(
        select(User).where(User.username == normalize_username(username))
    )
    return result.scalar_one_or_none()


async def get_user_by_id_async(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def authenticate_user_async(
    db: AsyncSession,
    *,
    username: str,
    password: str,
) -> User | None:
    user = await get_user_by_username_async(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, *, username: str, password: str) -> User | None:
    result = db.execute(
        select(User).where(User.username == normalize_username(username))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
