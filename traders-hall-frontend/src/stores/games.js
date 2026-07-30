import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiJson } from '../api/client'

function toGame(g) {
  return {
    id: g.id,
    joinCode: g.join_code,
    status: g.status,
    hostUserId: g.host_user_id,
    maxPlayers: g.max_players,
    createdAt: g.created_at,
    startedAt: g.started_at,
    players: (g.players ?? []).map((p) => ({
      id: p.id,
      seatIndex: p.seat_index,
      displayName: p.display_name,
      isBot: p.is_bot,
      status: p.status,
    })),
  }
}

function toOffer(o) {
  return {
    id: o.id,
    posterPlayerId: o.poster_player_id,
    posterName: o.poster_name,
    posterSeatIndex: o.poster_seat_index,
    kind: o.kind,
    offerCardType: o.offer_card_type,
    offerQuantity: o.offer_quantity,
    // pricePoints is PER UNIT; totalPricePoints is what the claimant pays for
    // the whole lot. The server sends both so nothing here has to multiply —
    // and so an affordability check is a comparison against one number.
    pricePoints: o.price_points,
    totalPricePoints: o.total_price_points,
    rentIntervalTurns: o.rent_interval_turns,
    claimCardType: o.claim_card_type,
    // Everyone with a hand up, oldest first. The poster picks one.
    claims: (o.claims ?? []).map((c) => ({
      playerId: c.player_id,
      playerName: c.player_name,
      seatIndex: c.seat_index,
      cardType: c.card_type,
    })),
    wantCardType: o.want_card_type,
    wantQuantity: o.want_quantity,
    status: o.status,
    claimedByPlayerId: o.claimed_by_player_id,
    claimedByName: o.claimed_by_name,
    claimedBySeatIndex: o.claimed_by_seat_index,
    createdTurn: o.created_turn,
    createdAt: o.created_at,
  }
}

function toState(s) {
  return {
    game: {
      id: s.game.id,
      joinCode: s.game.join_code,
      status: s.game.status,
      phase: s.game.phase,
      turnNumber: s.game.turn_number,
      currentPlayerId: s.game.current_player_id,
      stateVersion: s.game.state_version,
      maxPlayers: s.game.max_players,
      hostUserId: s.game.host_user_id,
      startedAt: s.game.started_at,
      winnerPlayerId: s.game.winner_player_id ?? null,
      winnerName: s.game.winner_name ?? null,
    },
    bank: s.bank,
    you: {
      playerId: s.you.player_id,
      seatIndex: s.you.seat_index,
      points: s.you.points,
      // Spendable balance: points minus anything reserved against an open
      // market claim. Controls should gate on this, not on `points`, or the
      // UI offers purchases the server will refuse.
      //
      // Falls back to the raw total when the field is absent, so a backend
      // that predates app/schemas/game_state.py shows the real balance rather
      // than a silent 0 — which reads as "you are broke" and disables every
      // control on the page.
      availablePoints: s.you.available_points ?? s.you.points,
      hand: s.you.hand,
      foodDue: s.you.food_due,
      rentDue: s.you.rent_due,
      isMyTurn: s.you.is_my_turn,
      // 'active' | 'eliminated' | 'resigned'. The defeat screen keys off this.
      status: s.you.status ?? 'active',
      canRollIncome: s.you.can_roll_income ?? false,
      lastDice: s.you.last_dice ?? [],
      lastIncome: s.you.last_income ?? 0,
      /*
        Present only while the game is frozen on a seizure — its presence IS the
        freeze, so nothing has to interpret game.phase. `mine` says whether this
        player is the one who has to choose; `seizable` is only populated for them.
      */
      seizure: s.you.seizure
        ? {
            agreementId: s.you.seizure.agreement_id,
            debtorPlayerId: s.you.seizure.debtor_player_id,
            debtorName: s.you.seizure.debtor_name,
            debtorSeatIndex: s.you.seizure.debtor_seat_index,
            landlordPlayerId: s.you.seizure.landlord_player_id,
            landlordName: s.you.seizure.landlord_name,
            landlordSeatIndex: s.you.seizure.landlord_seat_index,
            debt: s.you.seizure.debt,
            cardType: s.you.seizure.card_type,
            mine: s.you.seizure.mine,
            seizable: s.you.seizure.seizable ?? {},
          }
        : null,
      loanOutstanding: s.you.loan_outstanding,
      loanDue: s.you.loan_due,
      mortgageCardType: s.you.mortgage_card_type,
      mortgageOutstanding: s.you.mortgage_outstanding,
      mortgageDue: s.you.mortgage_due,
      residenceCardType: s.you.residence_card_type,
      residenceLandlordId: s.you.residence_landlord_id,
      roomsTotal: s.you.rooms_total ?? 0,
      roomsOccupied: s.you.rooms_occupied ?? 0,
      roomsFree: s.you.rooms_free ?? 0,
      roomsByCard: s.you.rooms_by_card ?? {},
      // The tenancy you are IN, and the ones you are landlord to. Both drive
      // controls the UI must disable rather than let fail server-side.
      tenancy: s.you.tenancy
        ? {
            agreementId: s.you.tenancy.agreement_id,
            landlordPlayerId: s.you.tenancy.landlord_player_id,
            cardType: s.you.tenancy.card_type,
            rentPoints: s.you.tenancy.rent_points,
            intervalTurns: s.you.tenancy.interval_turns,
            turnsUntilDue: s.you.tenancy.turns_until_due,
            moveoutStatus: s.you.tenancy.moveout_status,
            moveoutBuyout: s.you.tenancy.moveout_buyout,
          }
        : null,
      tenants: (s.you.tenants ?? []).map((t) => ({
        agreementId: t.agreement_id,
        tenantPlayerId: t.tenant_player_id,
        tenantName: t.tenant_name,
        tenantSeatIndex: t.tenant_seat_index,
        cardType: t.card_type,
        rentPoints: t.rent_points,
        turnsUntilDue: t.turns_until_due,
        moveoutStatus: t.moveout_status,
      })),
    },
    players: s.players.map((p) => ({
      id: p.id,
      seatIndex: p.seat_index,
      displayName: p.display_name,
      status: p.status,
      isBot: p.is_bot,
      points: p.points,
      foodDue: p.food_due,
      rentDue: p.rent_due,
      lastDice: p.last_dice ?? [],
      hand: p.hand,
      // Debt is public on purpose: knowing an opponent has one round left on a
      // loan is exactly the kind of thing the table should trade on.
      loanOutstanding: p.loan_outstanding,
      loanDue: p.loan_due,
      mortgageCardType: p.mortgage_card_type,
      mortgageOutstanding: p.mortgage_outstanding,
      mortgageDue: p.mortgage_due,
      residenceCardType: p.residence_card_type,
      residenceLandlordId: p.residence_landlord_id,
      roomsTotal: p.rooms_total ?? 0,
      roomsOccupied: p.rooms_occupied ?? 0,
      roomsFree: p.rooms_free ?? 0,
    })),
  }
}

export const useGamesStore = defineStore('games', () => {
  const myGames = ref([])
  const current = ref(null)
  const state = ref(null)
  const loadingMine = ref(false)
  const hasLoadedMine = ref(false)
  const hasLoadedState = ref(false)
  const busy = ref(false)
  const acting = ref(false)
  const error = ref(null)
  const stateError = ref(null)
  const actionError = ref(null)

  const offers = ref([])

  const events = ref([])
  const lastSeq = ref(0)
  const feedCode = ref('')
  const sendingChat = ref(false)

  async function fetchMine({ silent = false } = {}) {
    if (!silent) loadingMine.value = true
    try {
      const list = await apiJson('/api/v1/games/mine')
      myGames.value = list.map(toGame)
      hasLoadedMine.value = true
      if (!silent) error.value = null
    } catch (e) {
      if (!silent) error.value = e.message
    } finally {
      if (!silent) loadingMine.value = false
    }
  }

  async function fetchState(code, { silent = false } = {}) {
    try {
      const fresh = await apiJson(`/api/v1/games/${code.toUpperCase()}/state`)

      if (state.value && fresh.game.state_version === state.value.game.stateVersion) {
        hasLoadedState.value = true
        if (!silent) stateError.value = null
        return state.value
      }

      state.value = toState(fresh)
      hasLoadedState.value = true
      if (!silent) stateError.value = null
      return state.value
    } catch (e) {
      if (!silent) stateError.value = e.message
      return null
    }
  }

  async function fetchEvents(code) {
    const key = code.toUpperCase()

    if (feedCode.value !== key) {
      feedCode.value = key
      events.value = []
      lastSeq.value = 0
    }

    try {
      const fresh = await apiJson(`/api/v1/games/${key}/events?since=${lastSeq.value}`)
      if (fresh.length) {
        events.value = [...events.value, ...fresh]
        lastSeq.value = fresh[fresh.length - 1].seq
      }
      return fresh
    } catch {
      return []
    }
  }

  async function fetchOffers(code) {
    try {
      const list = await apiJson(`/api/v1/games/${code.toUpperCase()}/offers`)
      offers.value = list.map(toOffer)
      return offers.value
    } catch {
      return offers.value
    }
  }

  async function postOffer(code, body) {
    acting.value = true
    actionError.value = null
    try {
      const fresh = await apiJson(`/api/v1/games/${code.toUpperCase()}/offers`, {
        method: 'POST',
        body: JSON.stringify({
          ...body,
          expected_state_version: state.value?.game.stateVersion ?? null,
        }),
      })
      state.value = toState(fresh)
      await fetchOffers(code)
      return true
    } catch (e) {
      actionError.value = e.message
      if (e.status === 409) await fetchState(code, { silent: true })
      return false
    } finally {
      acting.value = false
    }
  }

  async function offerAction(code, offerId, action, withVersion = false, extra = {}) {
    acting.value = true
    actionError.value = null
    try {
      const fresh = await apiJson(
        `/api/v1/games/${code.toUpperCase()}/offers/${offerId}/${action}`,
        {
          method: 'POST',
          body: withVersion
            ? JSON.stringify({
                expected_state_version: state.value?.game.stateVersion ?? null,
                ...extra,
              })
            : undefined,
        }
      )
      state.value = toState(fresh)
      await fetchOffers(code)
      return true
    } catch (e) {
      actionError.value = e.message
      await fetchOffers(code)
      if (e.status === 409) await fetchState(code, { silent: true })
      return false
    } finally {
      acting.value = false
    }
  }

  // cardType is rent_ask only: the claiming LANDLORD names which property the
  // room is in. The server picks when only one is eligible.
  const claimOffer = (code, id, cardType = null) =>
    offerAction(code, id, 'claim', true, cardType ? { card_type: cardType } : {})

  const unclaimOffer = (code, id) => offerAction(code, id, 'unclaim')

  /*
    Several players can claim one offer, so accepting and declining both name
    WHICH. Null means "the only one" — the server rejects an ambiguous null once
    more than one player is in the running, rather than picking for the poster.
  */
  const declineOffer = (code, id, playerId = null) =>
    offerAction(code, id, 'decline', true, playerId ? { player_id: playerId } : {})

  const confirmOffer = (code, id, playerId = null) =>
    offerAction(code, id, 'confirm', true, playerId ? { player_id: playerId } : {})
  const cancelOffer = (code, id) => offerAction(code, id, 'cancel')

  // pricePoints is per unit — the server multiplies by quantity.
  const sellOffer = (code, cardType, quantity, pricePoints) =>
    postOffer(code, {
      kind: 'sell',
      offer_card_type: cardType,
      offer_quantity: quantity,
      price_points: pricePoints,
    })

  const rentOut = (code, cardType, rentPoints, intervalTurns) =>
    postOffer(code, {
      kind: 'rent_out', offer_card_type: cardType, offer_quantity: 1,
      price_points: rentPoints, rent_interval_turns: intervalTurns,
    })

  // No card: the request goes to every landlord, and whoever answers names the
  // property themselves.
  const rentAsk = (code, rentPoints, intervalTurns) =>
    postOffer(code, {
      kind: 'rent_ask', offer_quantity: 1,
      price_points: rentPoints, rent_interval_turns: intervalTurns,
    })

  const moveIn = (code, cardType) => act(code, 'move-in', { card_type: cardType })

  /*
    On a rented room this no longer ends anything — the server raises a move-out
    request for the landlord to answer. Owner-occupiers still leave outright.
  */
  const leaveResidence = (code) => act(code, 'leave-residence')

  // Landlord answers. Refusing quotes the tenant a buy-out rather than ending it.
  const respondMoveOut = (code, agreementId, accept) =>
    act(code, 'moveout-response', { agreement_id: agreementId, accept })

  // Tenant chooses after a refusal: true pays the quoted price and goes.
  const resolveMoveOut = (code, leave) => act(code, 'moveout-resolve', { leave })

  // Landlord ends it early and forfeits the rent for the period.
  const evictTenant = (code, agreementId) =>
    act(code, 'evict', { agreement_id: agreementId })

  /*
    The only two actions that work on a frozen game. Everything else comes back
    GAME_FROZEN until one of these resolves it.
  */
  const seizeCards = (code, picks) => act(code, 'seize', { picks })

  const waiveSeizure = (code) => act(code, 'waive-seizure')

  const tradeOffer = (code, cardType, quantity, wantCardType, wantQuantity) =>
    postOffer(code, {
      kind: 'trade',
      offer_card_type: cardType,
      offer_quantity: quantity,
      want_card_type: wantCardType,
      want_quantity: wantQuantity,
    })

  async function sendChat(code, text) {
    sendingChat.value = true
    try {
      const event = await apiJson(`/api/v1/games/${code.toUpperCase()}/chat`, {
        method: 'POST',
        body: JSON.stringify({ text }),
      })
      if (event.seq > lastSeq.value) {
        events.value = [...events.value, event]
        lastSeq.value = event.seq
      }
      return true
    } catch (e) {
      actionError.value = e.message
      return false
    } finally {
      sendingChat.value = false
    }
  }

  function clearState() {
    state.value = null
    hasLoadedState.value = false
    stateError.value = null
    actionError.value = null
    events.value = []
    lastSeq.value = 0
    feedCode.value = ''
    offers.value = []
  }

  async function act(code, action, body = {}) {
    acting.value = true
    actionError.value = null
    try {
      const fresh = await apiJson(`/api/v1/games/${code.toUpperCase()}/actions/${action}`, {
        method: 'POST',
        body: JSON.stringify({
          ...body,
          expected_state_version: state.value?.game.stateVersion ?? null,
        }),
      })
      state.value = toState(fresh)
      return true
    } catch (e) {
      actionError.value = e.message
      if (e.status === 409) await fetchState(code, { silent: true })
      return false
    } finally {
      acting.value = false
    }
  }

  const buyFromBank = (code, cardType, quantity) =>
    act(code, 'buy-from-bank', { card_type: cardType, quantity })

  const sellToBank = (code, cardType, quantity) =>
    act(code, 'sell-to-bank', { card_type: cardType, quantity })

  const endTurn = (code) => act(code, 'end-turn')

  // Two dice, once a round. The server rolls; the client only asks.
  const rollIncome = (code) => act(code, 'roll-income')

  /* ── upkeep ───────────────────────────────────────────────────────
     Eating is a player action, not something the server does at end of turn:
     forgetting to eat is a way to lose, so the decision stays with the player.
     Nutrition ADDS to whatever is left, so eating early stockpiles.
  ─────────────────────────────────────────────────────────────────── */

  // One card per meal: nutrition raises food_due TO the card's value rather
  // than adding onto it, so a second card cannot lift a ceiling the first
  // already reached.
  const eatFood = (code, cardType) => act(code, 'eat', { card_type: cardType })

  /* ── credit ───────────────────────────────────────────────────────
     All four go through act(), so they carry expected_state_version and
     resync on a 409 exactly like a purchase does. Taking a loan is a
     decision made against a view of the board; if that view has moved on,
     the client should see the new one rather than borrow blind.
  ─────────────────────────────────────────────────────────────────── */

  const borrow = (code, amount) => act(code, 'borrow', { amount })

  const repayLoan = (code, amount) => act(code, 'repay-loan', { amount })

  const openMortgage = (code, cardType) => act(code, 'open-mortgage', { card_type: cardType })

  const redeemMortgage = (code) => act(code, 'redeem-mortgage')

  async function createGame(maxPlayers = 4) {
    busy.value = true
    error.value = null
    try {
      const game = await apiJson('/api/v1/games', {
        method: 'POST',
        body: JSON.stringify({ max_players: maxPlayers }),
      })
      current.value = toGame(game)
      await fetchMine()
      return current.value
    } catch (e) {
      error.value = e.message
      return null
    } finally {
      busy.value = false
    }
  }

  async function joinGame(code) {
    busy.value = true
    error.value = null
    try {
      const game = await apiJson(`/api/v1/games/${code.toUpperCase()}/join`, { method: 'POST' })
      current.value = toGame(game)
      await fetchMine()
      return current.value
    } catch (e) {
      error.value = e.message
      return null
    } finally {
      busy.value = false
    }
  }

  async function fetchGame(code) {
    error.value = null
    try {
      current.value = toGame(await apiJson(`/api/v1/games/${code.toUpperCase()}`))
      return current.value
    } catch (e) {
      error.value = e.message
      return null
    }
  }

  async function startGame(code) {
    busy.value = true
    error.value = null
    try {
      current.value = toGame(
        await apiJson(`/api/v1/games/${code.toUpperCase()}/start`, { method: 'POST' })
      )
      return current.value
    } catch (e) {
      error.value = e.message
      return null
    } finally {
      busy.value = false
    }
  }

  async function closeGame(code) {
    busy.value = true
    error.value = null
    try {
      await apiJson(`/api/v1/games/${code.toUpperCase()}`, { method: 'DELETE' })
      myGames.value = myGames.value.filter((g) => g.joinCode !== code.toUpperCase())
      if (current.value?.joinCode === code.toUpperCase()) current.value = null
      await fetchMine()
      return true
    } catch (e) {
      error.value = e.message
      return false
    } finally {
      busy.value = false
    }
  }

  /**
   * Leave a table, optionally naming who inherits it.
   *
   * The endpoint takes a LeaveRequest body, and a Pydantic model parameter with
   * no default is REQUIRED — so a bodyless POST was coming back 422 and leaving
   * silently did nothing. The body is always sent now, with a null heir when
   * none was chosen, which is the server's cue to fall back to the lowest live
   * seat. The id is validated server-side against the remaining players, so a
   * stale pick cannot hand the table to someone who already left.
   */
  async function leaveGame(code, heirPlayerId = '') {
    error.value = null
    try {
      await apiJson(`/api/v1/games/${code.toUpperCase()}/leave`, {
        method: 'POST',
        body: JSON.stringify({ heir_player_id: heirPlayerId || null }),
      })
      myGames.value = myGames.value.filter((g) => g.joinCode !== code.toUpperCase())
      await fetchMine()
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }

  return {
    myGames, current, state, loadingMine, hasLoadedMine, hasLoadedState,
    busy, acting, error, stateError, actionError,
    events, lastSeq, sendingChat, offers,
    fetchMine, fetchState, fetchEvents, fetchOffers, sendChat, clearState, act,
    buyFromBank, sellToBank, endTurn, eatFood, rollIncome,
    borrow, repayLoan, openMortgage, redeemMortgage,
    sellOffer, tradeOffer, rentOut, rentAsk, moveIn, leaveResidence,
    respondMoveOut, resolveMoveOut, evictTenant, seizeCards, waiveSeizure,
    claimOffer, unclaimOffer, declineOffer, confirmOffer, cancelOffer,
    createGame, joinGame, fetchGame, startGame, closeGame, leaveGame,
  }
})