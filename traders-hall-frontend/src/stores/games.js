import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiJson } from '../api/client'

/**
 * Games: the lobby list, and the live state of one table.
 *
 * The API speaks snake_case; everything converts at this boundary so no
 * component has to know that.
 */
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
      hand: s.you.hand,
      foodDue: s.you.food_due,
      rentDue: s.you.rent_due,
      isMyTurn: s.you.is_my_turn,
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
    })),
  }
}

export const useGamesStore = defineStore('games', () => {
  const myGames = ref([])
  const current = ref(null)        // lobby-level shape, from /games/{code}
  const state = ref(null)          // full table projection
  const loadingMine = ref(false)
  const hasLoadedMine = ref(false)
  const hasLoadedState = ref(false)
  const busy = ref(false)
  const acting = ref(false)        // a player action is in flight
  const error = ref(null)
  const stateError = ref(null)
  const actionError = ref(null)    // shown at the table, cleared on next action

  async function fetchMine({ silent = false } = {}) {
    if (!silent) loadingMine.value = true
    try {
      const list = await apiJson('/api/v1/games/mine')
      myGames.value = list.map(toGame)
      hasLoadedMine.value = true
      if (!silent) error.value = null
    } catch (e) {
      // A failed poll should not wipe the list or flash a red error — the next
      // tick will most likely succeed, and a stale list beats nothing.
      if (!silent) error.value = e.message
    } finally {
      if (!silent) loadingMine.value = false
    }
  }

  /**
   * The whole table. This is the ONE function a WebSocket replaces later:
   * everything downstream reads `state`, so swapping poll-and-replace for
   * push-and-patch touches this and nothing else.
   */
  async function fetchState(code, { silent = false } = {}) {
    try {
      state.value = toState(await apiJson(`/api/v1/games/${code.toUpperCase()}/state`))
      hasLoadedState.value = true
      if (!silent) stateError.value = null
      return state.value
    } catch (e) {
      if (!silent) stateError.value = e.message
      return null
    }
  }

  function clearState() {
    state.value = null
    hasLoadedState.value = false
    stateError.value = null
    actionError.value = null
  }

  /**
   * Every player action goes through here.
   *
   * Two things it centralises. It sends expected_state_version, so the server
   * rejects an action decided against a stale view rather than applying it to
   * a world that moved. And it treats a 409 as routine — refetch and tell the
   * player to look again, never retry blindly, since the action they chose may
   * no longer be the one they want.
   *
   * Actions return the refreshed projection, so there is no second round trip.
   */
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

  async function leaveGame(code) {
    error.value = null
    try {
      await apiJson(`/api/v1/games/${code.toUpperCase()}/leave`, { method: 'POST' })
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
    fetchMine, fetchState, clearState, act, buyFromBank, sellToBank, endTurn,
    createGame, joinGame, fetchGame, startGame, closeGame, leaveGame,
  }
})