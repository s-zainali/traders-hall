"""Request body for eating.

Extends ActionRequest, so it carries the optional expected_state_version: eating
is a decision made against a view of your own hand, and it should be rejected if
that view has gone stale.
"""

from pydantic import Field

from app.schemas.action import ActionRequest


class EatRequest(ActionRequest):
    card_type: str = Field(min_length=1, max_length=32)
    # No quantity. Nutrition raises food_due TO the card's value rather than
    # adding onto it, so a second card in the same meal cannot raise a ceiling
    # the first already reached — it would only burn food for nothing.