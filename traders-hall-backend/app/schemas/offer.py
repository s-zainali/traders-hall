import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OfferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(sell|trade|rent_out|rent_ask|invest)$")
    # NULL only for rent_ask, which names no property: it broadcasts, and any
    # landlord with a spare room may accept.
    offer_card_type: str | None = Field(default=None, min_length=1, max_length=32)
    # cards for sell and trade; rooms for the rent kinds, always 1
    offer_quantity: int = Field(default=1, ge=1, le=99)

    # PER UNIT for sell; the whole rent per payment for the rent kinds
    price_points: int | None = Field(default=None, ge=1, le=999)
    # How many of the tenant's turns between payments. Negotiated in the offer,
    # never a constant.
    rent_interval_turns: int | None = Field(default=None, ge=1, le=99)
    # invest only: the investor's share of each rent payment, and how many of the
    # landlord's turns the stake runs for.
    yield_percent: int | None = Field(default=None, ge=1, le=100)
    term_turns: int | None = Field(default=None, ge=1, le=99)
    want_card_type: str | None = Field(default=None, min_length=1, max_length=32)
    want_quantity: int | None = Field(default=None, ge=1, le=99)

    expected_state_version: int | None = None

    @model_validator(mode="after")
    def check_shape(self):
        """Reject a body that cannot mean anything before it reaches the domain.

        Mirrors ck_offer_shape in the database. The constraint is the real
        guarantee; this exists so a malformed request comes back as a readable
        422 rather than an IntegrityError.
        """
        if self.kind == "sell":
            if self.offer_card_type is None:
                raise ValueError("offer_card_type is required for a sell offer")
            if self.price_points is None:
                raise ValueError("price_points is required for a sell offer")
            if self.want_card_type is not None:
                raise ValueError("want_card_type is not allowed on a sell offer")
            if self.rent_interval_turns is not None:
                raise ValueError("rent_interval_turns is not allowed on a sell offer")
        elif self.kind == "trade":
            if self.offer_card_type is None:
                raise ValueError("offer_card_type is required for a trade offer")
            if self.want_card_type is None or self.want_quantity is None:
                raise ValueError("want_card_type and want_quantity are required for a trade")
            if self.price_points is not None:
                raise ValueError("price_points is not allowed on a trade offer")
            if self.rent_interval_turns is not None:
                raise ValueError("rent_interval_turns is not allowed on a trade offer")
            if self.want_card_type == self.offer_card_type:
                raise ValueError("Trade the card for a different one")
        elif self.kind == "invest":
            if self.offer_card_type is None:
                raise ValueError("offer_card_type is required: name the property")
            if self.price_points is None:
                raise ValueError("price_points is the principal and is required")
            if self.yield_percent is None:
                raise ValueError("yield_percent is required")
            if self.term_turns is None:
                raise ValueError("term_turns is required")
            if self.want_card_type is not None:
                raise ValueError("want_card_type is not allowed on an invest offer")
            if self.rent_interval_turns is not None:
                raise ValueError("rent_interval_turns is not allowed on an invest offer")
        else:
            # rent_out names the property; rent_ask cannot, because it goes out
            # to every landlord rather than to one.
            if self.kind == "rent_out" and self.offer_card_type is None:
                raise ValueError("offer_card_type is required to let a room")
            if self.kind == "rent_ask" and self.offer_card_type is not None:
                raise ValueError("a room request names no property")
            if self.price_points is None:
                raise ValueError("price_points is required: rent cannot be free")
            if self.rent_interval_turns is None:
                raise ValueError("rent_interval_turns is required for a rent offer")
            if self.want_card_type is not None:
                raise ValueError("want_card_type is not allowed on a rent offer")
        return self


class OfferAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_state_version: int | None = None
    # rent_ask only: the claiming landlord names which property the room is in.
    # Optional because a landlord with exactly one eligible property does not
    # need to be asked.
    card_type: str | None = Field(default=None, min_length=1, max_length=32)
    # Which claimant the poster is accepting or declining. Required once more
    # than one player has claimed; optional when there is only one, so the
    # obvious case stays a single click.
    player_id: uuid.UUID | None = None


class OfferClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: uuid.UUID
    player_name: str
    seat_index: int
    # rent_ask only: the property this landlord offered
    card_type: str | None = None


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    poster_player_id: uuid.UUID
    poster_name: str
    poster_seat_index: int
    kind: str
    offer_card_type: str | None
    offer_quantity: int

    price_points: int | None
    total_price_points: int | None = None
    rent_interval_turns: int | None = None
    yield_percent: int | None = None
    term_turns: int | None = None
    claim_card_type: str | None = None

    want_card_type: str | None
    want_quantity: int | None
    status: str
    # Everyone with a hand up, oldest first. The poster picks one; the rest see
    # their own claim reflected so they know they are in the running.
    claims: list[OfferClaimOut] = []
    claimed_by_player_id: uuid.UUID | None = None
    claimed_by_name: str | None = None
    claimed_by_seat_index: int | None = None
    created_turn: int
    created_at: datetime