<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import EventLog from '../Components/EventLog.vue'
import OffersPanel from '../Components/OffersPanel.vue'
import { useCardTypesStore } from '../stores/cardTypes'
import { useGamesStore } from '../stores/games'

const props = defineProps({ code: { type: String, required: true } })

const router = useRouter()
const cardTypes = useCardTypesStore()
const games = useGamesStore()

const { loaded, error: cardError } = storeToRefs(cardTypes)
const {
    state, hasLoadedState, stateError, acting, actionError, events, sendingChat, offers,
} = storeToRefs(games)

async function load() {
    await Promise.all([
        cardTypes.fetchAll(),
        games.fetchState(props.code),
        games.fetchEvents(props.code),
        games.fetchOffers(props.code),
    ])
}

const POLL_MS = 2000
let pollTimer = null
let inFlight = false

async function poll() {
    if (inFlight || acting.value || document.hidden) return
    inFlight = true
    try {
        await games.fetchState(props.code, { silent: true })
        await games.fetchEvents(props.code)
        await games.fetchOffers(props.code)
    } finally {
        inFlight = false
    }
}

const startPolling = () => {
    stopPolling()
    pollTimer = setInterval(poll, POLL_MS)
}

const stopPolling = () => {
    clearInterval(pollTimer)
    pollTimer = null
}

function onVisibility() {
    if (document.hidden) stopPolling()
    else {
        poll()
        startPolling()
    }
}

onMounted(() => {
    load()
    startPolling()
    document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
    stopPolling()
    document.removeEventListener('visibilitychange', onVisibility)
    games.clearState()
})

const me = computed(() => state.value?.you ?? null)
const isMyTurn = computed(() => me.value?.isMyTurn ?? false)

const seatByPlayer = computed(() =>
    Object.fromEntries((state.value?.players ?? []).map((p) => [p.id, p.seatIndex]))
)
const nameByPlayer = computed(() =>
    Object.fromEntries((state.value?.players ?? []).map((p) => [p.id, p.displayName]))
)

const seats = computed(() => {
    const s = state.value
    if (!s) return []
    return Array.from({ length: s.game.maxPlayers }, (_, i) => {
        const player = s.players.find((p) => p.seatIndex === i) ?? null
        return {
            seatIndex: i,
            seatStatus: player?.status ?? 'empty',
            name: player?.displayName ?? 'Empty seat',
            isMe: player !== null && player.seatIndex === me.value?.seatIndex,
            isTurn: player !== null && player.id === s.game.currentPlayerId,
            hand: player?.hand ?? {},
            points: player?.points ?? 0,
            foodDue: player?.foodDue ?? 0,
            rentDue: player?.rentDue ?? 0,
        }
    })
})

const opponentSeats = computed(() => seats.value.filter((s) => !s.isMe))
const mine = computed(() => seats.value.find((s) => s.isMe) ?? null)

const activeAction = ref('')
const startAction = (action) => (activeAction.value = action)
const cancelAction = () => (activeAction.value = '')

async function onBuy({ type, quantity }) {
    if (await games.buyFromBank(props.code, type, quantity)) cancelAction()
}

async function onTransaction(payload) {
    let ok = false

    if (payload.kind === 'sell-to-bank') {
        ok = await games.sellToBank(props.code, payload.cardType, payload.quantity)
    } else if (payload.kind === 'sell-offer') {
        ok = await games.sellOffer(
            props.code, payload.cardType, payload.quantity, payload.pricePoints
        )
    } else if (payload.kind === 'trade-offer') {
        ok = await games.tradeOffer(
            props.code, payload.cardType, payload.quantity,
            payload.wantCardType, payload.wantQuantity
        )
    }

    if (ok) cancelAction()
}

const onClaimOffer = (id) => games.claimOffer(props.code, id)
const onUnclaimOffer = (id) => games.unclaimOffer(props.code, id)
const onDeclineOffer = (id) => games.declineOffer(props.code, id)
const onConfirmOffer = (id) => games.confirmOffer(props.code, id)
const onCancelOffer = (id) => games.cancelOffer(props.code, id)

async function onEndTurn() {
    cancelAction()
    await games.endTurn(props.code)
}

watch(
    () => state.value?.game.stateVersion,
    (next, prev) => {
        if (prev !== undefined && next !== prev) cancelAction()
    }
)

watch(isMyTurn, (turn) => {
    if (!turn) cancelAction()
})

watch(
    () => mine.value?.seatStatus,
    (status) => {
        if (status && status !== 'active' && status !== 'empty') {
            games.clearState()
            router.push({ name: 'lobby' })
        }
    }
)

watch(
    () => state.value?.game.status,
    (status) => {
        if (status && status !== 'in_progress') router.push({ name: 'lobby' })
    }
)
</script>

<template>
    <LoadingScreen v-if="!hasLoadedState || !loaded" message="Taking a seat…" :error="stateError ?? cardError ?? ''"
        @retry="load" />

    <div v-else class="relative flex h-[100dvh] gap-2 bg-gray-dark p-2 md:gap-3 md:p-3 xl:gap-6 xl:p-6">

        <div class="scroll-slim flex min-h-0 min-w-0 flex-1 flex-col gap-2 overflow-y-auto md:gap-3
                    xl:gap-4 xl:overflow-hidden">

            <Header :game-code="code" />

            <div class="game-grid min-h-0 flex-1">

                <div class="scroll-slim area-opp flex min-w-0 gap-2 overflow-x-auto pb-1 md:gap-3
                            lg:overflow-visible lg:pb-0
                            xl:flex-col xl:gap-3 xl:overflow-x-hidden xl:overflow-y-auto xl:pb-0 xl:pr-1">
                    <PlayerCardHolder v-for="seat in opponentSeats" :key="seat.seatIndex" :player-type="'opponent'"
                        :seat-index="seat.seatIndex" :player-name="seat.name" :seat-status="seat.seatStatus"
                        :is-turn="seat.isTurn" :hand="seat.hand" :points="seat.points" :food-due="seat.foodDue"
                        :rent-due="seat.rentDue"
                        class="w-[17rem] shrink-0 md:w-[19rem] lg:w-auto lg:min-w-0 lg:flex-1 xl:w-full xl:flex-none" />
                </div>

                <EventLog class="area-log min-h-0 min-w-0" :events="events" :seat-by-player="seatByPlayer"
                    :name-by-player="nameByPlayer" :sending="sendingChat"
                    @send="(text) => games.sendChat(code, text)" />

                <OffersPanel class="area-offers min-h-0 min-w-0" :offers="offers" :my-player-id="me?.playerId ?? ''"
                    :my-points="me?.points ?? 0" :my-hand="me?.hand ?? {}" :busy="acting" @claim="onClaimOffer"
                    @unclaim="onUnclaimOffer" @decline="onDeclineOffer" @confirm="onConfirmOffer"
                    @cancel="onCancelOffer" />

                <PlayerCardHolder class="area-own min-w-0" :active-action="activeAction"
                    :seat-index="mine?.seatIndex ?? -1" :player-name="mine?.name ?? ''"
                    :seat-status="mine?.seatStatus ?? 'empty'" :is-turn="isMyTurn" :hand="mine?.hand ?? {}"
                    :points="mine?.points ?? 0" :food-due="mine?.foodDue ?? 0" :rent-due="mine?.rentDue ?? 0"
                    :busy="acting" @buy="startAction('buy')" @sell="startAction('sell')" @trade="startAction('trade')"
                    @cancel-operation="cancelAction" @transaction="onTransaction" @end-turn="onEndTurn" />
            </div>
        </div>

        <BankSection :buying-active="activeAction === 'buy'" :pools="state.bank" :points="me?.points ?? 0"
            :busy="acting" @cancel="cancelAction" @confirm="onBuy" />

        <Transition name="toast">
            <div v-if="actionError"
                class="fixed bottom-6 left-1/2 z-[200] -translate-x-1/2 rounded-xl border-2 border-rose-400 bg-gray-x-dark px-5 py-3 shadow-2xl shadow-black/50">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-rose-400">{{ actionError }}</span>
                    <button type="button" @click="games.actionError = null"
                        class="cursor-pointer text-gray-x-light transition-colors duration-200 hover:text-gray-2x-light">✕</button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<style scoped>
.game-grid {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
        "opp"
        "own"
        "log"
        "offers";
}

@media (min-width: 768px) {
    .game-grid {
        gap: 0.75rem;
        grid-template-columns: 32rem minmax(0, 1fr);
        grid-template-rows: auto minmax(0, 1fr) minmax(0, 1fr);
        grid-template-areas:
            "opp    opp"
            "own    log"
            "offers offers";
    }
}

@media (min-width: 1024px) {
    .game-grid {
        grid-template-columns: 33% minmax(0, 1fr) 18rem;
        grid-template-rows: auto minmax(0, 1fr);
        grid-template-areas:
            "opp opp opp"
            "own log offers";
    }
}

@media (min-width: 1280px) {
    .game-grid {
        gap: 1rem;
        grid-template-columns: minmax(0, 1fr) 19rem 21rem;
        grid-template-rows: minmax(0, 1fr) auto;
        grid-template-areas:
            "log offers opp"
            "own own    own";
    }
}

.area-opp {
    grid-area: opp;
}

.area-own {
    grid-area: own;
}

.area-log {
    grid-area: log;
}

.area-offers {
    grid-area: offers;
}

.toast-enter-active,
.toast-leave-active {
    transition: opacity 200ms ease, transform 200ms ease;
}

.toast-enter-from,
.toast-leave-to {
    opacity: 0;
    transform: translate(-50%, 12px);
}

.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

.scroll-slim::-webkit-scrollbar-track {
    background: transparent;
}

.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}

.scroll-slim::-webkit-scrollbar-thumb:hover {
    background: color-mix(in oklab, var(--color-teal-light) 55%, transparent);
    background-clip: content-box;
}

@media (prefers-reduced-motion: reduce) {

    .toast-enter-active,
    .toast-leave-active {
        transition: none;
    }
}
</style>