<script setup>
import { computed } from 'vue'
import SeatToken from '../SeatToken.vue'

/**
 * The end of somebody's game.
 *
 * One component for both outcomes because they are the same moment seen from two
 * seats, and splitting them would mean two places to keep the wording and the
 * exit consistent.
 *
 * Deliberately not dismissable. A defeat screen with a close button invites the
 * player to sit in a game they can no longer act in, watching controls that will
 * refuse them. The only way out is the lobby.
 */
const props = defineProps({
    // 'eliminated' | 'won'
    outcome: { type: String, default: 'eliminated' },
    // 'starvation' | 'loan_default' | 'rent_default' | ''
    reason: { type: String, default: '' },
    seatIndex: { type: Number, default: -1 },
    playerName: { type: String, default: '' },
    // who took the estate, when a player rather than the bank did
    creditorName: { type: String, default: '' },
})

const emit = defineEmits(['leave'])

const won = computed(() => props.outcome === 'won')

/*
  Each cause gets its own words. "You were eliminated" tells a player nothing they
  can learn from; naming the clock that ran out does.
*/
const REASONS = {
    starvation: {
        title: 'You starved',
        body: 'The food counter reached zero with nothing left to eat.',
        icon: 'food',
    },
    loan_default: {
        title: 'The bank took everything',
        body: 'Your loan came due and your points and property still did not cover it.',
        icon: 'bank',
    },
    rent_default: {
        title: 'You could not make rent',
        body: 'What you owed was more than everything you had.',
        icon: 'home',
    },
}

const detail = computed(
    () => REASONS[props.reason] ?? {
        title: 'You are out',
        body: 'You ran out of room to manoeuvre.',
        icon: 'warn',
    }
)

const ICONS = {
    food: 'M13 3c0 5-3.5 8-9 9 0-5 3.5-8 9-9zM4 12l4-4',
    bank: 'M2.5 6.5 8 3l5.5 3.5M4.5 7.5v4.5M7 7.5v4.5M9 7.5v4.5M11.5 7.5v4.5M2.5 13.5h11',
    home: 'M2.5 8 8 3l5.5 5M4 7.5V13h8V7.5',
    warn: 'M8 2.5 14 13H2zM8 6.5v2.6M8 11.2v.1',
    crown: 'M2 12h12M3 12 2 5l3.5 3L8 3l2.5 5L14 5l-1 7',
}
</script>

<template>
    <div class="fixed inset-0 z-[400] flex items-center justify-center bg-gray-dark/95 p-6">
        <div role="dialog" aria-modal="true" aria-labelledby="outcome-title"
            class="flex w-full max-w-md flex-col items-center gap-6 rounded-[2rem] border-2 p-10 text-center shadow-2xl shadow-black/70"
            :class="won
                ? 'border-teal-light/60 bg-teal-dark/15'
                : 'border-rose-400/50 bg-gray-x-dark'">

            <span class="flex h-16 w-16 items-center justify-center rounded-2xl border-2"
                :class="won ? 'border-teal-light bg-teal-dark/40' : 'border-rose-400 bg-rose-400/10'">
                <svg viewBox="0 0 16 16" class="h-8 w-8" fill="none" stroke="currentColor" stroke-width="1.5"
                    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
                    :class="won ? 'text-teal-light' : 'text-rose-400'">
                    <path :d="won ? ICONS.crown : (ICONS[detail.icon] ?? ICONS.warn)" />
                </svg>
            </span>

            <div class="flex flex-col items-center gap-2">
                <span class="text-[10px] font-bold uppercase tracking-[0.35em]"
                    :class="won ? 'text-teal-light' : 'text-rose-400'">
                    {{ won ? 'The hall is yours' : 'Out of the game' }}
                </span>
                <h2 id="outcome-title" class="text-3xl font-bold tracking-wide text-gray-2x-light">
                    {{ won ? 'You win' : detail.title }}
                </h2>
            </div>

            <p class="text-sm leading-relaxed text-gray-x-light">
                {{ won
                    ? 'Everyone else ran out of points, food or roof. You did not.'
                    : detail.body }}
            </p>

            <!-- Who collected. Worth saying: a player taking your estate is a very
                 different game state from the bank absorbing it. -->
            <p v-if="!won && creditorName"
                class="flex items-center gap-2 rounded-xl border-2 border-gray-light px-4 py-2 text-xs text-gray-x-light">
                <span>Everything you held went to</span>
                <span class="font-bold text-gray-2x-light">{{ creditorName }}</span>
            </p>

            <div class="flex items-center gap-2">
                <SeatToken :seat-index="seatIndex" size="sm" />
                <span class="text-sm font-bold text-gray-2x-light">{{ playerName }}</span>
            </div>

            <button type="button" @click="emit('leave')"
                class="mt-2 cursor-pointer rounded-xl border-2 px-8 py-3 font-bold transition duration-200 ease-in-out hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2"
                :class="won
                    ? 'border-teal-light bg-teal-light text-gray-dark outline-teal-light'
                    : 'border-gray-light text-gray-x-light outline-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light'">
                Back to lobby
            </button>
        </div>
    </div>
</template>