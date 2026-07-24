<script setup>
import { computed, ref } from 'vue';
import Card from './Card.vue';
import CardDeck from './CardDeck.vue';
import SeatToken from './SeatToken.vue';
import TransactionModal from './Modals/TransactionModal.vue';
import { seatStyle } from '../seats';

const props = defineProps({
    playerType: { type: String, default: 'player' },
    activeAction: { type: String, default: '' },
    playerName: { type: String, default: 'Player' },
    playerActive: { type: Boolean, default: false },
    // which chair this panel is; drives the token and the accent colour
    seatIndex: { type: Number, default: -1 },
    // whose turn it is, for the pulsing ring
    isTurn: { type: Boolean, default: false },

    // ── server state ──────────────────────────────────────────
    // { cardType: quantity }. Includes zero counts, which is why the template
    // filters rather than rendering a deck per key.
    hand: { type: Object, default: () => ({}) },
    points: { type: Number, default: 0 },
    foodDue: { type: Number, default: 0 },
    rentDue: { type: Number, default: 0 },
    loanDue: { type: Number, default: 0 },
    residence: { type: String, default: '' },
    onRent: { type: Boolean, default: false },
    // an action is in flight; controls lock so a double-click cannot fire twice
    busy: { type: Boolean, default: false },
})
const emit = defineEmits(['buy', 'sell', 'trade', 'cancelOperation', 'transaction', 'endTurn'])

const isOwn = computed(() => props.playerType === 'player')

/*
  Sizes step down below xl. The panel shares its row with the event-log sidebar
  on a tablet, so it gets roughly 640px rather than the ~1000px a laptop gives
  it — the header alone does not fit at desktop sizing, which is why End Turn
  was being clipped.
*/
const buttonClass =
    'min-w-0 flex-1 rounded-lg py-1.5 text-sm font-bold cursor-pointer transition duration-300 ease-in-out ' +
    'hover:scale-105 hover:text-gray-2x-light xl:flex-none xl:w-18 xl:py-2 xl:text-base'

/*
  Label OUTSIDE the box, value inside. Pulling the caption out lets the box
  shrink to just the number, which is the height and width this reclaims — and
  the caption reads as a column header rather than as part of the readout.
*/
const statLabel = 'text-[10px] font-bold uppercase tracking-widest'
const statBox =
    'w-full rounded-lg border-2 px-3 py-0.5 text-center text-base font-bold tabular-nums'

// `caption` is the -dark token, so the label sits back against the panel while
// the box keeps the fuller -light treatment.
const stats = computed(() => [
    {
        key: 'food', label: 'Food', value: props.foodDue,
        caption: 'text-cream-dark',
        tone: 'border-cream-light bg-cream-dark text-cream-light',
    },
    {
        key: 'rent', label: 'Rent', value: props.rentDue,
        caption: 'text-purple-dark',
        tone: 'border-purple-light bg-purple-dark text-purple-light',
    },
    {
        key: 'loan', label: 'Loan', value: props.loanDue,
        caption: 'text-teal-dark',
        tone: 'border-teal-light bg-teal-dark text-teal-light',
    },
])

const actions = [
    { key: 'buy', label: 'Buy', hover: 'hover:bg-emerald-400/50', active: 'bg-emerald-400/60 text-gray-2x-light' },
    { key: 'sell', label: 'Sell', hover: 'hover:bg-rose-400/70', active: 'bg-rose-400/60 text-gray-2x-light' },
    { key: 'trade', label: 'Trade', hover: 'hover:bg-amber-300/70', active: 'bg-amber-300/60 text-gray-2x-light' },
]

// per-action chrome for the hand well and the panel border; full literal class
// strings so Tailwind generates them
const HAND_STATES = {
    sell: {
        well: 'outline-rose-400/50 border-rose-400/5 outline-4 -outline-offset-4 bg-gray-light/30',
        panel: 'border-rose-400/50',
    },
    trade: {
        well: 'outline-amber-400/50 border-amber-400/5 outline-4 -outline-offset-4 bg-gray-light/30',
        panel: 'border-amber-400/50',
    },
}
const handState = computed(() => HAND_STATES[props.activeAction] ?? null)

const seat = computed(() => seatStyle(props.seatIndex))

/*
  Buy, sell and trade are turn-gated on the server. Disabling them off-turn is
  not the enforcement — it is so the player can see whose turn it is from the
  controls, rather than finding out from a rejected request.
*/
const canAct = computed(() => props.isTurn && !props.busy)

/*
  The hand arrives with a row for EVERY card type, most of them zero — the
  backend keeps zero rows deliberately so a sale can guard on the row's
  existence. Rendering a deck per key would give a row of empty slots, so the
  view filters to what is actually held. Points are shown separately, as a
  balance rather than as cards in hand.
*/
const heldTypes = computed(() =>
    Object.entries(props.hand)
        .filter(([type, count]) => count > 0 && type !== 'point')
        .map(([type]) => type)
)

/*
  Panel border priority, most urgent first:
    1. an open transaction modal (rose / amber)
    2. empty seat (dashed grey — clearly not a player)
    3. this player's turn (their own seat colour, solid)
    4. otherwise a soft tint of their seat colour
  Exactly one wins, so the border always means one thing.
*/
const panelBorder = computed(() => {
    if (activeModal.value && handState.value) return handState.value.panel
    if (!props.playerActive) return 'border-dashed border-gray-light'
    if (props.isTurn) return seat.value.border
    return seat.value.borderSoft
})

// ONE ref for the card under action. Previously sell wrote `sellingType` and
// trade wrote `tradingType`, but the modal only ever read `sellingType` — so
// trading always showed whatever sell had left behind.
const selectedType = ref('')
const activeModal = ref('')

// the action already says whether this is a sell or a trade
function openModal(type) {
    selectedType.value = type
    activeModal.value = props.activeAction
}

function onConfirm(payload) {
    // The parent needs the card type as well as the quantity — it has no other
    // way to know which deck was clicked.
    emit('transaction', { action: activeModal.value, type: selectedType.value, payload })
    activeModal.value = ''
}
</script>

<template>
    <div class="relative flex flex-col gap-2 overflow-hidden rounded-[1.5rem] border-2 bg-gray-x-dark p-3 transition duration-300 ease-in-out xl:px-4 xl:py-3"
        :class="[panelBorder, isTurn && playerActive ? 'turn-ring' : '']"
        :style="isTurn && playerActive ? { '--seat': seat.hex } : {}">

        <TransactionModal v-if="activeModal !== ''" :transaction-type="activeModal" :card-type="selectedType"
            :available="hand[selectedType] ?? 1" :points="points" :busy="busy" @confirm="onConfirm"
            @cancel="activeModal = ''" />

        <!--
            Empty seat. A bare scrim read as "disabled" rather than "nobody
            here"; the dashed token matches the placeholders in the lobby list.
        -->
        <div v-if="!playerActive"
            class="absolute inset-0 z-100 flex flex-col items-center justify-center gap-3 bg-gray-dark/75 backdrop-blur-[2px]">
            <SeatToken :seat-index="-1" size="lg" />
            <div class="flex flex-col items-center gap-0.5">
                <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Empty seat</span>
                <span class="text-xs text-gray-light">Waiting for a player</span>
            </div>
        </div>

        <!-- ══ own panel ══════════════════════════════════════════════
            ONE wrapping row. At xl it is flex-nowrap, so identity, hand,
            residence, stats and buttons all sit on a single line — now that the
            bank overlays rather than pushes, the panel has the full table width
            and does not need two rows.

            Below xl the w-full items wrap onto their own lines. xl:order-* only
            reorders the single-row layout, so the stacked order still reads top
            to bottom as written.
        -->
        <div v-if="isOwn" class="flex flex-wrap items-center gap-2 xl:flex-nowrap xl:gap-3">

            <div class="flex min-w-0 shrink-0 items-center gap-2 xl:order-1">
                <SeatToken :seat-index="seatIndex" size="md" :filled="isTurn && playerActive" />
                <h1 class="truncate text-lg font-bold tracking-wide text-gray-2x-light xl:text-xl">
                    <span class="whitespace-nowrap">Your Cards</span>
                </h1>
            </div>

            <!--
                Points are their OWN flex item, not a child of the identity
                group. Nested inside it they would render wherever that group
                sits — which is always first — so no amount of reordering within
                the group could move them next to the residence badge. Only a
                sibling can carry its own order.
            -->
            <div class="flex shrink-0 items-center xl:order-3">
                <CardDeck v-if="points > 0" :key="`pts-${points}`" :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <span v-else class="px-1 text-sm font-bold text-gray-light">0 pts</span>
            </div>

            <!-- residence keeps its own badge: it holds a card, not a number,
                 so it does not belong in a row of numeric readouts -->
            <div
                class="flex shrink-0 items-center gap-1 rounded-[1rem] border-4 border-purple-light bg-purple-dark px-2 xl:order-4">
                <span class="text-xs font-bold text-purple-light">Residence</span>
                <div class="-mx-1">
                    <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                    <div v-else class="m-1 h-7 w-7 bg-purple-light" :style="{
                        mask: `url(/cancel.png) no-repeat center / contain`,
                        '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                    }"></div>
                </div>
            </div>

            <!-- hand: w-full wraps it below xl; flex-1 absorbs the slack on the
                 single row -->
            <div class="relative flex w-full min-w-0 justify-between overflow-hidden rounded-[1rem] border-1 px-3 py-1.5 transition duration-300 ease-in-out xl:order-2 xl:w-auto xl:flex-1"
                :class="handState ? handState.well : 'border-gray-light outline-0'">
                <button v-if="handState" @click="emit('cancelOperation')"
                    class="absolute top-0 right-0 z-50 flex items-center justify-center p-2 leading-none text-gray-x-light transition duration-200 ease-in-out hover:cursor-pointer hover:text-rose-400">🗙</button>

                <!-- overflow-x-auto: a full hand of six types would otherwise
                     widen the panel instead of scrolling -->
                <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto">
                    <!-- :key is required: without it Vue patches these decks in
                         place by index, which mixes card types between decks -->
                    <CardDeck v-for="type in heldTypes" :key="`${type}-${hand[type]}`" :content-small="true">
                        <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false"
                            :class="handState ? 'cursor-pointer' : ''" :selling="activeAction === 'sell'"
                            :trading="activeAction === 'trade'" @sell="openModal(type)" @trade="openModal(type)" />
                    </CardDeck>
                </div>
                <span v-else class="py-2 text-sm text-gray-light">No cards</span>
            </div>

            <!-- caption above, number in the box -->
            <div class="grid w-full shrink-0 grid-cols-3 gap-2 xl:order-5 xl:flex xl:w-auto">
                <div v-for="stat in stats" :key="stat.key" class="flex flex-col items-center gap-0.5">
                    <span :class="[statLabel, stat.caption]">{{ stat.label }}</span>
                    <div :class="[statBox, stat.tone]">{{ stat.value }}</div>
                </div>
            </div>

            <div class="flex w-full gap-2 xl:order-6 xl:w-auto">
                <button v-for="action in actions" :key="action.key" :disabled="!canAct" :class="[
                    buttonClass,
                    canAct ? action.hover : '',
                    activeAction === action.key ? action.active : 'text-gray-dark bg-gray-2x-light',
                    !canAct ? 'opacity-40 cursor-not-allowed hover:scale-100' : '',
                ]" @click="activeAction === '' ? $emit(action.key) : ''">{{ action.label }}</button>

                <button :disabled="!canAct" @click="$emit('endTurn')" :class="[
                    buttonClass,
                    'bg-rose-400/50 text-gray-2x-light xl:w-24',
                    canAct ? 'hover:bg-rose-500/50' : 'opacity-40 cursor-not-allowed hover:scale-100',
                ]">
                    {{ busy ? '…' : 'End Turn' }}
                </button>
            </div>
        </div>

        <!-- ══ opponent panel ═════════════════════════════════════════
            A separate block, not the same markup with different wrap points.
            The two shapes genuinely diverged once the own panel became a single
            wide row: an opponent card is narrow, has no controls and no timers,
            so forcing it through the same wrap logic is what scrambled it.
        -->
        <template v-else>
            <div class="flex min-w-0 items-center gap-2">
                <SeatToken :seat-index="seatIndex" size="sm" :filled="isTurn && playerActive" />
                <h1 class="truncate text-sm font-bold tracking-wide" :class="seat.text">{{ playerName }}</h1>
                <span v-if="isTurn"
                    class="shrink-0 rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                    :class="[seat.borderSoft, seat.bgSoft, seat.text]">Turn</span>

                <div class="ml-auto flex shrink-0 items-center gap-2">
                    <CardDeck v-if="points > 0" :key="`pts-${points}`" :content-small="true">
                        <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                    </CardDeck>
                    <span v-else class="text-sm font-bold text-gray-light">0 pts</span>

                    <div class="flex items-center rounded-lg border-2 border-purple-light bg-purple-dark px-1">
                        <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                        <div v-else class="m-1 h-6 w-6 bg-purple-light" :style="{
                            mask: `url(/cancel.png) no-repeat center / contain`,
                            '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                        }"></div>
                    </div>
                </div>
            </div>

            <div
                class="relative flex min-w-0 overflow-hidden rounded-[1rem] border-1 border-gray-light px-3 py-1.5">
                <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto">
                    <CardDeck v-for="type in heldTypes" :key="`${type}-${hand[type]}`" :content-small="true">
                        <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false" />
                    </CardDeck>
                </div>
                <span v-else class="py-2 text-sm text-gray-light">No cards</span>
            </div>
        </template>

    </div>
</template>

<style scoped>
/*
  Turn indicator. box-shadow rather than an extra element or a border change:
  it costs no layout, so the panel does not shift when the turn moves, and the
  --seat variable set inline lets one rule serve all four seat colours.
*/
.turn-ring {
    animation: turn-pulse 2.4s ease-in-out infinite;
}

@keyframes turn-pulse {

    0%,
    100% {
        box-shadow: 0 0 0 0 color-mix(in oklab, var(--seat) 45%, transparent);
    }

    50% {
        box-shadow: 0 0 0 6px color-mix(in oklab, var(--seat) 0%, transparent);
    }
}

.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    height: 8px;
}

.scroll-slim::-webkit-scrollbar-track {
    background: transparent;
}

.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 2px solid transparent;
    border-radius: 999px;
}

@media (prefers-reduced-motion: reduce) {
    .turn-ring {
        animation: none;
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--seat) 40%, transparent);
    }
}
</style>