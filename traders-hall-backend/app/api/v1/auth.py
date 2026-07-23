from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.auth import (
    RefreshRequest, TokenPair, UserLogin, UserOut, UserRegister,
)
from app.services import auth_service
from app.services.auth_service import AuthError

router = APIRouter()


def _fail(exc: AuthError, code: int) -> HTTPException:
    return HTTPException(
        status_code=code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: Db):
    try:
        user = await auth_service.register(
            db,
            username=body.username,
            password=body.password,
            email=body.email,
            display_name=body.display_name,
        )
    except AuthError as e:
        raise _fail(e, status.HTTP_409_CONFLICT)

    access, refresh = await auth_service.issue_tokens(db, user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, db: Db):
    try:
        user = await auth_service.authenticate(
            db, username=body.username, password=body.password
        )
    except AuthError as e:
        raise _fail(e, status.HTTP_401_UNAUTHORIZED)

    access, refresh = await auth_service.issue_tokens(db, user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: Db):
    try:
        access, new_refresh = await auth_service.refresh(db, body.refresh_token)
    except AuthError as e:
        raise _fail(e, status.HTTP_401_UNAUTHORIZED)

    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: Db):
    await auth_service.logout(db, body.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user