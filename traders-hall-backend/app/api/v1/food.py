"""Household upkeep endpoints.

Just eating for now. Rent will land here too once rental agreements exist, which
is why this is not folded into actions.py — buying and selling are market moves,
whereas eating and paying rent are survival, and they share validation shape
(you must hold the thing, it must be your turn, the counter moves).
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.food import EatRequest
from app.schemas.game_state import GameStateOut
from app.services import food_service, game_service
from app.services.action_service import ActionError
from app.services.projection import build_game_state

router = APIRouter()

_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
    "NOT_YOUR_TURN": status.HTTP_403_FORBIDDEN,
    "GAME_NOT_RUNNING": status.HTTP_409_CONFLICT,
    "STATE_VERSION_CONFLICT": status.HTTP_409_CONFLICT,
    "NOT_EDIBLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "UNKNOWN_CARD_TYPE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
}


def _http(exc: ActionError) -> HTTPException:
    detail = {"code": exc.code, "message": exc.message}
    detail.update(getattr(exc, "details", {}) or {})
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail=detail,
    )


@router.post("/{code}/actions/eat", response_model=GameStateOut)
async def eat(code: str, body: EatRequest, user: CurrentUser, db: Db):
    try:
        await food_service.eat(
            db, user=user, code=code,
            card_type=body.card_type,
            quantity=body.quantity,
            expected_state_version=body.expected_state_version,
        )
        raw = await game_service.get_game_state(db, user=user, code=code)
        return build_game_state(raw)
    except ActionError as e:
        raise _http(e)