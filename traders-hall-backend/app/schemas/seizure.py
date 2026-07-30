"""Request bodies for resolving a frozen game."""

from pydantic import Field

from app.schemas.action import ActionRequest


class SeizeCardsRequest(ActionRequest):
    """Which of the tenant's cards the landlord is taking.

    A mapping of card code to quantity. It must be worth at least the debt, and
    no single pick may be droppable while still covering it — the landlord
    collects what they are owed, not a hand.
    """

    picks: dict[str, int] = Field(min_length=1)


class WaiveSeizureRequest(ActionRequest):
    """The landlord letting the debt go, which also unfreezes the game."""