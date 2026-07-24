<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import { useCardTypesStore } from '../stores/cardTypes'
import { useGamesStore } from '../stores/games'

// From the /game/:code route via `props: true`
const props = defineProps({ code: { type: String, required: true } })

const cardTypes = useCardTypesStore()
const games = useGamesStore()

const { loaded, error: cardError } = storeToRefs(cardTypes)
const { state, hasLoadedState, stateError, acting, actionError } = storeToRefs(games)

async function load() {
  await Promise.all([cardTypes.fetchAll(), games.fetchState(props.code)])
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
  <LoadingScreen
    v-if="!hasLoadedState || !loaded"
    message="Taking a seat…"
    :error="stateError ?? cardError ?? ''"
    @retry="load"
  />

  <div v-else class="relative flex h-[100dvh] gap-6 bg-gray-dark p-6">
    <div class="flex w-full flex-col">
      <Header :game-code="code" />

      <div class="flex-grow py-4">
        <div class="flex w-full gap-4">
          <PlayerCardHolder
            v-for="seat in opponentSeats"
            :key="seat.seatIndex"
            :player-type="'opponent'"
            :seat-index="seat.seatIndex"
            :player-name="seat.name"
            :player-active="seat.occupied"
            :is-turn="seat.isTurn"
            :hand="seat.hand"
            :points="seat.points"
            :food-due="seat.foodDue"
            :rent-due="seat.rentDue"
            class="min-w-0 flex-1"
          />
        </div>
      </div>

      <PlayerCardHolder
        :active-action="activeAction"
        :seat-index="mine?.seatIndex ?? -1"
        :player-name="mine?.name ?? ''"
        :player-active="mine !== null"
        :is-turn="isMyTurn"
        :hand="mine?.hand ?? {}"
        :points="mine?.points ?? 0"
        :food-due="mine?.foodDue ?? 0"
        :rent-due="mine?.rentDue ?? 0"
        :busy="acting"
        @buy="startAction('buy')"
        @sell="startAction('sell')"
        @trade="startAction('trade')"
        @cancel-operation="cancelAction"
        @transaction="onSell"
        @end-turn="onEndTurn"
      />
    </div>

    <BankSection
      :buying-active="activeAction === 'buy'"
      :pools="state.bank"
      :points="me?.points ?? 0"
      :busy="acting"
      @cancel="cancelAction"
      @confirm="onBuy"
    />

    <!-- Action failures are transient and belong near the action, not in a
         panel that shifts layout when it appears. -->
    <Transition name="toast">
      <div
        v-if="actionError"
        class="fixed bottom-6 left-1/2 z-[200] -translate-x-1/2 rounded-xl border-2 border-rose-400
               bg-gray-x-dark px-5 py-3 shadow-2xl shadow-black/50"
      >
        <div class="flex items-center gap-3">
          <span class="text-sm font-bold text-rose-400">{{ actionError }}</span>
          <button
            type="button" @click="games.actionError = null"
            class="cursor-pointer text-gray-x-light transition duration-200 hover:text-gray-2x-light"
          >🗙</button>
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

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active { transition: none; }
}
</style>