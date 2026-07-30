"""add rent seizure state

Revision ID: c5e8a91b7d34
Revises: b91d7e4a3c25
Create Date: 2026-07-29 14:00:00.000000

When a tenant cannot cover rent and their cards COULD cover it, the landlord
chooses which cards to take — a decision by another player, out of turn. The game
freezes while it is pending, because otherwise value can be moved out from under
the choice.

games.phase carries the freeze ('seizure'); games.seizure_agreement_id says which
tenancy is waiting; rental_agreements.seizure_debt is what is still owed.

Only one seizure can be open at a time, which is why this is a column on games
rather than a queue: the game is stopped, so a second one cannot begin.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c5e8a91b7d34'
down_revision: Union[str, Sequence[str], None] = 'b91d7e4a3c25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("games", sa.Column("seizure_agreement_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_games_seizure_agreement",
        "games", "rental_agreements",
        ["seizure_agreement_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "rental_agreements", sa.Column("seizure_debt", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        "ck_rent_seizure_debt_positive",
        "rental_agreements",
        "seizure_debt IS NULL OR seizure_debt > 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_rent_seizure_debt_positive", "rental_agreements", type_="check")
    op.drop_column("rental_agreements", "seizure_debt")
    op.drop_constraint("fk_games_seizure_agreement", "games", type_="foreignkey")
    op.drop_column("games", "seizure_agreement_id")