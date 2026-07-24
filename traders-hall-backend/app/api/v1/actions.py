"""Player action endpoints.

Every route returns the refreshed game state, so a client never has to fire a
second request to see the result of its own action.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.action import ActionRequest, CardTradeRequest
from app.schemas.game_state import GameStateOut
from app.services import action_service, game_service
from app.services.action_service import ActionError
from app.services.projection import build_game_state

router = APIRouter()

# 403 means "you may not"; 409 means "the world changed"; 422 means "not
# currently possible". The client can present those three very differently — a
# disabled control, a silent resync, an explanatory message.
_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
    "NOT_YOUR_TURN": status.HTTP_403_FORBIDDEN,
    "GAME_NOT_RUNNING": status.HTTP_409_CONFLICT,
    "STATE_VERSION_CONFLICT": status.HTTP_409_CONFLICT,
    "INSUFFICIENT_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_BANK_STOCK": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "BANK_OUT_OF_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_PURCHASABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_SELLABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "UNKNOWN_CARD_TYPE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
}


def _http(exc: ActionError) -> HTTPException:
    detail = {"code": exc.code, "message": exc.message}
    detail.update(exc.details)
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail=detail,
    )


async def _state(db, user, code: str) -> GameStateOut:
    raw = await game_service.get_game_state(db, user=user, code=code)
    return build_game_state(raw)


@router.post("/{code}/actions/buy-from-bank", response_model=GameStateOut)
async def buy_from_bank(code: str, body: CardTradeRequest, user: CurrentUser, db: Db):
    try:
        await action_service.buy_from_bank(
            db, user=user, code=code,
            card_type=body.card_type, quantity=body.quantity,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/sell-to-bank", response_model=GameStateOut)
async def sell_to_bank(code: str, body: CardTradeRequest, user: CurrentUser, db: Db):
    try:
        await action_service.sell_to_bank(
            db, user=user, code=code,
            card_type=body.card_type, quantity=body.quantity,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/end-turn", response_model=GameStateOut)
async def end_turn(code: str, body: ActionRequest, user: CurrentUser, db: Db):
    try:
        await action_service.end_turn(
            db, user=user, code=code,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)