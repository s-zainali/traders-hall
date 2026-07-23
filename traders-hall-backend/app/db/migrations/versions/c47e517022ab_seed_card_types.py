"""seed card_types

Revision ID: c47e517022ab
Revises: 2dca638dae28
Create Date: 2026-07-23 12:19:48.185937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

CARDS = [
    dict(
        code="house", 
        title="House", 
        category="property", 
        base_cost=1, sell_value=1,
        nutrition_turns=None,
        base_output_points=1,
        icon_url="/home.png",
        accent_color="purple-dark",
        background_color="purple-light",
        is_tradeable=True, 
        sort_order=1),
    dict(
        code="mansion", 
        title="Mansion", 
        category="property",   
        base_cost=2, sell_value=2,
        nutrition_turns=None,
        base_output_points=2,
        icon_url="/mansion.png",
        accent_color="purple-dark",
        background_color="purple-light",
        is_tradeable=True, 
        sort_order=2),
    dict(
        code="tower",   
        title="Tower",   
        category="property",   
        base_cost=3, sell_value=3,
        nutrition_turns=None,
        base_output_points=3,
        icon_url="/building.png",
        accent_color="purple-dark",
        background_color="purple-light",
        is_tradeable=True, 
        sort_order=3),
    dict(
        code="rice",    
        title="Rice",    
        category="food",       
        base_cost=1, sell_value=1,
        nutrition_turns=2,   
        base_output_points=0,
        icon_url="/rice.png",
        accent_color="cream-dark", 
        background_color="cream-light",
        is_tradeable=True, 
        sort_order=4),
    dict(
        code="wheat",   
        title="Wheat",   
        category="food",       
        base_cost=1, sell_value=1,
        nutrition_turns=5,   
        base_output_points=0,
        icon_url="/wheat.png",
        accent_color="cream-dark", 
        background_color="cream-light",
        is_tradeable=True, 
        sort_order=5),
    dict(
        code="invest",  
        title="Invest",  
        category="investment", 
        base_cost=1, sell_value=1,
        nutrition_turns=None,
        base_output_points=0,
        icon_url="/investor.png",
        accent_color="blue-dark",  
        background_color="blue-light",
        is_tradeable=True, 
        sort_order=6),
    dict(
        code="point",   
        title="Point",   
        category="currency",   
        base_cost=0, sell_value=0,
        nutrition_turns=None,
        base_output_points=0,
        icon_url="/star.png",
        accent_color="teal-dark",  
        background_color="teal-light",
        is_tradeable=False,
        sort_order=7),
]

# revision identifiers, used by Alembic.
revision: str = 'c47e517022ab'
down_revision: Union[str, Sequence[str], None] = '2dca638dae28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    card_types = sa.table(
        "card_types",
        sa.column("code", sa.String),
        sa.column("title", sa.String),
        sa.column("category", sa.String),
        sa.column("base_cost", sa.Integer),
        sa.column("sell_value", sa.Integer),
        sa.column("nutrition_turns", sa.Integer),
        sa.column("base_output_points", sa.Integer),
        sa.column("icon_url", sa.String),
        sa.column("accent_color", sa.String),
        sa.column("background_color", sa.String),
        sa.column("is_tradeable", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )

    op.bulk_insert(card_types, CARDS)


def downgrade() -> None:
    op.execute("DELETE FROM card_types")
