"""Turns the raw state dict from game_service into the API response shape."""

from app.schemas.game_state import GameInfo, GameStateOut, PlayerPublic, YouBlock


def build_game_state(raw: dict) -> GameStateOut:
    game = raw["game"]
    pools = raw["pools"]
    hands = raw["hands"]
    me = raw["me"]

    players = [
        PlayerPublic(
            id=p.id,
            seat_index=p.seat_index,
            display_name=p.display_name,
            status=p.status,
            is_bot=p.is_bot,
            points=p.points,
            food_due=p.food_due,
            rent_due=p.rent_due,
            hand=hands.get(p.id, {}),
            loan_outstanding=p.loan_outstanding,
            loan_due=p.loan_due,
            mortgage_card_type=p.mortgage_card_type,
            mortgage_outstanding=p.mortgage_outstanding,
            mortgage_due=p.mortgage_due,
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
            loan_outstanding=me.loan_outstanding,
            loan_due=me.loan_due,
            mortgage_card_type=me.mortgage_card_type,
            mortgage_outstanding=me.mortgage_outstanding,
            mortgage_due=me.mortgage_due,
            available_points=me.points - me.reserved_points,
        ),
        players=players,
    )