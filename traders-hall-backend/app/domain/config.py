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
STARTING_POINTS = 10
STARTING_HAND = {
    "rice": 1,
    "wheat": 1,
}

# --- bank stock, PER PLAYER, before the opening deal is taken out of it ---
BANK_POOL_PER_PLAYER = {
    "point": 30,
    "house": 1,
    "mansion": 1,
    "tower": 1,
    "rice": 4,
    "wheat": 4,
    "invest": 1,
}

# --- upkeep timers, in turns ---
#
# FOOD_INTERVAL_TURNS is the opening grace period only. After the first meal the
# counter is set by the card eaten, via card_types.nutrition_turns (rice 2,
# wheat 5) — so this number governs the start of the game, not the rhythm of it.
FOOD_INTERVAL_TURNS = 3
RENT_INTERVAL_TURNS = 5

# Which category can be eaten. Named rather than inlined as "food" so the check
# reads as a rule and moves in one place.
EDIBLE_CATEGORY = "food"

# --- credit -----------------------------------------------------------------
#
# A "round" is one lap of the table from the borrower's point of view: every
# obligation counter ticks down by one when its owner ends a turn, so a term of
# 5 means five of that player's own turns, not five turns of play.
#
# Interest is zero for now. It is a named constant rather than an absent concept
# so that turning it on is a value change plus one multiplication, not a reshape
# of the settle path.

LOAN_MAX_PRINCIPAL = 5
LOAN_TERM_ROUNDS = 5
LOAN_INTEREST_PER_ROUND = 0

# One property, advanced at its sell_value and redeemed for the same. The bank
# seizes the card outright if the debt is not cleared by the due date.
MORTGAGE_TERM_ROUNDS = 5
MORTGAGE_INTEREST_PER_ROUND = 0

# Which card category can back a mortgage, and — separately — which category the
# bank may seize to settle a defaulted unsecured loan. The same value today;
# named twice because they answer different questions and will not necessarily
# move together.
MORTGAGEABLE_CATEGORY = "property"
SEIZABLE_CATEGORY = "property"


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


# --- income -----------------------------------------------------------------
#
# Two dice, once per round, paid out of the bank's point pile.
#
# The payout is floor(SUM / INCOME_DIVISOR), not per-die. Summing is what makes a
# second die worth rolling: 2-12 is a bell curve centred on 7, so the common roll
# pays 1 and the tails pay 0 or 3. Dividing each die separately would make both
# of them near coin-flips and flatten the whole thing.
#
#   sum   2-3  4-7  8-11  12
#   pays   0    1     2    3
#
# Expected income is about 1.44 a round.
INCOME_DICE = 2
INCOME_DIE_FACES = 6
INCOME_DIVISOR = 4