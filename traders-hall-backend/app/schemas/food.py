"""Request body for eating.

Extends ActionRequest, so it carries the optional expected_state_version: eating
is a decision made against a view of your own hand, and it should be rejected if
that view has gone stale.
"""

from pydantic import Field

from app.schemas.action import ActionRequest


class EatRequest(ActionRequest):
    card_type: str = Field(min_length=1, max_length=32)
    # More than one at a time is stockpiling, not a mistake — nutrition adds to
    # whatever is left. The real ceiling is what the player holds free, checked
    # in the service so the error can report the actual number.
    quantity: int = Field(default=1, ge=1, le=99)