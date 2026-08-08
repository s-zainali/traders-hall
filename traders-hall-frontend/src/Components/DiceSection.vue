<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
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
const AUTO_ROLL_MS = 10000

const props = defineProps({
    canRoll: { type: Boolean, default: false },
    // '' | 'not_your_turn' | 'already_rolled' | 'homeless' | 'frozen'
    blockedReason: { type: String, default: '' },
    dice: { type: Array, default: () => [] },
    income: { type: Number, default: 0 },
    busy: { type: Boolean, default: false },
    isMyTurn: { type: Boolean },
})

const emit = defineEmits(['roll'])

const tumbling = ref(false)

/*
  Auto-roll after ten seconds.

  The roll is not a decision — there is nothing to weigh and no reason to decline
  free points — so leaving it to the player only ever stalls the table on someone
  who stepped away. The countdown fills the button itself: the thing running out
  and the thing it will press are the same object.

  Driven by a deadline against the clock rather than a decrementing counter. A
  background tab throttles intervals, so a counter drifts while a deadline just
  arrives late.
*/
const remaining = ref(0)
let deadline = 0
let ticker = null

function stopTimer() {
    if (ticker) clearInterval(ticker)
    ticker = null
    remaining.value = 0
    deadline = 0
}

function startTimer() {
    stopTimer()
    deadline = Date.now() + AUTO_ROLL_MS
    remaining.value = AUTO_ROLL_MS
    ticker = setInterval(() => {
        remaining.value = Math.max(0, deadline - Date.now())
        if (remaining.value <= 0) {
            stopTimer()
            roll()
        }
    }, 100)
}

// Live only while the roll is genuinely available. Anything that takes it away —
// the turn passing, a seizure freezing the game — cancels it.
watch(
    () => props.canRoll && !props.busy,
    (live) => (live ? startTimer() : stopTimer()),
    { immediate: true }
)

onUnmounted(stopTimer)

const secondsLeft = computed(() => Math.ceil(remaining.value / 1000))
const fillPercent = computed(() =>
    remaining.value > 0 ? (remaining.value / AUTO_ROLL_MS) * 100 : 0
)

const BLOCKED = {
    homeless: 'You need somewhere to live',
    already_rolled: 'Taken this round',
    not_your_turn: 'Not your turn',
    frozen: 'Game paused',
}
const blockedLabel = computed(() => BLOCKED[props.blockedReason] ?? '')

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

    stopTimer()
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

        <!--
            Two rows, not one wrapping line.

            Four siblings competed for one row before: dice, payout, a blocked
            message and the button. flex-wrap let any of them jump a line
            independently, which is why they ended up on top of each other — the
            payout column had flex-1 and the message had no width of its own, so
            they occupied the same space.

            Now the dice and the payout own the top row and the button owns the
            bottom one. Both are full width, so nothing has to negotiate.
        -->
        <!--
            Wraps below xl, one line at xl.

            The section is a tall narrow column at xl, where a button under the
            dice leaves a band of empty panel; below xl it is a short wide block,
            where squeezing the button in beside the readout crushes the payout
            into a sliver. flex-wrap with a full-width basis does both: the
            button takes its own line until there is room for it beside.
        -->
        <div class="flex flex-wrap items-center gap-3">
            <div class="flex shrink-0 gap-2">
                <div v-for="(pips, i) in faces" :key="i"
                    class="die grid h-12 w-12 shrink-0 grid-cols-3 grid-rows-3 gap-0.5 rounded-xl border-2 border-gray-x-light bg-gray-2x-light p-1.5"
                    :class="tumbling ? 'is-tumbling' : ''">
                    <span v-for="cell in 9" :key="cell" class="flex items-center justify-center">
                        <span v-if="pips.includes(cell - 1)" class="h-1.5 w-1.5 rounded-full bg-gray-dark"></span>
                    </span>
                </div>
            </div>

            <!-- basis-24 so the readout keeps a sane width and the BUTTON is
                 what wraps when space runs out, not this. -->
            <div class="flex min-w-0 flex-1 basis-24 flex-col gap-0.5 leading-tight">
                <span class="truncate text-[10px] font-bold uppercase tracking-widest text-gray-light">
                    {{ dice.length ? `Rolled ${total}` : 'Not rolled' }}
                </span>
                <span v-if="dice.length" class="flex items-center gap-1.5">
                    <Card :card-type="'point'" :selected="true" :large="false" />
                    <span class="text-lg font-bold tabular-nums text-teal-light">+{{ income }}</span>
                </span>
                <span v-else class="truncate text-xs text-gray-x-light">Two dice, once a round.</span>
            </div>

            <button type="button" :disabled="!canRoll || busy || tumbling" @click="roll" :title="blockedLabel"
                class="relative w-full shrink-0 overflow-hidden rounded-xl border-2 px-5 py-2.5 text-sm font-bold transition duration-200 ease-in-out xl:w-60 focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2"
                :class="canRoll && !busy && !tumbling
                    ? 'cursor-pointer border-teal-light text-gray-2x-light hover:brightness-110'
                    : 'cursor-not-allowed border-gray-light text-gray-light opacity-50'">

                <span v-if="canRoll && !busy && !tumbling" class="absolute inset-0 bg-teal-dark"
                    aria-hidden="true"></span>
                <span v-if="canRoll && !busy && !tumbling" class="timer-fill absolute inset-y-0 left-0 bg-teal-light"
                    :style="{ width: `${100 - fillPercent}%` }" aria-hidden="true"></span>

                <!-- The reason lives ON the disabled button rather than beside it: a
                 message with no width of its own was what collided with the
                 payout column. -->
                <span class="relative z-10 truncate tabular-nums">
                    {{ tumbling ? '…'
                        : canRoll ? `Roll ${secondsLeft}`
                            : blockedLabel || 'Roll' }}
                </span>
            </button>
        </div>

    </div>
</template>

<style scoped>
.die {
    transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* Linear, matched to the tick interval: an eased countdown lies about how much
   time is left. */
.timer-fill {
    transition: width 100ms linear;
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