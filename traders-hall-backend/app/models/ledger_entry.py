import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LedgerEntry(Base):
    """Every movement of value, double-entry style.

    The invariant worth asserting in tests: for any game, SUM(points_delta)
    across all entries INCLUDING the bank is zero. Points are conserved; they
    only move. If that sum drifts, some rule has a leak — and this table is the
    only way to find out which one.
    """

    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("game_events.id", ondelete="CASCADE")
    )
    # null means the bank — the counterparty in every bank transaction
    player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    entry_type: Mapped[str] = mapped_column(String(32))
    points_delta: Mapped[int] = mapped_column(Integer, default=0)
    card_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_delta: Mapped[int] = mapped_column(Integer, default=0)

    turn_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )