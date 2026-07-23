<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

const created = ref(null)
const joinCode = ref('')
const copied = ref(false)

// Two-step confirm rather than a modal: destructive but small, and a modal for
// one button is more chrome than the action deserves. Holds the code of the
// game awaiting confirmation, plus which action it is.
const confirming = ref({ code: '', action: '' })
let confirmTimer = null

/* ── live-ish updates ──────────────────────────────────────────
   Polling, not a WebSocket. Three seconds of staleness on "has anyone joined"
   is imperceptible, and a socket's real value is latency on the game table —
   where it also gets a protocol designed against a real payload rather than a
   guess. This is the fifteen lines that get deleted when that lands.
─────────────────────────────────────────────────────────────── */
const POLL_MS = 3000
let pollTimer = null
let inFlight = false

async function poll() {
  // A slow response must not stack requests behind it; skipping a tick is
  // always better than queueing one.
  if (inFlight || document.hidden) return
  inFlight = true
  try {
    await games.fetchMine()
  } finally {
    inFlight = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(poll, POLL_MS)
}

function stopPolling() {
  clearInterval(pollTimer)
  pollTimer = null
}

// A backgrounded tab should not keep polling; refetch immediately on return so
// the list is current the moment it is looked at again.
function onVisibility() {
  if (document.hidden) stopPolling()
  else {
    poll()
    startPolling()
  }
}

onMounted(() => {
  games.fetchMine()
  startPolling()
  document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
  stopPolling()
  clearTimeout(confirmTimer)
  document.removeEventListener('visibilitychange', onVisibility)
})

/* ── actions ─────────────────────────────────────────────────── */

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
  if (game) {
    joinCode.value = ''
    // Deliberately NOT navigating: the lobby list is the waiting room, and
    // being thrown onto a table that has not started yet is disorienting.
  }
}

async function startGame(code) {
  const game = await games.startGame(code)
  if (game) enterGame(code)
}

function ask(code, action) {
  confirming.value = { code, action }
  clearTimeout(confirmTimer)
  // Long enough to read two options and decide. A short auto-revert is fine for
  // a one-click confirm but hostile when there is something to weigh up.
  confirmTimer = setTimeout(() => (confirming.value = { code: '', action: '' }), 12000)
}

function cancelConfirm() {
  clearTimeout(confirmTimer)
  confirming.value = { code: '', action: '' }
}

function isConfirming(code, action) {
  return confirming.value.code === code && confirming.value.action === action
}

async function doDelete(code) {
  clearTimeout(confirmTimer)
  confirming.value = { code: '', action: '' }
  await games.closeGame(code)
  if (created.value?.joinCode === code) created.value = null
}

async function doLeave(code) {
  clearTimeout(confirmTimer)
  confirming.value = { code: '', action: '' }
  await games.leaveGame(code)
  if (created.value?.joinCode === code) created.value = null
}

async function logout() {
  await auth.logout()
  router.push({ name: 'landing' })
}

/* ── derived ─────────────────────────────────────────────────── */

// Finished games stay in the API list; the lobby only shows live ones.
const activeGames = computed(() =>
  myGames.value.filter((g) => g.status === 'lobby' || g.status === 'in_progress')
)

function isHost(game) {
  return game.hostUserId === user.value?.id
}

function mySeat(game) {
  return game.players.find((p) => p.displayName === user.value?.display_name)?.seatIndex ?? -1
}

/**
 * One place decides what the primary button says and does, because the four
 * cases are mutually exclusive and scattering them across the template is how
 * they end up contradicting each other.
 */
function primaryAction(game) {
  if (game.status === 'in_progress') {
    return { label: 'Enter', disabled: false, run: () => enterGame(game.joinCode), primary: true }
  }
  if (!isHost(game)) {
    return { label: 'Waiting for host', disabled: true, run: () => {}, primary: false }
  }
  if (game.players.length < 2) {
    return { label: 'Need 2 players', disabled: true, run: () => {}, primary: false }
  }
  return { label: 'Start game', disabled: false, run: () => startGame(game.joinCode), primary: true }
}

/*
  The host owns the table, so leaving is genuinely two different actions with
  different consequences — hand it over, or bin it. A yes/no confirm cannot
  express that, so hosts get an explicit choice instead.
*/
function canDelete(game) {
  return isHost(game)
}

/** Who inherits the table if the host walks away: the next human seat. */
function heirOf(game) {
  return (
    game.players
      .filter((p) => p.displayName !== user.value?.display_name && p.status !== 'resigned')
      .sort((a, b) => a.seatIndex - b.seatIndex)[0] ?? null
  )
}

/** Whether the action reaches other people, which is what earns a warning. */
function isHighStakes(game) {
  return game.status === 'in_progress' || game.players.length > 1
}

function guestLabel(game) {
  return game.status === 'in_progress' ? 'Resign' : 'Leave'
}

function guestWarning(game) {
  return game.status === 'in_progress'
    ? 'Resigning forfeits the game.'
    : 'Frees your seat at this table.'
}

function deleteWarning(game) {
  if (game.status === 'in_progress') return 'Ends the game for everyone.'
  if (game.players.length > 1) return `Removes the table for ${game.players.length - 1} other player(s).`
  return 'Nobody else is seated.'
}

const STATUS_META = {
  lobby: { label: 'Waiting', class: 'border-amber-400/50 bg-amber-400/15 text-amber-400' },
  in_progress: { label: 'In progress', class: 'border-emerald-400/50 bg-emerald-400/15 text-emerald-400' },
}

const panelClass =
  'flex flex-col gap-4 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/85 p-6 ' +
  'shadow-2xl shadow-black/30 backdrop-blur-xl'
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'

const primaryBtn =
  'min-w-0 flex-1 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light py-2 ' +
  'font-bold text-gray-dark transition duration-200 ease-in-out hover:brightness-110 active:scale-[0.99]'
const mutedBtn =
  'min-w-0 flex-1 rounded-xl border-2 border-gray-light py-2 font-bold text-gray-x-light ' +
  'cursor-not-allowed opacity-60'
const dangerBtn =
  'shrink-0 cursor-pointer rounded-xl border-2 px-4 py-2 font-bold transition duration-200 ease-in-out'
</script>

<template>
  <div class="mx-auto flex h-full w-full max-w-6xl min-h-0 flex-col gap-4 p-6">
    <!--
      min-h-0 on the flex children is what keeps the page from scrolling: a flex
      item defaults to min-height:auto, refusing to shrink below its content, so
      a long table list would push the page taller instead of scrolling inside
      its own panel. The vertical twin of min-w-0.
    -->

    <header
      class="flex shrink-0 items-center justify-between rounded-[1.5rem] border-2 border-gray-light
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

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">

      <!-- ── left: create + join ──────────────────────────── -->
      <div class="flex min-h-0 flex-col justify-center gap-4">

        <div :class="panelClass">
          <div class="flex flex-col gap-1">
            <h2 class="text-xl font-bold tracking-wide text-gray-2x-light">Start a game</h2>
            <p class="text-sm text-gray-x-light">Create a table and share the code with up to three others.</p>
          </div>

          <button
            v-if="!created"
            type="button" :disabled="busy" @click="createGame"
            class="w-full cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light py-3
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
                  class="min-w-0 flex-1 rounded-xl border-2 border-teal-light/50 bg-gray-dark px-4 py-3
                         text-center text-3xl font-bold tracking-[0.3em] text-teal-light tabular-nums"
                >{{ created.joinCode }}</div>
                <button
                  type="button" @click="copyCode"
                  class="h-14 w-20 shrink-0 cursor-pointer rounded-xl border-2 border-gray-light font-bold
                         text-gray-x-light transition duration-200 ease-in-out
                         hover:border-gray-x-light hover:text-gray-2x-light"
                >{{ copied ? 'Copied' : 'Copy' }}</button>
              </div>
              <p class="text-sm text-gray-x-light">
                Share this code. The table appears on the right — start it once someone joins.
              </p>
            </div>

            <button
              type="button" @click="created = null"
              class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-2.5 font-bold
                     text-gray-x-light transition duration-200 ease-in-out
                     hover:border-gray-x-light hover:text-gray-2x-light"
            >Dismiss</button>
          </template>
        </div>

        <div :class="panelClass">
          <div class="flex flex-col gap-1">
            <h2 class="text-xl font-bold tracking-wide text-gray-2x-light">Join a game</h2>
            <p class="text-sm text-gray-x-light">Enter the six-character code you were given.</p>
          </div>

          <form class="flex gap-3" @submit.prevent="joinGame">
            <!--
              min-w-0 is load bearing: a flex item's default min-width:auto stops
              it shrinking below its content's intrinsic width, and with size=20
              plus wide tracking that exceeds the row — so the input refused to
              shrink and pushed the button past the edge.
            -->
            <input
              v-model="joinCode" maxlength="6" size="6" spellcheck="false"
              autocapitalize="characters" placeholder="ABC123"
              class="min-w-0 flex-1 rounded-xl border-2 border-gray-light bg-gray-dark px-4 py-3
                     text-center text-xl font-bold uppercase tracking-[0.3em] text-gray-2x-light
                     transition duration-200 ease-in-out placeholder:tracking-normal
                     placeholder:text-gray-light hover:border-gray-x-light/60
                     focus:border-teal-light focus:outline-none"
            />
            <button
              type="submit" :disabled="!canJoin || busy"
              class="shrink-0 cursor-pointer rounded-xl border-2 border-gray-light px-6 font-bold
                     text-gray-x-light transition duration-200 ease-in-out
                     hover:border-gray-x-light hover:text-gray-2x-light
                     disabled:cursor-not-allowed disabled:opacity-40"
            >Join</button>
          </form>

          <p v-if="error" class="text-sm font-bold text-rose-400">{{ error }}</p>
        </div>
      </div>

      <!-- ── right: your tables ───────────────────────────── -->
      <div :class="[panelClass, 'min-h-0']">
        <div class="flex shrink-0 items-center justify-between">
          <div class="flex flex-col gap-1">
            <h2 class="text-xl font-bold tracking-wide text-gray-2x-light">Your tables</h2>
            <p class="text-sm text-gray-x-light">Updates automatically as players join.</p>
          </div>
          <!-- a quiet pulse, so it is clear the list is live rather than stale -->
          <span
            class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-gray-x-light"
          >
            <span class="live-dot h-1.5 w-1.5 rounded-full bg-emerald-400"></span> Live
          </span>
        </div>

        <div v-if="loadingMine && !activeGames.length" class="py-10 text-center text-sm text-gray-x-light">
          Loading your tables…
        </div>

        <div
          v-else-if="!activeGames.length"
          class="flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border-2
                 border-dashed border-gray-light py-10 text-center"
        >
          <SeatToken :seat-index="-1" size="lg" />
          <div class="flex flex-col gap-0.5">
            <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">No tables yet</span>
            <span class="text-xs text-gray-light">Create one, or join with a code</span>
          </div>
        </div>

        <!-- overflow-y-auto + min-h-0: the LIST scrolls, the page does not -->
        <ul v-else class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
          <li
            v-for="game in activeGames"
            :key="game.id"
            class="flex flex-col gap-3 rounded-2xl border-2 border-gray-light bg-gray-dark/60 p-4
                   transition duration-200 ease-in-out hover:border-gray-x-light/60"
          >
            <div class="flex items-center gap-3">
              <SeatToken :seat-index="mySeat(game)" size="md" />

              <div class="flex min-w-0 flex-1 flex-col gap-1">
                <div class="flex items-center gap-2">
                  <span class="font-bold tracking-[0.25em] text-teal-light">{{ game.joinCode }}</span>
                  <span
                    class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                    :class="STATUS_META[game.status]?.class"
                  >{{ STATUS_META[game.status]?.label ?? game.status }}</span>
                  <span v-if="isHost(game)" class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
                    Host
                  </span>
                </div>

                <!-- filled tokens for taken seats, dashed for empty: occupancy
                     at a glance, and the thing that visibly changes on poll -->
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
            </div>

            <div class="flex gap-2">
              <button
                type="button"
                :disabled="primaryAction(game).disabled || busy"
                :class="primaryAction(game).primary ? primaryBtn : mutedBtn"
                @click="primaryAction(game).run()"
              >{{ primaryAction(game).label }}</button>

              <button
                type="button" :disabled="busy"
                :class="[dangerBtn, isConfirming(game.joinCode, 'destroy')
                  ? 'border-rose-400 text-rose-400'
                  : 'border-gray-light text-gray-x-light hover:border-rose-400 hover:text-rose-400']"
                @click="isConfirming(game.joinCode, 'destroy')
                  ? cancelConfirm()
                  : ask(game.joinCode, 'destroy')"
              >{{
                isConfirming(game.joinCode, 'destroy')
                  ? 'Cancel'
                  : canDelete(game) ? 'Leave table' : guestLabel(game)
              }}</button>
            </div>

            <!--
              Host: two named outcomes, not a yes/no. "Delete" and "hand over"
              are different decisions, and a confirm dialog can only ask about
              one of them — which is how people end up deleting a table they
              only meant to step away from.
            -->
            <div
              v-if="isConfirming(game.joinCode, 'destroy') && canDelete(game)"
              class="flex flex-col gap-2 rounded-xl border-2 border-gray-light bg-gray-dark/80 p-3"
            >
              <button
                v-if="heirOf(game)"
                type="button" :disabled="busy" @click="doLeave(game.joinCode)"
                class="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-gray-light
                       p-3 text-left transition duration-200 ease-in-out
                       hover:border-teal-light hover:bg-teal-dark/20 disabled:opacity-40"
              >
                <SeatToken :seat-index="heirOf(game).seatIndex" size="sm" />
                <span class="flex min-w-0 flex-col">
                  <span class="text-sm font-bold text-gray-2x-light">Hand over &amp; leave</span>
                  <span class="text-xs text-gray-x-light">
                    {{ heirOf(game).displayName }} becomes host. The table carries on.
                  </span>
                </span>
              </button>

              <button
                type="button" :disabled="busy" @click="doDelete(game.joinCode)"
                class="flex cursor-pointer items-center gap-3 rounded-lg border-2 border-gray-light
                       p-3 text-left transition duration-200 ease-in-out
                       hover:border-rose-400 hover:bg-rose-400/15 disabled:opacity-40"
              >
                <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2
                             border-rose-400/50 bg-rose-400/15 text-rose-400">🗑</span>
                <span class="flex min-w-0 flex-col">
                  <span class="text-sm font-bold text-gray-2x-light">Delete table</span>
                  <span class="text-xs" :class="isHighStakes(game) ? 'text-rose-400' : 'text-gray-x-light'">
                    {{ deleteWarning(game) }}
                  </span>
                </span>
              </button>
            </div>

            <!-- Guest: one outcome, so a plain confirm is the right shape -->
            <div
              v-else-if="isConfirming(game.joinCode, 'destroy')"
              class="flex items-center gap-3 rounded-xl border-2 border-gray-light bg-gray-dark/80 p-3"
            >
              <span class="flex-1 text-xs font-bold"
                :class="game.status === 'in_progress' ? 'text-rose-400' : 'text-gray-x-light'">
                {{ guestWarning(game) }}
              </span>
              <button
                type="button" :disabled="busy" @click="doLeave(game.joinCode)"
                class="shrink-0 cursor-pointer rounded-lg border-2 border-rose-400 bg-rose-400 px-4 py-2
                       text-sm font-bold text-gray-dark transition duration-200 ease-in-out
                       hover:bg-rose-300 hover:border-rose-300 disabled:opacity-40"
              >{{ guestLabel(game) }}</button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.live-dot {
  animation: live-pulse 2s ease-in-out infinite;
}

@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.25; }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot { animation: none; }
}
</style>