"""Eating: spending food cards to push back the hunger clock.

A meal is a player ACTION, not something upkeep does for you. That is a design
choice with teeth — forgetting to eat is a way to lose — so the server never
eats on your behalf, and the counter is visible on every panel.

Nutrition comes from card_types.nutrition_turns (rice 2, wheat 5) rather than
from a constant here, so rebalancing a food card is a migration and touches no
code. The card returns to the bank pool when eaten: it leaves your hand, but the
game's total card count is unchanged, which keeps the pool auditable.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import config
from app.models.game import Game
from app.models.user import User
from app.services.action_service import (
    ActionError,
    _append_event,
    _card,
    _check_version,
    _hand_row,
    _ledger,
    _lock_game,
    _pool_row,
    _require_turn,
    _seat_of,
)


async def eat(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    card_type: str,
    expected_state_version: int | None,
) -> Game:
    """Eat one food card, setting food_due UP TO its nutrition.

    Nutrition raises the counter TO its value rather than adding onto it: eating
    wheat with two turns left leaves you fed for five, not seven. Eating early
    therefore buys nothing, which is the point — food is a deadline you reset,
    not a resource you bank.

    max() rather than a plain assignment, so eating rice while five turns fed is
    a wasted card and not a self-inflicted penalty. Without it, snacking would
    shorten your own clock.

    One card at a time, for the same reason: a second card in the same meal
    cannot raise a ceiling the first already reached, so a quantity would only
    let players burn food for nothing.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    card = await _card(db, card_type)
    if card.category != config.EDIBLE_CATEGORY:
        raise ActionError("NOT_EDIBLE", f"{card.title} is not food")
    if card.nutrition_turns < 1:
        raise ActionError("NOT_EDIBLE", f"{card.title} has no nutritional value")

    hand = await _hand_row(db, game, seat, card_type)
    # Free cards only: the rest are backing an open offer, or held as collateral
    # against a mortgage. You cannot eat your own collateral.
    available = hand.quantity - hand.reserved_quantity
    if available < 1:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have no free {card.title} to eat",
            available=available,
        )

    before = seat.food_due
    hand.quantity -= 1
    (await _pool_row(db, game, card_type)).quantity += 1
    seat.food_due = max(seat.food_due, card.nutrition_turns)
    gained = seat.food_due - before

    event = await _append_event(
        db, game,
        event_type="food.eaten",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "quantity": 1,
            "nutrition_each": card.nutrition_turns,
            # Zero when the card was eaten while already better fed — worth
            # logging, because it is the player finding out it was wasted.
            "turns_gained": gained,
            "food_due": seat.food_due,
        },
    )
    # No points move, so this is a pure card transfer: hand -> bank pool.
    _ledger(db, game, event, player_id=seat.id, entry_type="eat",
            card_type=card_type, card_delta=-1)
    _ledger(db, game, event, player_id=None, entry_type="eat",
            card_type=card_type, card_delta=1)

    return game