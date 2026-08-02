"""Turns the raw state dict from game_service into the API response shape."""

from app.schemas.game_state import (
    GameInfo,
    GameStateOut,
    SeizureOut,
    TenantOut,
    PlayerPublic,
    TenancyOut,
    YouBlock,
)

_NO_ROOMS = {
    "rooms_total": 0,
    "rooms_occupied": 0,
    "rooms_pending": 0,
    "rooms_lettable": 0,
    "rooms_by_card": {},
}


def build_game_state(raw: dict) -> GameStateOut:
    game = raw["game"]
    pools = raw["pools"]
    hands = raw["hands"]
    me = raw["me"]
    # Defaulted rather than required: a caller that has not been updated to
    # supply capacity gets zeros instead of a KeyError, which keeps the whole
    # response alive while the rest catches up.
    rooms = raw.get("rooms", {})
    agreements = raw.get("agreements", [])

    by_seat = {p.id: p for p in game.players}

    # Exactly one active seat remains once a game completes, and that is the
    # winner.
    active = [p for p in game.players if p.status == "active"]
    winner = active[0] if game.status == "completed" and len(active) == 1 else None

    frozen = next(
        (a for a in agreements if a.id == game.seizure_agreement_id),
        None,
    ) if game.phase == "seizure" and game.seizure_agreement_id else None

    seizure = None
    if frozen is not None:
        debtor = by_seat.get(frozen.tenant_player_id)
        landlord = by_seat.get(frozen.landlord_player_id)
        is_mine = frozen.landlord_player_id == me.id
        seizure = SeizureOut(
            agreement_id=frozen.id,
            debtor_player_id=frozen.tenant_player_id,
            debtor_name=debtor.display_name if debtor else "Unknown",
            debtor_seat_index=debtor.seat_index if debtor else -1,
            landlord_player_id=frozen.landlord_player_id,
            landlord_name=landlord.display_name if landlord else "Unknown",
            landlord_seat_index=landlord.seat_index if landlord else -1,
            debt=frozen.seizure_debt or 0,
            card_type=frozen.card_type,
            mine=is_mine,
            # Only the landlord gets the list; it is theirs to choose from.
            seizable=raw.get("seizable", {}) if is_mine else {},
        )

    mine = next((a for a in agreements if a.tenant_player_id == me.id), None)
    tenancy = (
        TenancyOut(
            agreement_id=mine.id,
            landlord_player_id=mine.landlord_player_id,
            card_type=mine.card_type,
            rent_points=mine.rent_points,
            interval_turns=mine.interval_turns,
            turns_until_due=mine.turns_until_due,
            moveout_status=mine.moveout_status,
            moveout_buyout=mine.moveout_buyout,
        )
        if mine is not None
        else None
    )

    # Every live tenancy of mine, whatever state it is in. The landlord can end
    # any of them, so filtering to the ones asking to leave would hide the rest
    # from the only player able to act on them.
    tenants = [
        TenantOut(
            agreement_id=a.id,
            tenant_player_id=a.tenant_player_id,
            tenant_name=by_seat[a.tenant_player_id].display_name
            if a.tenant_player_id in by_seat
            else "Unknown",
            tenant_seat_index=by_seat[a.tenant_player_id].seat_index
            if a.tenant_player_id in by_seat
            else -1,
            card_type=a.card_type,
            rent_points=a.rent_points,
            turns_until_due=a.turns_until_due,
            moveout_status=a.moveout_status,
        )
        for a in agreements
        if a.landlord_player_id == me.id
    ]

    players = [
        PlayerPublic(
            id=p.id,
            seat_index=p.seat_index,
            display_name=p.display_name,
            status=p.status,
            is_bot=p.is_bot,
            points=p.points,
            food_due=p.food_due,
            last_dice=[d for d in (p.last_die_a, p.last_die_b) if d is not None],
            rent_due=p.rent_due,
            hand=hands.get(p.id, {}),
            loan_outstanding=p.loan_outstanding,
            loan_due=p.loan_due,
            mortgage_card_type=p.mortgage_card_type,
            mortgage_outstanding=p.mortgage_outstanding,
            mortgage_due=p.mortgage_due,
            residence_card_type=p.residence_card_type,
            residence_landlord_id=p.residence_landlord_id,
            **_capacity(rooms.get(p.id), public=True),
        )
        for p in sorted(game.players, key=lambda p: p.seat_index)
    ]

    return GameStateOut(
        game=GameInfo(
            id=game.id,
            join_code=game.join_code,
            status=game.status,
            phase=game.phase,
            turn_number=game.turn_number,
            current_player_id=game.current_player_id,
            state_version=game.state_version,
            max_players=game.max_players,
            host_user_id=game.host_user_id,
            started_at=game.started_at,
            winner_player_id=winner.id if winner else None,
            winner_name=winner.display_name if winner else None,
        ),
        bank=pools,
        you=YouBlock(
            player_id=me.id,
            seat_index=me.seat_index,
            points=me.points,
            hand=hands.get(me.id, {}),
            food_due=me.food_due,
            rent_due=me.rent_due,
            is_my_turn=game.current_player_id == me.id,
            status=me.status,
            can_roll_income=_can_roll(game, me),
            roll_blocked_reason=_roll_block(game, me),
            last_dice=[d for d in (me.last_die_a, me.last_die_b) if d is not None],
            last_income=(
                (me.last_die_a + me.last_die_b) // 4
                if me.last_die_a is not None and me.last_die_b is not None
                else 0
            ),
            seizure=seizure,
            loan_outstanding=me.loan_outstanding,
            loan_due=me.loan_due,
            mortgage_card_type=me.mortgage_card_type,
            mortgage_outstanding=me.mortgage_outstanding,
            mortgage_due=me.mortgage_due,
            residence_card_type=me.residence_card_type,
            residence_landlord_id=me.residence_landlord_id,
            **_capacity(rooms.get(me.id), public=False),
            tenancy=tenancy,
            tenants=tenants,
            available_points=me.points - me.reserved_points,
        ),
        players=players,
    )


def _can_roll(game, me) -> bool:
    """Income needs a roof.

    A player with nowhere to live has no household to earn for, so the roll is
    unavailable to them. That makes homelessness bite immediately rather than
    only when the food clock runs out.
    """
    return not _roll_block(game, me)


def _roll_block(game, me) -> str:
    """Why the roll is unavailable, in the order the player would ask.

    Returned as a code rather than a sentence so the client owns the wording,
    and empty when nothing is blocking.
    """
    if me.status != "active" or game.status != "in_progress":
        return "not_your_turn"
    if game.phase == "seizure":
        return "frozen"
    if game.current_player_id != me.id:
        return "not_your_turn"
    if me.residence_card_type is None:
        return "homeless"
    if me.income_round == game.turn_number:
        return "already_rolled"
    return ""


def _capacity(summary: dict | None, *, public: bool) -> dict:
    """Pick the capacity fields each block wants.

    Reads with .get rather than [] on purpose. room_summary lives in
    residence_service and has changed shape once already — it gained
    rooms_pending, which is why the old rooms_free key vanished and this blew up
    with a KeyError on every state poll. A missing number should degrade to zero,
    not take the whole response down.

    rooms_free is what the API calls the lettable count. The names differ because
    the service distinguishes rooms occupied from rooms merely PROMISED by a live
    offer, and only the sum of both is unavailable — the client just needs "how
    many can I let right now".

    The per-card breakdown is `you` only: it drives which properties the let-a-room
    control may offer, a decision only the owner makes. Opponents get the totals,
    since a spare room is public — it is what makes them eligible to answer a
    request.
    """
    data = summary or _NO_ROOMS
    out = {
        "rooms_total": data.get("rooms_total", 0),
        "rooms_occupied": data.get("rooms_occupied", 0),
        "rooms_free": data.get("rooms_lettable", 0),
    }
    if not public:
        out["rooms_by_card"] = data.get("rooms_by_card", {})
    return out