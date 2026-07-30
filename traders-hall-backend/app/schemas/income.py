"""Request body for taking income."""

from app.schemas.action import ActionRequest


class RollIncomeRequest(ActionRequest):
    """No fields of its own. The dice are the server's to roll."""