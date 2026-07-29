"""The card catalogue.

Every card and every number on it lives here rather than in a seed migration.
Changing what a mansion costs, how long wheat feeds you, or how many rooms a
tower has is now an edit and a restart — not a migration, a review and a
deployment for a number that will be tuned weekly for months.

The card_types TABLE still exists, but only as a registry of codes. Nine foreign
keys point at it — player_hands, game_card_pools, trade_offers (three of them),
game_players (two), rental_agreements, offer_claims, ledger_entries — and
dropping it would trade referential integrity for a convenience the code-only
column already buys. So the database answers "is this a real card?" and this
file answers "what does it do?", with no overlap and nothing to drift.

Adding a card means adding it here AND letting sync_card_codes insert its row at
startup. Removing one means deleting it here, but the row stays: a game already
holding that card still has rows pointing at it, and history should not rot
because a balance pass dropped a card.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    """One card type.

    Frozen because nothing should mutate the catalogue at runtime. If a value
    needs to differ per game, it belongs on the game, not here.
    """

    code: str
    title: str
    category: str

    # what the bank charges, and what it pays
    base_cost: int
    sell_value: int

    # food only: turns of food_due one card restores. None for everything else,
    # which is what makes "is this edible" a real question rather than a zero.
    nutrition_turns: int | None = None

    # property only
    base_output_points: int = 0
    rooms: int = 0

    icon_url: str = ""
    accent_color: str = ""
    background_color: str = ""

    is_tradeable: bool = True
    sort_order: int = 0


CARDS: tuple[Card, ...] = (
    Card(
        code="house",
        title="House",
        category="property",
        base_cost=1,
        sell_value=1,
        base_output_points=1,
        rooms=1,
        icon_url="/home.png",
        accent_color="purple-dark",
        background_color="purple-light",
        sort_order=1,
    ),
    Card(
        code="mansion",
        title="Mansion",
        category="property",
        base_cost=2,
        sell_value=2,
        base_output_points=2,
        rooms=2,
        icon_url="/mansion.png",
        accent_color="purple-dark",
        background_color="purple-light",
        sort_order=2,
    ),
    Card(
        code="tower",
        title="Tower",
        category="property",
        base_cost=3,
        sell_value=3,
        base_output_points=3,
        rooms=3,
        icon_url="/building.png",
        accent_color="purple-dark",
        background_color="purple-light",
        sort_order=3,
    ),
    Card(
        code="rice",
        title="Rice",
        category="food",
        base_cost=1,
        sell_value=1,
        nutrition_turns=2,
        icon_url="/rice.png",
        accent_color="cream-dark",
        background_color="cream-light",
        sort_order=4,
    ),
    Card(
        code="wheat",
        title="Wheat",
        category="food",
        base_cost=1,
        sell_value=1,
        nutrition_turns=5,
        icon_url="/wheat.png",
        accent_color="cream-dark",
        background_color="cream-light",
        sort_order=5,
    ),
    Card(
        code="invest",
        title="Invest",
        category="investment",
        base_cost=1,
        sell_value=1,
        icon_url="/investor.png",
        accent_color="blue-dark",
        background_color="blue-light",
        sort_order=6,
    ),
    Card(
        code="point",
        title="Point",
        category="currency",
        base_cost=0,
        sell_value=0,
        icon_url="/star.png",
        accent_color="teal-dark",
        background_color="teal-light",
        # Currency is not merchandise. Buying points with points is either a
        # no-op or an exploit depending on the price.
        is_tradeable=False,
        sort_order=7,
    ),
)

BY_CODE: dict[str, Card] = {c.code: c for c in CARDS}

ALL_CODES: tuple[str, ...] = tuple(c.code for c in CARDS)


def get(code: str) -> Card | None:
    return BY_CODE.get(code)


def by_category(category: str) -> tuple[Card, ...]:
    return tuple(c for c in CARDS if c.category == category)


def sorted_cards() -> tuple[Card, ...]:
    return tuple(sorted(CARDS, key=lambda c: c.sort_order))