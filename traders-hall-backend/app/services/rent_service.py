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
from app.services.action_service import (
    ActionError,
    _append_event,
    _check_version,
    _ledger,
    _lock_game,
    _require_turn,
    _seat_of,
)
from app.models.user import User


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
        # Points first, then cards. Whatever points they have go straight over —
        # there is no reason to make the landlord pick those.
        from app.services.elimination_service import eliminate, seizable_value

        taken = available
        shortfall = rent - taken

        if taken > 0:
            tenant.points -= taken
            landlord.points += taken

        event = await _append_event(
            db, game,
            event_type="rent.missed",
            actor_player_id=None,
            payload={
                "agreement_id": str(agreement.id),
                "player_id": str(tenant.id),
                "landlord_player_id": str(landlord.id),
                "card_type": agreement.card_type,
                "rent_points": rent,
                "points_taken": taken,
                "shortfall": shortfall,
            },
        )
        if taken > 0:
            _ledger(db, game, event, player_id=tenant.id, entry_type="rent",
                    points_delta=-taken)
            _ledger(db, game, event, player_id=landlord.id, entry_type="rent",
                    points_delta=taken)

        # Can their cards cover the rest at all? If not the outcome is already
        # decided, so there is nothing to freeze the game over and nothing for
        # the landlord to choose between — everything they own goes to the
        # landlord and they are out.
        if await seizable_value(db, game, tenant) < shortfall:
            await eliminate(db, game, tenant, reason="rent_default", creditor=landlord)
            return

        # Otherwise the landlord picks which cards to take, and the game waits.
        # Freezing is what makes that decision safe: nobody can move value out
        # from under it while it is pending.
        agreement.seizure_debt = shortfall
        game.phase = "seizure"
        game.seizure_agreement_id = agreement.id

        await _append_event(
            db, game,
            event_type="rent.seizure_opened",
            actor_player_id=None,
            payload={
                "agreement_id": str(agreement.id),
                "player_id": str(tenant.id),
                "landlord_player_id": str(landlord.id),
                "debt": shortfall,
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


MOVEOUT_PENALTY_NUMERATOR = 3
MOVEOUT_PENALTY_DENOMINATOR = 2


def buyout_price(rent_points: int) -> int:
    """What leaving costs once the landlord has refused: 1.5x rent, rounded up.

    Integer arithmetic rather than math.ceil on a float, because points are whole
    and 1.5 * 3 landing on 4.4999 would quietly undercharge. (3r + 1) // 2 is
    exactly ceil(1.5r): rent 1 costs 2, rent 2 costs 3, rent 3 costs 5.
    """
    return (
        rent_points * MOVEOUT_PENALTY_NUMERATOR + MOVEOUT_PENALTY_DENOMINATOR - 1
    ) // MOVEOUT_PENALTY_DENOMINATOR


async def _settle_departure(
    db: AsyncSession,
    game: Game,
    tenant: GamePlayer,
    agreement: RentalAgreement,
    *,
    amount: int,
    event_type: str,
) -> None:
    """Pay the landlord, end the tenancy, turn the tenant out.

    Shared by both exits — the landlord agreeing, and the tenant buying their way
    out after a refusal. Only the amount and the event differ, and keeping one
    path means the tenancy cannot end by one route with the payment skipped.
    """
    landlord = await db.get(GamePlayer, agreement.landlord_player_id)
    if landlord is None or landlord.status != "active":
        raise ActionError("LANDLORD_GONE", "That landlord has left the game")

    available = tenant.points - tenant.reserved_points
    if available < amount:
        raise ActionError(
            "INSUFFICIENT_POINTS",
            f"That costs {amount} points; you have {available} free",
            required=amount,
            available=available,
        )

    tenant.points -= amount
    landlord.points += amount

    agreement.status = "ended"
    agreement.ended_at = datetime.now(UTC)
    agreement.moveout_status = None
    agreement.moveout_buyout = None

    tenant.residence_card_type = None
    tenant.residence_landlord_id = None
    tenant.rent_due = 0

    event = await _append_event(
        db, game,
        event_type=event_type,
        actor_player_id=None,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(tenant.id),
            "landlord_player_id": str(landlord.id),
            "card_type": agreement.card_type,
            "amount": amount,
        },
    )
    _ledger(db, game, event, player_id=tenant.id, entry_type="rent",
            points_delta=-amount)
    _ledger(db, game, event, player_id=landlord.id, entry_type="rent",
            points_delta=amount)


async def request_moveout(
    db: AsyncSession, game: Game, tenant: GamePlayer, agreement: RentalAgreement
) -> None:
    """Ask the landlord to release you.

    Raised rather than granted: the tenant has occupied the room since their last
    payment, and walking out unannounced is precisely the hole this closes.
    """
    if agreement.moveout_status == "requested":
        raise ActionError("MOVEOUT_PENDING", "Your landlord has not answered yet")
    if agreement.moveout_status == "rejected":
        raise ActionError(
            "MOVEOUT_REFUSED",
            "Your landlord refused. Stay, or pay to leave.",
            buyout=agreement.moveout_buyout,
        )

    agreement.moveout_status = "requested"
    agreement.moveout_turn = game.turn_number

    await _append_event(
        db, game,
        event_type="tenancy.moveout_requested",
        actor_player_id=tenant.id,
        payload={
            "agreement_id": str(agreement.id),
            "landlord_player_id": str(agreement.landlord_player_id),
            "card_type": agreement.card_type,
            "rent_points": agreement.rent_points,
        },
    )


async def respond_moveout(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    agreement_id,
    accept: bool,
    expected_state_version: int | None,
) -> Game:
    """The landlord answers. Accepting collects the rent and lets them go.

    Not turn-gated, like settling an offer: a request that could only be answered
    on the landlord's own turn would stall the tenant for most of a lap.
    """
    game = await _lock_game(db, code)
    landlord = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    agreement = await db.get(RentalAgreement, agreement_id)
    if agreement is None or agreement.game_id != game.id:
        raise ActionError("NO_TENANCY", "No such tenancy")
    if agreement.landlord_player_id != landlord.id:
        raise ActionError("NOT_LANDLORD", "That is not your property")
    if agreement.status != "active" or agreement.moveout_status != "requested":
        raise ActionError("NO_MOVEOUT_REQUEST", "Nobody is asking to leave")

    tenant = await db.get(GamePlayer, agreement.tenant_player_id)
    if tenant is None:
        raise ActionError("NO_TENANCY", "That tenant has left the game")

    if accept:
        await _settle_departure(
            db, game, tenant, agreement,
            amount=agreement.rent_points,
            event_type="tenancy.moveout_accepted",
        )
        return game

    agreement.moveout_status = "rejected"
    agreement.moveout_buyout = buyout_price(agreement.rent_points)

    await _append_event(
        db, game,
        event_type="tenancy.moveout_rejected",
        actor_player_id=landlord.id,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(tenant.id),
            "card_type": agreement.card_type,
            "rent_points": agreement.rent_points,
            "buyout": agreement.moveout_buyout,
        },
    )
    return game


async def resolve_moveout(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    leave: bool,
    expected_state_version: int | None,
) -> Game:
    """After a refusal the tenant picks: stay put, or pay the penalty and go."""
    game = await _lock_game(db, code)
    tenant = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, tenant)

    agreement = await active_for_tenant(db, game, tenant)
    if agreement is None or agreement.moveout_status != "rejected":
        raise ActionError("NO_MOVEOUT_REFUSAL", "There is nothing to settle")

    if not leave:
        agreement.moveout_status = None
        agreement.moveout_buyout = None
        agreement.moveout_turn = None

        await _append_event(
            db, game,
            event_type="tenancy.moveout_withdrawn",
            actor_player_id=tenant.id,
            payload={
                "agreement_id": str(agreement.id),
                "landlord_player_id": str(agreement.landlord_player_id),
                "card_type": agreement.card_type,
            },
        )
        return game

    # The quoted price, not a fresh calculation: the tenant agreed to a number.
    await _settle_departure(
        db, game, tenant, agreement,
        amount=agreement.moveout_buyout or buyout_price(agreement.rent_points),
        event_type="tenancy.moveout_bought_out",
    )
    return game


async def evict(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    agreement_id,
    expected_state_version: int | None,
) -> Game:
    """End a tenancy from the landlord's side, charging nothing.

    Deliberately asymmetric with a tenant leaving. A tenant walking out
    mid-period owes the rent for the period they lived through; a landlord
    turning someone out forfeits it. Whoever ends it early bears the cost of
    ending it early.

    Not turn-gated, like answering a move-out. It also clears any request in
    flight: a landlord who evicts has answered by other means.
    """
    game = await _lock_game(db, code)
    landlord = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    agreement = await db.get(RentalAgreement, agreement_id)
    if agreement is None or agreement.game_id != game.id:
        raise ActionError("NO_TENANCY", "No such tenancy")
    if agreement.landlord_player_id != landlord.id:
        raise ActionError("NOT_LANDLORD", "That is not your property")
    if agreement.status != "active":
        raise ActionError("NO_TENANCY", "That tenancy has already ended")

    tenant = await db.get(GamePlayer, agreement.tenant_player_id)

    agreement.status = "ended"
    agreement.ended_at = datetime.now(UTC)
    agreement.moveout_status = None
    agreement.moveout_buyout = None
    agreement.moveout_turn = None

    if tenant is not None:
        tenant.residence_card_type = None
        tenant.residence_landlord_id = None
        tenant.rent_due = 0

    # No ledger rows: nothing changed hands. The forfeited rent was never
    # collected, so there is nothing to record.
    await _append_event(
        db, game,
        event_type="tenancy.evicted",
        actor_player_id=landlord.id,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(agreement.tenant_player_id),
            "landlord_player_id": str(landlord.id),
            "card_type": agreement.card_type,
            "rent_forfeited": agreement.rent_points,
        },
    )
    return game


async def pay_now(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Settle rent early, before the clock runs out.

    Upkeep collects automatically at zero, so this changes nothing about what is
    owed — it lets a tenant clear the debt while they still have the points,
    rather than watching the counter fall and hoping they can cover it on the
    turn it lands. Paying resets the interval exactly as an automatic charge
    would.
    """
    game = await _lock_game(db, code)
    tenant = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, tenant)

    agreement = await active_for_tenant(db, game, tenant)
    if agreement is None:
        raise ActionError("NO_TENANCY", "You are not renting")

    landlord = await db.get(GamePlayer, agreement.landlord_player_id)
    if landlord is None or landlord.status != "active":
        raise ActionError("LANDLORD_GONE", "That landlord has left the game")

    rent = agreement.rent_points
    available = tenant.points - tenant.reserved_points
    if available < rent:
        raise ActionError(
            "INSUFFICIENT_POINTS",
            f"Rent is {rent}; you have {available} free",
            required=rent,
            available=available,
        )

    tenant.points -= rent
    landlord.points += rent
    agreement.turns_until_due = agreement.interval_turns
    tenant.rent_due = agreement.interval_turns

    event = await _append_event(
        db, game,
        event_type="rent.paid",
        actor_player_id=tenant.id,
        payload={
            "agreement_id": str(agreement.id),
            "player_id": str(tenant.id),
            "landlord_player_id": str(landlord.id),
            "card_type": agreement.card_type,
            "rent_points": rent,
            "next_due_in": agreement.interval_turns,
            "early": True,
        },
    )
    _ledger(db, game, event, player_id=tenant.id, entry_type="rent",
            points_delta=-rent)
    _ledger(db, game, event, player_id=landlord.id, entry_type="rent",
            points_delta=rent)

    # Investors take their share of an early payment exactly as they would of an
    # automatic one — the landlord received the same rent either way.
    from app.services.investment_service import pay_out

    await pay_out(db, game, landlord, agreement.card_type, rent, event)

    return game