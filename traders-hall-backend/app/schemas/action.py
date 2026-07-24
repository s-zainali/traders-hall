"""Request bodies for player actions."""

from pydantic import BaseModel, ConfigDict, Field


class ActionRequest(BaseModel):
    """Shared base.

    expected_state_version is optional but strongly encouraged: sending it means
    "apply this only if the world still looks the way I last saw it". Omitting
    it means "apply regardless", which is fine for a fire-and-forget action and
    wrong for anything the player made a decision about.
    """

    model_config = ConfigDict(extra="forbid")

    expected_state_version: int | None = None


class CardTradeRequest(ActionRequest):
    card_type: str = Field(min_length=1, max_length=32)
    # An upper bound here stops a typo'd 99999 reaching the domain layer at all
    quantity: int = Field(ge=1, le=999)