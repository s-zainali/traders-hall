<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const { user } = storeToRefs(auth)

const creating = ref(false)
const gameCode = ref('')
const joinCode = ref('')
const error = ref('')

/*
  PLACEHOLDER. A real join code has to come from the server: it must be unique
  across all games, and it has to correspond to a row other players can join.
  Generating it here produces a code that means nothing to anyone else.

  Replaced by POST /api/v1/games once the games table exists.
*/
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   // no I/O/0/1 — unreadable aloud

function generatePlaceholderCode() {
  return Array.from(
    { length: 6 },
    () => ALPHABET[Math.floor(Math.random() * ALPHABET.length)]
  ).join('')
}

async function createGame() {
  creating.value = true
  error.value = ''
  try {
    await new Promise((r) => setTimeout(r, 400))   // stand-in for the request
    gameCode.value = generatePlaceholderCode()
  } catch (e) {
    error.value = e.message
  } finally {
    creating.value = false
  }
}

const copied = ref(false)
async function copyCode() {
  await navigator.clipboard.writeText(gameCode.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}

function enterGame() {
  router.push({ name: 'game', params: { code: gameCode.value } })
}

const canJoin = computed(() => joinCode.value.trim().length === 6)

function joinGame() {
  if (!canJoin.value) return
  router.push({ name: 'game', params: { code: joinCode.value.trim().toUpperCase() } })
}

async function logout() {
  await auth.logout()
  router.push({ name: 'landing' })
}

const panelClass = 'flex flex-col gap-5 p-8 bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem]'
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
</script>

<template>
  <div class="min-h-[100dvh] bg-gray-dark p-6">
    <div class="mx-auto flex max-w-3xl flex-col gap-6">

      <header class="flex items-center justify-between rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4">
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

      <!-- create -->
      <div :class="panelClass">
        <div class="flex flex-col gap-1">
          <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Start a game</h2>
          <p class="text-sm text-gray-x-light">Create a table and share the code with up to three others.</p>
        </div>

        <template v-if="!gameCode">
          <button
            type="button" :disabled="creating" @click="createGame"
            class="w-full cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light py-3.5
                   font-bold text-gray-dark transition duration-200 ease-in-out hover:brightness-110
                   disabled:cursor-not-allowed disabled:opacity-40"
          >{{ creating ? 'Creating…' : 'Create game' }}</button>
        </template>

        <template v-else>
          <div class="flex flex-col gap-2">
            <span :class="labelClass">Game code</span>
            <div class="flex items-center gap-3">
              <div
                class="flex-1 rounded-xl border-2 border-teal-light/50 bg-gray-dark px-6 py-4 text-center
                       text-4xl font-bold tracking-[0.4em] text-teal-light tabular-nums"
              >{{ gameCode }}</div>
              <button
                type="button" @click="copyCode"
                class="h-16 cursor-pointer rounded-xl border-2 border-gray-light px-5 font-bold
                       text-gray-x-light transition duration-200 ease-in-out
                       hover:border-gray-x-light hover:text-gray-2x-light"
              >{{ copied ? 'Copied' : 'Copy' }}</button>
            </div>
            <p class="text-sm text-gray-x-light">Others join with this code. Keep it handy.</p>
          </div>

          <div class="flex gap-3">
            <button
              type="button" @click="gameCode = ''"
              class="cursor-pointer rounded-xl border-2 border-gray-light px-6 py-3 font-bold
                     text-gray-x-light transition duration-200 ease-in-out
                     hover:border-gray-x-light hover:text-gray-2x-light"
            >Discard</button>
            <button
              type="button" @click="enterGame"
              class="flex-1 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light py-3
                     font-bold text-gray-dark transition duration-200 ease-in-out hover:brightness-110"
            >Enter table</button>
          </div>
        </template>
      </div>

      <!-- join -->
      <div :class="panelClass">
        <div class="flex flex-col gap-1">
          <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Join a game</h2>
          <p class="text-sm text-gray-x-light">Enter the six-character code you were given.</p>
        </div>

        <form class="flex gap-3" @submit.prevent="joinGame">
          <input
            v-model="joinCode" maxlength="6" spellcheck="false" autocapitalize="characters"
            placeholder="ABC123"
            class="flex-1 rounded-xl border-2 border-gray-light bg-gray-dark px-6 py-4 text-center
                   text-2xl font-bold uppercase tracking-[0.4em] text-gray-2x-light
                   transition duration-200 ease-in-out placeholder:tracking-normal
                   placeholder:text-gray-light focus:border-teal-light focus:outline-none"
          />
          <button
            type="submit" :disabled="!canJoin"
            class="cursor-pointer rounded-xl border-2 border-gray-light px-8 font-bold text-gray-x-light
                   transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light
                   disabled:cursor-not-allowed disabled:opacity-40"
          >Join</button>
        </form>

        <p v-if="error" class="text-sm font-bold text-rose-400">{{ error }}</p>
      </div>
    </div>
  </div>
</template>