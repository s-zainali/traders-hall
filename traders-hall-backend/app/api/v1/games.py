from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.game import GameCreate, GameOut
from app.schemas.game_state import GameStateOut
from app.services import game_service
from app.services.game_service import GameError
from app.services.projection import build_game_state

router = APIRouter()

# domain error code -> HTTP status. 403 means "you may not", 422 means
# "not currently possible", 404 means "no such thing".
_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "NOT_HOST": status.HTTP_403_FORBIDDEN,
    "GAME_FULL": status.HTTP_409_CONFLICT,
    "GAME_ALREADY_STARTED": status.HTTP_409_CONFLICT,
    "GAME_NOT_STARTED": status.HTTP_409_CONFLICT,
    "NOT_ENOUGH_PLAYERS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "CODE_GENERATION_FAILED": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _http(exc: GameError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.post("", response_model=GameOut, status_code=status.HTTP_201_CREATED)
async def create_game(body: GameCreate, user: CurrentUser, db: Db):
    try:
        return await game_service.create_game(db, host=user, max_players=body.max_players)
    except GameError as e:
        raise _http(e)


# ── literal paths BEFORE parameterised ones ──────────────────────────
# FastAPI matches routes in declaration order. "/{code}" declared above would
# swallow "/mine" and try to look up a game whose code is literally "mine".
@router.get("/mine", response_model=list[GameOut])
async def my_games(user: CurrentUser, db: Db):
    return await game_service.list_my_games(db, user=user)


# Likewise this must precede "/{code}", or "/ABC123/state" never matches.
@router.get("/{code}/state", response_model=GameStateOut)
async def game_state(code: str, user: CurrentUser, db: Db):
    try:
        raw = await game_service.get_game_state(db, user=user, code=code)
    except GameError as e:
        raise _http(e)
    return build_game_state(raw)


@router.get("/{code}", response_model=GameOut)
async def get_game(code: str, user: CurrentUser, db: Db):
    try:
        return await game_service.get_game(db, code=code)
    except GameError as e:
        raise _http(e)


@router.post("/{code}/join", response_model=GameOut)
async def join_game(code: str, user: CurrentUser, db: Db):
    try:
        return await game_service.join_game(db, user=user, code=code)
    except GameError as e:
        raise _http(e)


@router.post("/{code}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_game(code: str, user: CurrentUser, db: Db):
    try:
        await game_service.leave_game(db, user=user, code=code)
    except GameError as e:
        raise _http(e)


@router.post("/{code}/start", response_model=GameOut)
async def start_game(code: str, user: CurrentUser, db: Db):
    try:
        return await game_service.start_game(db, user=user, code=code)
    except GameError as e:
        raise _http(e)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def close_game(code: str, user: CurrentUser, db: Db):
    try:
        await game_service.close_game(db, user=user, code=code)
    except GameError as e:
        raise _http(e)