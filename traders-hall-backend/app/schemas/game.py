"""Lobby-level game shapes.

The richer in-game projection lives in app/schemas/game_state.py — this file is
only the create/list/detail shapes the lobby needs.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GameCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 2-4 enforced here as a shape rule, so a bad value comes back as a 422 with
    # a clear field error rather than as a domain exception from deeper in.
    max_players: int = Field(default=4, ge=2, le=4)


class GamePlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seat_index: int
    display_name: str
    is_bot: bool
    status: str

class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heir_player_id: uuid.UUID | None = None

class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    join_code: str
    status: str
    # the lobby needs this to decide who sees Delete vs Leave
    host_user_id: uuid.UUID
    max_players: int
    created_at: datetime
    started_at: datetime | None
    players: list[GamePlayerOut]