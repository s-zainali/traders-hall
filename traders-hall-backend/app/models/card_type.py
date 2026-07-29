from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CardType(Base):
    """A registry of valid card codes. Nothing more.

    Every number that used to live here — cost, sell value, nutrition, rooms,
    colours, icon — moved to app/domain/cards.py, so balancing the game is an
    edit and a restart rather than a migration.

    The table stays because nine foreign keys point at it: player_hands,
    game_card_pools, trade_offers (offer, want and claim), game_players
    (mortgage and residence), rental_agreements, offer_claims and
    ledger_entries. Dropping it would trade referential integrity — the database
    refusing to store a card that does not exist — for a convenience this
    one-column version already provides.

    So the database answers "is this a real card?" and the catalogue answers
    "what does it do?". Neither can contradict the other, because neither knows
    what the other knows.
    """

    __tablename__ = "card_types"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)