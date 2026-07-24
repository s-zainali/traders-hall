"""Feed shapes: the game event log, which chat lives inside."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    event_type: str
    actor_player_id: uuid.UUID | None
    payload: dict
    created_at: datetime


class ChatSend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 500 is generous for a game chat and stops a single message from bloating
    # every subsequent feed poll for the rest of the match.
    text: str = Field(min_length=1, max_length=500)