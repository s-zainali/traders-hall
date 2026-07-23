from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

Db = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    unauthenticated = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHENTICATED", "message": "Not authenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthenticated

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthenticated

    user = await db.get(User, user_id)
    if user is None or user.status != "active":
        raise unauthenticated

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]