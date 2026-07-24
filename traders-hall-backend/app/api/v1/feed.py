"""Event log and chat endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, Db
from app.schemas.event import ChatSend, EventOut
from app.services import event_service
from app.services.event_service import FeedError

router = APIRouter()

_STATUS = {
    "GAME_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_A_PLAYER": status.HTTP_403_FORBIDDEN,
    "PLAYER_ELIMINATED": status.HTTP_403_FORBIDDEN,
}


def _http(exc: FeedError) -> HTTPException:
    return HTTPException(
        status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/{code}/events", response_model=list[EventOut])
async def list_events(
    code: str,
    user: CurrentUser,
    db: Db,
    since: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    try:
        return await event_service.list_events(
            db, user=user, code=code, since=since, limit=limit
        )
    except FeedError as e:
        raise _http(e)


@router.post("/{code}/chat", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def post_chat(code: str, body: ChatSend, user: CurrentUser, db: Db):
    try:
        return await event_service.post_chat(db, user=user, code=code, text=body.text)
    except FeedError as e:
        raise _http(e)