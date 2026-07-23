<script setup>
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import { useCardTypesStore } from '../stores/cardTypes'
import { useGamesStore } from '../stores/games'
import { useAuthStore } from '../stores/auth'

// From the /game/:code route via `props: true`
const props = defineProps({ code: { type: String, required: true } })

const cardTypes = useCardTypesStore()
const games = useGamesStore()
const auth = useAuthStore()

const { loaded, error: cardError } = storeToRefs(cardTypes)
const { current, error: gameError } = storeToRefs(games)
const { user } = storeToRefs(auth)

const ready = ref(false)

async function load() {
  ready.value = false
  await Promise.all([cardTypes.fetchAll(), games.fetchGame(props.code)])
  ready.value = true
}
onMounted(load)

// Which seat is mine. game_players carries no user_id in the public shape, so
// this matches on the display-name snapshot for now — swap to a `you` block on
// the projection when the game state endpoint lands.
const mySeat = computed(() =>
  current.value?.players.find((p) => p.displayName === user.value?.display_name) ?? null
)

/*
  Every seat, occupied or not, so the table always has max_players panels and
  an empty chair looks like an empty chair rather than a missing panel.
*/
const seats = computed(() => {
  const game = current.value
  if (!game) return []
  return Array.from({ length: game.maxPlayers }, (_, i) => {
    const player = game.players.find((p) => p.seatIndex === i) ?? null
    return {
      seatIndex: i,
      occupied: player !== null,
      name: player?.displayName ?? 'Empty seat',
      isMe: player != null && player.seatIndex === mySeat.value?.seatIndex,
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
</script>

<template>
  <LoadingScreen
    v-if="!ready || !loaded"
    message="Taking a seat…"
    :error="cardError ?? gameError ?? ''"
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
            class="min-w-0 flex-1"
          />
        </div>
      </div>

      <PlayerCardHolder
        :active-action="activeAction"
        :seat-index="mine?.seatIndex ?? -1"
        :player-name="mine?.name ?? ''"
        :player-active="mine !== null"
        :is-turn="true"
        @buy="startAction('buy')"
        @sell="startAction('sell')"
        @trade="startAction('trade')"
        @cancel-operation="cancelAction"
      />
    </div>

    <BankSection :buying-active="activeAction === 'buy'" @cancel="cancelAction" />
  </div>
</template>