<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import { useCardTypesStore } from '../stores/cardTypes'
import { useGamesStore } from '../stores/games'
import EventLog from '../Components/EventLog.vue'

// From the /game/:code route via `props: true`
const props = defineProps({ code: { type: String, required: true } })

const cardTypes = useCardTypesStore()
const games = useGamesStore()

const { loaded, error: cardError } = storeToRefs(cardTypes)
const { state, hasLoadedState, stateError, acting, actionError,
    events, sendingChat } = storeToRefs(games)

async function load() {
    await Promise.all([
        cardTypes.fetchAll(),
        games.fetchState(props.code),
        games.fetchEvents(props.code),
    ])
}

/* ── live updates ──────────────────────────────────────────────
   Polling, faster than the lobby and more clearly temporary. A 3s delay on
   "has anyone joined" is fine; a 2s delay on "did my opponent take the last
   rice" is not. This is the screen that actually wants a socket, and
   games.fetchState is the single function that gets replaced.
─────────────────────────────────────────────────────────────── */
const POLL_MS = 2000
let pollTimer = null
let inFlight = false

async function poll() {
    // Never poll while an action is in flight: the response would arrive with a
    // stale state_version and clobber the fresher state the action returns.
    if (inFlight || acting.value || document.hidden) return
    inFlight = true
    try {
        await games.fetchState(props.code, { silent: true })
        await games.fetchEvents(props.code)
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
    // Wipe on the way out so returning to a different table cannot flash the
    // previous one's cards before the first fetch lands.
    games.clearState()
})

/* ── derived ─────────────────────────────────────────────────── */

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
            occupied: player !== null,
            name: player?.displayName ?? 'Empty seat',
            // seat_index is the identity, not display_name — two players can share a
            // name, and the projection gives us the real seat.
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

// One ref for the current mode: '' | 'buy' | 'sell' | 'trade'.
const activeAction = ref('')
const startAction = (action) => (activeAction.value = action)
const cancelAction = () => (activeAction.value = '')

/* ── actions ─────────────────────────────────────────────────── */

async function onBuy({ type, quantity }) {
    if (await games.buyFromBank(props.code, type, quantity)) cancelAction()
}

async function onSell({ type, payload }) {
    if (await games.sellToBank(props.code, type, payload)) cancelAction()
}

async function onEndTurn() {
    cancelAction()
    await games.endTurn(props.code)
}

// Any state change from elsewhere closes an open modal: confirming a purchase
// against stock that moved two seconds ago is exactly the mistake
// expected_state_version exists to catch, and it is better not to offer it.
watch(
    () => state.value?.game.stateVersion,
    (next, prev) => {
        if (prev !== undefined && next !== prev) cancelAction()
    }
)

// Losing the turn mid-decision should close the modal too.
watch(isMyTurn, (mine) => {
    if (!mine) cancelAction()
})
</script>

<template>
    <LoadingScreen v-if="!hasLoadedState || !loaded" message="Taking a seat…" :error="stateError ?? cardError ?? ''"
        @retry="load" />

    <!--
        Breakpoints:
          base        phone / narrow
          md  768px   tablet portrait
          xl 1280px   laptop and desktop

        The log sits BESIDE the player panel below xl and above it from xl up.
        Tablet landscape is only ~768px tall, so vertical space is the scarce
        resource there and a side-by-side log costs none of it; a laptop has the
        height to stack and the width to give the log a full row.

        xl rather than lg for that switch: iPad landscape is exactly 1024px, so
        an lg: breakpoint would flip to the laptop layout on the device this is
        meant to suit.

        The root stays a row at every size because the collapsed bank rail is
        only 4rem; turning it into a bottom bar would cost more space, not less.
    -->
    <div v-else class="relative flex h-[100dvh] gap-2 bg-gray-dark p-2 md:gap-3 md:p-3 xl:gap-6 xl:p-6">

        <!--
            min-w-0 lets this column shrink so the bank rail always fits;
            without it the panels' intrinsic width wins and the rail is pushed
            off-screen. Below lg the column scrolls; at lg everything fits.
        -->
        <div class="scroll-slim flex min-h-0 min-w-0 flex-1 flex-col gap-2 overflow-y-auto md:gap-3
                    xl:gap-4 xl:overflow-hidden">

            <Header :game-code="code" />

            <!--
                Opponents. Three panels side by side need roughly 900px, so
                below lg they become a horizontal strip at a fixed width and
                scroll sideways — legible panels you swipe beats three panels
                squeezed to illegibility.
            -->
            <div class="scroll-slim flex w-full shrink-0 gap-2 overflow-x-auto pb-1 md:gap-3
                        xl:gap-4 xl:overflow-visible xl:pb-0">
                <PlayerCardHolder v-for="seat in opponentSeats" :key="seat.seatIndex" :player-type="'opponent'"
                    :seat-index="seat.seatIndex" :player-name="seat.name" :player-active="seat.occupied"
                    :is-turn="seat.isTurn" :hand="seat.hand" :points="seat.points" :food-due="seat.foodDue"
                    :rent-due="seat.rentDue" class="w-[17rem] shrink-0 md:w-[19rem] xl:w-auto xl:min-w-0 xl:flex-1" />
            </div>

            <div class="flex min-h-0 flex-1 flex-row gap-2 md:gap-3 xl:flex-col xl:gap-4">
                <!--
                    Below xl the log is a fixed-width sidebar so the player
                    panel keeps the room it needs; from xl it takes a full row
                    and grows into the leftover height.

                    min-h-0 on both axes matters: a flex item defaults to
                    min-height/min-width auto and refuses to shrink below its
                    content, which would make the log push the layout rather
                    than scroll inside itself.
                -->
                <EventLog class="w-64 min-h-0 shrink-0 md:w-72 xl:w-full xl:flex-1" :events="events"
                    :seat-by-player="seatByPlayer" :name-by-player="nameByPlayer" :sending="sendingChat"
                    @send="(text) => games.sendChat(code, text)" />

                <PlayerCardHolder class="min-w-0 flex-1 xl:w-full xl:flex-none" :active-action="activeAction"
                    :seat-index="mine?.seatIndex ?? -1" :player-name="mine?.name ?? ''" :player-active="mine !== null"
                    :is-turn="isMyTurn" :hand="mine?.hand ?? {}" :points="mine?.points ?? 0"
                    :food-due="mine?.foodDue ?? 0" :rent-due="mine?.rentDue ?? 0" :busy="acting"
                    @buy="startAction('buy')" @sell="startAction('sell')" @trade="startAction('trade')"
                    @cancel-operation="cancelAction" @transaction="onSell" @end-turn="onEndTurn" />
            </div>
        </div>

        <BankSection :buying-active="activeAction === 'buy'" :pools="state.bank" :points="me?.points ?? 0"
            :busy="acting" @cancel="cancelAction" @confirm="onBuy" />

        <!-- Action failures are transient and belong near the action, not in a
         panel that shifts layout when it appears. -->
        <Transition name="toast">
            <div v-if="actionError" class="fixed bottom-6 left-1/2 z-[200] -translate-x-1/2 rounded-xl border-2 border-rose-400
               bg-gray-x-dark px-5 py-3 shadow-2xl shadow-black/50">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-rose-400">{{ actionError }}</span>
                    <button type="button" @click="games.actionError = null"
                        class="cursor-pointer text-gray-x-light transition duration-200 hover:text-gray-2x-light">🗙</button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<style scoped>
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

/* content-box clip plus a transparent border is what makes the thumb read as
   inset and pill-shaped: the border reserves padding the background skips */
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