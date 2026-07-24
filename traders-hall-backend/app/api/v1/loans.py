"""Credit endpoints: loans and mortgages.

Mounted under the same /games prefix as actions.py and shaped the same way —
every route returns the refreshed game state, so a client never has to fire a
second request to see the result of its own action.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.game_state import GameStateOut
from app.schemas.loan import (
    LoanBorrowRequest,
    LoanRepayRequest,
    MortgageOpenRequest,
    MortgageRedeemRequest,
)
from app.services import game_service, loan_service
from app.services.action_service import ActionError
from app.services.projection import build_game_state

router = APIRouter()

# 403 means "you may not"; 409 means "the world changed, or you already have
# one"; 422 means "not currently possible".
_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
    "NOT_YOUR_TURN": status.HTTP_403_FORBIDDEN,
    "GAME_NOT_RUNNING": status.HTTP_409_CONFLICT,
    "STATE_VERSION_CONFLICT": status.HTTP_409_CONFLICT,
    "LOAN_ALREADY_ACTIVE": status.HTTP_409_CONFLICT,
    "MORTGAGE_ALREADY_ACTIVE": status.HTTP_409_CONFLICT,
    "LOAN_LIMIT_EXCEEDED": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NO_ACTIVE_LOAN": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NO_ACTIVE_MORTGAGE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_MORTGAGEABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "BANK_OUT_OF_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
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


@router.post("/{code}/actions/borrow", response_model=GameStateOut)
async def borrow(code: str, body: LoanBorrowRequest, user: CurrentUser, db: Db):
    try:
        await loan_service.borrow(
            db, user=user, code=code,
            amount=body.amount,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/repay-loan", response_model=GameStateOut)
async def repay_loan(code: str, body: LoanRepayRequest, user: CurrentUser, db: Db):
    try:
        await loan_service.repay(
            db, user=user, code=code,
            amount=body.amount,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/open-mortgage", response_model=GameStateOut)
async def open_mortgage(code: str, body: MortgageOpenRequest, user: CurrentUser, db: Db):
    try:
        await loan_service.open_mortgage(
            db, user=user, code=code,
            card_type=body.card_type,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/actions/redeem-mortgage", response_model=GameStateOut)
async def redeem_mortgage(code: str, body: MortgageRedeemRequest, user: CurrentUser, db: Db):
    try:
        await loan_service.redeem_mortgage(
            db, user=user, code=code,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)