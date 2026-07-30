"""Elimination: taking a player out and settling what they leave behind.

Three ways to go, and they differ only in who collects:

    starvation                 the bank
    loan or mortgage default   the bank, once cards still cannot cover it
    rent default               the landlord

So one function does the work and takes a creditor. None means the bank.

Bank seniority is absolute: a mortgaged card is collateral the bank already has a
prior claim on, so it goes back to the pool before a landlord takes anything.
Without that a landlord could walk away with a card the bank was owed, and the
mortgage would be left pointing at a card nobody holds.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import cards
from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.rental_agreement import RentalAgreement
from app.services.action_service import _append_event, _ledger, _pool_row


async def seizable_value(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> int:
    """What this player's free cards are worth at bank sell prices.

    Used to decide whether a debt can be covered at all, which is what separates
    "they lose everything and survive" from "they are out". Reserved cards are
    excluded: they are already promised to an open offer or held as collateral,
    so they cannot also be sold to clear a different debt.
    """
    hands = list(await db.scalars(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
        )
    ))

    total = 0
    for hand in hands:
        card = cards.get(hand.card_type)
        if card is None or card.sell_value < 1:
            continue
        free = hand.quantity - hand.reserved_quantity
        if free > 0:
            total += free * card.sell_value
    return total


async def _return_mortgage_to_bank(
    db: AsyncSession, game: Game, seat: GamePlayer, event
) -> str | None:
    """Give the bank its collateral back before anyone else is paid.

    Returns the card code it took, so the caller can log it. The card leaves the
    hand and the reservation with it, which is what keeps reserved <= quantity.
    """
    if seat.mortgage_outstanding <= 0 or seat.mortgage_card_type is None:
        return None

    code = seat.mortgage_card_type

    hand = await db.scalar(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
            PlayerHand.card_type == code,
        )
    )
    if hand is not None and hand.quantity > 0:
        hand.quantity -= 1
        hand.reserved_quantity = max(0, hand.reserved_quantity - 1)
        (await _pool_row(db, game, code)).quantity += 1

        _ledger(db, game, event, player_id=seat.id, entry_type="eliminate_collateral",
                card_type=code, card_delta=-1)
        _ledger(db, game, event, player_id=None, entry_type="eliminate_collateral",
                card_type=code, card_delta=1)

    seat.mortgage_card_type = None
    seat.mortgage_outstanding = 0
    seat.mortgage_due = 0
    return code


async def _hand_over_estate(
    db: AsyncSession,
    game: Game,
    seat: GamePlayer,
    creditor: GamePlayer | None,
    event,
) -> dict:
    """Move every remaining point and card to whoever is owed.

    A player creditor receives cards into their hand, so they can put the
    property back on the market themselves. The bank receives them into the pool,
    which is the same thing by another route: they become buyable again.
    """
    moved_cards: dict[str, int] = {}

    points = seat.points
    if points > 0:
        seat.points = 0
        seat.reserved_points = 0
        if creditor is None:
            (await _pool_row(db, game, "point")).quantity += points
            _ledger(db, game, event, player_id=seat.id, entry_type="eliminate",
                    points_delta=-points)
            _ledger(db, game, event, player_id=None, entry_type="eliminate",
                    points_delta=points)
        else:
            creditor.points += points
            _ledger(db, game, event, player_id=seat.id, entry_type="eliminate",
                    points_delta=-points)
            _ledger(db, game, event, player_id=creditor.id, entry_type="eliminate",
                    points_delta=points)

    hands = list(await db.scalars(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
        )
    ))

    for hand in hands:
        if hand.quantity < 1:
            continue
        qty, code = hand.quantity, hand.card_type
        hand.quantity = 0
        hand.reserved_quantity = 0
        moved_cards[code] = moved_cards.get(code, 0) + qty

        if creditor is None:
            (await _pool_row(db, game, code)).quantity += qty
            _ledger(db, game, event, player_id=seat.id, entry_type="eliminate",
                    card_type=code, card_delta=-qty)
            _ledger(db, game, event, player_id=None, entry_type="eliminate",
                    card_type=code, card_delta=qty)
        else:
            target = await db.scalar(
                select(PlayerHand).where(
                    PlayerHand.game_id == game.id,
                    PlayerHand.player_id == creditor.id,
                    PlayerHand.card_type == code,
                )
            )
            if target is None:
                target = PlayerHand(
                    game_id=game.id, player_id=creditor.id,
                    card_type=code, quantity=0, reserved_quantity=0,
                )
                db.add(target)
                await db.flush()
            target.quantity += qty
            _ledger(db, game, event, player_id=seat.id, entry_type="eliminate",
                    card_type=code, card_delta=-qty)
            _ledger(db, game, event, player_id=creditor.id, entry_type="eliminate",
                    card_type=code, card_delta=qty)

    return moved_cards


async def _break_tenancies(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> list[str]:
    """End every tenancy this player is party to and turn the tenants out.

    A landlord's contracts die with them: the property is changing hands, so the
    agreement has no landlord to point at. Tenants are evicted rather than left
    in place — the new owner never agreed to house them, and a tenancy nobody
    consented to is not a tenancy.

    Returns the ids of the players turned out, so the caller can log who this
    just made homeless. Their own clocks start biting immediately, which is how
    one elimination can cascade into another.
    """
    evicted: list[str] = []

    agreements = list(await db.scalars(
        select(RentalAgreement).where(
            RentalAgreement.game_id == game.id,
            RentalAgreement.status == "active",
        )
    ))

    for agreement in agreements:
        is_landlord = agreement.landlord_player_id == seat.id
        is_tenant = agreement.tenant_player_id == seat.id
        if not (is_landlord or is_tenant):
            continue

        agreement.status = "ended"
        agreement.ended_at = datetime.now(UTC)
        agreement.moveout_status = None
        agreement.moveout_buyout = None
        agreement.moveout_turn = None

        if is_landlord:
            tenant = await db.get(GamePlayer, agreement.tenant_player_id)
            if tenant is not None and tenant.status == "active":
                tenant.residence_card_type = None
                tenant.residence_landlord_id = None
                tenant.rent_due = 0
                evicted.append(str(tenant.id))

    seat.residence_card_type = None
    seat.residence_landlord_id = None
    seat.rent_due = 0
    return evicted


async def eliminate(
    db: AsyncSession,
    game: Game,
    seat: GamePlayer,
    *,
    reason: str,
    creditor: GamePlayer | None = None,
) -> None:
    """Take a player out and settle their estate.

    Order matters and is not arbitrary:

      1. the bank reclaims its collateral, ahead of every other claim
      2. what is left goes to the creditor, or to the bank if there is none
      3. tenancies break and tenants are turned out
      4. offers and claims are released
      5. the turn moves on if it was theirs
      6. the match ends if nobody is left to play

    Debts are cleared rather than carried: there is no one left to collect from.
    """
    event = await _append_event(
        db, game,
        event_type="player.eliminated",
        actor_player_id=None,
        payload={
            "player_id": str(seat.id),
            "reason": reason,
            "creditor_player_id": str(creditor.id) if creditor else None,
            # filled in below, once the estate has actually moved
            "collateral_to_bank": None,
            "cards": {},
            "evicted": [],
        },
    )

    collateral = await _return_mortgage_to_bank(db, game, seat, event)
    moved = await _hand_over_estate(db, game, seat, creditor, event)
    evicted = await _break_tenancies(db, game, seat)

    seat.loan_outstanding = 0
    seat.loan_due = 0
    seat.food_due = 0
    seat.status = "eliminated"
    seat.left_at = datetime.now(UTC)

    # Imported here: offer_service reaches into action_service for the same
    # transaction kernel this module uses, and importing it at module level
    # closes a cycle.
    from app.services.offer_service import release_offers_for

    await release_offers_for(db, game, seat)

    # JSONB is not mutation-tracked, so the whole dict is reassigned rather than
    # updated in place — mutating it would be dropped silently at flush.
    event.payload = {
        **event.payload,
        "collateral_to_bank": collateral,
        "cards": moved,
        "evicted": evicted,
    }

    await _advance_turn_past(db, game, seat)
    await check_last_standing(db, game)


async def _advance_turn_past(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> None:
    """Hand the turn on if the eliminated player was holding it.

    Without this the game stops: current_player_id points at somebody who can no
    longer act, and nothing else moves it.
    """
    if game.current_player_id != seat.id:
        return

    remaining = list(await db.scalars(
        select(GamePlayer)
        .where(
            GamePlayer.game_id == game.id,
            GamePlayer.status == "active",
            GamePlayer.id != seat.id,
        )
        .order_by(GamePlayer.seat_index)
    ))

    if not remaining:
        game.current_player_id = None
        return

    # The next active seat by index, wrapping — resignations and eliminations
    # leave gaps, so this cannot be seat_index + 1.
    nxt = next(
        (p for p in remaining if p.seat_index > seat.seat_index),
        remaining[0],
    )
    game.current_player_id = nxt.id
    game.phase = "main"


async def check_last_standing(db: AsyncSession, game: Game) -> GamePlayer | None:
    """End the match when one player is left, or none.

    Returns the winner if there is one. Called after every elimination rather
    than on a timer, because an elimination is the only thing that can produce a
    winner.
    """
    if game.status != "in_progress":
        return None

    active = list(await db.scalars(
        select(GamePlayer).where(
            GamePlayer.game_id == game.id,
            GamePlayer.status == "active",
        )
    ))

    if len(active) > 1:
        return None

    winner = active[0] if active else None

    game.status = "completed"
    game.phase = "ended"
    game.ended_at = datetime.now(UTC)
    game.current_player_id = None

    await _append_event(
        db, game,
        event_type="game.ended",
        actor_player_id=None,
        payload={
            "reason": "last_standing" if winner else "no_active_players",
            "winner_player_id": str(winner.id) if winner else None,
            "winner_name": winner.display_name if winner else None,
        },
    )
    return winner