"""Where players live, and how many rooms exist.

Capacity is derived, never stored. A player's total rooms is the sum over the
property cards in their hand of quantity times that card's `rooms`; occupancy is
the count of live tenancies plus themselves if they live in their own property.
Caching either number would mean invalidating it on every buy, sell, trade,
mortgage seizure and eviction — five paths that already exist — so it is
computed on read.

Mortgaged property is excluded from capacity. The card is collateral: letting a
room in it would promise a tenant something the bank can take away.

Four numbers that are easy to confuse:

    total      rooms the player owns
    occupied   rooms lived in right now
    pending    rooms promised by an open or claimed rent_out offer
    lettable   total - occupied - pending

`lettable` is the one that gates a new offer. Without subtracting pending, two
rent_out offers against a one-room house could both settle and the house would
end up housing two tenants.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_type import CardType
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.rental_agreement import RentalAgreement
from app.models.trade_offer import TradeOffer
from app.services.action_service import (
    ActionError,
    _append_event,
    _card,
    _check_version,
    _hand_row,
    _lock_game,
    _require_turn,
    _seat_of,
)

LIVE_OFFER_STATUSES = ("open", "claimed")


async def rooms_by_card(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> dict[str, int]:
    """Rooms this player owns, per property type, excluding mortgaged cards."""
    rows = (
        await db.execute(
            select(PlayerHand, CardType)
            .join(CardType, CardType.code == PlayerHand.card_type)
            .where(
                PlayerHand.game_id == game.id,
                PlayerHand.player_id == seat.id,
                CardType.rooms > 0,
            )
        )
    ).all()

    out: dict[str, int] = {}
    for hand, card in rows:
        # Free cards only: a mortgaged property is promised to the bank.
        free = hand.quantity - hand.reserved_quantity
        if free > 0:
            out[card.code] = free * card.rooms
    return out


async def occupancy_by_card(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> dict[str, int]:
    """Rooms of this player's property currently lived in.

    Counts live tenancies, plus the player themselves when they occupy their own
    property — an owner-occupier fills a room exactly as a tenant does, and
    forgetting that is how a house ends up housing two people.
    """
    rows = (
        await db.execute(
            select(RentalAgreement.card_type, func.count())
            .where(
                RentalAgreement.game_id == game.id,
                RentalAgreement.landlord_player_id == seat.id,
                RentalAgreement.status == "active",
            )
            .group_by(RentalAgreement.card_type)
        )
    ).all()

    out = {card_type: count for card_type, count in rows}

    if seat.residence_card_type is not None and seat.residence_landlord_id is None:
        code = seat.residence_card_type
        out[code] = out.get(code, 0) + 1

    return out


async def pending_by_card(
    db: AsyncSession,
    game: Game,
    seat: GamePlayer,
    *,
    exclude_offer_id=None,
) -> dict[str, int]:
    """Rooms already promised by a live rent_out offer.

    exclude_offer_id is for the settle path: when confirming an offer, that
    offer's own room must not count against its landlord, or the check it is
    about to pass would fail on itself.
    """
    stmt = (
        select(TradeOffer.offer_card_type, func.count())
        .where(
            TradeOffer.game_id == game.id,
            TradeOffer.poster_player_id == seat.id,
            TradeOffer.kind == "rent_out",
            TradeOffer.status.in_(LIVE_OFFER_STATUSES),
        )
        .group_by(TradeOffer.offer_card_type)
    )
    if exclude_offer_id is not None:
        stmt = stmt.where(TradeOffer.id != exclude_offer_id)

    rows = (await db.execute(stmt)).all()
    return {card_type: count for card_type, count in rows if card_type is not None}


async def lettable_by_card(
    db: AsyncSession,
    game: Game,
    seat: GamePlayer,
    *,
    exclude_offer_id=None,
) -> dict[str, int]:
    """Rooms this player could let right now, per property type.

    Floored at zero. Capacity can fall below occupancy without any tenancy
    ending — sell a mansion with a tenant in it, or have one seized to settle a
    defaulted loan — and a negative count would propagate into offer validation
    as a nonsense allowance.
    """
    owned = await rooms_by_card(db, game, seat)
    used = await occupancy_by_card(db, game, seat)
    promised = await pending_by_card(db, game, seat, exclude_offer_id=exclude_offer_id)
    return {
        code: max(0, total - used.get(code, 0) - promised.get(code, 0))
        for code, total in owned.items()
    }


async def room_summary(db: AsyncSession, game: Game, seat: GamePlayer) -> dict:
    """The capacity numbers the client needs to render housing."""
    owned = await rooms_by_card(db, game, seat)
    used = await occupancy_by_card(db, game, seat)
    promised = await pending_by_card(db, game, seat)

    total = sum(owned.values())
    # Clamped to capacity for display: the underlying numbers can cross when a
    # property leaves the hand, and "3 of 2 rooms used" is worse than a slightly
    # lossy 2 of 2.
    occupied = min(total, sum(used.values()))
    pending = min(max(0, total - occupied), sum(promised.values()))

    return {
        "rooms_total": total,
        "rooms_occupied": occupied,
        "rooms_pending": pending,
        "rooms_lettable": max(0, total - occupied - pending),
        "rooms_by_card": {
            code: max(0, count - used.get(code, 0) - promised.get(code, 0))
            for code, count in owned.items()
        },
    }


async def active_tenancy(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> RentalAgreement | None:
    """The agreement under which this player rents, if they rent at all."""
    return await db.scalar(
        select(RentalAgreement).where(
            RentalAgreement.game_id == game.id,
            RentalAgreement.tenant_player_id == seat.id,
            RentalAgreement.status == "active",
        )
    )


def is_housed(seat: GamePlayer) -> bool:
    return seat.residence_card_type is not None


async def move_in(
    db: AsyncSession,
    *,
    user,
    code: str,
    card_type: str,
    expected_state_version: int | None,
) -> Game:
    """Occupy a room in a property you own.

    Explicit rather than automatic on purchase: buying a tower to let all three
    rooms out is a legitimate strategy, and moving the owner in by default would
    silently cost them a room's rent.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if is_housed(seat):
        raise ActionError(
            "ALREADY_RESIDING",
            "Leave your current residence first",
            card_type=seat.residence_card_type,
        )

    card = await _card(db, card_type)
    if card.rooms < 1:
        raise ActionError("NOT_HABITABLE", f"{card.title} has no rooms")

    hand = await _hand_row(db, game, seat, card_type)
    if hand.quantity - hand.reserved_quantity < 1:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have no free {card.title} to live in",
        )

    lettable = await lettable_by_card(db, game, seat)
    if lettable.get(card_type, 0) < 1:
        raise ActionError(
            "NO_FREE_ROOM",
            f"Every room in your {card.title} is taken or promised",
            card_type=card_type,
        )

    seat.residence_card_type = card_type
    seat.residence_landlord_id = None

    await _append_event(
        db, game,
        event_type="residence.moved_in",
        actor_player_id=seat.id,
        payload={"card_type": card_type, "own_property": True},
    )
    return game


async def leave(
    db: AsyncSession,
    *,
    user,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Vacate the current residence.

    No penalty and no notice period, as specified. If the residence was rented,
    the tenancy ends here — which also frees the landlord's room, since capacity
    is derived from live agreements rather than stored.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if not is_housed(seat):
        raise ActionError("NO_RESIDENCE", "You do not live anywhere")

    card_type = seat.residence_card_type
    landlord_id = seat.residence_landlord_id

    agreement = await active_tenancy(db, game, seat)
    if agreement is not None:
        agreement.status = "ended"
        agreement.ended_at = func.now()

    seat.residence_card_type = None
    seat.residence_landlord_id = None
    # rent_due mirrors the tenancy's countdown, so it goes with it.
    seat.rent_due = 0

    await _append_event(
        db, game,
        event_type="residence.left",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "landlord_player_id": str(landlord_id) if landlord_id else None,
            "was_rented": agreement is not None,
        },
    )
    return game

free_rooms_by_card = lettable_by_card
