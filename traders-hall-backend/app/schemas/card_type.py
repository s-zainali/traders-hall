from pydantic import BaseModel, ConfigDict


class CardTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    category: str
    base_cost: int
    sell_value: int
    nutrition_turns: int | None
    base_output_points: int
    icon_url: str
    accent_color: str
    background_color: str
    is_tradeable: bool
    sort_order: int