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
        pricePoints: o.price_points,
        wantCardType: o.want_card_type,
        wantQuantity: o.want_quantity,
        status: o.status,
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

    async function acceptOffer(code, offerId) {
        acting.value = true
        actionError.value = null
        try {
            const fresh = await apiJson(
                `/api/v1/games/${code.toUpperCase()}/offers/${offerId}/accept`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        expected_state_version: state.value?.game.stateVersion ?? null,
                    }),
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

    async function cancelOffer(code, offerId) {
        acting.value = true
        actionError.value = null
        try {
            const fresh = await apiJson(
                `/api/v1/games/${code.toUpperCase()}/offers/${offerId}/cancel`,
                { method: 'POST' }
            )
            state.value = toState(fresh)
            await fetchOffers(code)
            return true
        } catch (e) {
            actionError.value = e.message
            await fetchOffers(code)
            return false
        } finally {
            acting.value = false
        }
    }

    const sellOffer = (code, cardType, quantity, pricePoints) =>
        postOffer(code, {
            kind: 'sell',
            offer_card_type: cardType,
            offer_quantity: quantity,
            price_points: pricePoints,
        })

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
        buyFromBank, sellToBank, endTurn,
        sellOffer, tradeOffer, acceptOffer, cancelOffer,
        createGame, joinGame, fetchGame, startGame, closeGame, leaveGame,
    }
})