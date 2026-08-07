"""Housing endpoints: moving into your own property, and vacating.

Letting rooms out and requesting one go through the marketplace instead, as
rent_out and rent_ask offers, so they are not here.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.game_state import GameStateOut
from app.schemas.residence import (
    EvictRequest,
    LeaveResidenceRequest,
    MoveInRequest,
    MoveOutResolveRequest,
    MoveOutResponseRequest,
    PayRentRequest,
)
from app.services import game_service, rent_service, residence_service
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
    "ALREADY_RESIDING": status.HTTP_409_CONFLICT,
    "NO_RESIDENCE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NO_TENANCY": status.HTTP_404_NOT_FOUND,
    "INSUFFICIENT_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_LANDLORD": status.HTTP_403_FORBIDDEN,
    "NO_MOVEOUT_REQUEST": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NO_MOVEOUT_REFUSAL": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "MOVEOUT_PENDING": status.HTTP_409_CONFLICT,
    "MOVEOUT_REFUSED": status.HTTP_409_CONFLICT,
    "LANDLORD_GONE": status.HTTP_409_CONFLICT,
    "NO_FREE_ROOM": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_HABITABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
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


async def _state(db, user, code: str) -> GameStateOut:
    raw = await game_service.get_game_state(db, user=user, code=code)
    return build_game_state(raw)


@router.post("/{code}/actions/move-in", response_model=GameStateOut)
async def move_in(code: str, body: MoveInRequest, user: CurrentUser, db: Db):
    try:
        await residence_service.move_in(
            db, user=user, code=code,
            card_type=body.card_type,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/leave-residence", response_model=GameStateOut)
async def leave_residence(
    code: str, body: LeaveResidenceRequest, user: CurrentUser, db: Db
):
    try:
        await residence_service.leave(
            db, user=user, code=code,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/moveout-response", response_model=GameStateOut)
async def moveout_response(
    code: str, body: MoveOutResponseRequest, user: CurrentUser, db: Db
):
    """Landlord answers a tenant asking to leave.

    Not turn-gated, the same as settling an offer: a request answerable only on
    the landlord's own turn would strand the tenant for most of a lap.
    """
    try:
        await rent_service.respond_moveout(
            db, user=user, code=code,
            agreement_id=body.agreement_id,
            accept=body.accept,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/moveout-resolve", response_model=GameStateOut)
async def moveout_resolve(
    code: str, body: MoveOutResolveRequest, user: CurrentUser, db: Db
):
    """Tenant chooses after a refusal: stay, or pay the quoted price and go."""
    try:
        await rent_service.resolve_moveout(
            db, user=user, code=code,
            leave=body.leave,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/evict", response_model=GameStateOut)
async def evict(code: str, body: EvictRequest, user: CurrentUser, db: Db):
    """Landlord ends a tenancy early. The forfeited rent is not collected."""
    try:
        await rent_service.evict(
            db, user=user, code=code,
            agreement_id=body.agreement_id,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/pay-rent", response_model=GameStateOut)
async def pay_rent(code: str, body: PayRentRequest, user: CurrentUser, db: Db):
    """Clear rent now rather than waiting for the counter to reach zero."""
    try:
        await rent_service.pay_now(
            db, user=user, code=code,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)