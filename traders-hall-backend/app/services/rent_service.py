"""Tenancies: starting them when a rent offer settles, and charging rent.

Rent moves player to player and never through the bank, so a payment is two
ledger rows that sum to zero and the bank's point pool is untouched.

The clock belongs to the TENANT. turns_until_due counts down when the tenant
ends a turn, not the landlord — a tenant would otherwise pay on someone else's
schedule, and a landlord with three tenants would collect three times a lap
while each tenant paid once. game_players.rent_due mirrors the countdown purely
so the panel can render it without a join; the agreement is the source of truth
and this module keeps the mirror in step.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.rental_agreement import RentalAgreement
from app.services.action_service import ActionError, _append_event, _ledger


async def open_agreement(
    db: AsyncSession,
    game: Game,
    *,
    landlord: GamePlayer,
    tenant: GamePlayer,
    card_type: str,
    rent_points: int,
    interval_turns: int,
) -> RentalAgreement:
    """Start a tenancy and move the tenant in.

    Called from offer_service at settle time for both rent kinds, which differ
    only in who posted: for rent_out the landlord posted, for rent_ask the
    tenant did. By this point the roles are known, so the agreement is built the
    same way either way.

    The first payment falls due after a full interval — nothing is owed on the
    day you move in.
    """
    if tenant.residence_card_type is not None:
        raise ActionError(
            "ALREADY_RESIDING",
            "That player already lives somewhere",
            card_type=tenant.residence_card_type,
        )

    agreement = RentalAgreement(
        game_id=game.id,
        landlord_player_id=landlord.id,
        tenant_player_id=tenant.id,
        card_type=card_type,
        rent_points=rent_points,
        interval_turns=interval_turns,
        turns_until_due=interval_turns,
        status="active",
        created_turn=game.turn_number,
    )
    db.add(agreement)

    tenant.residence_card_type = card_type
    tenant.residence_landlord_id = landlord.id
    tenant.rent_due = interval_turns

    await db.flush()
    return agreement


async def active_for_tenant(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> RentalAgreement | None:
    return await db.scalar(
        select(RentalAgreement).where(
            RentalAgreement.game_id == game.id,
            RentalAgreement.tenant_player_id == seat.id,
            RentalAgreement.status == "active",
        )
    )


async def end_agreement(
    db: AsyncSession,
    game: Game,
    agreement: RentalAgreement,
    *,
    reason: str,
    evict: bool = True,
) -> None:
    """Close a tenancy, optionally turning the tenant out.

    Ended agreements are kept rather than deleted: they are the record of who
    lived where, and the events that reference them outlive them. Closing one
    frees the landlord's room automatically, because capacity counts live
    agreements rather than storing a number.
    """
    agreement.status = "ended"
    agreement.ended_at = datetime.now(UTC)

    if evict:
        tenant = await db.get(GamePlayer, agreement.tenant_player_id)
        if tenant is not None:
            tenant.residence_card_type = None
            tenant.residence_landlord_id = None
            tenant.rent_due = 0

    await _append_event(
        db, game,
        event_type="tenancy.ended",
        actor_player_id=None,
        payload={
            "agreement_id": str(agreement.id),
            "tenant_player_id": str(agreement.tenant_player_id),
            "landlord_player_id": str(agreement.landlord_player_id),
            "card_type": agreement.card_type,
            "reason": reason,
        },
    )


async def tick(db: AsyncSession, game: Game, seat: GamePlayer) -> None:
    """Advance this tenant's rent clock and collect if it has run out.

    No-op for anyone who is not renting: owner-occupiers and the homeless have
    no agreement, and rent_due means nothing for them.
    """
    agreement = await active_for_tenant(db, game, seat)
    if agreement is None:
        # Keep the mirror honest — a stale rent_due on a player who has since
        # moved into their own place would render a countdown to nothing.
        seat.rent_due = 0
        return

    if agreement.turns_until_due > 0:
        agreement.turns_until_due -= 1

    seat.rent_due = agreement.turns_until_due

    if agreement.turns_until_due > 0:
        return

    await _charge(db, game, seat, agreement)


async def _charge(
    db: AsyncSession,
    game: Game,
    tenant: GamePlayer,
    agreement: RentalAgreement,
) -> None:
    """Take one payment, or record that it could not be taken."""
    landlord = await db.get(GamePlayer, agreement.landlord_player_id)
    rent = agreement.rent_points

    # A landlord who has left the game cannot collect. The tenancy dies with
    # them rather than charging rent into the void, and the tenant keeps the
    # room — losing your home because your landlord quit would be a punishment
    # for someone else's action.
    if landlord is None or landlord.status != "active":
        await end_agreement(db, game, agreement, reason="landlord_gone", evict=False)
        tenant.residence_landlord_id = None
        tenant.rent_due = 0
        return

    # Reserved points are promised to an open market claim and cannot be spent
    # on rent, exactly as they cannot be spent on a purchase.
    available = tenant.points - tenant.reserved_points

    if available < rent:
        # The counter stays at zero so the debt is still visible and will be
        # retried on the tenant's next turn.
        #
        # SEIZURE IS NOT IMPLEMENTED. The rule is that the tenant goes bankrupt
        # and the LANDLORD chooses which cards to take, which needs a pending
        # obligation the game freezes on while another player decides — plus
        # elimination when the cards do not cover the debt. None of that exists
        # yet, so this records the miss and changes nothing else rather than
        # inventing a different penalty.
        await _append_event(
            db, game,
            event_type="rent.missed",
            actor_player_id=None,
            payload={
                "agreement_id": str(agreement.id),
                "player_id": str(tenant.id),
                "landlord_player_id": str(landlord.id),
                "card_type": agreement.card_type,
                "rent_points": rent,
                "available": available,
                "shortfall": rent - available,
            },
        )
        return

    tenant.points -= rent
    landlord.points += rent
    agreement.turns_until_due = agreement.interval_turns
    tenant.rent_due = agreement.interval_turns

    event = await _append_event(
        db, game,
        event_type="rent.paid",
        actor_player_id=None,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(tenant.id),
            "landlord_player_id": str(landlord.id),
            "card_type": agreement.card_type,
            "rent_points": rent,
            "next_due_in": agreement.interval_turns,
        },
    )
    # Player to player: no bank row, and the pair still sums to zero.
    _ledger(db, game, event, player_id=tenant.id, entry_type="rent",
            points_delta=-rent)
    _ledger(db, game, event, player_id=landlord.id, entry_type="rent",
            points_delta=rent)