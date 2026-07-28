import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_player import GamePlayer
from app.models.player_hand import PlayerHand
from app.models.offer_claim import OfferClaim
from app.models.trade_offer import TradeOffer
from app.models.user import User
from app.services.residence_service import (
    free_rooms_by_card,
    housing_cards_by_card,
    movable_quantity,
)
from app.services.rent_service import open_agreement
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

RENT_KINDS = ("rent_out", "rent_ask")


def _total_price(offer: TradeOffer) -> int:
    """What a claimant pays for a whole SELL lot.

    price_points is PER UNIT — what the poster typed into "price each" — so
    every reservation, transfer and unreserve goes through here rather than
    reading the column. Reading it raw is how a 2-card offer at 3 each settled
    for 3.

    Rent deliberately does NOT route through this. rent_points is already the
    whole payment for one room, and multiplying it by offer_quantity would
    double a tenancy's rent the moment quantity was ever anything but 1.
    """
    return (offer.price_points or 0) * offer.offer_quantity


def _is_rent(offer: TradeOffer) -> bool:
    return offer.kind in RENT_KINDS


def _rent_parties(offer: TradeOffer, poster: GamePlayer, claimant: GamePlayer):
    """Who is the landlord and who is the tenant.

    The two rent kinds differ only in who posted. rent_out is a landlord
    advertising a room, so the claimant moves in; rent_ask is a tenant looking
    for one, so the claimant is the landlord. Everything downstream — capacity,
    the agreement, the residence — is identical once the roles are named, which
    is why this is one function rather than two settle paths.
    """
    if offer.kind == "rent_out":
        return poster, claimant
    return claimant, poster


def _rent_card(offer: TradeOffer) -> str:
    """Which property the room belongs to.

    For rent_out the poster named it up front. For rent_ask the request names no
    property at all, so the landlord chose one when claiming and it lives in
    claim_card_type.
    """
    return offer.offer_card_type if offer.kind == "rent_out" else offer.claim_card_type


async def _offer(db: AsyncSession, game: Game, offer_id: uuid.UUID) -> TradeOffer:
    offer = await db.get(TradeOffer, offer_id)
    if offer is None or offer.game_id != game.id:
        raise ActionError("OFFER_NOT_FOUND", "No such offer")
    return offer


async def _release_claim(db: AsyncSession, game: Game, offer: TradeOffer) -> None:
    """Clear every hand raised on an offer.

    There is nothing to give back. Claims reserve neither points nor cards, so
    releasing one is just forgetting it — which is what lets any number of
    players want the same offer without freezing anybody's balance.
    """
    await db.execute(delete(OfferClaim).where(OfferClaim.offer_id == offer.id))
    offer.claimed_by_player_id = None
    offer.claimed_at = None


async def _claims_for(db: AsyncSession, offer: TradeOffer) -> list[OfferClaim]:
    return list(await db.scalars(
        select(OfferClaim)
        .where(OfferClaim.offer_id == offer.id)
        .order_by(OfferClaim.created_at)
    ))


async def _claim_of(
    db: AsyncSession, offer: TradeOffer, player_id: uuid.UUID
) -> OfferClaim | None:
    return await db.scalar(
        select(OfferClaim).where(
            OfferClaim.offer_id == offer.id, OfferClaim.player_id == player_id
        )
    )



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
        .where(TradeOffer.game_id == game.id, TradeOffer.status == "open")
        .order_by(TradeOffer.created_at.desc())
    ))

    seats = {
        p.id: p for p in await db.scalars(
            select(GamePlayer).where(GamePlayer.game_id == game.id)
        )
    }

    # One query for every claim in the game rather than one per offer.
    all_claims = list(await db.scalars(
        select(OfferClaim)
        .where(OfferClaim.game_id == game.id)
        .order_by(OfferClaim.created_at)
    ))
    claims_by_offer: dict = {}
    for c in all_claims:
        claims_by_offer.setdefault(c.offer_id, []).append(c)

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
            # Sent so the client never multiplies and affordability is one
            # comparison. Null for rent, where price_points is already whole.
            "total_price_points": _total_price(offer) if offer.kind == "sell" else None,
            "rent_interval_turns": offer.rent_interval_turns,
            "claim_card_type": offer.claim_card_type,
            "want_card_type": offer.want_card_type,
            "want_quantity": offer.want_quantity,
            "status": offer.status,
            "claims": [
                {
                    "player_id": c.player_id,
                    "player_name": seats[c.player_id].display_name if c.player_id in seats else "Unknown",
                    "seat_index": seats[c.player_id].seat_index if c.player_id in seats else -1,
                    "card_type": c.card_type,
                }
                for c in claims_by_offer.get(offer.id, [])
            ],
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
    offer_card_type: str | None,
    offer_quantity: int,
    price_points: int | None,
    want_card_type: str | None,
    want_quantity: int | None,
    rent_interval_turns: int | None,
    expected_state_version: int | None,
) -> Game:
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    if game.current_player_id != seat.id:
        raise ActionError("NOT_YOUR_TURN", "Offers can only be posted on your turn")
    if kind not in ("sell", "trade") + RENT_KINDS:
        raise ActionError("VALIDATION_ERROR", f"Unknown offer kind: {kind}")
    if kind in ("sell", "trade") and offer_card_type == "point":
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

    if kind == "rent_out":
        # Letting a room reserves NO card. The property stays fully yours and
        # its other rooms stay available — reserving it would make it unsellable
        # and block the rest of its capacity, neither of which a tenancy
        # implies. Capacity is policed by counting live agreements instead.
        free = await free_rooms_by_card(db, game, seat)
        if free.get(offer_card_type, 0) < 1:
            raise ActionError(
                "NO_FREE_ROOM",
                "You have no spare room in that property",
                card_type=offer_card_type,
            )
    elif kind == "rent_ask":
        # A request names no property: it broadcasts, and any landlord with a
        # spare room may accept. Nothing of the asker's is committed.
        if seat.residence_card_type is not None:
            raise ActionError(
                "ALREADY_RESIDING",
                "Leave your current residence before asking for a room",
                card_type=seat.residence_card_type,
            )
    else:
        hand = await _hand_row(db, game, seat, offer_card_type)
        # Held back by a live offer, a mortgage, OR a resident. An occupied
        # property cannot be put up for sale or trade at all.
        available = await movable_quantity(db, game, seat, offer_card_type)
        if available < offer_quantity:
            housed = hand.quantity - hand.reserved_quantity - available
            raise ActionError(
                "PROPERTY_OCCUPIED" if housed > 0 else "INSUFFICIENT_CARDS",
                "Someone lives in that property"
                if housed > 0
                else f"You have only {available} free to offer",
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
        rent_interval_turns=rent_interval_turns,
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
            "rent_interval_turns": rent_interval_turns,
            "want_card_type": want_card_type,
            "want_quantity": want_quantity,
        },
    )
    return game


async def claim_offer(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID,
    expected_state_version: int | None,
    card_type: str | None = None,
) -> Game:
    """Put your hand up. Does not lock the offer, and does not reserve anything.

    Several players may claim the same offer; the poster chooses between them.
    Eligibility is still checked here so a player learns immediately that they
    cannot afford it or have nowhere to put a tenant — but affordability is
    RE-checked at settle, because nothing was frozen in the meantime.

    card_type applies to rent_ask only, where the claimant is the LANDLORD and
    must name which property the room is in.
    """
    game = await _lock_game(db, code)
    claimant = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    offer = await _offer(db, game, offer_id)
    if offer.status != "open":
        raise ActionError("OFFER_NOT_OPEN", "That offer is no longer open")
    if offer.poster_player_id == claimant.id:
        raise ActionError("CANNOT_CLAIM_OWN_OFFER", "That is your own offer")
    if await _claim_of(db, offer, claimant.id) is not None:
        raise ActionError("ALREADY_CLAIMED", "You have already claimed that offer")

    if offer.kind == "sell":
        total = _total_price(offer)
        available = claimant.points - claimant.reserved_points
        if available < total:
            raise ActionError(
                "INSUFFICIENT_POINTS",
                f"That costs {total} points; you have {available} free",
                required=total, available=available,
            )
    elif offer.kind == "trade":
        want = await _hand_row(db, game, claimant, offer.want_card_type)
        if want.quantity - want.reserved_quantity < offer.want_quantity:
            raise ActionError(
                "INSUFFICIENT_CARDS",
                f"You need {offer.want_quantity} free {offer.want_card_type}",
            )
    elif offer.kind == "rent_out":
        if claimant.residence_card_type is not None:
            raise ActionError(
                "ALREADY_RESIDING",
                "Leave your current residence before taking a room",
                card_type=claimant.residence_card_type,
            )
    else:  # rent_ask — the claimant is the landlord
        free = await free_rooms_by_card(db, game, claimant)
        if not any(free.values()):
            raise ActionError("NO_FREE_ROOM", "You have no spare room to let")
        if card_type is None:
            candidates = [c for c, n in free.items() if n > 0]
            if len(candidates) == 1:
                card_type = candidates[0]
            else:
                raise ActionError(
                    "CARD_TYPE_REQUIRED",
                    "Choose which property the room is in",
                    options=candidates,
                )
        if free.get(card_type, 0) < 1:
            raise ActionError(
                "NO_FREE_ROOM", "You have no spare room in that property",
                card_type=card_type,
            )

    db.add(OfferClaim(
        game_id=game.id,
        offer_id=offer.id,
        player_id=claimant.id,
        card_type=card_type if offer.kind == "rent_ask" else None,
    ))
    await db.flush()

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
    """Take your own hand back down. The offer stays open to everyone else."""
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)

    offer = await _offer(db, game, offer_id)
    claim = await _claim_of(db, offer, seat.id)
    if claim is None:
        raise ActionError("NOT_CLAIMANT", "You have not claimed that offer")

    await db.delete(claim)
    await _append_event(
        db, game,
        event_type="offer.claim_withdrawn",
        actor_player_id=seat.id,
        payload={"offer_id": str(offer.id)},
    )
    return game



async def decline_claim(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID,
    player_id: uuid.UUID | None = None,
) -> Game:
    """Turn down ONE claimant, leaving the rest in the running.

    player_id is required once more than one player has claimed — declining
    without saying who would be ambiguous, and silently picking the first would
    reject someone the poster never looked at.
    """
    game = await _lock_game(db, code)
    seat = await _seat_of(db, game, user)

    offer = await _offer(db, game, offer_id)
    if offer.poster_player_id != seat.id:
        raise ActionError("NOT_OFFER_OWNER", "Only the poster can decline a claim")

    claims = await _claims_for(db, offer)
    if not claims:
        raise ActionError("OFFER_NOT_CLAIMED", "Nobody has claimed that offer")

    if player_id is None:
        if len(claims) > 1:
            raise ActionError("PLAYER_REQUIRED", "Choose which claim to decline")
        player_id = claims[0].player_id

    claim = await _claim_of(db, offer, player_id)
    if claim is None:
        raise ActionError("NOT_CLAIMANT", "That player has not claimed this offer")

    await db.delete(claim)
    await _append_event(
        db, game,
        event_type="offer.declined",
        actor_player_id=seat.id,
        payload={"offer_id": str(offer.id), "declined_player_id": str(player_id)},
    )
    return game



async def confirm_offer(
    db: AsyncSession, *, user: User, code: str, offer_id: uuid.UUID,
    expected_state_version: int | None,
    player_id: uuid.UUID | None = None,
) -> Game:
    """Accept ONE of the players who claimed, and settle with them.

    player_id is required whenever more than one player has claimed. Everything
    is validated here rather than at claim time, because claims reserve nothing —
    the winner may have spent their points on something else since. If they have,
    the poster gets a clear error and can accept somebody else instead.
    """
    game = await _lock_game(db, code)
    poster = await _seat_of(db, game, user)
    _check_version(game, expected_state_version)

    offer = await _offer(db, game, offer_id)
    if offer.poster_player_id != poster.id:
        raise ActionError("NOT_OFFER_OWNER", "Only the poster can settle an offer")
    if offer.status != "open":
        raise ActionError("OFFER_NOT_OPEN", "That offer is no longer live")

    claims = await _claims_for(db, offer)
    if not claims:
        raise ActionError("OFFER_NOT_CLAIMED", "Nobody has claimed that offer")

    if player_id is None:
        if len(claims) > 1:
            raise ActionError("PLAYER_REQUIRED", "Choose which player to accept")
        player_id = claims[0].player_id

    chosen = await _claim_of(db, offer, player_id)
    if chosen is None:
        raise ActionError("NOT_CLAIMANT", "That player has not claimed this offer")

    buyer = await db.get(GamePlayer, player_id)
    if buyer is None or buyer.status != "active":
        await db.delete(chosen)
        raise ActionError("CLAIMANT_GONE", "That player has left the game")

    # rent_ask carries the landlord's chosen property on the CLAIM, not the
    # offer — the request itself names no property.
    if offer.kind == "rent_ask":
        offer.claim_card_type = chosen.card_type

    if _is_rent(offer):
        landlord, tenant = _rent_parties(offer, poster, buyer)
        card_type = _rent_card(offer)

        if card_type is None:
            raise ActionError("CARD_TYPE_REQUIRED", "No property was named for that room")

        # Re-checked at settle, not just at claim. Between the two the landlord
        # may have sold the property, had it seized to cover a defaulted loan,
        # or let the room to someone else; and the tenant may have moved in
        # elsewhere. The claim reserves nothing, so nothing held any of it still.
        # exclude_offer_id matters: lettable_by_card subtracts rooms promised
        # by live rent_out offers, and THIS offer is one of them. Without the
        # exclusion a landlord letting their only room always sees zero free and
        # the settle can never succeed.
        free = await free_rooms_by_card(db, game, landlord, exclude_offer_id=offer.id)
        if free.get(card_type, 0) < 1:
            raise ActionError(
                "NO_FREE_ROOM",
                "That room is no longer available",
                card_type=card_type,
            )
        if tenant.residence_card_type is not None:
            raise ActionError(
                "ALREADY_RESIDING",
                "That player already lives somewhere",
                card_type=tenant.residence_card_type,
            )

        agreement = await open_agreement(
            db, game,
            landlord=landlord,
            tenant=tenant,
            card_type=card_type,
            rent_points=offer.price_points,
            interval_turns=offer.rent_interval_turns,
        )

        # No ledger rows: nothing has moved yet. The first payment writes the
        # first pair, which keeps SUM(points_delta) at zero throughout.
        await _append_event(
            db, game,
            event_type="offer.settled",
            actor_player_id=poster.id,
            payload={
                "offer_id": str(offer.id),
                "kind": offer.kind,
                "with_player_id": str(buyer.id),
                "agreement_id": str(agreement.id),
                "landlord_player_id": str(landlord.id),
                "tenant_player_id": str(tenant.id),
                "card_type": card_type,
                "rent_points": offer.price_points,
                "rent_interval_turns": offer.rent_interval_turns,
            },
        )

        offer.settled_with_player_id = buyer.id
        offer.claimed_by_player_id = None
        offer.claimed_at = None
        offer.status = "settled"
        offer.resolved_at = datetime.now(UTC)
        return game

    poster_hand = await _hand_row(db, game, poster, offer.offer_card_type)
    buyer_hand = await _hand_row(db, game, buyer, offer.offer_card_type)

    if poster_hand.quantity < offer.offer_quantity:
        raise ActionError("INSUFFICIENT_CARDS", "You no longer hold those cards")

    # Re-checked at settle, not only when posted: a tenant can move in between
    # the two. A reservation holds a card against other OFFERS, not against
    # somebody coming to live in it.
    #
    # Stated directly rather than through movable_quantity, which nets off ALL
    # reservations — including this offer's own, and any unrelated offer the
    # poster happens to have open. The only question here is whether enough
    # cards remain to house everybody once these ones leave.
    committed = (await housing_cards_by_card(db, game, poster)).get(
        offer.offer_card_type, 0
    )
    if poster_hand.quantity - offer.offer_quantity < committed:
        raise ActionError(
            "PROPERTY_OCCUPIED",
            "Someone moved into that property before you settled",
        )

    poster_hand.quantity -= offer.offer_quantity
    poster_hand.reserved_quantity -= offer.offer_quantity
    buyer_hand.quantity += offer.offer_quantity

    if offer.kind == "sell":
        price = _total_price(offer)
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
                "price_points": offer.price_points,
                "total_price_points": price,
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

    # Everyone else's hand comes down with the settle. Nothing was reserved, so
    # the losers simply stop seeing it.
    await _release_claim(db, game, offer)
    offer.settled_with_player_id = buyer.id
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
    if offer.status != "open":
        raise ActionError("OFFER_NOT_OPEN", "That offer is no longer live")

    await _release_claim(db, game, offer)

    # Rent offers reserve nothing, and rent_ask has no card at all — _hand_row
    # would raise UNKNOWN_CARD_TYPE on a NULL.
    if not _is_rent(offer):
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
    """Tidy up after a player leaves: kill their offers, drop their claims."""
    posted = list(await db.scalars(
        select(TradeOffer).where(
            TradeOffer.game_id == game.id,
            TradeOffer.poster_player_id == player.id,
            TradeOffer.status == "open",
        )
    ))
    for offer in posted:
        await _release_claim(db, game, offer)
        if not _is_rent(offer):
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

    # Their hands on OTHER people's offers simply come down. Nothing was
    # reserved, so there is nothing to unwind.
    await db.execute(
        delete(OfferClaim).where(
            OfferClaim.game_id == game.id, OfferClaim.player_id == player.id
        )
    )