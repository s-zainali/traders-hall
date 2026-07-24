"""The game feed: actions, turns, and chat, in one ordered stream.

Chat is stored as a game event rather than in its own table. The alternative —
a separate chat table — means merging two streams with different orderings
every time the feed is read, and inventing a tiebreak when a message and an
action share a timestamp. One table with one gapless sequence removes that
problem entirely, and the log/chat split becomes a filter on event_type.

The cost is that the event log contains chat. That would matter if state were
rebuilt by folding events; it is not — current state lives in normal tables and
the log is a parallel record.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_player import GamePlayer
from app.models.user import User

CHAT_EVENT = "chat.message"


class FeedError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


async def _game_and_seat(db: AsyncSession, user: User, code: str) -> tuple[Game, GamePlayer]:
    game = await db.scalar(select(Game).where(Game.join_code == code.upper()))
    if game is None:
        raise FeedError("GAME_NOT_FOUND", "No game with that code")

    seat = await db.scalar(
        select(GamePlayer).where(
            GamePlayer.game_id == game.id, GamePlayer.user_id == user.id
        )
    )
    if seat is None:
        # Only players see the feed. It carries chat, and a game's chat is not
        # public just because its join code is guessable.
        raise FeedError("NOT_A_PLAYER", "You are not in that game")

    return game, seat


async def list_events(
    db: AsyncSession, *, user: User, code: str, since: int = 0, limit: int = 100
) -> list[GameEvent]:
    """Events after `since`, oldest first.

    Incremental by design: the client keeps the last seq it saw and asks only
    for what follows, so a long match does not re-send its whole history every
    two seconds.
    """
    game, _ = await _game_and_seat(db, user, code)

    stmt = (
        select(GameEvent)
        .where(GameEvent.game_id == game.id, GameEvent.seq > since)
        .order_by(GameEvent.seq)
        .limit(limit)
    )
    return list(await db.scalars(stmt))


async def post_chat(db: AsyncSession, *, user: User, code: str, text: str) -> GameEvent:
    game, seat = await _game_and_seat(db, user, code)

    if seat.status != "active":
        raise FeedError("PLAYER_ELIMINATED", "You are no longer in this game")

    # Same seq allocation as action_service._append_event. Chat does NOT bump
    # state_version: it changes nothing about the game, and bumping it would
    # invalidate every client's pending action for no reason.
    last = await db.scalar(
        select(GameEvent.seq)
        .where(GameEvent.game_id == game.id)
        .order_by(GameEvent.seq.desc())
        .limit(1)
    )

    event = GameEvent(
        game_id=game.id,
        seq=(last or 0) + 1,
        event_type=CHAT_EVENT,
        actor_player_id=seat.id,
        payload={"text": text.strip(), "display_name": seat.display_name},
        state_version_after=game.state_version,
    )
    db.add(event)
    await db.flush()
    return event