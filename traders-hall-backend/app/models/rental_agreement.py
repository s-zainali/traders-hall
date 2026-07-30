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


class RentalAgreement(Base):
    """One tenancy: a tenant occupying one room of a landlord's property.

    A table rather than columns on game_players, unlike loans and mortgages. A
    landlord can hold several tenancies at once — a tower has three rooms — each
    with its own rent, interval and countdown, and columns cannot hold more than
    one of anything.

    Both the rent and the interval are stored per agreement because both are
    negotiated in the offer. Nothing here is a constant.
    """

    __tablename__ = "rental_agreements"
    __table_args__ = (
        CheckConstraint("rent_points >= 1", name="ck_rent_positive"),
        CheckConstraint("interval_turns >= 1", name="ck_rent_interval_positive"),
        CheckConstraint("turns_until_due >= 0", name="ck_rent_due_non_negative"),
        CheckConstraint(
            "landlord_player_id <> tenant_player_id", name="ck_rent_distinct_parties"
        ),
        CheckConstraint(
            "moveout_status IS NULL OR moveout_status IN ('requested', 'rejected')",
            name="ck_rent_moveout_status",
        ),
        CheckConstraint(
            "moveout_buyout IS NULL OR moveout_status = 'rejected'",
            name="ck_rent_moveout_buyout_shape",
        ),
        CheckConstraint(
            "seizure_debt IS NULL OR seizure_debt > 0",
            name="ck_rent_seizure_debt_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )

    landlord_player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )
    tenant_player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE"), index=True
    )

    # Which of the landlord's property types the room belongs to. Hands are
    # counts, not instances, so this identifies the KIND of property rather than
    # a particular card — enough to price it and to count capacity.
    card_type: Mapped[str] = mapped_column(String(32), ForeignKey("card_types.code"))

    rent_points: Mapped[int] = mapped_column(Integer)
    interval_turns: Mapped[int] = mapped_column(Integer)
    # Counts down on the TENANT's end of turn, then resets to interval_turns.
    # Tenant-driven rather than landlord-driven so a player always pays on their
    # own clock, however many landlords or tenants are involved.
    turns_until_due: Mapped[int] = mapped_column(Integer)

    # 'active' | 'ended' | 'defaulted'
    # Ended agreements are kept rather than deleted: they are the record of who
    # lived where, and the ledger references them through their events.
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)

    # --- moving out ---
    # A tenant cannot simply walk. Leaving is a request the landlord answers,
    # because otherwise the turn before rent falls due is a free exit from a
    # period already lived through.
    #
    # NULL       nobody is leaving
    # requested  waiting on the landlord
    # rejected   refused; the tenant now chooses to stay or to pay their way out
    moveout_status: Mapped[str | None] = mapped_column(
        String(16), nullable=True, default=None
    )
    moveout_turn: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    # Frozen when the landlord refuses, so a later rule change cannot reprice a
    # decision the tenant has already been quoted.
    moveout_buyout: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )

    # What is still owed once the tenant's points have been taken. Set only while
    # a seizure is open, and cleared when it resolves.
    seizure_debt: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )

    created_turn: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )