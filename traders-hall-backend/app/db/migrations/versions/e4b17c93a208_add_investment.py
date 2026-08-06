"""add investments

Revision ID: e4b17c93a208
Revises: d7a2f5b81c60
Create Date: 2026-08-01 10:00:00.000000

An investor buys a share of what one room earns. They put up a principal, take a
percentage of every rent payment that room collects, and the arrangement runs for
a fixed number of the LANDLORD's turns.

The principal is not returned — it buys the share outright — so the investor
profits only if the room earns more than they paid. A room with no tenant earns
nothing, which is the risk: the investor is betting the landlord fills it before
the term expires.

Offers reuse trade_offers, as the rent kinds do. Live investments get their own
table because a landlord can carry several at once, each on its own term and
percentage, which columns cannot hold.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4b17c93a208'
down_revision: Union[str, Sequence[str], None] = 'd7a2f5b81c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Percentage of each rent payment, and how many of the landlord's turns the
    # arrangement lasts. Both are negotiated in the offer, like rent.
    op.add_column(
        "trade_offers", sa.Column("yield_percent", sa.Integer(), nullable=True)
    )
    op.add_column(
        "trade_offers", sa.Column("term_turns", sa.Integer(), nullable=True)
    )

    op.drop_constraint("ck_offer_shape", "trade_offers", type_="check")
    op.create_check_constraint(
        "ck_offer_shape",
        "trade_offers",
        "(kind = 'sell' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NULL"
        " AND yield_percent IS NULL)"
        " OR (kind = 'trade' AND offer_card_type IS NOT NULL AND want_card_type IS NOT NULL"
        " AND price_points IS NULL AND rent_interval_turns IS NULL"
        " AND yield_percent IS NULL)"
        " OR (kind = 'rent_out' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL"
        " AND yield_percent IS NULL)"
        " OR (kind = 'rent_ask' AND offer_card_type IS NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL"
        " AND yield_percent IS NULL)"
        # invest: a principal, a share of the takings, a term, and the property
        # whose room is being bought into.
        " OR (kind = 'invest' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NULL"
        " AND yield_percent IS NOT NULL AND term_turns IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_offer_yield_range",
        "trade_offers",
        "yield_percent IS NULL OR yield_percent BETWEEN 1 AND 100",
    )
    op.create_check_constraint(
        "ck_offer_term_positive",
        "trade_offers",
        "term_turns IS NULL OR term_turns > 0",
    )

    op.create_table(
        "investments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("game_id", sa.UUID(), nullable=False),
        # The one who put up the principal and takes the share.
        sa.Column("investor_player_id", sa.UUID(), nullable=False),
        # The one who owns the room and pays the share out of its rent.
        sa.Column("landlord_player_id", sa.UUID(), nullable=False),
        sa.Column("card_type", sa.String(length=32), nullable=False),
        sa.Column("principal", sa.Integer(), nullable=False),
        sa.Column("yield_percent", sa.Integer(), nullable=False),
        sa.Column("term_turns", sa.Integer(), nullable=False),
        # Counts down on the LANDLORD's end of turn, so a term is that many of
        # their turns however long the table takes to come round.
        sa.Column("turns_remaining", sa.Integer(), nullable=False),
        # What the investor has actually been paid, so the UI can show whether
        # the stake has earned back its principal yet.
        sa.Column("paid_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_turn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investor_player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["landlord_player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_type"], ["card_types.code"]),
        sa.CheckConstraint("principal >= 1", name="ck_investment_principal"),
        sa.CheckConstraint(
            "yield_percent BETWEEN 1 AND 100", name="ck_investment_yield"
        ),
        sa.CheckConstraint("term_turns > 0", name="ck_investment_term"),
        sa.CheckConstraint("turns_remaining >= 0", name="ck_investment_remaining"),
        sa.CheckConstraint(
            "investor_player_id <> landlord_player_id",
            name="ck_investment_distinct_parties",
        ),
    )
    op.create_index("ix_investments_game_id", "investments", ["game_id"])
    op.create_index("ix_investments_investor", "investments", ["investor_player_id"])
    op.create_index("ix_investments_landlord", "investments", ["landlord_player_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_investments_landlord", table_name="investments")
    op.drop_index("ix_investments_investor", table_name="investments")
    op.drop_index("ix_investments_game_id", table_name="investments")
    op.drop_table("investments")

    op.drop_constraint("ck_offer_term_positive", "trade_offers", type_="check")
    op.drop_constraint("ck_offer_yield_range", "trade_offers", type_="check")
    op.drop_constraint("ck_offer_shape", "trade_offers", type_="check")
    op.create_check_constraint(
        "ck_offer_shape",
        "trade_offers",
        "(kind = 'sell' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NULL)"
        " OR (kind = 'trade' AND offer_card_type IS NOT NULL AND want_card_type IS NOT NULL"
        " AND price_points IS NULL AND rent_interval_turns IS NULL)"
        " OR (kind = 'rent_out' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL)"
        " OR (kind = 'rent_ask' AND offer_card_type IS NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL)",
    )
    op.drop_column("trade_offers", "term_turns")
    op.drop_column("trade_offers", "yield_percent")