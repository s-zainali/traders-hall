"""Request bodies for housing actions."""

from pydantic import Field

from app.schemas.action import ActionRequest


class MoveInRequest(ActionRequest):
    card_type: str = Field(min_length=1, max_length=32)


class LeaveResidenceRequest(ActionRequest):
    """No fields of its own: a player lives in at most one place."""