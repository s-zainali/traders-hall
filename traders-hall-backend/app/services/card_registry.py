"""Keeps the card_types table in step with the catalogue.

The table exists so nine foreign keys have something to point at. It holds codes
and nothing else, so the only way it can be wrong is by missing one — which
happens the moment somebody adds a card to app/domain/cards.py.

Run at startup. Inserts what is missing and never deletes: a game already
holding a card still has rows referencing it, and a balance pass that drops a
card should not take that history with it.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import cards
from app.models.card_type import CardType


async def sync_card_codes(db: AsyncSession) -> list[str]:
    """Insert any catalogue code the table does not have yet.

    Returns the codes it added, so startup can log them rather than doing this
    silently.
    """
    existing = set(await db.scalars(select(CardType.code)))
    missing = [code for code in cards.ALL_CODES if code not in existing]

    for code in missing:
        db.add(CardType(code=code))

    if missing:
        await db.commit()

    return missing