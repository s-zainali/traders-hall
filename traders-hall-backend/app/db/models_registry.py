"""Import every ORM model here so Alembic can see it.

Autogenerate diffs the live database against Base.metadata. A model class that
nothing has imported was never registered on that metadata, so Alembic either
ignores its table entirely or writes a migration that DROPS it.
"""

from app.db.base import Base  # noqa: F401

from app.models.card_type import CardType  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.game import Game  # noqa: F401
from app.models.game_player import GamePlayer  # noqa: F401
from app.models.game_card_pool import GameCardPool  # noqa: F401
from app.models.player_hand import PlayerHand  # noqa: F401
from app.models.game_event import GameEvent  # noqa: F401
from app.models.ledger_entry import LedgerEntry  # noqa: F401