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
    # House 1, mansion 2, tower 3. Sent so the client can size a property's
    # capacity without hardcoding the same table a second time.
    rooms: int
    icon_url: str
    accent_color: str
    background_color: str
    is_tradeable: bool
    sort_order: int