import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, Db
from app.schemas.game_state import GameStateOut
from app.schemas.offer import OfferAction, OfferCreate, OfferOut
from app.services import game_service, offer_service
from app.services.action_service import ActionError
from app.services.projection import build_game_state

router = APIRouter()

_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "OFFER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
    "NOT_YOUR_TURN": status.HTTP_403_FORBIDDEN,
    "NOT_OFFER_OWNER": status.HTTP_403_FORBIDDEN,
    "NOT_CLAIMANT": status.HTTP_403_FORBIDDEN,
    "GAME_NOT_RUNNING": status.HTTP_409_CONFLICT,
    "STATE_VERSION_CONFLICT": status.HTTP_409_CONFLICT,
    "OFFER_NOT_OPEN": status.HTTP_409_CONFLICT,
    "OFFER_NOT_CLAIMED": status.HTTP_409_CONFLICT,
    "CLAIMANT_GONE": status.HTTP_409_CONFLICT,
    "CANNOT_CLAIM_OWN_OFFER": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_CARDS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "INSUFFICIENT_POINTS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_OFFERS": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "NOT_TRADEABLE": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "ALREADY_RESIDING": status.HTTP_409_CONFLICT,
    "NO_FREE_ROOM": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "CARD_TYPE_REQUIRED": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "UNKNOWN_CARD_TYPE": status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def _http(exc: ActionError) -> HTTPException:
    detail = {"code": exc.code, "message": exc.message}
    detail.update(getattr(exc, "details", {}) or {})
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail=detail,
    )


async def _state(db, user, code: str) -> GameStateOut:
    """Commit the action, then read the world back.

    The commit is here and not left to get_db because that dependency commits in
    TEARDOWN — after the handler has already returned its response. The client
    gets its 200, immediately fires GET /offers on another connection, and that
    read can arrive before the write lands: the player who just claimed sees an
    offer with no claim on it, and only a page reload (by which time the commit
    has settled) shows the truth.

    Committing before building the response also means the state returned here
    is the state everyone else will see, rather than a view only this
    transaction has.
    """
    await db.commit()
    raw = await game_service.get_game_state(db, user=user, code=code)
    return build_game_state(raw)


@router.get("/{code}/offers", response_model=list[OfferOut])
async def list_offers(code: str, user: CurrentUser, db: Db):
    try:
        return await offer_service.list_offers(db, user=user, code=code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers", response_model=GameStateOut, status_code=status.HTTP_201_CREATED)
async def create_offer(code: str, body: OfferCreate, user: CurrentUser, db: Db):
    try:
        await offer_service.create_offer(
            db, user=user, code=code,
            kind=body.kind,
            offer_card_type=body.offer_card_type,
            offer_quantity=body.offer_quantity,
            price_points=body.price_points,
            want_card_type=body.want_card_type,
            want_quantity=body.want_quantity,
            rent_interval_turns=body.rent_interval_turns,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers/{offer_id}/claim", response_model=GameStateOut)
async def claim_offer(code: str, offer_id: uuid.UUID, body: OfferAction, user: CurrentUser, db: Db):
    try:
        await offer_service.claim_offer(
            db, user=user, code=code, offer_id=offer_id,
            expected_state_version=body.expected_state_version,
            # rent_ask only: which of the claiming landlord's properties the
            # room is in. Ignored by every other kind.
            card_type=body.card_type,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers/{offer_id}/unclaim", response_model=GameStateOut)
async def withdraw_claim(code: str, offer_id: uuid.UUID, user: CurrentUser, db: Db):
    try:
        await offer_service.withdraw_claim(db, user=user, code=code, offer_id=offer_id)
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers/{offer_id}/decline", response_model=GameStateOut)
async def decline_claim(
    code: str, offer_id: uuid.UUID, user: CurrentUser, db: Db,
    # Optional so a decline on a single-claim offer stays a bodyless POST, which
    # is what the client has always sent. player_id only becomes necessary once
    # several players are in the running.
    body: OfferAction | None = None,
):
    try:
        await offer_service.decline_claim(
            db, user=user, code=code, offer_id=offer_id,
            player_id=body.player_id if body else None,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers/{offer_id}/confirm", response_model=GameStateOut)
async def confirm_offer(code: str, offer_id: uuid.UUID, body: OfferAction, user: CurrentUser, db: Db):
    try:
        await offer_service.confirm_offer(
            db, user=user, code=code, offer_id=offer_id,
            expected_state_version=body.expected_state_version,
        )
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)


@router.post("/{code}/offers/{offer_id}/cancel", response_model=GameStateOut)
async def cancel_offer(code: str, offer_id: uuid.UUID, user: CurrentUser, db: Db):
    try:
        await offer_service.cancel_offer(db, user=user, code=code, offer_id=offer_id)
        return await _state(db, user, code)
    except ActionError as e:
        raise _http(e)