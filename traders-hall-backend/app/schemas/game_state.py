"""Response shapes for the game state projection.

Built by hand rather than from_attributes, because the response draws on several
tables and splits into a public part and a private one — a shape no single table
has.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class GameInfo(BaseModel):
    id: uuid.UUID
    join_code: str
    status: str
    phase: str
    turn_number: int
    current_player_id: uuid.UUID | None
    state_version: int
    max_players: int
    host_user_id: uuid.UUID
    started_at: datetime | None
    # Derived, not stored: when a game completes there is exactly one active
    # player left, and that is the winner. Storing it would be a second source of
    # truth for something the seats already say.
    winner_player_id: uuid.UUID | None = None
    winner_name: str | None = None


class PlayerPublic(BaseModel):
    """Hands are public in this game, so this is genuinely the full picture.

    Debt and housing are public too, deliberately: knowing an opponent has one
    round left on a loan, or a spare room going empty, is exactly the kind of
    thing the table should be able to trade on.
    """

    id: uuid.UUID
    seat_index: int
    display_name: str
    status: str
    is_bot: bool
    points: int
    food_due: int
    # Public: everyone watches everyone else's luck.
    last_dice: list[int] = []
    rent_due: int
    hand: dict[str, int]

    # --- credit ---
    loan_outstanding: int
    loan_due: int
    mortgage_card_type: str | None
    mortgage_outstanding: int
    mortgage_due: int

    # --- housing ---
    # residence_landlord_id NULL alongside a residence means they own the place.
    residence_card_type: str | None
    residence_landlord_id: uuid.UUID | None
    # Derived capacity, not stored. rooms_free is what makes a player eligible to
    # accept a tenant's request, so the client needs it to know which claim
    # buttons to enable.
    rooms_total: int
    rooms_occupied: int
    rooms_free: int


class TenancyOut(BaseModel):
    """The tenancy you are IN, if any."""

    agreement_id: uuid.UUID
    landlord_player_id: uuid.UUID
    card_type: str
    rent_points: int
    interval_turns: int
    turns_until_due: int
    # None | 'requested' | 'rejected'
    moveout_status: str | None = None
    # only quoted once the landlord has refused
    moveout_buyout: int | None = None


class SeizureOut(BaseModel):
    """The seizure the game is frozen on.

    Sent to everyone, not just the landlord: every other player needs to know why
    nothing responds, and who they are waiting for.
    """

    agreement_id: uuid.UUID
    debtor_player_id: uuid.UUID
    debtor_name: str
    debtor_seat_index: int
    landlord_player_id: uuid.UUID
    landlord_name: str
    landlord_seat_index: int
    debt: int
    card_type: str
    # True when the recipient is the one who has to choose.
    mine: bool = False
    # What may be taken: free cards with a sell value. Only populated for the
    # landlord — it is their hand to pick from, and nobody else needs the list.
    seizable: dict[str, int] = {}


class TenantOut(BaseModel):
    """Somebody renting a room from YOU.

    Every live tenancy, not only the ones asking to leave — a landlord can end
    any of them, and moveout_status tells the client which need answering.
    """

    agreement_id: uuid.UUID
    tenant_player_id: uuid.UUID
    tenant_name: str
    tenant_seat_index: int
    card_type: str
    rent_points: int
    turns_until_due: int
    # None | 'requested' | 'rejected'
    moveout_status: str | None = None


class YouBlock(BaseModel):
    """The private slice.

    Everything here is also in `players` today, since hands are public. The
    block exists anyway so that making hands secret later is a one-field change
    rather than a reshape — and `legal_actions` will never be public.
    """

    player_id: uuid.UUID
    seat_index: int
    points: int
    hand: dict[str, int]
    food_due: int
    rent_due: int
    is_my_turn: bool
    # 'active' | 'eliminated' | 'resigned'. On `you` as well as in `players`
    # because the defeat screen keys off it and should not have to find itself in
    # a list.
    status: str = "active"

    # --- income ---
    # Whether this round's roll is still available, and what the last one was.
    # can_roll is computed server-side so the client never has to know that
    # turn_number advances per lap.
    can_roll_income: bool = False
    # Why rolling is unavailable, when it is. The UI shows this rather than
    # guessing, so a disabled button always explains itself.
    #   '' | 'not_your_turn' | 'already_rolled' | 'homeless' | 'frozen'
    roll_blocked_reason: str = ""
    last_dice: list[int] = []
    last_income: int = 0

    # --- credit ---
    loan_outstanding: int
    loan_due: int
    mortgage_card_type: str | None
    mortgage_outstanding: int
    mortgage_due: int

    # --- housing ---
    residence_card_type: str | None
    residence_landlord_id: uuid.UUID | None
    rooms_total: int
    rooms_occupied: int
    rooms_free: int
    # Per property type, so the "let a room" modal can offer only the properties
    # that actually have capacity left.
    rooms_by_card: dict[str, int]

    # The tenancy you are in, and any your tenants are trying to end. Both are
    # on `you` rather than the public block: a move-out is a negotiation between
    # two players, not table information.
    # Set only while the game is frozen. Its presence IS the freeze, so the
    # client does not have to interpret game.phase.
    seizure: SeizureOut | None = None

    tenancy: TenancyOut | None = None
    tenants: list[TenantOut] = []

    # Spendable balance: points minus anything reserved against an open market
    # claim. The client needs this to disable controls correctly — showing the
    # raw total invites a purchase the server will refuse.
    available_points: int


class GameStateOut(BaseModel):
    game: GameInfo
    bank: dict[str, int]
    you: YouBlock
    players: list[PlayerPublic]