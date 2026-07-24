"""add loans and mortgages

Revision ID: c8d41a7b93f2
Revises: b2158ed730e0
Create Date: 2026-07-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8d41a7b93f2'
down_revision: Union[str, Sequence[str], None] = 'b2158ed730e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills the rows that already exist, then is dropped so
    # the column matches the model. Leaving it in place would make every future
    # autogenerate emit a spurious default-removal diff.
    op.add_column(
        "game_players",
        sa.Column("loan_outstanding", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_players",
        sa.Column("loan_due", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_players",
        sa.Column("mortgage_card_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "game_players",
        sa.Column("mortgage_outstanding", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "game_players",
        sa.Column("mortgage_due", sa.Integer(), nullable=False, server_default="0"),
    )

    op.alter_column("game_players", "loan_outstanding", server_default=None)
    op.alter_column("game_players", "loan_due", server_default=None)
    op.alter_column("game_players", "mortgage_outstanding", server_default=None)
    op.alter_column("game_players", "mortgage_due", server_default=None)

    op.create_foreign_key(
        "fk_game_players_mortgage_card_type",
        "game_players",
        "card_types",
        ["mortgage_card_type"],
        ["code"],
    )

    op.create_check_constraint(
        "ck_player_loan_non_negative", "game_players", "loan_outstanding >= 0"
    )
    op.create_check_constraint(
        "ck_player_mortgage_non_negative", "game_players", "mortgage_outstanding >= 0"
    )
    op.create_check_constraint(
        "ck_player_mortgage_shape",
        "game_players",
        "(mortgage_card_type IS NULL) = (mortgage_outstanding = 0)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_player_mortgage_shape", "game_players", type_="check")
    op.drop_constraint("ck_player_mortgage_non_negative", "game_players", type_="check")
    op.drop_constraint("ck_player_loan_non_negative", "game_players", type_="check")
    op.drop_constraint(
        "fk_game_players_mortgage_card_type", "game_players", type_="foreignkey"
    )

    op.drop_column("game_players", "mortgage_due")
    op.drop_column("game_players", "mortgage_outstanding")
    op.drop_column("game_players", "mortgage_card_type")
    op.drop_column("game_players", "loan_due")
    op.drop_column("game_players", "loan_outstanding")