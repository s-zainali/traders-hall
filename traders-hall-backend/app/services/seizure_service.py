"""The landlord's choice, and the only way out of a frozen game.

A tenant who cannot pay rent but whose cards COULD cover it hands the decision to
their landlord: which cards to take. The game is stopped while that sits, so this
module is the one thing allowed to act on a frozen game — everything else is
turned away by _lock_game.

The tenant survives this. Their cards covered the debt, which is exactly the line
between "lost everything" and "out of the game": if the cards had not been enough
the elimination would already have happened, without a choice to make.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import cards
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.rental_agreement import RentalAgreement
from app.models.user import User
from app.services.action_service import (
    ActionError,
    _append_event,
    _check_version,
    _ledger,
    _lock_game,
    _seat_of,
)


async def pending(db: AsyncSession, game: Game) -> RentalAgreement | None:
    if game.phase != "seizure" or game.seizure_agreement_id is None:
        return None
    return await db.get(RentalAgreement, game.seizure_agreement_id)


async def seizable_hand(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> dict[str, int]:
    """What the landlord may choose from: free cards with a sell value.

    Reserved cards are excluded. A card promised to an open offer or held as
    mortgage collateral is already committed, and letting a landlord take it
    would break a promise made to somebody else.
    """
    hands = list(await db.scalars(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
        )
    ))

    out: dict[str, int] = {}
    for hand in hands:
        card = cards.get(hand.card_type)
        if card is None or card.sell_value < 1:
            continue
        free = hand.quantity - hand.reserved_quantity
        if free > 0:
            out[hand.card_type] = free
    return out


async def take_cards(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    picks: dict[str, int],
    expected_state_version: int | None,
) -> Game:
    """Settle the debt with the cards the landlord named.

    The picks must be worth AT LEAST the debt. They are allowed to be worth more
    — cards are indivisible and the bank gives no change, so a landlord owed 2
    who takes a tower gets 3 worth. What is not allowed is taking more cards than
    the debt needs: the landlord may not help themselves to a hand because rent
    was late.
    """
    game = await _lock_game(db, code, allow_frozen=True)
    landlord = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    agreement = await pending(db, game)
    if agreement is None:
        raise ActionError("NO_SEIZURE", "Nothing is waiting to be seized")
    if agreement.landlord_player_id != landlord.id:
        raise ActionError("NOT_LANDLORD", "That is not your tenancy")

    tenant = await db.get(GamePlayer, agreement.tenant_player_id)
    if tenant is None:
        raise ActionError("NO_SEIZURE", "That tenant is gone")

    debt = agreement.seizure_debt or 0
    available = await seizable_hand(db, game, tenant)

    if not picks:
        raise ActionError("NOTHING_PICKED", "Choose which cards to take")

    total = 0
    for card_code, qty in picks.items():
        if qty < 1:
            raise ActionError("VALIDATION_ERROR", "Quantities must be positive")
        card = cards.get(card_code)
        if card is None or card.sell_value < 1:
            raise ActionError("NOT_SEIZABLE", f"{card_code} has no value to seize")
        if available.get(card_code, 0) < qty:
            raise ActionError(
                "INSUFFICIENT_CARDS",
                f"They do not have {qty} free {card.title}",
                available=available.get(card_code, 0),
            )
        total += card.sell_value * qty

    if total < debt:
        raise ActionError(
            "DEBT_NOT_COVERED",
            f"That comes to {total}; the debt is {debt}",
            debt=debt,
            offered=total,
        )

    # No taking a spare card on top. Every pick has to be doing work: dropping
    # any single one of them must leave the debt uncovered.
    for card_code in picks:
        card = cards.get(card_code)
        if total - card.sell_value >= debt:
            raise ActionError(
                "TOO_MANY_CARDS",
                f"You are taking more than you are owed — drop a {card.title}",
                debt=debt,
                offered=total,
            )

    event = await _append_event(
        db, game,
        event_type="rent.seized",
        actor_player_id=landlord.id,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(tenant.id),
            "landlord_player_id": str(landlord.id),
            "debt": debt,
            "cards": picks,
            "value": total,
        },
    )

    for card_code, qty in picks.items():
        src = await db.scalar(
            select(PlayerHand).where(
                PlayerHand.game_id == game.id,
                PlayerHand.player_id == tenant.id,
                PlayerHand.card_type == card_code,
            )
        )
        dst = await db.scalar(
            select(PlayerHand).where(
                PlayerHand.game_id == game.id,
                PlayerHand.player_id == landlord.id,
                PlayerHand.card_type == card_code,
            )
        )
        if dst is None:
            dst = PlayerHand(
                game_id=game.id, player_id=landlord.id,
                card_type=card_code, quantity=0, reserved_quantity=0,
            )
            db.add(dst)
            await db.flush()

        src.quantity -= qty
        dst.quantity += qty

        _ledger(db, game, event, player_id=tenant.id, entry_type="rent_seizure",
                card_type=card_code, card_delta=-qty)
        _ledger(db, game, event, player_id=landlord.id, entry_type="rent_seizure",
                card_type=card_code, card_delta=qty)

    # Paid, so the tenancy continues and the rent clock restarts. The tenant keeps
    # the room: they settled, just not in points.
    agreement.seizure_debt = None
    agreement.turns_until_due = agreement.interval_turns
    tenant.rent_due = agreement.interval_turns

    game.phase = "main"
    game.seizure_agreement_id = None

    return game


async def forgive(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Let it go. The debt is written off and the tenancy carries on.

    A landlord should not be able to stall the whole game by refusing to choose,
    and forcing a seizure they do not want is worse than letting them waive it.
    """
    game = await _lock_game(db, code, allow_frozen=True)
    landlord = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    agreement = await pending(db, game)
    if agreement is None:
        raise ActionError("NO_SEIZURE", "Nothing is waiting to be seized")
    if agreement.landlord_player_id != landlord.id:
        raise ActionError("NOT_LANDLORD", "That is not your tenancy")

    tenant = await db.get(GamePlayer, agreement.tenant_player_id)

    debt = agreement.seizure_debt or 0
    agreement.seizure_debt = None
    agreement.turns_until_due = agreement.interval_turns
    if tenant is not None:
        tenant.rent_due = agreement.interval_turns

    game.phase = "main"
    game.seizure_agreement_id = None

    await _append_event(
        db, game,
        event_type="rent.seizure_waived",
        actor_player_id=landlord.id,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(agreement.tenant_player_id),
            "landlord_player_id": str(landlord.id),
            "debt": debt,
        },
    )
    return game