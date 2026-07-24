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

const indicatorClass =
    'flex flex-col justify-between rounded-xl border-4 px-3 py-1.5 text-sm font-bold ' +
    'xl:w-30 xl:px-4 xl:py-2 xl:text-base'

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
    <div class="relative flex flex-col gap-2 overflow-hidden rounded-[1.5rem] border-2 bg-gray-x-dark p-3 transition duration-300 ease-in-out xl:p-4 w-full"
        :class="[panelBorder, isTurn && playerActive ? 'turn-ring' : '', isOwn? '`max-w-sm xl:max-w-auto' : '']"
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

        <!-- ── top area ───────────────────────────────────────────────
             ONE wrapping row. At xl it is flex-nowrap, so title on the left and
             points / residence / buttons on the right — the original two-row
             panel, which keeps the table short.

             Below xl it wraps: the buttons carry w-full, so they are forced
             onto their own line while everything else stays on the first. No
             restructuring, just a wrap point.
        -->
        <div class="flex flex-wrap items-center gap-2"
            :class="isOwn ? 'xl:flex-nowrap xl:gap-4' : 'flex-col-reverse gap-1'">

            <div class="flex min-w-0 items-center gap-2">
                <!-- the seat token identifies WHICH player, not just "a" player -->
                <SeatToken :seat-index="seatIndex" :size="isOwn ? 'md' : 'sm'" :filled="isTurn && playerActive" />
                <h1 class="truncate font-bold tracking-wide text-gray-2x-light"
                    :class="isOwn ? 'text-lg xl:text-2xl' : 'text-sm'">
                    <!-- nowrap: a two-word wrap costs more vertical space in a
                         tight panel than truncation costs in legibility -->
                    <span class="whitespace-nowrap">{{ isOwn ? 'Your Cards' : 'Cards' }}</span>
                </h1>
                <span v-if="!isOwn && isTurn"
                    class="shrink-0 rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                    :class="[seat.borderSoft, seat.bgSoft, seat.text]">Turn</span>
            </div>

            <!-- ml-auto groups this against the right edge on both layouts -->
            <div class="flex min-w-0 items-center gap-2"
                :class="isOwn ? 'ml-auto xl:gap-4' : 'w-full justify-between'">
                <CardDeck v-if="points > 0" :key="`pts-${points}`" :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <span v-else class="px-1 text-sm font-bold text-gray-light">0 pts</span>

                <h1 v-if="!isOwn" class="truncate text-base font-bold tracking-wide" :class="seat.text">
                    {{ playerName }}
                </h1>

                <div
                    class="flex shrink-0 items-center gap-1 rounded-[1rem] border-4 border-purple-light bg-purple-dark px-2">
                    <span v-if="isOwn" class="text-xs font-bold text-purple-light xl:text-sm">Residence</span>
                    <div class="-mx-1">
                        <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                        <div v-else class="m-1 h-8 w-8 bg-purple-light" :style="{
                            mask: `url(/cancel.png) no-repeat center / contain`,
                            '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                        }"></div>
                    </div>
                </div>
            </div>

            <!-- w-full is the wrap trigger below xl; w-auto puts them back on
                 the same line from xl -->
            <div v-if="isOwn" class="flex w-full gap-2 xl:w-auto xl:gap-4">
                <button v-for="action in actions" :key="action.key" :disabled="!canAct" :class="[
                    buttonClass,
                    canAct ? action.hover : '',
                    activeAction === action.key ? action.active : 'text-gray-dark bg-gray-2x-light',
                    !canAct ? 'opacity-40 cursor-not-allowed hover:scale-100' : '',
                ]" @click="activeAction === '' ? $emit(action.key) : ''">{{ action.label }}</button>

                <button :disabled="!canAct" @click="$emit('endTurn')" :class="[
                    buttonClass,
                    'bg-rose-400/50 text-gray-2x-light xl:w-30',
                    canAct ? 'hover:bg-rose-500/50' : 'opacity-40 cursor-not-allowed hover:scale-100',
                ]">
                    {{ busy ? '…' : 'End Turn' }}
                </button>
            </div>
        </div>

        <!-- ── hand + indicators ───────────────────────────────────────
             Stacked below xl, side by side from xl. Three indicators plus a
             hand well need about 900px in a row; the tablet panel has ~640. -->
        <div class="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between xl:gap-4">

            <div class="relative flex min-w-0 flex-1 justify-between overflow-hidden rounded-[1rem] border-1 px-3 py-2 transition duration-300 ease-in-out xl:max-w-md xl:px-4"
                :class="handState ? handState.well : 'border-gray-light outline-0'">
                <button v-if="handState" @click="emit('cancelOperation')"
                    class="absolute top-0 right-0 z-50 flex items-center justify-center p-3 leading-none text-gray-x-light transition duration-200 ease-in-out hover:cursor-pointer hover:text-rose-400">🗙</button>

                <!-- overflow-x-auto: a full hand of six types would otherwise
                     widen the panel instead of scrolling -->
                <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto pb-1">
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

            <!-- grid below xl so the three sit evenly across the full width;
                 a flex row would leave them ragged -->
            <div v-if="isOwn" class="grid shrink-0 grid-cols-3 gap-2 xl:flex xl:gap-4">
                <div :class="indicatorClass" class="border-cream-light bg-cream-dark text-cream-light">
                    <span>Food Due</span>
                    <span>{{ foodDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="border-purple-light bg-purple-dark text-purple-light">
                    <span>Rent Due</span>
                    <span>{{ rentDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="border-teal-light bg-teal-dark text-teal-light">
                    <span>Loan Due</span>
                    <span>{{ loanDue }} turns</span>
                </div>
            </div>
        </div>
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