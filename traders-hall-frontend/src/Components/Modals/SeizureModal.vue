<script setup>
import { computed, ref, watch } from 'vue'
import Card from '../Card.vue'
import SeatToken from '../SeatToken.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * The frozen game, from both sides.
 *
 * A tenant could not make rent but their cards can cover it, so the landlord
 * chooses which to take and nothing else may move until they do. One component
 * serves both views because they are the same event: the landlord gets a picker,
 * everyone else gets told who they are waiting for.
 *
 * Not dismissable by anyone. A closable overlay on a frozen game leaves players
 * clicking controls that will all come back GAME_FROZEN.
 */
const props = defineProps({
    seizure: { type: Object, required: true },
    busy: { type: Boolean, default: false },
})

const emit = defineEmits(['seize', 'waive'])

const cardTypes = useCardTypesStore()

const picks = ref({})

// A fresh seizure must not inherit the last one's selection.
watch(() => props.seizure?.agreementId, () => { picks.value = {} })

const options = computed(() =>
    Object.entries(props.seizure.seizable ?? {})
        .map(([code, free]) => {
            const card = cardTypes.get(code)
            return {
                code,
                free,
                title: card?.title ?? code,
                value: card?.sellValue ?? 0,
            }
        })
        .filter((o) => o.value > 0)
        .sort((a, b) => b.value - a.value)
)

const total = computed(() =>
    options.value.reduce((sum, o) => sum + (picks.value[o.code] ?? 0) * o.value, 0)
)

const debt = computed(() => props.seizure.debt ?? 0)
const covered = computed(() => total.value >= debt.value)

/*
  Mirrors the server rule: every pick has to be doing work. If dropping any one
  card would still cover the debt, the selection takes more than it is owed.
  Checked here so the button is disabled rather than the request refused.
*/
const excessive = computed(() =>
    covered.value &&
    options.value.some(
        (o) => (picks.value[o.code] ?? 0) > 0 && total.value - o.value >= debt.value
    )
)

const canSeize = computed(() => covered.value && !excessive.value && !props.busy)

function step(code, delta, max) {
    const next = Math.min(max, Math.max(0, (picks.value[code] ?? 0) + delta))
    picks.value = { ...picks.value, [code]: next }
}

const chosen = computed(() =>
    Object.fromEntries(Object.entries(picks.value).filter(([, n]) => n > 0))
)

const stepBtn =
    'flex h-7 w-7 items-center justify-center rounded-lg border-2 border-gray-x-light bg-gray-light text-sm font-bold text-gray-2x-light transition duration-200 ease-in-out hover:bg-gray-x-light hover:text-gray-dark disabled:cursor-not-allowed disabled:opacity-30'
const actionBtn =
    'rounded-xl border-2 px-5 py-2.5 font-bold transition duration-200 ease-in-out disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2'
</script>

<template>
    <div class="fixed inset-0 z-[350] flex items-center justify-center bg-gray-dark/95 p-6">
        <div role="dialog" aria-modal="true" aria-labelledby="seizure-title"
            class="scroll-slim flex max-h-full w-full max-w-lg flex-col gap-5 overflow-y-auto rounded-[2rem] border-2 border-amber-400/50 bg-gray-x-dark p-8 shadow-2xl shadow-black/70">

            <div class="flex flex-col gap-1">
                <span class="text-[10px] font-bold uppercase tracking-[0.35em] text-amber-400">
                    Game paused
                </span>
                <h2 id="seizure-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                    {{ seizure.mine ? 'Take what you are owed' : 'A landlord is collecting' }}
                </h2>
            </div>

            <p class="flex flex-wrap items-center gap-2 text-sm text-gray-x-light">
                <SeatToken :seat-index="seizure.debtorSeatIndex" size="sm" />
                <span class="font-bold text-gray-2x-light">{{ seizure.debtorName }}</span>
                <span>could not make rent to</span>
                <SeatToken :seat-index="seizure.landlordSeatIndex" size="sm" />
                <span class="font-bold text-gray-2x-light">{{ seizure.landlordName }}</span>
            </p>

            <div class="flex items-center justify-between gap-3 rounded-xl border-2 border-gray-light bg-gray-dark px-4 py-3">
                <span class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">
                    Still owed
                </span>
                <span class="flex items-center gap-2">
                    <Card :card-type="'point'" :selected="true" :large="false" />
                    <span class="text-xl font-bold tabular-nums text-rose-400">{{ debt }}</span>
                </span>
            </div>

            <!-- ══ the landlord chooses ══ -->
            <template v-if="seizure.mine">
                <div v-if="options.length" class="flex flex-col gap-2">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">
                        Their cards
                    </span>
                    <div v-for="o in options" :key="o.code"
                        class="flex items-center gap-3 rounded-xl border-2 px-3 py-2 transition-colors duration-200"
                        :class="(picks[o.code] ?? 0) > 0 ? 'border-amber-400/60 bg-amber-400/10' : 'border-gray-light'">
                        <Card :card-type="o.code" :selected="true" :large="false" />
                        <span class="flex min-w-0 flex-1 flex-col leading-tight">
                            <span class="truncate text-sm font-bold text-gray-2x-light">{{ o.title }}</span>
                            <span class="text-[10px] tabular-nums text-gray-light">
                                worth {{ o.value }} · {{ o.free }} free
                            </span>
                        </span>
                        <button type="button" :class="stepBtn" :disabled="(picks[o.code] ?? 0) <= 0"
                            :aria-label="`Take fewer ${o.title}`" @click="step(o.code, -1, o.free)">−</button>
                        <span class="w-6 text-center text-sm font-bold tabular-nums text-gray-2x-light">
                            {{ picks[o.code] ?? 0 }}
                        </span>
                        <button type="button" :class="stepBtn" :disabled="(picks[o.code] ?? 0) >= o.free"
                            :aria-label="`Take another ${o.title}`" @click="step(o.code, 1, o.free)">+</button>
                    </div>
                </div>

                <p v-else class="text-sm text-gray-light">
                    They have nothing left worth taking.
                </p>

                <div class="flex items-center justify-between gap-3 rounded-xl border-2 px-4 py-2"
                    :class="covered && !excessive
                        ? 'border-emerald-400/50 bg-emerald-400/10'
                        : 'border-gray-light'">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">
                        Taking
                    </span>
                    <span class="text-sm font-bold tabular-nums"
                        :class="covered && !excessive ? 'text-emerald-400' : 'text-gray-2x-light'">
                        {{ total }} of {{ debt }}
                    </span>
                </div>

                <p v-if="excessive" class="text-xs font-bold text-amber-400">
                    That is more than you are owed. Drop one.
                </p>
                <p v-else-if="!covered" class="text-xs text-gray-x-light">
                    Cards are indivisible, so you may end up taking slightly more than the debt.
                    You cannot take a card that is not needed.
                </p>

                <footer class="flex items-center justify-end gap-2 border-t-1 border-gray-light pt-4">
                    <button type="button" :class="[actionBtn, 'border-gray-light text-gray-x-light outline-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light']"
                        :disabled="busy" @click="emit('waive')">
                        Let it go
                    </button>
                    <button type="button" :class="[actionBtn, 'border-emerald-400 bg-emerald-400 text-gray-dark outline-emerald-400 hover:brightness-110']"
                        :disabled="!canSeize" @click="emit('seize', chosen)">
                        Seize
                    </button>
                </footer>
            </template>

            <!-- ══ everyone else waits ══ -->
            <template v-else>
                <p class="text-sm leading-relaxed text-gray-x-light">
                    Nothing can move until {{ seizure.landlordName }} decides which cards to take.
                </p>
                <div class="flex items-center gap-2 rounded-xl border-2 border-amber-400/40 bg-amber-400/10 px-4 py-3">
                    <span class="dots flex gap-1" aria-hidden="true">
                        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                    </span>
                    <span class="text-xs font-bold uppercase tracking-widest text-amber-400">
                        Waiting
                    </span>
                </div>
            </template>
        </div>
    </div>
</template>

<style scoped>
.dot {
    height: 0.4rem;
    width: 0.4rem;
    border-radius: 999px;
    background-color: var(--color-amber-400, #fbbf24);
    animation: pulse-dot 1.4s ease-in-out infinite;
}

.dot:nth-child(2) {
    animation-delay: 0.2s;
}

.dot:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes pulse-dot {

    0%,
    100% {
        opacity: 0.3;
        transform: translateY(0);
    }

    50% {
        opacity: 1;
        transform: translateY(-2px);
    }
}

.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    width: 10px;
}

.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}

@media (prefers-reduced-motion: reduce) {
    .dot {
        animation: none;
        opacity: 0.8;
    }
}
</style>