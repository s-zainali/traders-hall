"""Player actions: buy from the bank, sell to the bank, end a turn.

Every mutation follows the same lifecycle:

    lock the game row  ->  version check  ->  validate  ->  mutate
    ->  ledger  ->  append event  ->  bump state_version

The lock is what makes it safe. `SELECT ... FOR UPDATE` on `games` serialises
every mutation for that game; games are independent, so this scales by game with
no distributed locking. It is a DATABASE lock, not an asyncio one — an in-process
lock is worthless the moment you run a second uvicorn worker.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_type import CardType
from app.models.game import Game
from app.models.game_card_pool import GameCardPool
from app.models.game_event import GameEvent
from app.models.game_player import GamePlayer
from app.models.ledger_entry import LedgerEntry
from app.models.player_hand import PlayerHand
from app.models.user import User


class ActionError(Exception):
    def __init__(self, code: str, message: str, **details):
        self.code = code
        self.message = message
        self.details = details


# ── shared plumbing ──────────────────────────────────────────────────


async def _lock_game(db: AsyncSession, code: str) -> Game:
    """Load the game and hold a row lock for the rest of the transaction.

    with_for_update() blocks any other request touching this game until we
    commit. Everything after this point can therefore assume nothing moves
    underneath it.
    """
    game = await db.scalar(
        select(Game).where(Game.join_code == code.upper()).with_for_update()
    )
    if game is None:
        raise ActionError("GAME_NOT_FOUND", "No game with that code")
    if game.status != "in_progress":
        raise ActionError("GAME_NOT_RUNNING", "That game is not in progress")
    return game


async def _seat_of(db: AsyncSession, game: Game, user: User) -> GamePlayer:
    seat = await db.scalar(
        select(GamePlayer).where(
            GamePlayer.game_id == game.id, GamePlayer.user_id == user.id
        )
    )
    if seat is None:
        raise ActionError("NOT_A_PLAYER", "You are not in that game")
    if seat.status != "active":
        raise ActionError("PLAYER_ELIMINATED", "You are no longer in this game")
    return seat


def _check_version(game: Game, expected: int | None) -> None:
    """Optimistic concurrency.

    Solves a different problem from the row lock: not two writers racing, but
    ONE client acting on a view of the world that has since changed. You click
    "buy 3 rice" while an opponent drains the pool; this catches it and the
    client resyncs instead of silently doing something you did not intend.
    """
    if expected is not None and expected != game.state_version:
        raise ActionError(
            "STATE_VERSION_CONFLICT",
            "The game moved on before that action arrived",
            state_version=game.state_version,
        )


def _require_turn(game: Game, seat: GamePlayer) -> None:
    if game.current_player_id != seat.id:
        raise ActionError("NOT_YOUR_TURN", "It is not your turn")


async def _append_event(
    db: AsyncSession,
    game: Game,
    *,
    event_type: str,
    actor_player_id: uuid.UUID | None,
    payload: dict,
) -> GameEvent:
    """Bump state_version and write the next event in sequence.

    seq is derived from the current maximum inside the locked transaction, so it
    cannot collide — and the unique constraint on (game_id, seq) is the backstop
    if that reasoning is ever wrong.
    """
    game.state_version += 1

    last = await db.scalar(
        select(GameEvent.seq)
        .where(GameEvent.game_id == game.id)
        .order_by(GameEvent.seq.desc())
        .limit(1)
    )

    event = GameEvent(
        game_id=game.id,
        seq=(last or 0) + 1,
        event_type=event_type,
        actor_player_id=actor_player_id,
        payload=payload,
        state_version_after=game.state_version,
    )
    db.add(event)
    await db.flush()
    return event


def _ledger(
    db: AsyncSession,
    game: Game,
    event: GameEvent,
    *,
    player_id: uuid.UUID | None,
    entry_type: str,
    points_delta: int = 0,
    card_type: str | None = None,
    card_delta: int = 0,
) -> None:
    db.add(LedgerEntry(
        game_id=game.id,
        event_id=event.id,
        player_id=player_id,
        entry_type=entry_type,
        points_delta=points_delta,
        card_type=card_type,
        card_delta=card_delta,
        turn_number=game.turn_number,
    ))


async def _hand_row(db: AsyncSession, game: Game, seat: GamePlayer, card_type: str) -> PlayerHand:
    row = await db.scalar(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
            PlayerHand.card_type == card_type,
        )
    )
    if row is None:
        # _deal creates a row per card type per player, including zeroes, so a
        # missing row means the card code itself is wrong.
        raise ActionError("UNKNOWN_CARD_TYPE", f"No such card type: {card_type}")
    return row


async def _pool_row(db: AsyncSession, game: Game, card_type: str) -> GameCardPool:
    row = await db.scalar(
        select(GameCardPool).where(
            GameCardPool.game_id == game.id, GameCardPool.card_type == card_type
        )
    )
    if row is None:
        raise ActionError("UNKNOWN_CARD_TYPE", f"No such card type: {card_type}")
    return row


async def _card(db: AsyncSession, card_type: str) -> CardType:
    card = await db.get(CardType, card_type)
    if card is None:
        raise ActionError("UNKNOWN_CARD_TYPE", f"No such card type: {card_type}")
    return card


# ── actions ──────────────────────────────────────────────────────────


async def buy_from_bank(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    card_type: str,
    quantity: int,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if quantity < 1:
        raise ActionError("VALIDATION_ERROR", "Quantity must be at least 1")

    card = await _card(db, card_type)
    if card_type == "point":
        # Points are currency, not merchandise. Buying them with points is
        # either a no-op or an exploit depending on the price.
        raise ActionError("NOT_PURCHASABLE", "Points cannot be bought")

    total = card.base_cost * quantity

    pool = await _pool_row(db, game, card_type)
    if pool.quantity < quantity:
        raise ActionError(
            "INSUFFICIENT_BANK_STOCK",
            f"The bank has only {pool.quantity} left",
            available=pool.quantity,
        )
    if seat.points < total:
        raise ActionError(
            "INSUFFICIENT_POINTS",
            f"That costs {total} points; you have {seat.points}",
            required=total,
            available=seat.points,
        )

    hand = await _hand_row(db, game, seat, card_type)

    pool.quantity -= quantity
    hand.quantity += quantity
    seat.points -= total
    # The bank's own point stock grows by what it was paid — that is what keeps
    # SUM(points) across players and bank constant.
    (await _pool_row(db, game, "point")).quantity += total

    event = await _append_event(
        db, game,
        event_type="cards.bought",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "quantity": quantity,
            "unit_cost": card.base_cost,
            "total_cost": total,
        },
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="buy",
            points_delta=-total, card_type=card_type, card_delta=quantity)
    _ledger(db, game, event, player_id=None, entry_type="buy",
            points_delta=total, card_type=card_type, card_delta=-quantity)

    return game


async def sell_to_bank(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    card_type: str,
    quantity: int,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if quantity < 1:
        raise ActionError("VALIDATION_ERROR", "Quantity must be at least 1")

    card = await _card(db, card_type)
    if card_type == "point":
        raise ActionError("NOT_SELLABLE", "Points cannot be sold")

    total = card.sell_value * quantity

    hand = await _hand_row(db, game, seat, card_type)
    # available, not raw quantity: reserved cards are already promised to an
    # open market offer. The column is unused today but the check is free now
    # and easy to forget later.
    available = hand.quantity - hand.reserved_quantity
    if available < quantity:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have only {available} to sell",
            available=available,
        )

    bank_points = await _pool_row(db, game, "point")
    if bank_points.quantity < total:
        raise ActionError(
            "BANK_OUT_OF_POINTS",
            "The bank cannot cover that sale",
            available=bank_points.quantity,
        )

    pool = await _pool_row(db, game, card_type)

    hand.quantity -= quantity
    pool.quantity += quantity
    seat.points += total
    bank_points.quantity -= total

    event = await _append_event(
        db, game,
        event_type="cards.sold",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "quantity": quantity,
            "unit_value": card.sell_value,
            "total_value": total,
        },
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="sell",
            points_delta=total, card_type=card_type, card_delta=-quantity)
    _ledger(db, game, event, player_id=None, entry_type="sell",
            points_delta=-total, card_type=card_type, card_delta=quantity)

    return game


async def end_turn(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Pass to the next active seat.

    No upkeep yet — food, rent, interest and elimination all land in a later
    step. This exists now because turn-gating buy and sell makes the game
    unplayable without it: seat 0 would act forever and nobody else ever could.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    seats = list(await db.scalars(
        select(GamePlayer)
        .where(GamePlayer.game_id == game.id, GamePlayer.status == "active")
        .order_by(GamePlayer.seat_index)
    ))

    if not seats:
        game.status = "completed"
        game.ended_at = datetime.now(UTC)
        game.current_player_id = None
        await _append_event(db, game, event_type="game.ended",
                            actor_player_id=None, payload={"reason": "no_active_players"})
        return game

    # Wrap to the next seat by POSITION in the active list, not by seat_index +
    # 1 — resignations leave gaps, and index arithmetic would land on an empty
    # or resigned chair.
    idx = next((i for i, p in enumerate(seats) if p.id == seat.id), -1)
    nxt = seats[(idx + 1) % len(seats)]

    # A full lap means a new round.
    if nxt.seat_index <= seat.seat_index:
        game.turn_number += 1

    game.current_player_id = nxt.id
    game.phase = "main"

    await _append_event(
        db, game,
        event_type="turn.ended",
        actor_player_id=seat.id,
        payload={"next_player_id": str(nxt.id), "turn_number": game.turn_number},
    )
    return game