<script setup>
import { computed, ref, watch } from 'vue'
import Card from './Card.vue'
import SeatToken from './SeatToken.vue'

/**
 * Income: two dice, once a round.
 *
 * Sits under the log because that is where the round's history already is, and a
 * roll is the most recent line of it. Keeping them adjacent means a player can see
 * their roll and what it paid without looking in two places.
 *
 * The dice animate on a roll, but the RESULT comes from the server — the pips
 * shown mid-tumble are decoration, and the ones that land are the ones the server
 * rolled. Deciding the outcome on the client and reconciling later is how dice
 * end up appearing to change after they have settled.
 */
const props = defineProps({
    canRoll: { type: Boolean, default: false },
    dice: { type: Array, default: () => [] },
    income: { type: Number, default: 0 },
    busy: { type: Boolean, default: false },
    // opponents' most recent rolls, so the table can see everyone's luck
    others: { type: Array, default: () => [] },
})

const emit = defineEmits(['roll'])

const tumbling = ref(false)
const shown = ref([1, 1])

// Follow the server's dice whenever they change, except while the animation is
// running — landing on the real value is the point of the animation.
watch(
    () => props.dice,
    (next) => {
        if (!tumbling.value && next.length) shown.value = [...next]
    },
    { immediate: true }
)

let timer = null

function roll() {
    if (!props.canRoll || props.busy || tumbling.value) return

    tumbling.value = true
    // Decorative faces while the request is in flight. Cleared by the watcher
    // below the moment the real dice arrive.
    timer = setInterval(() => {
        shown.value = [1 + Math.floor(Math.random() * 6), 1 + Math.floor(Math.random() * 6)]
    }, 70)

    emit('roll')
}

// The roll is finished when the server's dice come back and busy drops.
watch(
    () => [props.busy, props.dice],
    () => {
        if (tumbling.value && !props.busy) {
            clearInterval(timer)
            timer = null
            tumbling.value = false
            if (props.dice.length) shown.value = [...props.dice]
        }
    },
    { deep: true }
)

const total = computed(() => shown.value.reduce((a, b) => a + b, 0))

/*
  Pip layout per face. Positions on a 3x3 grid, which is how dice actually read —
  drawing them as a number would lose the thing that makes dice legible at a
  glance.
*/
const PIPS = {
    1: [4],
    2: [0, 8],
    3: [0, 4, 8],
    4: [0, 2, 6, 8],
    5: [0, 2, 4, 6, 8],
    6: [0, 2, 3, 5, 6, 8],
}

const faces = computed(() => shown.value.map((n) => PIPS[n] ?? [4]))
</script>

<template>
    <div class="flex shrink-0 flex-col gap-3 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4">
        <div class="flex items-center justify-between">
            <h2 class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Income</h2>
            <span class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
                Sum ÷ 4
            </span>
        </div>

        <div class="flex items-center gap-4">
            <div class="flex gap-2">
                <div v-for="(pips, i) in faces" :key="i"
                    class="die grid h-12 w-12 shrink-0 grid-cols-3 grid-rows-3 gap-0.5 rounded-xl border-2 border-gray-x-light bg-gray-2x-light p-1.5"
                    :class="tumbling ? 'is-tumbling' : ''">
                    <span v-for="cell in 9" :key="cell" class="flex items-center justify-center">
                        <span v-if="pips.includes(cell - 1)" class="h-1.5 w-1.5 rounded-full bg-gray-dark"></span>
                    </span>
                </div>
            </div>

            <div class="flex min-w-0 flex-1 flex-col leading-tight">
                <span class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
                    {{ dice.length ? `Rolled ${total}` : 'Not rolled' }}
                </span>
                <span v-if="dice.length" class="flex items-center gap-1.5">
                    <Card :card-type="'point'" :selected="true" :large="false" />
                    <span class="text-lg font-bold tabular-nums text-teal-light">+{{ income }}</span>
                </span>
                <span v-else class="text-xs text-gray-x-light">Two dice, once a round.</span>
            </div>

            <button type="button" :disabled="!canRoll || busy || tumbling" @click="roll"
                class="shrink-0 rounded-xl border-2 px-5 py-2.5 text-sm font-bold transition duration-200 ease-in-out focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2"
                :class="canRoll && !busy && !tumbling
                    ? 'cursor-pointer border-teal-light bg-teal-light text-gray-dark hover:brightness-110'
                    : 'cursor-not-allowed border-gray-light text-gray-light opacity-50'">
                {{ tumbling ? '…' : 'Roll' }}
            </button>
        </div>

        <p v-if="!canRoll && dice.length" class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
            Taken this round
        </p>

        <!-- Everyone else's last roll. Income is public, and knowing a rival just
             pulled 3 is part of reading the table. -->
        <div v-if="others.length" class="flex flex-wrap items-center gap-2 border-t-1 border-gray-light pt-3">
            <span v-for="o in others" :key="o.id"
                class="flex items-center gap-1.5 rounded-lg border-2 border-gray-light px-2 py-1"
                :title="`${o.name} rolled ${o.dice.join(' + ')}`">
                <SeatToken :seat-index="o.seatIndex" size="sm" />
                <span class="text-[10px] font-bold tabular-nums text-gray-x-light">
                    {{ o.dice.join('+') }}
                </span>
                <span class="text-[10px] font-bold tabular-nums text-teal-light">
                    +{{ Math.floor(o.dice.reduce((a, b) => a + b, 0) / 4) }}
                </span>
            </span>
        </div>
    </div>
</template>

<style scoped>
.die {
    transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

/*
  Rotation and a small hop, on ONE transform — a second declaration would replace
  the first rather than compose with it.
*/
.is-tumbling {
    animation: tumble 0.28s linear infinite;
}

@keyframes tumble {
    0% {
        transform: rotate(0deg) translateY(0);
    }

    50% {
        transform: rotate(180deg) translateY(-4px);
    }

    100% {
        transform: rotate(360deg) translateY(0);
    }
}

@media (prefers-reduced-motion: reduce) {
    .is-tumbling {
        animation: none;
    }

    .die {
        transition: none;
    }
}
</style>