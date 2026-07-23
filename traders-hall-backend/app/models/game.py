import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # short, human-typeable, unique. The unique index is what actually prevents
    # collisions — the retry loop in the service is just for a nicer error.
    join_code: Mapped[str] = mapped_column(String(6), unique=True, index=True)

    status: Mapped[str] = mapped_column(String(16), default="lobby", index=True)
    host_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    max_players: Mapped[int] = mapped_column(Integer, default=4)

    # bumped on every mutation once the game is running; the optimistic
    # concurrency token from the design doc. Unused this step, but adding it now
    # avoids a migration later.
    state_version: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # ORM convenience: game.players gives the seats without a manual join.
    # cascade delete-orphan means removing a game removes its seats.
    players: Mapped[list["GamePlayer"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GamePlayer.seat_index",
    )