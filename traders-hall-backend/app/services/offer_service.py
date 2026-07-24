import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.trade_offer import TradeOffer
from app.models.user import User
from app.services.action_service import (
    ActionError,
    _append_event,
    _check_version,
    _hand_row,
    _ledger,
    _lock_game,
    _seat_of,
)

MAX_OPEN_PER_PLAYER = 5


async def _offer(db: AsyncSession, game: Game, offer_id: uuid.UUID) -> TradeOffer:
    offer = await db.get(TradeOffer, offer_id)
    if offer is None or offer.game_id != game.id:
        raise ActionError("OFFER_NOT_FOUND", "No such offer")
    return offer


async def _release_claim(db: AsyncSession, game: Game, offer: TradeOffer) -> None:
    if offer.claimed_by_player_id is None:
        return

    claimant = await db.get(GamePlayer, offer.claimed_by_player_id)
    if claimant is not None:
        if offer.kind == "sell":
            claimant.reserved_points = max(
                0, claimant.reserved_points - offer.price_points
            )
        else:
            want = await db.scalar(
                select(PlayerHand).where(
                    PlayerHand.game_id == game.id,
                    PlayerHand.player_id == claimant.id,
                    PlayerHand.card_type == offer.want_card_type,
                )
            )
            if want is not None:
                want.reserved_quantity = max(
                    0, want.reserved_quantity - offer.want_quantity
                )

    offer.claimed_by_player_id = None
    offer.claimed_at = None


async def list_offers(db: AsyncSession, *, user: User, code: str) -> list[dict]:
    game = await db.scalar(select(Game).where(Game.join_code == code.upper()))
    if game is None:
        raise ActionError("GAME_NOT_FOUND", "No game with that code")

    seat = await db.scalar(
        select(GamePlayer).where(
            GamePlayer.game_id == game.id, GamePlayer.user_id == user.id
        )
    )
    if seat is None:
        raise ActionError("NOT_A_PLAYER", "You are not in that game")

    rows = list(await db.scalars(
        select(TradeOffer)
        .where(TradeOffer.game_id == game.id, TradeOffer.status.in_(("open", "claimed")))
        .order_by(TradeOffer.created_at.desc())
    ))

    seats = {
        p.id: p for p in await db.scalars(
            select(GamePlayer).where(GamePlayer.game_id == game.id)
        )
    }

    out = []
    for offer in rows:
        poster = seats.get(offer.poster_player_id)
        claimant = seats.get(offer.claimed_by_player_id) if offer.claimed_by_player_id else None
        out.append({
            "id": offer.id,
            "poster_player_id": offer.poster_player_id,
            "poster_name": poster.display_name if poster else "Unknown",
            "poster_seat_index": poster.seat_index if poster else -1,
            "kind": offer.kind,
            "offer_card_type": offer.offer_card_type,
            "offer_quantity": offer.offer_quantity,
            "price_points": offer.price_points,
            "want_card_type": offer.want_card_type,
            "want_quantity": offer.want_quantity,
            "status": offer.status,
            "claimed_by_player_id": offer.claimed_by_player_id,
            "claimed_by_name": claimant.display_name if claimant else None,
            "claimed_by_seat_index": claimant.seat_index if claimant else None,
            "created_turn": offer.created_turn,
            "created_at": offer.created_at,
        })
    return out


async def create_offer(
    db: AsyncSession,
    *,
    user: User,
    code: str,
    kind: str,
    offer_card_type: str,
    offer_quantity: int,
    price_points: int | None,
    want_card_type: str | None,
    want_quantity: int | None,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    if game.current_player_id != seat.id:
        raise ActionError("NOT_YOUR_TURN", "Offers can only be posted on your turn")
    if offer_card_type == "point":
        raise ActionError("NOT_TRADEABLE", "Points cannot be offered as goods")

    open_count = len(list(await db.scalars(
        select(TradeOffer).where(
            TradeOffer.game_id == game.id,
            TradeOffer.poster_player_id == seat.id,
            TradeOffer.status.in_(("open", "claimed")),
        )
    )))
    if open_count >= MAX_OPEN_PER_PLAYER:
        raise ActionError("TOO_MANY_OFFERS", f"You already have {open_count} live offers")

    hand = await _hand_row(db, game, seat, offer_card_type)
    available = hand.quantity - hand.reserved_quantity
    if available < offer_quantity:
        raise ActionError(
            "INSUFFICIENT_CARDS",
            f"You have only {available} free to offer",
            available=available,
        )

    hand.reserved_quantity += offer_quantity

    offer = TradeOffer(
        game_id=game.id,
        poster_player_id=seat.id,
        kind=kind,
        offer_card_type=offer_card_type,
        offer_quantity=offer_quantity,
        price_points=price_points,
        want_card_type=want_card_type,
        want_quantity=want_quantity,
        created_turn=game.turn_number,
    )
    db.add(offer)
    await db.flush()

    await _append_event(
        db, game,
        event_type="offer.posted",
        actor_player_id=seat.id,
        payload={
            "offer_id": str(offer.id),
            "kind": kind,
            "card_type": offer_card_type,
            "quantity": offer_quantity,
            "price_points": price_points,
            "want_card_type": want_card_type,
            "want_quantity": want_quantity,
        },
    )
    return game


async def claim_offer(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    claimant = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    offer = await _offer(db, game, offer_id)
    if offer.status != "open":
        raise ActionError("OFFER_NOT_OPEN", "That offer is no longer open")
    if offer.poster_player_id == claimant.id:
        raise ActionError("CANNOT_CLAIM_OWN_OFFER", "That is your own offer")

    if offer.kind == "sell":
        available = claimant.points - claimant.reserved_points
        if available < offer.price_points:
            raise ActionError(
                "INSUFFICIENT_POINTS",
                f"That costs {offer.price_points} points; you have {available} free",
                required=offer.price_points,
                available=available,
            )
        claimant.reserved_points += offer.price_points
    else:
        want = await _hand_row(db, game, claimant, offer.want_card_type)
        available = want.quantity - want.reserved_quantity
        if available < offer.want_quantity:
            raise ActionError(
                "INSUFFICIENT_CARDS",
                f"You have only {available} free {offer.want_card_type}",
                available=available,
            )
        want.reserved_quantity += offer.want_quantity

    offer.claimed_by_player_id = claimant.id
    offer.claimed_at = datetime.now(UTC)
    offer.status = "claimed"

    await _append_event(
        db, game,
        event_type="offer.claimed",
        actor_player_id=claimant.id,
        payload={"offer_id": str(offer.id), "poster_player_id": str(offer.poster_player_id)},
    )
    return game


async def withdraw_claim(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)

    offer = await _offer(db, game, offer_id)
    if offer.status != "claimed":
        raise ActionError("OFFER_NOT_CLAIMED", "That offer has not been claimed")
    if offer.claimed_by_player_id != seat.id:
        raise ActionError("NOT_CLAIMANT", "You did not claim that offer")

    await _release_claim(db, game, offer)
    offer.status = "open"

    await _append_event(
        db, game,
        event_type="offer.claim_withdrawn",
        actor_player_id=seat.id,
        payload={"offer_id": str(offer.id)},
    )
    return game


async def decline_claim(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)

    offer = await _offer(db, game, offer_id)
    if offer.poster_player_id != seat.id:
        raise ActionError("NOT_OFFER_OWNER", "Only the poster can decline a claim")
    if offer.status != "claimed":
        raise ActionError("OFFER_NOT_CLAIMED", "Nobody has claimed that offer")

    declined = offer.claimed_by_player_id
    await _release_claim(db, game, offer)
    offer.status = "open"

    await _append_event(
        db, game,
        event_type="offer.declined",
        actor_player_id=seat.id,
        payload={"offer_id": str(offer.id), "declined_player_id": str(declined)},
    )
    return game


async def confirm_offer(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    poster = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    offer = await _offer(db, game, offer_id)
    if offer.poster_player_id != poster.id:
        raise ActionError("NOT_OFFER_OWNER", "Only the poster can settle an offer")
    if offer.status != "claimed":
        raise ActionError("OFFER_NOT_CLAIMED", "Nobody has claimed that offer")

    buyer = await db.get(GamePlayer, offer.claimed_by_player_id)
    if buyer is None or buyer.status != "active":
        await _release_claim(db, game, offer)
        offer.status = "open"
        raise ActionError("CLAIMANT_GONE", "The claiming player has left the game")

    poster_hand = await _hand_row(db, game, poster, offer.offer_card_type)
    buyer_hand = await _hand_row(db, game, buyer, offer.offer_card_type)

    if poster_hand.quantity < offer.offer_quantity:
        raise ActionError("INSUFFICIENT_CARDS", "You no longer hold those cards")

    poster_hand.quantity -= offer.offer_quantity
    poster_hand.reserved_quantity -= offer.offer_quantity
    buyer_hand.quantity += offer.offer_quantity

    if offer.kind == "sell":
        price = offer.price_points
        if buyer.points < price:
            raise ActionError("INSUFFICIENT_POINTS", "The buyer can no longer pay")

        buyer.points -= price
        buyer.reserved_points = max(0, buyer.reserved_points - price)
        poster.points += price

        event = await _append_event(
            db, game,
            event_type="offer.settled",
            actor_player_id=poster.id,
            payload={
                "offer_id": str(offer.id),
                "kind": "sell",
                "with_player_id": str(buyer.id),
                "card_type": offer.offer_card_type,
                "quantity": offer.offer_quantity,
                "price_points": price,
            },
        )
        _ledger(db, game, event, player_id=buyer.id, entry_type="trade",
                points_delta=-price, card_type=offer.offer_card_type,
                card_delta=offer.offer_quantity)
        _ledger(db, game, event, player_id=poster.id, entry_type="trade",
                points_delta=price, card_type=offer.offer_card_type,
                card_delta=-offer.offer_quantity)
    else:
        buyer_want = await _hand_row(db, game, buyer, offer.want_card_type)
        poster_want = await _hand_row(db, game, poster, offer.want_card_type)

        if buyer_want.quantity < offer.want_quantity:
            raise ActionError("INSUFFICIENT_CARDS", "The other player no longer holds those cards")

        buyer_want.quantity -= offer.want_quantity
        buyer_want.reserved_quantity = max(
            0, buyer_want.reserved_quantity - offer.want_quantity
        )
        poster_want.quantity += offer.want_quantity

        event = await _append_event(
            db, game,
            event_type="offer.settled",
            actor_player_id=poster.id,
            payload={
                "offer_id": str(offer.id),
                "kind": "trade",
                "with_player_id": str(buyer.id),
                "card_type": offer.offer_card_type,
                "quantity": offer.offer_quantity,
                "want_card_type": offer.want_card_type,
                "want_quantity": offer.want_quantity,
            },
        )
        _ledger(db, game, event, player_id=buyer.id, entry_type="trade",
                card_type=offer.offer_card_type, card_delta=offer.offer_quantity)
        _ledger(db, game, event, player_id=poster.id, entry_type="trade",
                card_type=offer.offer_card_type, card_delta=-offer.offer_quantity)
        _ledger(db, game, event, player_id=buyer.id, entry_type="trade",
                card_type=offer.want_card_type, card_delta=-offer.want_quantity)
        _ledger(db, game, event, player_id=poster.id, entry_type="trade",
                card_type=offer.want_card_type, card_delta=offer.want_quantity)

    offer.settled_with_player_id = buyer.id
    offer.claimed_by_player_id = None
    offer.claimed_at = None
    offer.status = "settled"
    offer.resolved_at = datetime.now(UTC)
    return game


async def cancel_offer(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)

    offer = await _offer(db, game, offer_id)
    if offer.poster_player_id != seat.id:
        raise ActionError("NOT_OFFER_OWNER", "Only the poster can withdraw an offer")
    if offer.status not in ("open", "claimed"):
        raise ActionError("OFFER_NOT_OPEN", "That offer is no longer live")

    await _release_claim(db, game, offer)

    poster_hand = await _hand_row(db, game, seat, offer.offer_card_type)
    poster_hand.reserved_quantity = max(
        0, poster_hand.reserved_quantity - offer.offer_quantity
    )

    offer.status = "cancelled"
    offer.resolved_at = datetime.now(UTC)

    await _append_event(
        db, game,
        event_type="offer.cancelled",
        actor_player_id=seat.id,
        payload={"offer_id": str(offer.id)},
    )
    return game


async def release_offers_for(db: AsyncSession, game: Game, player: GamePlayer) -> None:
    posted = list(await db.scalars(
        select(TradeOffer).where(
            TradeOffer.game_id == game.id,
            TradeOffer.poster_player_id == player.id,
            TradeOffer.status.in_(("open", "claimed")),
        )
    ))
    for offer in posted:
        await _release_claim(db, game, offer)
        hand = await db.scalar(
            select(PlayerHand).where(
                PlayerHand.game_id == game.id,
                PlayerHand.player_id == player.id,
                PlayerHand.card_type == offer.offer_card_type,
            )
        )
        if hand is not None:
            hand.reserved_quantity = max(
                0, hand.reserved_quantity - offer.offer_quantity
            )
        offer.status = "cancelled"
        offer.resolved_at = datetime.now(UTC)

    claimed = list(await db.scalars(
        select(TradeOffer).where(
            TradeOffer.game_id == game.id,
            TradeOffer.claimed_by_player_id == player.id,
            TradeOffer.status == "claimed",
        )
    ))
    for offer in claimed:
        await _release_claim(db, game, offer)
        offer.status = "open"