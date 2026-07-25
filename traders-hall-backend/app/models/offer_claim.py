import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OfferClaim(Base):
    """One player putting their hand up for an offer.

    A table rather than a column on trade_offers, because an offer is a public
    posting and any number of players may want it. The poster then chooses,
    which is the whole point — the old single-claim column handed the decision
    to whoever clicked first.

    Nothing is reserved when a claim is made. Reserving would mean freezing the
    points or cards of every hopeful for an offer only one of them can win, and
    on a ten-point economy that is a real cost imposed on people who lose. The
    winner is validated at settle instead, and a poster whose pick can no longer
    pay simply picks someone else.
    """

    __tablename__ = "offer_claims"
    __table_args__ = (
        # Pressing claim twice is a double click, not a second bid.
        UniqueConstraint("offer_id", "player_id", name="uq_offer_claim_player"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), index=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trade_offers.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_players.id", ondelete="CASCADE")
    )

    # rent_ask only: which of this claimant's properties the room sits in.
    card_type: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("card_types.code"), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )