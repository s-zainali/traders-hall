import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OfferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(sell|trade)$")
    offer_card_type: str = Field(min_length=1, max_length=32)
    offer_quantity: int = Field(ge=1, le=99)

    price_points: int | None = Field(default=None, ge=1, le=999)
    want_card_type: str | None = Field(default=None, min_length=1, max_length=32)
    want_quantity: int | None = Field(default=None, ge=1, le=99)

    expected_state_version: int | None = None

    @model_validator(mode="after")
    def check_shape(self):
        if self.kind == "sell":
            if self.price_points is None:
                raise ValueError("price_points is required for a sell offer")
            if self.want_card_type is not None:
                raise ValueError("want_card_type is not allowed on a sell offer")
        else:
            if self.want_card_type is None or self.want_quantity is None:
                raise ValueError("want_card_type and want_quantity are required for a trade")
            if self.price_points is not None:
                raise ValueError("price_points is not allowed on a trade offer")
            if self.want_card_type == self.offer_card_type:
                raise ValueError("Trade the card for a different one")
        return self


class OfferAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_state_version: int | None = None


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    poster_player_id: uuid.UUID
    poster_name: str
    poster_seat_index: int
    kind: str
    offer_card_type: str
    offer_quantity: int
    price_points: int | None
    want_card_type: str | None
    want_quantity: int | None
    status: str
    claimed_by_player_id: uuid.UUID | None
    claimed_by_name: str | None
    claimed_by_seat_index: int | None
    created_turn: int
    created_at: datetime