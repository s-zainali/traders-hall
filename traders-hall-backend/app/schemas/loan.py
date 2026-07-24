"""Request bodies for the credit endpoints: loans and mortgages.

Four actions, four bodies. Each carries the optimistic-concurrency token and
nothing the server can derive for itself. The borrower is always the current
player — read from the turn, not the payload — and a mortgage advance is the
card's sell_value, looked up in card_types rather than named by the client.

The field bounds here are sanity limits, not business rules. The real credit
ceilings live in domain.config and are enforced in loan_service, where a breach
becomes a labelled ActionError the UI can act on — LOAN_LIMIT_EXCEEDED carries
the actual maximum, INSUFFICIENT_POINTS the shortfall. If the schema also capped
`amount` at LOAN_MAX_PRINCIPAL, an over-borrow would surface as a generic 422
validation error instead: the same rejection with a worse message, and the limit
now pinned in two places that must move together. So the bounds stay loose on
purpose; they exist only to stop an absurd value reaching the domain layer.
"""

from pydantic import BaseModel, ConfigDict, Field


class _CreditRequest(BaseModel):
    """Shared base for every credit action.

    extra="forbid" rejects an unrecognised key outright rather than ignoring it,
    so a client that misspells a field is told, not silently misread.

    expected_state_version is optional but strongly encouraged: sending it means
    "apply this only if the world still looks the way I last saw it". Borrowing
    or redeeming against a stale view is precisely the kind of decision that
    token exists to guard.
    """

    model_config = ConfigDict(extra="forbid")

    expected_state_version: int | None = None


class LoanBorrowRequest(_CreditRequest):
    # ge=1 forbids a zero-point loan; the loose upper bound is a sanity cap, not
    # the bank's limit. LOAN_MAX_PRINCIPAL is checked in loan_service so the
    # ceiling lives in one place and a breach returns LOAN_LIMIT_EXCEEDED with
    # the real maximum attached, rather than a bare pydantic error.
    amount: int = Field(ge=1, le=999)


class LoanRepayRequest(_CreditRequest):
    # Overpayment is clamped to the outstanding balance in the service, not
    # rejected here, so a "repay all" button firing on a slightly stale balance
    # settles the debt instead of failing validation. ge=1 only rules out a
    # no-op zero repayment.
    amount: int = Field(ge=1, le=999)


class MortgageOpenRequest(_CreditRequest):
    # Which property to put up as collateral. The advance is that card's
    # sell_value, read server-side — the client names the card, never prices it.
    card_type: str = Field(min_length=1, max_length=32)


class MortgageRedeemRequest(_CreditRequest):
    """Redemption takes no amount.

    A mortgage is a debt against one indivisible card, cleared in full or not at
    all, so there is nothing to size. The concurrency token is the whole body.
    """