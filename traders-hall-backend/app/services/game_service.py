import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.user import User

MIN_PLAYERS = 2

# No I, O, 0 or 1 — these codes get read aloud and typed by hand.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
MAX_CODE_ATTEMPTS = 5


class GameError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


def _random_code() -> str:
    # secrets, not random: predictable codes would let anyone walk into games
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


async def _load(db: AsyncSession, *, code: str | None = None, game_id=None) -> Game | None:
    """Load a game WITH its players eagerly.

    selectinload matters in async: lazy loading a relationship needs I/O, and
    SQLAlchemy cannot do implicit I/O in async code — touching game.players on a
    lazily-loaded object raises MissingGreenlet instead of querying.
    """
    stmt = select(Game).options(selectinload(Game.players))
    stmt = stmt.where(Game.join_code == code) if code else stmt.where(Game.id == game_id)
    return await db.scalar(stmt)


async def create_game(db: AsyncSession, *, host: User, max_players: int) -> Game:
    for _ in range(MAX_CODE_ATTEMPTS):
        game = Game(
            join_code=_random_code(),
            host_user_id=host.id,
            max_players=max_players,
            status="lobby",
        )
        db.add(game)
        try:
            # flush sends the INSERT so the unique index is checked now, while
            # we can still retry, rather than at commit when it is too late
            await db.flush()
        except IntegrityError:
            await db.rollback()
            continue

        db.add(GamePlayer(
            game_id=game.id,
            user_id=host.id,
            seat_index=0,               # creator always takes seat 0
            display_name=host.display_name,
        ))
        await db.flush()
        await db.refresh(game, ["players"])
        return game

    raise GameError("CODE_GENERATION_FAILED", "Could not allocate a join code, try again")


async def join_game(db: AsyncSession, *, user: User, code: str) -> Game:
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")

    # Already seated? Return the game rather than erroring — this makes rejoining
    # after a refresh or a dropped connection a no-op instead of a failure.
    if any(p.user_id == user.id for p in game.players):
        return game

    if game.status != "lobby":
        raise GameError("GAME_ALREADY_STARTED", "That game has already started")
    if len(game.players) >= game.max_players:
        raise GameError("GAME_FULL", "That game is full")

    # lowest free seat, so leaving and rejoining does not leave gaps
    taken = {p.seat_index for p in game.players}
    seat = next(i for i in range(game.max_players) if i not in taken)

    db.add(GamePlayer(
        game_id=game.id,
        user_id=user.id,
        seat_index=seat,
        display_name=user.display_name,
    ))
    await db.flush()
    await db.refresh(game, ["players"])
    return game


async def leave_game(db: AsyncSession, *, user: User, code: str) -> None:
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")

    player = next((p for p in game.players if p.user_id == user.id), None)
    if player is None:
        raise GameError("NOT_A_PLAYER", "You are not in that game")

    if game.status == "lobby":
        await db.delete(player)          # in a lobby, leaving frees the seat
        await db.flush()
        await db.refresh(game, ["players"])

        if not game.players:
            game.status = "abandoned"    # last one out closes the room
            game.ended_at = datetime.now(UTC)
        elif game.host_user_id == user.id:
            # hand the host role to the next seat rather than orphaning the game
            game.host_user_id = game.players[0].user_id
    else:
        player.status = "resigned"       # mid-game, the seat stays for history
        player.left_at = datetime.now(UTC)


async def start_game(db: AsyncSession, *, user: User, code: str) -> Game:
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")
    if game.host_user_id != user.id:
        raise GameError("NOT_HOST", "Only the host can start the game")
    if game.status != "lobby":
        raise GameError("GAME_ALREADY_STARTED", "That game has already started")
    if len(game.players) < MIN_PLAYERS:
        raise GameError("NOT_ENOUGH_PLAYERS", f"Need at least {MIN_PLAYERS} players")

    game.status = "in_progress"
    game.started_at = datetime.now(UTC)
    game.state_version += 1
    return game

async def close_game(db: AsyncSession, *, user: User, code: str) -> None:
    """Host deletes the table outright, whatever state it is in."""
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")
    if game.host_user_id != user.id:
        raise GameError("NOT_HOST", "Only the host can delete the table")

    # No emptiness check any more: the host owns the table and may bin it with
    # players still seated. The frontend warns before confirming, since this
    # removes the game for everyone, not just the host.
    # game_players has ondelete=CASCADE, so seats go with it.
    await db.delete(game)


async def get_game(db: AsyncSession, *, code: str) -> Game:
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")
    return game


async def list_my_games(db: AsyncSession, *, user: User) -> list[Game]:
    stmt = (
        select(Game)
        .join(GamePlayer, GamePlayer.game_id == Game.id)
        .where(GamePlayer.user_id == user.id)
        .options(selectinload(Game.players))   # ← required
        .order_by(Game.created_at.desc())
    )
    return list(await db.scalars(stmt))