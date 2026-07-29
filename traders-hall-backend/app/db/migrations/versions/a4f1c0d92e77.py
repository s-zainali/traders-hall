"""add tenancy move-out requests

Revision ID: a4f1c0d92e77
Revises: f2b6d80c4a51
Create Date: 2026-07-29 10:00:00.000000

A tenant could walk out the turn before rent fell due and pay nothing for the
period they had just lived through. Leaving a RENTED room is now a request the
landlord answers.

Three columns rather than a table: a tenancy has at most one move-out in flight,
and the whole exchange is over within a couple of turns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4f1c0d92e77'
down_revision: Union[str, Sequence[str], None] = 'f2b6d80c4a51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NULL = nobody is trying to leave. 'requested' = waiting on the landlord.
    # 'rejected' = refused, and the tenant now picks between staying and paying
    # their way out.
    op.add_column(
        "rental_agreements",
        sa.Column("moveout_status", sa.String(length=16), nullable=True),
    )
    # The turn it was raised, so the log and the UI can say how long the
    # landlord has been sitting on it.
    op.add_column(
        "rental_agreements",
        sa.Column("moveout_turn", sa.Integer(), nullable=True),
    )
    # What leaving costs, frozen when the landlord refuses. Stored rather than
    # recomputed so a later rule change cannot silently reprice a decision the
    # tenant has already been quoted.
    op.add_column(
        "rental_agreements",
        sa.Column("moveout_buyout", sa.Integer(), nullable=True),
    )

    op.create_check_constraint(
        "ck_rent_moveout_status",
        "rental_agreements",
        "moveout_status IS NULL OR moveout_status IN ('requested', 'rejected')",
    )
    # A quoted price only makes sense once the landlord has refused.
    op.create_check_constraint(
        "ck_rent_moveout_buyout_shape",
        "rental_agreements",
        "moveout_buyout IS NULL OR moveout_status = 'rejected'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_rent_moveout_buyout_shape", "rental_agreements", type_="check")
    op.drop_constraint("ck_rent_moveout_status", "rental_agreements", type_="check")
    op.drop_column("rental_agreements", "moveout_buyout")
    op.drop_column("rental_agreements", "moveout_turn")
    op.drop_column("rental_agreements", "moveout_status")