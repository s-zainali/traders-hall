import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiJson } from '../api/client'

/**
 * Games: create, join, start, close, and the list of games you are seated in.
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

export const useGamesStore = defineStore('games', () => {
  const myGames = ref([])
  const current = ref(null)        // the game most recently created/fetched
  const loadingMine = ref(false)
  const busy = ref(false)          // a create/join/start/close is in flight
  const error = ref(null)

  async function fetchMine() {
    loadingMine.value = true
    error.value = null
    try {
      const list = await apiJson('/api/v1/games/mine')
      myGames.value = list.map(toGame)
    } catch (e) {
      error.value = e.message
    } finally {
      loadingMine.value = false
    }
  }

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

  /** Host-only, lobby-only, and only when nobody else has joined. */
  async function closeGame(code) {
    busy.value = true
    error.value = null
    try {
      await apiJson(`/api/v1/games/${code.toUpperCase()}`, { method: 'DELETE' })
      // drop it locally too, so the list updates before the refetch lands
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
    myGames, current, loadingMine, busy, error,
    fetchMine, createGame, joinGame, fetchGame, startGame, closeGame, leaveGame,
  }
})