"""Balance constants.

These live in a module rather than a `rulesets` table for now. The table is the
right long-term answer — it lets a game pin its config so a balance change
cannot break a match already in progress — but it is a table, a join and a
migration for numbers that will be edited weekly for months. Move them when two
rulesets genuinely need to coexist, not before.

Bank stock scales with player count: a 2-player game should not face the same
supply as a 4-player one.
"""

MIN_PLAYERS = 2
MAX_PLAYERS = 4

# --- what each player starts with ---
STARTING_POINTS = 2
STARTING_HAND = {
    "rice": 1,
    "wheat": 1,
}

# --- bank stock, PER PLAYER, before the opening deal is taken out of it ---
BANK_POOL_PER_PLAYER = {
    "point": 10,
    "house": 1,
    "mansion": 1,
    "tower": 1,
    "rice": 4,
    "wheat": 4,
    "invest": 1,
}

# --- upkeep timers, in turns ---
FOOD_INTERVAL_TURNS = 3
RENT_INTERVAL_TURNS = 5


def bank_pool_for(player_count: int) -> dict[str, int]:
    """Bank stock the moment the game starts, AFTER the opening deal.

    The opening hand and starting points come OUT of the bank rather than
    appearing from nowhere. Without that, the total number of cards and points
    in the game is not conserved from turn zero, and the invariant that makes
    the ledger auditable — nothing is created, only moved — is already false
    before anyone has played.
    """
    pool = {code: per * player_count for code, per in BANK_POOL_PER_PLAYER.items()}

    for code, count in STARTING_HAND.items():
        pool[code] -= count * player_count

    pool["point"] -= STARTING_POINTS * player_count

    # A negative pool means the constants contradict each other. Fail loudly at
    # start time rather than silently dealing cards that do not exist.
    for code, qty in pool.items():
        if qty < 0:
            raise ValueError(f"bank pool for {code!r} would be negative ({qty})")

    return pool