"""The upkeep tick: obligations falling due at the end of a player's turn.

One player's counters advance by one when that player ends a turn, which makes a
"round" mean five of YOUR turns rather than five turns of play. Ticking every
seat on a lap boundary would be the alternative, and it is worse: a player who
joins the rotation late would take a full round of upkeep on their first turn.

Every settlement here runs inside the caller's locked transaction, appends its
own event and writes its own ledger pair, so an obligation enforced by the
server is exactly as auditable as an action taken by a player.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import cards, config
from app.models.game import Game
from app.models.game_event import GameEvent
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.services import rent_service
from app.services.action_service import (
    _append_event,
    _hand_row,
    _ledger,
    _pool_row,
)


async def run_upkeep(db: AsyncSession, game: Game, seat: GamePlayer) -> None:
    """Advance one player's obligations by a round and settle anything due.

    Called from end_turn BEFORE the baton passes, so the events land under the
    turn they belong to and the ledger records them against the right
    turn_number.
    """
    await _tick_food(db, game, seat)

    if seat.loan_outstanding > 0:
        seat.loan_due -= 1
        if seat.loan_due <= 0:
            await _settle_loan(db, game, seat)

    if seat.mortgage_outstanding > 0:
        seat.mortgage_due -= 1
        if seat.mortgage_due <= 0:
            await _settle_mortgage(db, game, seat)

    await rent_service.tick(db, game, seat)


async def _tick_food(db: AsyncSession, game: Game, seat: GamePlayer) -> None:
    """Burn one turn of nutrition.

    Clamped at zero rather than allowed to go negative: "how many turns until
    you must eat" has no meaningful negative value, and a negative counter would
    render as a nonsense number on every panel.

    The transition to zero emits an event ONCE. Re-announcing hunger every turn
    would bury the log, and the panel already shows the counter in red.
    """
    if seat.food_due <= 0:
        # Already out of food. The consequence of staying here is the open
        # question below, not something to re-log each turn.
        return

    seat.food_due -= 1
    if seat.food_due > 0:
        return

    await _append_event(
        db, game,
        event_type="food.exhausted",
        actor_player_id=None,
        payload={"player_id": str(seat.id)},
    )

    # ── starvation ───────────────────────────────────────────────────
    # This is where the penalty goes. It is NOT implemented because the rule is
    # "you lose the game", and losing does not exist yet: nothing sets
    # status='eliminated', nothing releases an eliminated player's offers or
    # skips their seat, and nothing decides what ends the match.
    #
    # game_players.status already has room for it and the frontend already
    # renders an `eliminated` state, so the wiring is short — but it is the win
    # condition, and inventing one silently would be worse than a counter that
    # sits at zero.


async def _settle_loan(db: AsyncSession, game: Game, seat: GamePlayer) -> None:
    """Collect the loan, seizing points and then property to cover it.

    Points first, because they are fungible and cost the player nothing beyond
    the number. Property only for the shortfall, highest value first so the
    fewest cards leave the hand — the bank gives no change, so seizing a tower
    for a 2 point debt is worse for the player than it looks, and taking the
    smallest cards first would compound that by taking more of them.

    Reserved points and mortgaged cards are untouchable: both are already
    promised elsewhere, and seizing them would break the invariant that a
    reservation can always be honoured.
    """
    owed = seat.loan_outstanding
    available = seat.points - seat.reserved_points

    bank_points = await _pool_row(db, game, "point")

    if available >= owed:
        seat.points -= owed
        bank_points.quantity += owed
        seat.loan_outstanding = 0
        seat.loan_due = 0

        event = await _append_event(
            db, game,
            event_type="loan.repaid",
            actor_player_id=None,
            payload={
                "player_id": str(seat.id),
                "amount": owed,
                "outstanding": 0,
                "cleared": True,
                "automatic": True,
            },
        )
        _ledger(db, game, event, player_id=seat.id, entry_type="loan_repay",
                points_delta=-owed)
        _ledger(db, game, event, player_id=None, entry_type="loan_repay",
                points_delta=owed)
        return

    # --- default ---
    seized_points = available
    shortfall = owed - seized_points

    seat.points -= seized_points
    bank_points.quantity += seized_points

    event = await _append_event(
        db, game,
        event_type="loan.defaulted",
        actor_player_id=None,
        payload={
            "player_id": str(seat.id),
            "owed": owed,
            "seized_points": seized_points,
            # filled in below once the seizure has run
            "seized_cards": {},
            "written_off": shortfall,
        },
    )
    if seized_points:
        _ledger(db, game, event, player_id=seat.id, entry_type="loan_default",
                points_delta=-seized_points)
        _ledger(db, game, event, player_id=None, entry_type="loan_default",
                points_delta=seized_points)

    seized_cards, recovered = await _seize_property(db, game, seat, event, shortfall)

    # JSONB is not mutation-tracked by SQLAlchemy: reassigning the whole dict is
    # what marks the attribute dirty. Mutating payload["seized_cards"] in place
    # would be silently dropped at flush.
    event.payload = {
        **event.payload,
        "seized_cards": seized_cards,
        "written_off": max(0, shortfall - recovered),
    }

    seat.loan_outstanding = 0
    seat.loan_due = 0


async def _seize_property(
    db: AsyncSession,
    game: Game,
    seat: GamePlayer,
    event: GameEvent,
    shortfall: int,
) -> tuple[dict[str, int], int]:
    """Take property cards back to the bank until `shortfall` is covered.

    Returns (what was taken, what it was worth). The bank does not give change:
    the last card seized may be worth more than the remaining debt, and the
    surplus is simply the price of defaulting.
    """
    seized: dict[str, int] = {}
    recovered = 0

    if shortfall <= 0:
        return seized, recovered

    # The category filter and the highest-value-first ordering are catalogue
    # facts, so both move into Python. A hand is at most seven rows; sorting it
    # here costs nothing and keeps the values in one place.
    hands = list(await db.scalars(
        select(PlayerHand).where(
            PlayerHand.game_id == game.id,
            PlayerHand.player_id == seat.id,
        )
    ))

    rows = [
        (hand, card)
        for hand in hands
        if (card := cards.get(hand.card_type)) is not None
        and card.category == config.SEIZABLE_CATEGORY
    ]
    rows.sort(key=lambda pair: pair[1].sell_value, reverse=True)

    for hand, card in rows:
        if recovered >= shortfall:
            break
        if card.sell_value < 1:
            continue

        # Mortgaged cards are held by reserved_quantity and are collateral for a
        # different debt, so only the free ones can be taken here.
        free = hand.quantity - hand.reserved_quantity
        pool = await _pool_row(db, game, card.code)

        while free > 0 and recovered < shortfall:
            hand.quantity -= 1
            pool.quantity += 1
            free -= 1
            recovered += card.sell_value
            seized[card.code] = seized.get(card.code, 0) + 1

    for code, count in seized.items():
        _ledger(db, game, event, player_id=seat.id, entry_type="loan_default",
                card_type=code, card_delta=-count)
        _ledger(db, game, event, player_id=None, entry_type="loan_default",
                card_type=code, card_delta=count)

    return seized, recovered


async def _settle_mortgage(db: AsyncSession, game: Game, seat: GamePlayer) -> None:
    """Redeem the property automatically, or let the bank seize it."""
    owed = seat.mortgage_outstanding
    card_type = seat.mortgage_card_type
    available = seat.points - seat.reserved_points

    hand = await _hand_row(db, game, seat, card_type)

    if available >= owed:
        seat.points -= owed
        (await _pool_row(db, game, "point")).quantity += owed
        hand.reserved_quantity = max(0, hand.reserved_quantity - 1)

        seat.mortgage_card_type = None
        seat.mortgage_outstanding = 0
        seat.mortgage_due = 0

        event = await _append_event(
            db, game,
            event_type="mortgage.redeemed",
            actor_player_id=None,
            payload={
                "player_id": str(seat.id),
                "card_type": card_type,
                "amount": owed,
                "automatic": True,
            },
        )
        _ledger(db, game, event, player_id=seat.id, entry_type="mortgage_redeem",
                points_delta=-owed, card_type=card_type, card_delta=0)
        _ledger(db, game, event, player_id=None, entry_type="mortgage_redeem",
                points_delta=owed, card_type=card_type, card_delta=0)
        return

    # Seizure: the card leaves the hand and returns to the bank's stock. Both
    # the held count and the reservation drop, which is what keeps
    # ck_hand_reserved_le_qty satisfied.
    hand.quantity -= 1
    hand.reserved_quantity = max(0, hand.reserved_quantity - 1)
    (await _pool_row(db, game, card_type)).quantity += 1

    seat.mortgage_card_type = None
    seat.mortgage_outstanding = 0
    seat.mortgage_due = 0

    event = await _append_event(
        db, game,
        event_type="mortgage.seized",
        actor_player_id=None,
        payload={
            "player_id": str(seat.id),
            "card_type": card_type,
            "owed": owed,
        },
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="mortgage_seize",
            card_type=card_type, card_delta=-1)
    _ledger(db, game, event, player_id=None, entry_type="mortgage_seize",
            card_type=card_type, card_delta=1)