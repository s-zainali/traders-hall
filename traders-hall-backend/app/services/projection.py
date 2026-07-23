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
        ),
        players=players,
    )