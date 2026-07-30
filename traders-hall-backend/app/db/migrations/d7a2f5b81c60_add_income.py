"""add income dice rolls

Revision ID: d7a2f5b81c60
Revises: c5e8a91b7d34
Create Date: 2026-07-29 16:00:00.000000

Income is a roll of two dice once per round. The dice are stored, not just the
payout, so the section can show a player their last roll after a refresh without
replaying the event log.

income_round is the game's turn_number when they last rolled. turn_number
advances once per lap, so comparing the two answers "have I rolled this round"
without a separate flag anyone has to remember to clear.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7a2f5b81c60'
down_revision: Union[str, Sequence[str], None] = 'c5e8a91b7d34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_players", sa.Column("income_round", sa.Integer(), nullable=True))
    op.add_column("game_players", sa.Column("last_die_a", sa.Integer(), nullable=True))
    op.add_column("game_players", sa.Column("last_die_b", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_player_dice_range",
        "game_players",
        "(last_die_a IS NULL OR last_die_a BETWEEN 1 AND 6)"
        " AND (last_die_b IS NULL OR last_die_b BETWEEN 1 AND 6)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_player_dice_range", "game_players", type_="check")
    op.drop_column("game_players", "last_die_b")
    op.drop_column("game_players", "last_die_a")
    op.drop_column("game_players", "income_round")