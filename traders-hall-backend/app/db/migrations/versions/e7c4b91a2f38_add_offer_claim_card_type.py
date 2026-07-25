"""add claim_card_type to trade offers

Revision ID: e7c4b91a2f38
Revises: d3f8a1c62b47
Create Date: 2026-07-25 13:00:00.000000

A landlord claiming a tenant's rent_ask has to say WHICH of their properties the
room is in — they may own a house and a tower, and the rent is the same either
way but the capacity is not. There was nowhere to record that between the claim
and the confirm: offer_card_type and want_card_type are both pinned NULL for
rent_ask by ck_offer_shape, so reusing either would violate it.

Resolving it at confirm time by picking the landlord's first property with a
spare room was the alternative. That takes the choice away from the landlord for
no gain beyond avoiding this column.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e7c4b91a2f38'
down_revision: Union[str, Sequence[str], None] = 'd3f8a1c62b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "trade_offers",
        sa.Column("claim_card_type", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_trade_offers_claim_card_type",
        "trade_offers", "card_types",
        ["claim_card_type"], ["code"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_trade_offers_claim_card_type", "trade_offers", type_="foreignkey"
    )
    op.drop_column("trade_offers", "claim_card_type")