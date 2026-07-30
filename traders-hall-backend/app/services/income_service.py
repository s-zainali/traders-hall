"""Income: two dice, once a round, paid out of the bank.

Points come from the bank's pile rather than appearing, so the invariant that
nothing is created holds here as it does everywhere else. That has a consequence
worth knowing: the bank can run dry, and when it does income pays what is left
and logs the shortfall rather than minting the difference.

The roll is a player action, not something upkeep does. Rolling is the one moment
each round that is purely theirs, and taking it away would make the dice a number
that simply appears.
"""

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import config
from app.models.game import Game
from app.models.user import User
from app.services.action_service import (
    ActionError,
    _append_event,
    _check_version,
    _ledger,
    _lock_game,
    _pool_row,
    _require_turn,
    _seat_of,
)


def payout_for(total: int) -> int:
    """floor(sum / divisor).

    The SUM, deliberately, not each die. 2-12 is a bell curve centred on 7, so
    the common roll pays 1 and only the tails pay 0 or 3. Dividing each die
    separately would turn both into near coin-flips and flatten the curve the
    second die exists to create.
    """
    return total // config.INCOME_DIVISOR


def roll_dice() -> list[int]:
    """Two dice from the system CSPRNG.

    secrets rather than random: random is seeded deterministically and its stream
    is reconstructable from observed output, which for a value players are paid is
    a thing somebody would eventually try.
    """
    return [
        secrets.randbelow(config.INCOME_DIE_FACES) + 1
        for _ in range(config.INCOME_DICE)
    ]


async def collect(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Roll for income and take it from the bank."""
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    # income_round holds the turn_number of the last roll, and turn_number moves
    # once per lap — so this is "already rolled this round" with nothing to reset.
    if seat.income_round == game.turn_number:
        raise ActionError(
            "ALREADY_ROLLED",
            "You have already taken your income this round",
            round=game.turn_number,
        )

    dice = roll_dice()
    total = sum(dice)
    earned = payout_for(total)

    bank = await _pool_row(db, game, "point")
    # The bank pays what it has. A short payout is a real state of the game, not
    # an error, and minting the difference would break the one invariant every
    # other path is careful about.
    paid = min(earned, bank.quantity)
    shortfall = earned - paid

    if paid > 0:
        bank.quantity -= paid
        seat.points += paid

    seat.income_round = game.turn_number
    seat.last_die_a = dice[0]
    seat.last_die_b = dice[1] if len(dice) > 1 else None

    event = await _append_event(
        db, game,
        event_type="income.rolled",
        actor_player_id=seat.id,
        payload={
            "dice": dice,
            "total": total,
            "earned": earned,
            "paid": paid,
            "shortfall": shortfall,
        },
    )

    if paid > 0:
        _ledger(db, game, event, player_id=seat.id, entry_type="income",
                points_delta=paid)
        _ledger(db, game, event, player_id=None, entry_type="income",
                points_delta=-paid)

    return game