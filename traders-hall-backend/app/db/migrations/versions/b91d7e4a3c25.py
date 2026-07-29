"""strip card_types to a code registry

Revision ID: b91d7e4a3c25
Revises: a4f1c0d92e77
Create Date: 2026-07-29 12:00:00.000000

Card attributes move to app/domain/cards.py. The table keeps only its primary
key, because nine foreign keys point at it and referential integrity is worth
more than the columns.

The rows themselves are untouched: every existing code stays, so nothing
pointing at them breaks. sync_card_codes inserts any code the catalogue gains
later, at startup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b91d7e4a3c25'
down_revision: Union[str, Sequence[str], None] = 'a4f1c0d92e77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for column in (
        "title",
        "category",
        "base_cost",
        "sell_value",
        "nutrition_turns",
        "base_output_points",
        "rooms",
        "icon_url",
        "accent_color",
        "background_color",
        "is_tradeable",
        "sort_order",
    ):
        op.drop_column("card_types", column)


def downgrade() -> None:
    """Downgrade schema.

    Columns come back empty. The values live in the catalogue now, and copying
    them into a migration would recreate exactly the duplication this removed —
    re-seed from app/domain/cards.py if you genuinely need them in the table.
    """
    op.add_column("card_types", sa.Column("title", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("card_types", sa.Column("category", sa.String(length=32), nullable=False, server_default=""))
    op.add_column("card_types", sa.Column("base_cost", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("card_types", sa.Column("sell_value", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("card_types", sa.Column("nutrition_turns", sa.Integer(), nullable=True))
    op.add_column("card_types", sa.Column("base_output_points", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("card_types", sa.Column("rooms", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("card_types", sa.Column("icon_url", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("card_types", sa.Column("accent_color", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("card_types", sa.Column("background_color", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("card_types", sa.Column("is_tradeable", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("card_types", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))