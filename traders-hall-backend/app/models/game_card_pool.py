import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameCardPool(Base):
    """The bank's stock: one row per card type per game."""

    __tablename__ = "game_card_pools"
    __table_args__ = (
        # The last line of defence against overselling. Application code checks
        # first for a good error message; this is what makes it CORRECT if that
        # check ever races.
        CheckConstraint("quantity >= 0", name="ck_pool_non_negative"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    card_type: Mapped[str] = mapped_column(
        String(32), ForeignKey("card_types.code"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)