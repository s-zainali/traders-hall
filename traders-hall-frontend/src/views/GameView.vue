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
const { state, hasLoadedState, stateError } = storeToRefs(games)

async function load() {
  await Promise.all([cardTypes.fetchAll(), games.fetchState(props.code)])
}

/* ── live updates ──────────────────────────────────────────────
   Polling, same shape as the lobby but faster — and more clearly temporary.
   A 2s delay on "has anyone joined" is fine; a 2s delay on "did my opponent
   just take the last rice" is not. This screen is the one that actually wants
   a socket, and games.fetchState is the single function that gets replaced.
─────────────────────────────────────────────────────────────── */
const POLL_MS = 2000
let pollTimer = null
let inFlight = false

async function poll() {
  // A slow response must not stack requests behind it; skipping a tick beats
  // queueing one.
  if (inFlight || document.hidden) return
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

/*
  Every seat, occupied or not, so the table always shows max_players panels and
  an empty chair looks like an empty chair rather than a missing panel.
*/
const seats = computed(() => {
  const s = state.value
  if (!s) return []
  return Array.from({ length: s.game.maxPlayers }, (_, i) => {
    const player = s.players.find((p) => p.seatIndex === i) ?? null
    return {
      seatIndex: i,
      occupied: player !== null,
      name: player?.displayName ?? 'Empty seat',
      // seat_index is the identity here, not display_name — two players can
      // share a name, and the projection gives us the real seat.
      isMe: player !== null && player.seatIndex === me.value?.seatIndex,
      isTurn: player !== null && player.id === s.game.currentPlayerId,
      hand: player?.hand ?? {},
      points: player?.points ?? 0,
      foodDue: player?.foodDue ?? 0,
      rentDue: player?.rentDue ?? 0,
      status: player?.status ?? 'empty',
    }
  })
})

// opponents render across the top, my own panel sits at the bottom
const opponentSeats = computed(() => seats.value.filter((s) => !s.isMe))
const mine = computed(() => seats.value.find((s) => s.isMe) ?? null)

// One ref for the current mode: '' | 'buy' | 'sell' | 'trade'.
const activeAction = ref('')
const startAction = (action) => (activeAction.value = action)
const cancelAction = () => (activeAction.value = '')

// A poll that arrives mid-transaction must not leave a modal open against stock
// that has since changed under it.
watch(
  () => state.value?.game.stateVersion,
  (next, prev) => {
    if (prev !== undefined && next !== prev) cancelAction()
  }
)
</script>

<template>
  <LoadingScreen
    v-if="!hasLoadedState || !loaded"
    message="Taking a seat…"
    :error="stateError ?? cardError ?? ''"
    @retry="load"
  />

  <div v-else class="flex min-h-[100dvh] gap-6 bg-gray-dark p-6">
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
        :is-turn="mine?.isTurn ?? false"
        :hand="mine?.hand ?? {}"
        :points="mine?.points ?? 0"
        :food-due="mine?.foodDue ?? 0"
        :rent-due="mine?.rentDue ?? 0"
        @buy="startAction('buy')"
        @sell="startAction('sell')"
        @trade="startAction('trade')"
        @cancel-operation="cancelAction"
      />
    </div>

    <BankSection
      :buying-active="activeAction === 'buy'"
      :pools="state.bank"
      @cancel="cancelAction"
    />
  </div>
</template>