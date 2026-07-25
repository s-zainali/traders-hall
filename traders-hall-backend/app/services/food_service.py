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
    quantity: int,
    expected_state_version: int | None,
) -> Game:
    """Eat one or more food cards, extending food_due by their nutrition.

    Nutrition ADDS to whatever is left rather than resetting to it, so eating
    early is stockpiling rather than waste. That follows from calling the value
    an offset: two rice while three turns fed leaves you fed for seven, not two.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if quantity < 1:
        raise ActionError("VALIDATION_ERROR", "Quantity must be at least 1")

    card = await _card(db, card_type)
    if card.category != config.EDIBLE_CATEGORY:
        raise ActionError("NOT_EDIBLE", f"{card.title} is not food")
    if card.nutrition_turns < 1:
        raise ActionError("NOT_EDIBLE", f"{card.title} has no nutritional value")

    hand = await _hand_row(db, game, seat, card_type)
    # Free cards only: the rest are backing an open offer, or held as collateral
    # against a mortgage. You cannot eat your own collateral.
    available = hand.quantity - hand.reserved_quantity
    if available < quantity:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have only {available} free {card.title} to eat",
            available=available,
        )

    gained = card.nutrition_turns * quantity

    hand.quantity -= quantity
    (await _pool_row(db, game, card_type)).quantity += quantity
    seat.food_due += gained

    event = await _append_event(
        db, game,
        event_type="food.eaten",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "quantity": quantity,
            "nutrition_each": card.nutrition_turns,
            "turns_gained": gained,
            "food_due": seat.food_due,
        },
    )
    # No points move, so this is a pure card transfer: hand -> bank pool.
    _ledger(db, game, event, player_id=seat.id, entry_type="eat",
            card_type=card_type, card_delta=-quantity)
    _ledger(db, game, event, player_id=None, entry_type="eat",
            card_type=card_type, card_delta=quantity)

    return game