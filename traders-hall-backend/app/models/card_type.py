from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CardType(Base):
    __tablename__ = "card_types"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))

    base_cost: Mapped[int] = mapped_column(default=0)
    sell_value: Mapped[int] = mapped_column(default=0)

    # food only: how many turns of food_due one card restores
    nutrition_turns: Mapped[int | None] = mapped_column(default=None)
    # properties only: points produced per yield interval before investment
    base_output_points: Mapped[int] = mapped_column(default=0)

    icon_url: Mapped[str] = mapped_column(String(255))
    accent_color: Mapped[str] = mapped_column(String(64))
    background_color: Mapped[str] = mapped_column(String(64))

    is_tradeable: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)