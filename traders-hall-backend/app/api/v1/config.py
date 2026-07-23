from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.card_type import CardType
from app.schemas.card_type import CardTypeOut

router = APIRouter()

@router.get("/card-types", response_model=list[CardTypeOut])
async def list_card_types(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(CardType).order_by(CardType.sort_order))
    return result.scalars().all()