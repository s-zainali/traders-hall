"""Reference data for clients.

Served from the catalogue rather than the table. The table holds codes only —
every value below is configuration, so this endpoint reads the same source the
game rules read and cannot disagree with them.
"""

from fastapi import APIRouter

from app.domain import cards
from app.schemas.card_type import CardTypeOut

router = APIRouter()


@router.get("/card-types", response_model=list[CardTypeOut])
async def list_card_types():
    return [CardTypeOut.model_validate(card) for card in cards.sorted_cards()]