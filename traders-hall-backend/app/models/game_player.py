import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GamePlayer(Base):
    __tablename__ = "game_players"
    __table_args__ = (
        UniqueConstraint("game_id", "seat_index", name="uq_game_seat"),
        UniqueConstraint("game_id", "user_id", name="uq_game_user"),
        # Bankruptcy is terminal, not an overdraft. A negative balance is
        # unrepresentable by design, so the moment a payment cannot be covered
        # the elimination path runs instead of the number going red.
        CheckConstraint("points >= 0", name="ck_player_points_non_negative"),
        CheckConstraint("reserved_points >= 0", name="ck_player_reserved_non_negative"),
        CheckConstraint("reserved_points <= points", name="ck_player_reserved_le_points"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    # nullable so a bot can occupy a seat with no account behind it
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    seat_index: Mapped[int] = mapped_column(Integer)
    # snapshot at join time, so a later rename does not rewrite match history
    display_name: Mapped[str] = mapped_column(String(64))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="active")

    # --- economy ---
    points: Mapped[int] = mapped_column(Integer, default=0)
    # locked by open market buy offers; unused until the marketplace lands, but
    # here now so that does not need a second migration
    reserved_points: Mapped[int] = mapped_column(Integer, default=0)

    # --- upkeep countdowns, in turns; at zero the obligation falls due ---
    food_due: Mapped[int] = mapped_column(Integer, default=0)
    rent_due: Mapped[int] = mapped_column(Integer, default=0)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # foreign_keys is required now that games.current_player_id creates a second
    # FK between these tables — without it SQLAlchemy cannot tell which one this
    # relationship follows.
    game: Mapped["Game"] = relationship(
        back_populates="players",
        foreign_keys=[game_id],
    )