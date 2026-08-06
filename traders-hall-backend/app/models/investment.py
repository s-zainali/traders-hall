import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Investment(Base):
    """A share of what one room earns.

    The investor puts up a principal and takes a percentage of every rent
    payment that property collects, for a fixed number of the landlord's turns.

    The principal is NOT returned: it buys the share outright, so the investor
    profits only if the room earns more than they paid. A room with no tenant
    earns nothing, which is the risk they are taking — they are betting the
    landlord fills it before the term runs out.

    A table rather than columns, because a landlord can carry several at once,
    each with its own percentage and its own clock.
    """

    __tablename__ = "investments"
    __table_args__ = (
        CheckConstraint("principal >= 1", name="ck_investment_principal"),
        CheckConstraint("yield_percent BETWEEN 1 AND 100", name="ck_investment_yield"),
        CheckConstraint("term_turns > 0", name="ck_investment_term"),
        CheckConstraint("turns_remaining >= 0", name="ck_investment_remaining"),
        CheckConstraint(
            "investor_player_id <> landlord_player_id",
            name="ck_investment_distinct_parties",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )

    investor_player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )
    landlord_player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )

    # Which property type the invested room belongs to. Hands are counts rather
    # than instances, so this names the KIND — enough to match rent payments
    # against it, which is all the payout needs.
    card_type: Mapped[str] = mapped_column(String(32), ForeignKey("card_types.code"))

    principal: Mapped[int] = mapped_column(Integer)
    yield_percent: Mapped[int] = mapped_column(Integer)
    term_turns: Mapped[int] = mapped_column(Integer)

    # Counts down when the LANDLORD ends a turn, so a term of five is five of
    # their turns regardless of how long the lap takes.
    turns_remaining: Mapped[int] = mapped_column(Integer)

    # Running total actually paid to the investor, so the UI can show whether
    # the stake has earned back its principal yet.
    paid_out: Mapped[int] = mapped_column(Integer, default=0)

    # 'active' | 'ended'
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)

    created_turn: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )