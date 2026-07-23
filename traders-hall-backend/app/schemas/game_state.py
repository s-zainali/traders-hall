"""Response shapes for the game state projection.

Built by hand rather than from_attributes, because the response draws on four
tables and splits into a public part and a private one — a shape no single
table has.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class GameInfo(BaseModel):
    id: uuid.UUID
    join_code: str
    status: str
    phase: str
    turn_number: int
    current_player_id: uuid.UUID | None
    state_version: int
    max_players: int
    host_user_id: uuid.UUID
    started_at: datetime | None


class PlayerPublic(BaseModel):
    """Hands are public in this game, so this is genuinely the full picture."""

    id: uuid.UUID
    seat_index: int
    display_name: str
    status: str
    is_bot: bool
    points: int
    food_due: int
    rent_due: int
    hand: dict[str, int]


class YouBlock(BaseModel):
    """The private slice.

    Everything here is also in `players` today, since hands are public. The
    block exists anyway so that making hands secret later is a one-field change
    rather than a reshape — and `legal_actions` will never be public.
    """

    player_id: uuid.UUID
    seat_index: int
    points: int
    hand: dict[str, int]
    food_due: int
    rent_due: int
    is_my_turn: bool


class GameStateOut(BaseModel):
    game: GameInfo
    bank: dict[str, int]
    you: YouBlock
    players: list[PlayerPublic]