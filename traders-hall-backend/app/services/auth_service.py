import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.session import Session
from app.models.user import User

settings = get_settings()


class AuthError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


async def register(db: AsyncSession, *, username: str, password: str,
                   email: str | None, display_name: str | None) -> User:
    existing = await db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise AuthError("USERNAME_TAKEN", "That username is already registered")

    if email:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise AuthError("EMAIL_TAKEN", "That email is already registered")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or username,
    )
    db.add(user)
    await db.flush()      # assigns defaults / validates constraints, no commit yet
    return user


async def authenticate(db: AsyncSession, *, username: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.username == username))

    # Same error whether the user is missing or the password is wrong — telling
    # them apart lets an attacker enumerate valid usernames.
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("INVALID_CREDENTIALS", "Incorrect username or password")

    if user.status != "active":
        raise AuthError("ACCOUNT_DISABLED", "This account is not active")

    user.last_seen_at = datetime.now(UTC)
    return user


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create an access token and a fresh refresh session."""
    raw_refresh, refresh_hash = create_refresh_token()

    db.add(Session(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))

    return create_access_token(user.id), raw_refresh


async def refresh(db: AsyncSession, raw_token: str) -> tuple[str, str]:
    token_hash = hash_refresh_token(raw_token)
    session = await db.scalar(
        select(Session).where(Session.refresh_token_hash == token_hash)
    )

    invalid = AuthError("INVALID_REFRESH_TOKEN", "Refresh token is invalid or expired")
    if session is None or session.revoked_at is not None:
        raise invalid
    if session.expires_at <= datetime.now(UTC):
        raise invalid

    user = await db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise invalid

    # Rotation: this token is spent. A replay of it now fails.
    session.revoked_at = datetime.now(UTC)

    return await issue_tokens(db, user)


async def logout(db: AsyncSession, raw_token: str) -> None:
    session = await db.scalar(
        select(Session).where(Session.refresh_token_hash == hash_refresh_token(raw_token))
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)