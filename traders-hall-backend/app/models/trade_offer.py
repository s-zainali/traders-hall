import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TradeOffer(Base):
    """A posting on the marketplace. Four kinds, one table.

    'sell'      a card for points
    'trade'     a card for another card
    'rent_out'  a landlord offering one room, at a rent and an interval
    'rent_ask'  a tenant requesting a room, at a rent and an interval
    'invest'    a stake in what one property earns, at a principal, a share and
                a term

    The rent kinds live here rather than in their own table because they share
    the whole lifecycle — post, claim, decline, confirm, cancel — and duplicating
    that state machine is worse than one nullable column. The cost is that
    offer_card_type is nullable now: a tenant's request names no property,
    because it broadcasts and any landlord with a free room may accept. The
    shape constraint below is what keeps each kind honest.
    """

    __tablename__ = "trade_offers"
    __table_args__ = (
        CheckConstraint("offer_quantity > 0", name="ck_offer_qty_positive"),
        CheckConstraint(
            "(kind = 'sell' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
            " AND want_card_type IS NULL AND rent_interval_turns IS NULL)"
            " OR (kind = 'trade' AND offer_card_type IS NOT NULL AND want_card_type IS NOT NULL"
            " AND price_points IS NULL AND rent_interval_turns IS NULL)"
            " OR (kind = 'rent_out' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
            " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL)"
            " OR (kind = 'rent_ask' AND offer_card_type IS NULL AND price_points IS NOT NULL"
            " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL"
            " AND yield_percent IS NULL)"
            " OR (kind = 'invest' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
            " AND want_card_type IS NULL AND rent_interval_turns IS NULL"
            " AND yield_percent IS NOT NULL AND term_turns IS NOT NULL)",
            name="ck_offer_shape",
        ),
        CheckConstraint(
            "yield_percent IS NULL OR yield_percent BETWEEN 1 AND 100",
            name="ck_offer_yield_range",
        ),
        CheckConstraint(
            "term_turns IS NULL OR term_turns > 0", name="ck_offer_term_positive"
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

    kind: Mapped[str] = mapped_column(String(16))

    # NULL only for 'rent_ask' — see the class docstring.
    offer_card_type: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("card_types.code"), nullable=True
    )
    # cards for sell/trade; rooms for the rent kinds, which is always 1
    offer_quantity: Mapped[int] = mapped_column(Integer)

    # PER UNIT for 'sell'; the rent per payment for the rent kinds
    price_points: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # How many of the tenant's turns between rent payments. Set in the offer, not
    # from a constant: the interval is part of what the two players agree on.
    rent_interval_turns: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # invest only: the investor's share of each rent payment, and how many of the
    # landlord's turns the arrangement runs for. Both negotiated in the offer.
    yield_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    term_turns: Mapped[int | None] = mapped_column(Integer, nullable=True)

    want_card_type: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("card_types.code"), nullable=True
    )
    want_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)

    claimed_by_player_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # rent_ask only: which of the CLAIMANT's properties the room is in. A
    # landlord answering a request has to name it, and neither offer_card_type
    # nor want_card_type can hold it — ck_offer_shape pins both NULL for that
    # kind.
    claim_card_type: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("card_types.code"), nullable=True
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