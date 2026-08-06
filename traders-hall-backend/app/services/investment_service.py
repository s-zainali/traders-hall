"""Investments: buying a share of what a room earns.

An investor puts up a principal and takes a percentage of every rent payment the
landlord collects on that property, for a fixed number of the landlord's turns.

Three things worth knowing about the shape of this:

The principal is not returned. It buys the share outright, so an investor only
profits if the room earns more than they paid — and a room with no tenant earns
nothing at all. That is the risk, and it is why the UI warns before committing.

Payouts come out of the rent the landlord receives, not out of the bank. The
landlord ends up with the remainder, so points are moved rather than created and
the ledger still sums to zero.

The share is rounded DOWN. On small rents that means a low percentage can pay
nothing at all: 20% of 2 points is 0. The alternative is rounding up, which pays
the investor more than the agreed share on every small rent, and that is the
worse error — it invents points the landlord never collected.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.investment import Investment
from app.services.action_service import _append_event, _ledger


def share_of(rent: int, percent: int) -> int:
    """The investor's cut of one rent payment, rounded down.

    Down rather than up: rounding up hands the investor more than the agreed
    percentage on every small payment, which would be points the landlord never
    received.
    """
    return (rent * percent) // 100


async def active_for_landlord(
    db: AsyncSession, game: Game, landlord: GamePlayer, card_type: str
) -> list[Investment]:
    """Live stakes against one of this landlord's property types."""
    return list(await db.scalars(
        select(Investment)
        .where(
            Investment.game_id == game.id,
            Investment.landlord_player_id == landlord.id,
            Investment.card_type == card_type,
            Investment.status == "active",
        )
        .order_by(Investment.created_at)
    ))


async def open_investment(
    db: AsyncSession,
    game: Game,
    *,
    investor: GamePlayer,
    landlord: GamePlayer,
    card_type: str,
    principal: int,
    yield_percent: int,
    term_turns: int,
) -> Investment:
    """Start a stake. Called from offer_service when an invest offer settles.

    The principal moves immediately and does not come back. The investor is
    buying a share, not making a loan.
    """
    investment = Investment(
        game_id=game.id,
        investor_player_id=investor.id,
        landlord_player_id=landlord.id,
        card_type=card_type,
        principal=principal,
        yield_percent=yield_percent,
        term_turns=term_turns,
        turns_remaining=term_turns,
        paid_out=0,
        status="active",
        created_turn=game.turn_number,
    )
    db.add(investment)
    await db.flush()
    return investment


async def pay_out(
    db: AsyncSession,
    game: Game,
    landlord: GamePlayer,
    card_type: str,
    rent: int,
    event,
) -> int:
    """Hand every live investor their share of one rent payment.

    Returns what was paid in total, so the caller knows how much of the rent the
    landlord actually keeps.

    Called AFTER the rent has landed in the landlord's balance, so the points
    being shared are ones they genuinely hold. Paying before would let a landlord
    who is already at zero go negative on somebody else's rent.
    """
    investments = await active_for_landlord(db, game, landlord, card_type)
    if not investments:
        return 0

    total = 0
    for investment in investments:
        cut = share_of(rent, investment.yield_percent)
        if cut < 1:
            continue

        # Never pay out more than the landlord is holding. Several stakes on one
        # property can sum past 100% of a small rent once each is rounded, and a
        # landlord cannot pay what they do not have.
        cut = min(cut, landlord.points)
        if cut < 1:
            break

        investor = await db.get(GamePlayer, investment.investor_player_id)
        if investor is None or investor.status != "active":
            continue

        landlord.points -= cut
        investor.points += cut
        investment.paid_out += cut
        total += cut

        _ledger(db, game, event, player_id=landlord.id, entry_type="investment",
                points_delta=-cut)
        _ledger(db, game, event, player_id=investor.id, entry_type="investment",
                points_delta=cut)

    if total:
        await _append_event(
            db, game,
            event_type="investment.paid",
            actor_player_id=None,
            payload={
                "landlord_player_id": str(landlord.id),
                "card_type": card_type,
                "rent_points": rent,
                "total_paid": total,
                "shares": [
                    {
                        "investment_id": str(i.id),
                        "investor_player_id": str(i.investor_player_id),
                        "percent": i.yield_percent,
                        "paid": share_of(rent, i.yield_percent),
                    }
                    for i in investments
                    if share_of(rent, i.yield_percent) >= 1
                ],
            },
        )

    return total


async def tick(db: AsyncSession, game: Game, landlord: GamePlayer) -> None:
    """Age this landlord's stakes by one of their turns and close any that expire.

    The clock belongs to the landlord, not the investor: the term is a promise
    the landlord is making, so it should run on their turns however long anybody
    else takes.
    """
    investments = list(await db.scalars(
        select(Investment).where(
            Investment.game_id == game.id,
            Investment.landlord_player_id == landlord.id,
            Investment.status == "active",
        )
    ))

    for investment in investments:
        if investment.turns_remaining > 0:
            investment.turns_remaining -= 1
        if investment.turns_remaining > 0:
            continue

        investment.status = "ended"
        investment.ended_at = datetime.now(UTC)

        await _append_event(
            db, game,
            event_type="investment.ended",
            actor_player_id=None,
            payload={
                "investment_id": str(investment.id),
                "investor_player_id": str(investment.investor_player_id),
                "landlord_player_id": str(landlord.id),
                "card_type": investment.card_type,
                "principal": investment.principal,
                "paid_out": investment.paid_out,
                # Negative when the room never earned enough to cover the stake,
                # which is the whole risk of investing an empty room.
                "profit": investment.paid_out - investment.principal,
            },
        )


async def close_for_player(
    db: AsyncSession, game: Game, seat: GamePlayer
) -> None:
    """End every stake this player is party to.

    Called when they leave or are eliminated. A stake needs both parties: with
    the landlord gone there is no rent to share, and with the investor gone
    there is nobody to pay.
    """
    investments = list(await db.scalars(
        select(Investment).where(
            Investment.game_id == game.id,
            Investment.status == "active",
        )
    ))

    for investment in investments:
        if seat.id not in (investment.investor_player_id, investment.landlord_player_id):
            continue
        investment.status = "ended"
        investment.ended_at = datetime.now(UTC)