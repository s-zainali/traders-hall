"""add offer claims table

Revision ID: f2b6d80c4a51
Revises: e7c4b91a2f38
Create Date: 2026-07-25 15:00:00.000000

An offer used to hold ONE claimant in trade_offers.claimed_by_player_id, so the
first player to press claim locked everyone else out and the poster had no
choice to make. Claims move to their own table: any number of players may put
their hand up, the poster sees them all and picks one.

The old columns are left in place rather than dropped. claimed_by_player_id is
now unused, but dropping a column is irreversible against live data and this
migration is already replacing a constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f2b6d80c4a51'
down_revision: Union[str, Sequence[str], None] = 'e7c4b91a2f38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "offer_claims",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("offer_id", sa.UUID(), nullable=False),
        sa.Column("player_id", sa.UUID(), nullable=False),
        # rent_ask only: which of this claimant's properties the room is in.
        # A landlord answering a request has to name it, and the request itself
        # carries no property.
        sa.Column("card_type", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["offer_id"], ["trade_offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["game_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_type"], ["card_types.code"]),
        # One hand up per player per offer. Pressing claim twice is a double
        # click, not a second bid.
        sa.UniqueConstraint("offer_id", "player_id", name="uq_offer_claim_player"),
    )
    op.create_index("ix_offer_claims_offer_id", "offer_claims", ["offer_id"])
    op.create_index("ix_offer_claims_game_id", "offer_claims", ["game_id"])

    # An offer with claims stays 'open' — more players may still join — so the
    # status can no longer imply a claimant.
    op.drop_constraint("ck_offer_claim_consistent", "trade_offers", type_="check")

    # Anything mid-claim under the old model is migrated across, so a game in
    # progress does not lose its offers.
    op.execute(
        """
        INSERT INTO offer_claims (id, game_id, offer_id, player_id, card_type)
        SELECT gen_random_uuid(), game_id, id, claimed_by_player_id, claim_card_type
        FROM trade_offers
        WHERE claimed_by_player_id IS NOT NULL
        """
    )
    op.execute("UPDATE trade_offers SET status = 'open' WHERE status = 'claimed'")


def downgrade() -> None:
    """Downgrade schema."""
    # Collapse back to one claimant per offer, keeping the earliest.
    op.execute(
        """
        UPDATE trade_offers t
        SET claimed_by_player_id = c.player_id,
            claim_card_type = c.card_type,
            status = 'claimed'
        FROM (
            SELECT DISTINCT ON (offer_id) offer_id, player_id, card_type
            FROM offer_claims ORDER BY offer_id, created_at
        ) c
        WHERE c.offer_id = t.id AND t.status = 'open'
        """
    )
    op.drop_index("ix_offer_claims_game_id", table_name="offer_claims")
    op.drop_index("ix_offer_claims_offer_id", table_name="offer_claims")
    op.drop_table("offer_claims")

    op.create_check_constraint(
        "ck_offer_claim_consistent",
        "trade_offers",
        "(status = 'claimed') = (claimed_by_player_id IS NOT NULL)",
    )