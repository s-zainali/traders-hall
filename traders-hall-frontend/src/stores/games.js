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
    // Rent kinds only. rentIntervalTurns is how many of the TENANT's turns
    // between payments; claimCardType is which property a claiming landlord
    // named when answering a rent_ask.
    rentIntervalTurns: o.rent_interval_turns,
    claimCardType: o.claim_card_type,
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
      loanOutstanding: s.you.loan_outstanding,
      loanDue: s.you.loan_due,
      mortgageCardType: s.you.mortgage_card_type,
      mortgageOutstanding: s.you.mortgage_outstanding,
      mortgageDue: s.you.mortgage_due,
      // Housing. A landlord id alongside a residence means you rent; a
      // residence with no landlord means you own the place; neither means
      // homeless.
      residenceCardType: s.you.residence_card_type,
      residenceLandlordId: s.you.residence_landlord_id,
      roomsTotal: s.you.rooms_total ?? 0,
      roomsOccupied: s.you.rooms_occupied ?? 0,
      roomsFree: s.you.rooms_free ?? 0,
      // Per property type, so the let-a-room control offers only the
      // properties that actually have capacity left.
      roomsByCard: s.you.rooms_by_card ?? {},
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
      hand: p.hand,
      // Debt is public on purpose: knowing an opponent has one round left on a
      // loan is exactly the kind of thing the table should trade on.
      loanOutstanding: p.loan_outstanding,
      loanDue: p.loan_due,
      mortgageCardType: p.mortgage_card_type,
      mortgageOutstanding: p.mortgage_outstanding,
      mortgageDue: p.mortgage_due,
      // Public: a spare room is what makes a player eligible to answer a
      // request, so every client needs to see it.
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

  // cardType is only meaningful for rent_ask, where the claimant is the
  // LANDLORD and must name which of their properties the room is in. The server
  // picks for them when only one property is eligible.
  const claimOffer = (code, id, cardType = null) =>
    offerAction(code, id, 'claim', true, cardType ? { card_type: cardType } : {})
  const unclaimOffer = (code, id) => offerAction(code, id, 'unclaim')
  const declineOffer = (code, id) => offerAction(code, id, 'decline')
  const confirmOffer = (code, id) => offerAction(code, id, 'confirm', true)
  const cancelOffer = (code, id) => offerAction(code, id, 'cancel')

  // pricePoints is per unit — the server multiplies by quantity.
  const sellOffer = (code, cardType, quantity, pricePoints) =>
    postOffer(code, {
      kind: 'sell',
      offer_card_type: cardType,
      offer_quantity: quantity,
      price_points: pricePoints,
    })

  /* ── housing ──────────────────────────────────────────────────────
     Two routes into a tenancy, differing only in who posts. rentOut is a
     landlord advertising one room; rentAsk is a homeless player broadcasting
     what they will pay. Both carry the rent AND the interval, because both are
     negotiated rather than fixed anywhere.
  ─────────────────────────────────────────────────────────────────── */

  const rentOut = (code, cardType, rentPoints, intervalTurns) =>
    postOffer(code, {
      kind: 'rent_out',
      offer_card_type: cardType,
      offer_quantity: 1,
      price_points: rentPoints,
      rent_interval_turns: intervalTurns,
    })

  // No card: the request goes to every landlord, and whoever answers names the
  // property themselves.
  const rentAsk = (code, rentPoints, intervalTurns) =>
    postOffer(code, {
      kind: 'rent_ask',
      offer_quantity: 1,
      price_points: rentPoints,
      rent_interval_turns: intervalTurns,
    })

  const moveIn = (code, cardType) => act(code, 'move-in', { card_type: cardType })

  const leaveResidence = (code) => act(code, 'leave-residence')

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

  /* ── upkeep ───────────────────────────────────────────────────────
     Eating is a player action, not something the server does at end of turn:
     forgetting to eat is a way to lose, so the decision stays with the player.
     Nutrition ADDS to whatever is left, so eating early stockpiles.
  ─────────────────────────────────────────────────────────────────── */

  const eatFood = (code, cardType, quantity = 1) =>
    act(code, 'eat', { card_type: cardType, quantity })

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
    buyFromBank, sellToBank, endTurn, eatFood,
    borrow, repayLoan, openMortgage, redeemMortgage,
    sellOffer, tradeOffer, rentOut, rentAsk, moveIn, leaveResidence,
    claimOffer, unclaimOffer, declineOffer, confirmOffer, cancelOffer,
    createGame, joinGame, fetchGame, startGame, closeGame, leaveGame,
  }
})