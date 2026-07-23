import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain import config
from app.models.card_type import CardType
from app.models.game import Game
from app.models.game_card_pool import GameCardPool
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.user import User

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
            phase="lobby",
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

    was_current = game.current_player_id == player.id

    if game.status == "lobby":
        await db.delete(player)          # in a lobby, leaving frees the seat
        await db.flush()
        await db.refresh(game, ["players"])
    else:
        player.status = "resigned"       # mid-game the seat stays, for history
        player.left_at = datetime.now(UTC)

    # Everyone still holding a live seat, excluding whoever just left. Computed
    # AFTER the mutation so it is correct in both branches — mid-game the row is
    # still present, just resigned, so filtering on user_id alone would keep it.
    remaining = [
        p for p in game.players
        if p.user_id != user.id and p.status == "active"
    ]

    if not remaining:
        game.status = "abandoned" if game.status == "lobby" else "completed"
        game.ended_at = datetime.now(UTC)
        game.current_player_id = None
    else:
        if game.host_user_id == user.id:
            # hand the table to the next seat rather than orphaning it
            game.host_user_id = remaining[0].user_id
        # Someone resigning on their own turn would otherwise leave the game
        # pointing at a player who can no longer act — a permanent stall.
        if was_current:
            game.current_player_id = remaining[0].id


async def start_game(db: AsyncSession, *, user: User, code: str) -> Game:
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")
    if game.host_user_id != user.id:
        raise GameError("NOT_HOST", "Only the host can start the game")
    if game.status != "lobby":
        raise GameError("GAME_ALREADY_STARTED", "That game has already started")
    if len(game.players) < config.MIN_PLAYERS:
        raise GameError("NOT_ENOUGH_PLAYERS", f"Need at least {config.MIN_PLAYERS} players")

    await _deal(db, game)

    game.status = "in_progress"
    game.started_at = datetime.now(UTC)
    game.turn_number = 1
    game.current_player_id = game.players[0].id     # seat 0 opens
    game.phase = "main"
    game.state_version += 1
    return game


async def _deal(db: AsyncSession, game: Game) -> None:
    """Seed the bank and deal opening hands.

    Runs inside the caller's transaction, which is the point: a game is never
    left half-dealt. If any part of this fails the whole start fails and the
    game stays in lobby.
    """
    player_count = len(game.players)

    # Every known card type gets a hand row, including ones a player has none
    # of. Rows at zero are kept deliberately — a sale can then be
    # `UPDATE ... WHERE quantity >= :n`, using the row's existence as a
    # guarantee, with no upsert and no gap between checking and writing.
    all_codes = list(await db.scalars(select(CardType.code)))

    for card_type, quantity in config.bank_pool_for(player_count).items():
        db.add(GameCardPool(game_id=game.id, card_type=card_type, quantity=quantity))

    for player in game.players:
        player.points = config.STARTING_POINTS
        player.food_due = config.FOOD_INTERVAL_TURNS
        player.rent_due = config.RENT_INTERVAL_TURNS

        for card_type in all_codes:
            db.add(PlayerHand(
                game_id=game.id,
                player_id=player.id,
                card_type=card_type,
                quantity=config.STARTING_HAND.get(card_type, 0),
            ))

    await db.flush()


async def close_game(db: AsyncSession, *, user: User, code: str) -> None:
    """Host deletes the table outright, whatever state it is in."""
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")
    if game.host_user_id != user.id:
        raise GameError("NOT_HOST", "Only the host can delete the table")

    # No emptiness check: the host owns the table and may bin it with players
    # still seated. The frontend names the consequence before confirming.
    # Everything below hangs off game_id with ondelete=CASCADE, so seats, pools
    # and hands all go with it — enforced by Postgres, not by remembering to.
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
        .options(selectinload(Game.players))
        .order_by(Game.created_at.desc())
    )
    return list(await db.scalars(stmt))


async def get_game_state(db: AsyncSession, *, user: User, code: str) -> dict:
    """Everything one player needs to render the table.

    Returned as a plain dict rather than ORM objects: the response draws on four
    tables and splits into a public part and a private one, a shape no single
    table has. app/services/projection.py turns it into the response model.
    """
    game = await _load(db, code=code.upper())
    if game is None:
        raise GameError("GAME_NOT_FOUND", "No game with that code")

    me = next((p for p in game.players if p.user_id == user.id), None)
    if me is None:
        raise GameError("NOT_A_PLAYER", "You are not in that game")

    if game.status == "lobby":
        raise GameError("GAME_NOT_STARTED", "That game has not started yet")

    pools = {
        row.card_type: row.quantity
        for row in await db.scalars(
            select(GameCardPool).where(GameCardPool.game_id == game.id)
        )
    }

    # ONE query for every hand in the game, grouped in Python. A query per
    # player would be a needless N+1 for a table of at most four.
    hands: dict[uuid.UUID, dict[str, int]] = {}
    for row in await db.scalars(select(PlayerHand).where(PlayerHand.game_id == game.id)):
        hands.setdefault(row.player_id, {})[row.card_type] = row.quantity

    return {"game": game, "pools": pools, "hands": hands, "me": me}