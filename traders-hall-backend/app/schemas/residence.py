"""Request bodies for housing actions."""

from pydantic import Field
import uuid

from app.schemas.action import ActionRequest


class MoveInRequest(ActionRequest):
    card_type: str = Field(min_length=1, max_length=32)


class LeaveResidenceRequest(ActionRequest):
    """No fields of its own: a player lives in at most one place."""

class MoveOutResponseRequest(ActionRequest):
    """The landlord answering a tenant who wants out."""
 
    agreement_id: uuid.UUID
    # False refuses, which quotes the tenant a buy-out rather than ending
    # anything. There is no third answer.
    accept: bool
 
 
class MoveOutResolveRequest(ActionRequest):
    """The tenant choosing, after a refusal."""
 
    # True pays the quoted penalty and goes; False stays and clears the request.
    leave: bool
