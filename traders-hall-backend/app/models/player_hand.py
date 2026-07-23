import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlayerHand(Base):
    """A player's card counts: one row per card type.

    Counts rather than one row per physical card. The UI only ever shows counts,
    and "does this player have 3 rice" becomes a single row read. Cards that
    later acquire per-instance state (a mortgaged property) get their own table.
    """

    __tablename__ = "player_hands"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_hand_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_hand_reserved_non_negative"),
        CheckConstraint("reserved_quantity <= quantity", name="ck_hand_reserved_le_qty"),
    )

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("game_players.id", ondelete="CASCADE"), primary_key=True
    )
    card_type: Mapped[str] = mapped_column(
        String(32), ForeignKey("card_types.code"), primary_key=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=0)
    # Locked by open market offers, so one card cannot back two of them. Unused
    # until the marketplace lands; here now to avoid a second migration.
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)