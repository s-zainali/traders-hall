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

    // ── server state, was hardcoded here ──────────────────────
    // { cardType: quantity }. Includes zero counts, which is why the template
    // filters rather than rendering a deck per key.
    hand: { type: Object, default: () => ({}) },
    points: { type: Number, default: 0 },
    foodDue: { type: Number, default: 0 },
    rentDue: { type: Number, default: 0 },
    loanDue: { type: Number, default: 0 },
    residence: { type: String, default: '' },
    onRent: { type: Boolean, default: false },
})
const emit = defineEmits(['buy', 'sell', 'trade', 'cancelOperation', 'transaction'])

// NOTE: no bg-* here. The background is chosen per-state below so exactly one
// background utility is ever present, avoiding a stylesheet-order conflict.
const buttonClass = 'w-18 py-2 rounded-lg cursor-pointer font-bold hover:scale-105 transition duration-300 ease-in-out hover:text-gray-2x-light'
const indicatorClass = 'py-2 w-30 rounded-xl font-bold border-4 px-4 flex flex-col justify-between'

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
    emit('transaction', { action: activeModal.value, type: selectedType.value, payload })
    activeModal.value = ''
    emit('cancelOperation')
}
</script>

<template>
    <div class="relative flex flex-col p-4 gap-2 bg-gray-x-dark border-2 rounded-[1.5rem] overflow-hidden transition duration-300 ease-in-out"
        :class="[panelBorder, isTurn && playerActive ? 'turn-ring' : '']"
        :style="isTurn && playerActive ? { '--seat': seat.hex } : {}">

        <TransactionModal v-if="activeModal !== ''" :transaction-type="activeModal" :card-type="selectedType"
            :available="hand[selectedType] ?? 1" @confirm="onConfirm" @cancel="activeModal = ''" />

        <!--
            Empty seat. A bare scrim read as "disabled" rather than "nobody
            here"; the dashed token matches the placeholders in the lobby list.
        -->
        <div v-if="!playerActive"
            class="absolute inset-0 z-100 flex flex-col items-center justify-center gap-3
                   bg-gray-dark/75 backdrop-blur-[2px]">
            <SeatToken :seat-index="-1" size="lg" />
            <div class="flex flex-col items-center gap-0.5">
                <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Empty seat</span>
                <span class="text-xs text-gray-light">Waiting for a player</span>
            </div>
        </div>

        <div class="flex justify-between items-center" :class="[playerType === 'player' ? 'gap-4' : 'flex-col-reverse']">
            <div class="flex items-center gap-2">
                <!-- the seat token replaces the generic user glyph: same slot,
                     but now it identifies WHICH player rather than just "a" player -->
                <SeatToken :seat-index="seatIndex" :size="playerType === 'player' ? 'lg' : 'sm'"
                    :filled="isTurn && playerActive" />
                <h1 class="text-gray-2x-light font-bold tracking-wide"
                    :class="playerType === 'player' ? 'text-2xl' : 'text-md'">
                    {{ playerType === 'player' ? 'Your' : '' }} Cards
                </h1>
            </div>
            <div class="flex gap-4 items-center"
                :class="playerType === 'player' ? 'justify-end' : 'w-full justify-between'">
                <!-- points are a balance, drawn as a deck. v-if because a deck
                     of zero cards would otherwise render an empty stub. -->
                <CardDeck v-if="points > 0" :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <span v-else class="px-2 text-sm font-bold text-gray-light">0 pts</span>

                <div v-if="playerType !== 'player'" class="flex items-center gap-2 px-2 py-2">
                    <h1 class="text-lg font-bold tracking-wide" :class="seat.text">{{ playerName }}</h1>
                    <span v-if="isTurn"
                        class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                        :class="[seat.borderSoft, seat.bgSoft, seat.text]">Turn</span>
                </div>

                <div class="flex px-2 bg-purple-dark border-4 border-purple-light rounded-[1rem]">
                    <span v-if="onRent">On Rent</span>
                    <div class="flex gap-2 items-center">
                        <span v-if="playerType === 'player'"
                            class="font-bold text-sm text-purple-light">Residence</span>
                        <div class="-mx-2">
                            <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                            <div v-else class="h-9 w-9 bg-purple-light m-1" :style="{
                                mask: `url(/cancel.png) no-repeat center / contain`,
                                '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                            }"></div>
                        </div>
                    </div>
                </div>

                <div v-if="playerType === 'player'" class="flex gap-4">
                    <button v-for="action in actions" :key="action.key" :class="[
                        buttonClass,
                        action.hover,
                        activeAction === action.key ? action.active : 'text-gray-dark bg-gray-2x-light',
                    ]" @click="activeAction === '' ? $emit(action.key) : ''">{{ action.label }}</button>
                    <button
                        class="bg-rose-400/50 w-30 py-3 rounded-xl font-bold hover:bg-rose-500/50 cursor-pointer transition duration-300 ease-in-out hover:scale-110 text-gray-2x-light">End Turn</button>
                </div>
            </div>
        </div>

        <div class="flex justify-between gap-4 items-center">
            <div class="relative p-2 border-1 rounded-[1rem] min-w-[100px] flex justify-between px-4 w-full max-w-md overflow-hidden transition duration-300 ease-in-out"
                :class="handState ? handState.well : 'border-gray-light outline-0'">
                <button v-if="handState" @click="emit('cancelOperation')"
                    class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

                <div v-if="heldTypes.length" class="flex gap-2">
                    <!-- :key is required here: without it Vue patches these decks
                         in place by index, which mixes card types between decks -->
                    <CardDeck v-for="type in heldTypes" :key="type" :content-small="true">
                        <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false"
                            :class="handState ? 'cursor-pointer' : ''" :selling="activeAction === 'sell'"
                            :trading="activeAction === 'trade'" @sell="openModal(type)" @trade="openModal(type)" />
                    </CardDeck>
                </div>
                <span v-else class="py-3 text-sm text-gray-light">No cards</span>
            </div>

            <div v-if="playerType === 'player'" class="flex justify-evenly items-center gap-4">
                <div :class="indicatorClass" class="bg-cream-dark text-cream-light border-cream-light">
                    <span>Food Due</span>
                    <span>{{ foodDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="bg-purple-dark text-purple-light border-purple-light">
                    <span>Rent Due</span>
                    <span>{{ rentDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="bg-teal-dark text-teal-light border-teal-light">
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
    0%, 100% { box-shadow: 0 0 0 0 color-mix(in oklab, var(--seat) 45%, transparent); }
    50%      { box-shadow: 0 0 0 6px color-mix(in oklab, var(--seat) 0%, transparent); }
}

@media (prefers-reduced-motion: reduce) {
    .turn-ring {
        animation: none;
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--seat) 40%, transparent);
    }
}
</style>