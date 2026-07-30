"""Resolving a seizure, and the only endpoints that work on a frozen game.

Every other route is refused by _lock_game while phase == 'seizure'. These two
are the exits: take what you are owed, or waive it.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.game_state import GameStateOut
from app.schemas.seizure import SeizeCardsRequest, WaiveSeizureRequest
from app.services import game_service, seizure_service
from app.services.action_service import ActionError
from app.services.projection import build_game_state

router = APIRouter()

_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
    "NOT_LANDLORD": status.HTTP_403_FORBIDDEN,
    "GAME_NOT_RUNNING": status.HTTP_409_CONFLICT,
    "STATE_VERSION_CONFLICT": status.HTTP_409_CONFLICT,
    "NO_SEIZURE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOTHING_PICKED": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_SEIZABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "DEBT_NOT_COVERED": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
}


def _http(exc: ActionError) -> HTTPException:
    detail = {"code": exc.code, "message": exc.message}
    detail.update(getattr(exc, "details", {}) or {})
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail=detail,
    )


async def _state(db, user, code: str) -> GameStateOut:
    await db.commit()
    raw = await game_service.get_game_state(db, user=user, code=code)
    return build_game_state(raw)


@router.post("/{code}/actions/seize", response_model=GameStateOut)
async def seize(code: str, body: SeizeCardsRequest, user: CurrentUser, db: Db):
    try:
        await seizure_service.take_cards(
            db, user=user, code=code,
            picks=body.picks,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/waive-seizure", response_model=GameStateOut)
async def waive_seizure(
    code: str, body: WaiveSeizureRequest, user: CurrentUser, db: Db
):
    try:
        await seizure_service.forgive(
            db, user=user, code=code,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)