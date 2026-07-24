import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameEvent(Base):
    """Append-only log of everything that happened in a game.

    Four things for the price of one table: reconnect (replay from a seq), audit
    (who did what), debugging (deterministic replay of a bug report), and the
    payload a WebSocket will eventually push.

    This is NOT event sourcing — current state lives in normal tables and stays
    authoritative. The log is a parallel record.
    """

    __tablename__ = "game_events"
    __table_args__ = (
        # This constraint is what makes ordering gapless under concurrency. A
        # duplicate seq is a hard failure, never a retry — and gaplessness is
        # what lets a client detect a dropped message by seeing a seq that is
        # not last + 1.
        UniqueConstraint("game_id", "seq", name="uq_event_game_seq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(BigInteger)

    event_type: Mapped[str] = mapped_column(String(48))
    # null when the server acted rather than a player (upkeep, turn advance)
    actor_player_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    state_version_after: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )