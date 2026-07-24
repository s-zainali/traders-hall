import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TradeOffer(Base):
    __tablename__ = "trade_offers"
    __table_args__ = (
        CheckConstraint("offer_quantity > 0", name="ck_offer_qty_positive"),
        CheckConstraint(
            "(kind = 'sell' AND price_points IS NOT NULL AND want_card_type IS NULL)"
            " OR (kind = 'trade' AND want_card_type IS NOT NULL AND price_points IS NULL)",
            name="ck_offer_shape",
        ),
        CheckConstraint(
            "(status = 'claimed') = (claimed_by_player_id IS NOT NULL)",
            name="ck_offer_claim_consistent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    poster_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )

    kind: Mapped[str] = mapped_column(String(8))

    offer_card_type: Mapped[str] = mapped_column(String(32), ForeignKey("card_types.code"))
    offer_quantity: Mapped[int] = mapped_column(Integer)

    price_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    want_card_type: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("card_types.code"), nullable=True
    )
    want_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)

    claimed_by_player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    settled_with_player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    created_turn: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)