<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useGamesStore } from '../stores/games'
import SeatToken from '../Components/SeatToken.vue'

const router = useRouter()
const auth = useAuthStore()
const games = useGamesStore()

const { user } = storeToRefs(auth)
const { myGames, loadingMine, busy, error } = storeToRefs(games)

// The created game now comes from the server, not a local generator: it is a
// real row with a unique code that other players can actually join.
const created = ref(null)
const joinCode = ref('')
const copied = ref(false)

onMounted(() => games.fetchMine())

async function createGame() {
  const game = await games.createGame(4)
  if (game) created.value = game
}

async function copyCode() {
  await navigator.clipboard.writeText(created.value.joinCode)
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}

function enterGame(code) {
  router.push({ name: 'game', params: { code } })
}

const canJoin = computed(() => joinCode.value.trim().length === 6)

async function joinGame() {
  if (!canJoin.value) return
  const game = await games.joinGame(joinCode.value.trim())
  if (game) enterGame(game.joinCode)
}

async function logout() {
  await auth.logout()
  router.push({ name: 'landing' })
}

// Finished games stay in the list from the API; the lobby only shows live ones.
const activeGames = computed(() =>
  myGames.value.filter((g) => g.status === 'lobby' || g.status === 'in_progress')
)

function mySeat(game) {
  return game.players.find((p) => p.displayName === user.value?.display_name)?.seatIndex ?? -1
}

const STATUS_META = {
  lobby: { label: 'Waiting', class: 'border-amber-400/50 bg-amber-400/15 text-amber-400' },
  in_progress: { label: 'In progress', class: 'border-emerald-400/50 bg-emerald-400/15 text-emerald-400' },
}

const panelClass =
  'flex flex-col gap-5 rounded-[1.75rem] border-2 border-gray-light bg-gray-x-dark/85 p-8 ' +
  'shadow-2xl shadow-black/30 backdrop-blur-xl'
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
</script>

<template>
  <div class="mx-auto flex w-full max-w-3xl flex-col gap-6 p-6">

    <header
      class="flex items-center justify-between rounded-[1.5rem] border-2 border-gray-light
             bg-gray-x-dark/85 p-4 backdrop-blur-xl"
    >
      <h1 class="text-2xl font-bold tracking-widest text-gray-2x-light">TRADERS HALL</h1>
      <div class="flex items-center gap-3">
        <div class="flex flex-col items-end leading-tight">
          <span class="font-bold text-gray-2x-light">{{ user?.display_name }}</span>
          <span class="text-xs text-gray-x-light">@{{ user?.username }}</span>
        </div>
        <button
          type="button" aria-label="Log out" title="Log out" @click="logout"
          class="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg border-2
                 border-gray-light bg-gray-dark text-gray-x-light transition duration-200 ease-in-out
                 hover:border-rose-400 hover:text-rose-400"
        >⏻</button>
      </div>
    </header>

    <div class="flex flex-1 flex-col justify-center gap-6">

      <!-- ── my games ───────────────────────────────────────── -->
      <div v-if="loadingMine || activeGames.length" :class="panelClass">
        <div class="flex items-center justify-between">
          <div class="flex flex-col gap-1">
            <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Your tables</h2>
            <p class="text-sm text-gray-x-light">Games you are seated at right now.</p>
          </div>
          <button
            type="button" :disabled="loadingMine" @click="games.fetchMine()"
            class="cursor-pointer rounded-lg border-2 border-gray-light px-3 py-1.5 text-sm font-bold
                   text-gray-x-light transition duration-200 ease-in-out hover:border-gray-x-light
                   hover:text-gray-2x-light disabled:opacity-40"
          >{{ loadingMine ? '…' : 'Refresh' }}</button>
        </div>

        <div v-if="loadingMine && !activeGames.length" class="py-6 text-center text-sm text-gray-x-light">
          Loading your tables…
        </div>

        <ul v-else class="flex flex-col gap-3">
          <li
            v-for="game in activeGames"
            :key="game.id"
            class="group flex items-center gap-4 rounded-2xl border-2 border-gray-light bg-gray-dark/60
                   p-4 transition duration-200 ease-in-out hover:border-gray-x-light/60"
          >
            <!-- your own token, so you can tell your tables apart at a glance -->
            <SeatToken :seat-index="mySeat(game)" size="md" />

            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <div class="flex items-center gap-3">
                <span class="font-bold tracking-[0.3em] text-teal-light">{{ game.joinCode }}</span>
                <span
                  class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                  :class="STATUS_META[game.status]?.class"
                >{{ STATUS_META[game.status]?.label ?? game.status }}</span>
              </div>

              <!-- filled seats as tokens, empty ones as dashed placeholders:
                   the row shows how full the table is without a count -->
              <div class="flex items-center gap-1.5">
                <SeatToken
                  v-for="i in game.maxPlayers"
                  :key="i"
                  :seat-index="game.players.some((p) => p.seatIndex === i - 1) ? i - 1 : -1"
                  size="sm"
                />
                <span class="ml-1 text-xs text-gray-x-light">
                  {{ game.players.length }} / {{ game.maxPlayers }}
                </span>
              </div>
            </div>

            <button
              type="button" @click="enterGame(game.joinCode)"
              class="shrink-0 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light px-5 py-2.5
                     font-bold text-gray-dark transition duration-200 ease-in-out hover:brightness-110
                     active:scale-[0.99]"
            >{{ game.status === 'lobby' ? 'Open' : 'Resume' }}</button>
          </li>
        </ul>
      </div>

      <!-- ── create ─────────────────────────────────────────── -->
      <div :class="panelClass">
        <div class="flex flex-col gap-1">
          <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Start a game</h2>
          <p class="text-sm text-gray-x-light">Create a table and share the code with up to three others.</p>
        </div>

        <button
          v-if="!created"
          type="button" :disabled="busy" @click="createGame"
          class="w-full cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light py-3.5
                 font-bold text-gray-dark transition duration-200 ease-in-out hover:brightness-110
                 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span class="flex items-center justify-center gap-2">
            <span
              v-if="busy"
              class="h-4 w-4 animate-spin rounded-full border-2 border-gray-dark/30 border-t-gray-dark"
            ></span>
            {{ busy ? 'Creating' : 'Create game' }}
          </span>
        </button>

        <template v-else>
          <div class="flex flex-col gap-2">
            <span :class="labelClass">Game code</span>
            <div class="flex items-center gap-3">
              <div
                class="min-w-0 flex-1 rounded-xl border-2 border-teal-light/50 bg-gray-dark px-6 py-4
                       text-center text-4xl font-bold tracking-[0.4em] text-teal-light tabular-nums"
              >{{ created.joinCode }}</div>
              <button
                type="button" @click="copyCode"
                class="h-16 w-24 shrink-0 cursor-pointer rounded-xl border-2 border-gray-light font-bold
                       text-gray-x-light transition duration-200 ease-in-out
                       hover:border-gray-x-light hover:text-gray-2x-light"
              >{{ copied ? 'Copied' : 'Copy' }}</button>
            </div>
            <p class="text-sm text-gray-x-light">Others join with this code. Keep it handy.</p>
          </div>

          <div class="flex gap-3">
            <button
              type="button" @click="created = null"
              class="shrink-0 cursor-pointer rounded-xl border-2 border-gray-light px-6 py-3 font-bold
                     text-gray-x-light transition duration-200 ease-in-out
                     hover:border-gray-x-light hover:text-gray-2x-light"
            >Dismiss</button>
            <button
              type="button" @click="enterGame(created.joinCode)"
              class="min-w-0 flex-1 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light
                     py-3 font-bold text-gray-dark transition duration-200 ease-in-out
                     hover:brightness-110 active:scale-[0.99]"
            >Enter table</button>
          </div>
        </template>
      </div>

      <!-- ── join ───────────────────────────────────────────── -->
      <div :class="panelClass">
        <div class="flex flex-col gap-1">
          <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Join a game</h2>
          <p class="text-sm text-gray-x-light">Enter the six-character code you were given.</p>
        </div>

        <form class="flex gap-3" @submit.prevent="joinGame">
          <!--
            min-w-0 is load bearing. A flex item's default min-width:auto stops
            it shrinking below its content's intrinsic width, and with size=20,
            text-2xl and tracking-[0.4em] that width exceeds the row — so the
            input refused to shrink and pushed the button past the edge.
          -->
          <input
            v-model="joinCode" maxlength="6" size="6" spellcheck="false"
            autocapitalize="characters" placeholder="ABC123"
            class="min-w-0 flex-1 rounded-xl border-2 border-gray-light bg-gray-dark px-6 py-4
                   text-center text-2xl font-bold uppercase tracking-[0.4em] text-gray-2x-light
                   transition duration-200 ease-in-out placeholder:tracking-normal
                   placeholder:text-gray-light hover:border-gray-x-light/60
                   focus:border-teal-light focus:outline-none"
          />
          <button
            type="submit" :disabled="!canJoin || busy"
            class="shrink-0 cursor-pointer rounded-xl border-2 border-gray-light px-8 font-bold
                   text-gray-x-light transition duration-200 ease-in-out
                   hover:border-gray-x-light hover:text-gray-2x-light
                   disabled:cursor-not-allowed disabled:opacity-40"
          >Join</button>
        </form>

        <p v-if="error" class="text-sm font-bold text-rose-400">{{ error }}</p>
      </div>
    </div>
  </div>
</template>