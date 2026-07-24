"""Bank credit: unsecured loans and property mortgages.

Both are debts owed to the bank, both tick down once per round in
upkeep_service, and both settle through the same two outcomes — paid, or
enforced. They live in one module because changing the terms of one almost
always means looking at the other.

Points borrowed come OUT of the bank's point pool and repayments go back into
it, exactly like a sale. Nothing is minted: the ledger invariant that
SUM(points_delta) across every entry including the bank is zero holds through
every path here.

Every function reuses the transaction kernel in action_service — lock, version
check, turn check, mutate, ledger, event — so a loan is subject to the same
concurrency guarantees as a purchase.
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


async def borrow(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    amount: int,
    expected_state_version: int | None,
) -> Game:
    """Take an unsecured loan from the bank."""
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if amount < 1:
        raise ActionError("VALIDATION_ERROR", "Loan amount must be at least 1")
    if amount > config.LOAN_MAX_PRINCIPAL:
        raise ActionError(
            "LOAN_LIMIT_EXCEEDED",
            f"The bank lends at most {config.LOAN_MAX_PRINCIPAL} points",
            maximum=config.LOAN_MAX_PRINCIPAL,
        )
    if seat.loan_outstanding > 0:
        raise ActionError(
            "LOAN_ALREADY_ACTIVE",
            f"You already owe {seat.loan_outstanding} points",
            outstanding=seat.loan_outstanding,
        )

    bank_points = await _pool_row(db, game, "point")
    if bank_points.quantity < amount:
        raise ActionError(
            "BANK_OUT_OF_POINTS",
            "The bank cannot cover that loan",
            available=bank_points.quantity,
        )

    bank_points.quantity -= amount
    seat.points += amount
    seat.loan_outstanding = amount
    seat.loan_due = config.LOAN_TERM_ROUNDS

    event = await _append_event(
        db, game,
        event_type="loan.borrowed",
        actor_player_id=seat.id,
        payload={
            "amount": amount,
            "outstanding": seat.loan_outstanding,
            "due_in_rounds": seat.loan_due,
        },
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="loan_borrow",
            points_delta=amount)
    _ledger(db, game, event, player_id=None, entry_type="loan_borrow",
            points_delta=-amount)

    return game


async def repay(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    amount: int,
    expected_state_version: int | None,
) -> Game:
    """Pay down an outstanding loan, in part or in full.

    Partial repayment does NOT extend the term. Paying three points off a five
    point loan with two rounds left still leaves two due in two rounds — the
    clock belongs to the loan, not to the balance.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if amount < 1:
        raise ActionError("VALIDATION_ERROR", "Repayment must be at least 1")
    if seat.loan_outstanding <= 0:
        raise ActionError("NO_ACTIVE_LOAN", "You have no loan to repay")

    # Overpaying is a UI slip, not an attack. Clamp rather than reject, so an
    # obvious "repay everything" button cannot 422 on a slightly stale balance.
    amount = min(amount, seat.loan_outstanding)

    # reserved_points are promised to an open market claim and cannot be spent
    # here, for the same reason they cannot be spent on a purchase.
    available = seat.points - seat.reserved_points
    if available < amount:
        raise ActionError(
            "INSUFFICIENT_POINTS",
            f"That repayment needs {amount} points; you have {available} free",
            required=amount,
            available=available,
        )

    seat.points -= amount
    seat.loan_outstanding -= amount
    (await _pool_row(db, game, "point")).quantity += amount

    cleared = seat.loan_outstanding == 0
    if cleared:
        seat.loan_due = 0

    event = await _append_event(
        db, game,
        event_type="loan.repaid",
        actor_player_id=seat.id,
        payload={
            "amount": amount,
            "outstanding": seat.loan_outstanding,
            "cleared": cleared,
            "automatic": False,
        },
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="loan_repay",
            points_delta=-amount)
    _ledger(db, game, event, player_id=None, entry_type="loan_repay",
            points_delta=amount)

    return game


async def open_mortgage(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    card_type: str,
    expected_state_version: int | None,
) -> Game:
    """Borrow against one property, which stays in hand but is locked.

    The card is held by incrementing player_hands.reserved_quantity. Sell, trade
    and offer all already spend against `quantity - reserved_quantity`, so a
    mortgaged property becomes untradeable with no change to any of them.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if seat.mortgage_outstanding > 0:
        raise ActionError(
            "MORTGAGE_ALREADY_ACTIVE",
            f"You already have a mortgage on your {seat.mortgage_card_type}",
            card_type=seat.mortgage_card_type,
        )

    card = await _card(db, card_type)
    if card.category != config.MORTGAGEABLE_CATEGORY:
        raise ActionError("NOT_MORTGAGEABLE", f"{card.title} is not a property")

    advance = card.sell_value
    if advance < 1:
        raise ActionError("NOT_MORTGAGEABLE", f"{card.title} has no mortgage value")

    hand = await _hand_row(db, game, seat, card_type)
    free = hand.quantity - hand.reserved_quantity
    if free < 1:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have no free {card.title} to mortgage",
            available=free,
        )

    bank_points = await _pool_row(db, game, "point")
    if bank_points.quantity < advance:
        raise ActionError(
            "BANK_OUT_OF_POINTS",
            "The bank cannot cover that mortgage",
            available=bank_points.quantity,
        )

    hand.reserved_quantity += 1
    bank_points.quantity -= advance
    seat.points += advance
    seat.mortgage_card_type = card_type
    seat.mortgage_outstanding = advance
    seat.mortgage_due = config.MORTGAGE_TERM_ROUNDS

    event = await _append_event(
        db, game,
        event_type="mortgage.opened",
        actor_player_id=seat.id,
        payload={
            "card_type": card_type,
            "advance": advance,
            "outstanding": advance,
            "due_in_rounds": seat.mortgage_due,
        },
    )
    # The card does not move, so card_delta is zero on both sides: this is a
    # points movement against collateral that stays where it is.
    _ledger(db, game, event, player_id=seat.id, entry_type="mortgage_open",
            points_delta=advance, card_type=card_type, card_delta=0)
    _ledger(db, game, event, player_id=None, entry_type="mortgage_open",
            points_delta=-advance, card_type=card_type, card_delta=0)

    return game


async def redeem_mortgage(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    expected_state_version: int | None,
) -> Game:
    """Clear the mortgage and unlock the property.

    All or nothing: the debt is against one indivisible card, so a partial
    payment would leave a fraction of a house held hostage.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)
    _require_turn(game, seat)

    if seat.mortgage_outstanding <= 0:
        raise ActionError("NO_ACTIVE_MORTGAGE", "You have no mortgage to redeem")

    owed = seat.mortgage_outstanding
    card_type = seat.mortgage_card_type

    available = seat.points - seat.reserved_points
    if available < owed:
        raise ActionError(
            "INSUFFICIENT_POINTS",
            f"Redeeming costs {owed} points; you have {available} free",
            required=owed,
            available=available,
        )

    hand = await _hand_row(db, game, seat, card_type)

    seat.points -= owed
    (await _pool_row(db, game, "point")).quantity += owed
    hand.reserved_quantity = max(0, hand.reserved_quantity - 1)

    # Cleared together, in one flush — ck_player_mortgage_shape rejects a
    # dangling card reference or a debt with no collateral behind it.
    seat.mortgage_card_type = None
    seat.mortgage_outstanding = 0
    seat.mortgage_due = 0

    event = await _append_event(
        db, game,
        event_type="mortgage.redeemed",
        actor_player_id=seat.id,
        payload={"card_type": card_type, "amount": owed, "automatic": False},
    )
    _ledger(db, game, event, player_id=seat.id, entry_type="mortgage_redeem",
            points_delta=-owed, card_type=card_type, card_delta=0)
    _ledger(db, game, event, player_id=None, entry_type="mortgage_redeem",
            points_delta=owed, card_type=card_type, card_delta=0)

    return game