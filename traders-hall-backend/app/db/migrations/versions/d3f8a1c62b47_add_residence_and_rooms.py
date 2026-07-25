"""add residence, rooms and rental agreements

Revision ID: d3f8a1c62b47
Revises: c8d41a7b93f2
Create Date: 2026-07-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3f8a1c62b47'
down_revision: Union[str, Sequence[str], None] = 'c8d41a7b93f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ── rooms ────────────────────────────────────────────────────────
    # A property's capacity, as its own column rather than reusing
    # base_output_points. Those two happen to hold the same numbers today
    # (1/2/3), which is exactly why they should not share a column: yield and
    # capacity are different rules and will be balanced separately.
    op.add_column(
        "card_types",
        sa.Column("rooms", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("card_types", "rooms", server_default=None)

    op.execute("UPDATE card_types SET rooms = 1 WHERE code = 'house'")
    op.execute("UPDATE card_types SET rooms = 2 WHERE code = 'mansion'")
    op.execute("UPDATE card_types SET rooms = 3 WHERE code = 'tower'")

    # ── where a player lives ─────────────────────────────────────────
    # residence_landlord_id NULL with a residence set means "my own property".
    # Kept on game_players rather than derived from rental_agreements because
    # a player living in their own house has no agreement to derive it from.
    op.add_column(
        "game_players",
        sa.Column("residence_card_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "game_players",
        sa.Column("residence_landlord_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_game_players_residence_card_type",
        "game_players", "card_types",
        ["residence_card_type"], ["code"],
    )
    op.create_foreign_key(
        "fk_game_players_residence_landlord",
        "game_players", "game_players",
        ["residence_landlord_id"], ["id"],
        ondelete="SET NULL",
    )
    # A landlord without a residence is incoherent: you cannot be renting a room
    # from someone and living nowhere.
    op.create_check_constraint(
        "ck_player_residence_shape",
        "game_players",
        "residence_landlord_id IS NULL OR residence_card_type IS NOT NULL",
    )
    # You cannot rent from yourself — that is owning, and it is expressed by a
    # NULL landlord.
    op.create_check_constraint(
        "ck_player_not_own_landlord",
        "game_players",
        "residence_landlord_id IS NULL OR residence_landlord_id <> id",
    )

    # ── rental agreements ────────────────────────────────────────────
    # Its own table, unlike loans and mortgages: a landlord can have several
    # tenants at once, each on their own rent, interval and countdown. Columns
    # on game_players could not hold more than one.
    op.create_table(
        "rental_agreements",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("landlord_player_id", sa.UUID(), nullable=False),
        sa.Column("tenant_player_id", sa.UUID(), nullable=False),
        sa.Column("card_type", sa.String(length=32), nullable=False),
        # Both set by the players in the offer, never hardcoded: rent is a
        # negotiated number and so is how often it falls due.
        sa.Column("rent_points", sa.Integer(), nullable=False),
        sa.Column("interval_turns", sa.Integer(), nullable=False),
        sa.Column("turns_until_due", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_turn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["landlord_player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_type"], ["card_types.code"]),
        sa.CheckConstraint("rent_points >= 1", name="ck_rent_positive"),
        sa.CheckConstraint("interval_turns >= 1", name="ck_rent_interval_positive"),
        sa.CheckConstraint("turns_until_due >= 0", name="ck_rent_due_non_negative"),
        sa.CheckConstraint(
            "landlord_player_id <> tenant_player_id", name="ck_rent_distinct_parties"
        ),
    )
    op.create_index("ix_rental_agreements_game_id", "rental_agreements", ["game_id"])
    op.create_index(
        "ix_rental_agreements_landlord", "rental_agreements", ["landlord_player_id"]
    )
    op.create_index(
        "ix_rental_agreements_tenant", "rental_agreements", ["tenant_player_id"]
    )
    # One live tenancy per tenant. A partial unique index rather than a plain
    # one, so ended agreements stay on the record as history.
    op.create_index(
        "uq_rental_active_tenant",
        "rental_agreements",
        ["tenant_player_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # ── rent offers on the existing marketplace ──────────────────────
    # kind was String(8), which fits 'rent_out' and 'rent_ask' but nothing
    # longer — widened now so a future kind is not another migration.
    op.alter_column(
        "trade_offers", "kind",
        existing_type=sa.String(length=8), type_=sa.String(length=16),
    )
    # A tenant's request names no property: it broadcasts, and any landlord with
    # a free room can accept. So the card becomes optional, guarded per kind by
    # the shape constraint below.
    op.alter_column(
        "trade_offers", "offer_card_type",
        existing_type=sa.String(length=32), nullable=True,
    )
    op.add_column(
        "trade_offers",
        sa.Column("rent_interval_turns", sa.Integer(), nullable=True),
    )

    op.drop_constraint("ck_offer_shape", "trade_offers", type_="check")
    op.create_check_constraint(
        "ck_offer_shape",
        "trade_offers",
        # sell:      a card for points
        # trade:     a card for another card
        # rent_out:  a landlord's room, at a rent and an interval
        # rent_ask:  a tenant's request, at a rent and an interval, no card
        "(kind = 'sell' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NULL)"
        " OR (kind = 'trade' AND offer_card_type IS NOT NULL AND want_card_type IS NOT NULL"
        " AND price_points IS NULL AND rent_interval_turns IS NULL)"
        " OR (kind = 'rent_out' AND offer_card_type IS NOT NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL)"
        " OR (kind = 'rent_ask' AND offer_card_type IS NULL AND price_points IS NOT NULL"
        " AND want_card_type IS NULL AND rent_interval_turns IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_offer_shape", "trade_offers", type_="check")
    op.create_check_constraint(
        "ck_offer_shape",
        "trade_offers",
        "(kind = 'sell' AND price_points IS NOT NULL AND want_card_type IS NULL)"
        " OR (kind = 'trade' AND want_card_type IS NOT NULL AND price_points IS NULL)",
    )
    op.drop_column("trade_offers", "rent_interval_turns")
    op.alter_column(
        "trade_offers", "offer_card_type",
        existing_type=sa.String(length=32), nullable=False,
    )
    op.alter_column(
        "trade_offers", "kind",
        existing_type=sa.String(length=16), type_=sa.String(length=8),
    )

    op.drop_index("uq_rental_active_tenant", table_name="rental_agreements")
    op.drop_index("ix_rental_agreements_tenant", table_name="rental_agreements")
    op.drop_index("ix_rental_agreements_landlord", table_name="rental_agreements")
    op.drop_index("ix_rental_agreements_game_id", table_name="rental_agreements")
    op.drop_table("rental_agreements")

    op.drop_constraint("ck_player_not_own_landlord", "game_players", type_="check")
    op.drop_constraint("ck_player_residence_shape", "game_players", type_="check")
    op.drop_constraint(
        "fk_game_players_residence_landlord", "game_players", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_game_players_residence_card_type", "game_players", type_="foreignkey"
    )
    op.drop_column("game_players", "residence_landlord_id")
    op.drop_column("game_players", "residence_card_type")

    op.drop_column("card_types", "rooms")