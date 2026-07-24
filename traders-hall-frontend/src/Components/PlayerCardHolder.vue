<script setup>
import { computed, ref } from 'vue'
import Card from './Card.vue'
import CardDeck from './CardDeck.vue'
import SeatToken from './SeatToken.vue'
import TransactionModal from './Modals/TransactionModal.vue'
import { seatStyle } from '../seats'

const props = defineProps({
    playerType: { type: String, default: 'player' },
    activeAction: { type: String, default: '' },
    playerName: { type: String, default: 'Player' },
    seatStatus: { type: String, default: 'empty' },
    /** which chair this panel is; drives the token and the accent colour */
    seatIndex: { type: Number, default: -1 },
    /** whose turn it is, for the pulsing ring */
    isTurn: { type: Boolean, default: false },

    // ── server state ──────────────────────────────────────────────
    /** { cardType: quantity } — includes zero counts, hence heldTypes below */
    hand: { type: Object, default: () => ({}) },
    points: { type: Number, default: 0 },
    foodDue: { type: Number, default: 0 },
    rentDue: { type: Number, default: 0 },
    loanDue: { type: Number, default: 0 },
    residence: { type: String, default: '' },
    onRent: { type: Boolean, default: false },
    /** an action is in flight; controls lock so a double-click cannot fire twice */
    busy: { type: Boolean, default: false },
})

const emit = defineEmits([
    'buy', 'sell', 'trade', 'cancelOperation', 'transaction', 'endTurn',
])

/* ── local state ──────────────────────────────────────────────────
   ONE ref for the card under action. Sell and trade previously wrote to
   separate refs while the modal read only one of them, so trading always
   showed whatever sell had left behind.
────────────────────────────────────────────────────────────────── */
const selectedType = ref('')
const activeModal = ref('')

/* ── derived ─────────────────────────────────────────────────────── */

const isOwn = computed(() => props.playerType === 'player')
const seat = computed(() => seatStyle(props.seatIndex))

const playerActive = computed(() => props.seatStatus === 'active')
const isEmpty = computed(() => props.seatStatus === 'empty')
const isOut = computed(() => !playerActive.value && !isEmpty.value)

const OUT_STATES = {
    resigned: { label: 'Resigned', note: 'Left the game', tone: 'text-rose-400', border: 'border-rose-400/50' },
    eliminated: { label: 'Eliminated', note: 'Out of the game', tone: 'text-rose-400', border: 'border-rose-400/50' },
}
const outState = computed(() => OUT_STATES[props.seatStatus] ?? OUT_STATES.resigned)

/**
 * Buy, sell and trade are turn-gated on the server. Disabling them off-turn is
 * not the enforcement — it is so the player can see whose turn it is from the
 * controls rather than from a rejected request.
 */
const canAct = computed(() => props.isTurn && !props.busy && playerActive.value)

/**
 * The hand arrives with a row for EVERY card type, most of them zero: the
 * backend keeps zero rows so a sale can guard on the row's existence. Rendering
 * a deck per key would give a row of empty slots, so filter to what is held.
 * Points are a balance, shown separately rather than as cards in hand.
 */
const heldTypes = computed(() =>
    Object.entries(props.hand)
        .filter(([type, count]) => count > 0 && type !== 'point')
        .map(([type]) => type)
)

/**
 * Border priority, most urgent first:
 *   1. an open transaction  2. empty seat  3. this player's turn  4. resting
 * Exactly one wins, so the border always means one thing.
 */
const panelBorder = computed(() => {
    if (activeModal.value && handState.value) return handState.value.panel
    if (isEmpty.value) return 'border-dashed border-gray-light'
    if (isOut.value) return outState.value.border
    if (props.isTurn) return seat.value.border
    return seat.value.borderSoft
})

/* ── static class maps ────────────────────────────────────────────
   Full literal strings throughout: Tailwind's scanner cannot see an
   interpolated class name, so `bg-${x}` would never be generated.
────────────────────────────────────────────────────────────────── */

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

const ACTIONS = [
    { key: 'buy', label: 'Buy', hover: 'hover:bg-emerald-400/50', active: 'bg-emerald-400/60 text-gray-2x-light' },
    { key: 'sell', label: 'Sell', hover: 'hover:bg-rose-400/70', active: 'bg-rose-400/60 text-gray-2x-light' },
    { key: 'trade', label: 'Trade', hover: 'hover:bg-amber-300/70', active: 'bg-amber-300/60 text-gray-2x-light' },
]

/*
  Button classes are split base / enabled / disabled so exactly ONE cursor
  utility and ONE hover rule ever reach the element.

  Emitting `cursor-pointer` and `cursor-not-allowed` together — as an earlier
  version did — leaves the winner to Tailwind's stylesheet order rather than to
  the order of this array, which is why the pointer cursor stuck on disabled
  buttons. `:disabled` also does NOT suppress `:hover` in CSS, so a disabled
  button keeps matching hover rules unless none are attached at all.
*/
const BTN_BASE =
    'rounded-lg px-3 py-1.5 text-sm font-bold whitespace-nowrap select-none ' +
    'xl:px-4 xl:py-2 xl:text-base'
const BTN_ENABLED =
    'cursor-pointer transition-colors duration-200 ease-in-out hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'
const BTN_DISABLED = 'cursor-not-allowed opacity-40'

const statLabel = 'text-[10px] font-bold uppercase tracking-widest'
const statBox = 'w-full rounded-lg border-2 px-3 py-0.5 text-center text-base font-bold tabular-nums'

// `caption` is the -dark token so the label sits back against the panel while
// the box keeps the fuller -light treatment.
const stats = computed(() => [
    { key: 'food', label: 'Food', value: props.foodDue, caption: 'text-cream-dark', tone: 'border-cream-light bg-cream-dark text-cream-light' },
    { key: 'rent', label: 'Rent', value: props.rentDue, caption: 'text-purple-dark', tone: 'border-purple-light bg-purple-dark text-purple-light' },
    { key: 'loan', label: 'Loan', value: props.loanDue, caption: 'text-teal-dark', tone: 'border-teal-light bg-teal-dark text-teal-light' },
])

/* ── behaviour ────────────────────────────────────────────────────── */

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

/**
 * Closing the popover MUST also clear the parent's activeAction, or the parent
 * still believes a sell is in progress and every later action click is ignored.
 */
function closeModal() {
    activeModal.value = ''
    emit('cancelOperation')
}

/** Clicking the button for the running action cancels it, rather than doing nothing. */
function onAction(key) {
    if (!canAct.value) return
    if (props.activeAction === key) emit('cancelOperation')
    else if (props.activeAction === '') emit(key)
}

function onEndTurn() {
    if (!canAct.value) return
    emit('endTurn')
}
</script>

<template>
    <!--
        No overflow-hidden: the sell/trade popover is anchored outside this box
        and would be clipped. The empty-seat overlay carries its own rounding,
        which is all that clipping was doing.

        transition-colors, not transition: a blanket transition animates every
        animatable property, so any re-layout tweens widths for 300ms and drags
        controls around under the cursor.
    -->
    <section
        class="relative flex flex-col gap-2 rounded-[1.5rem] border-2 bg-gray-x-dark p-3 transition-colors duration-300 ease-in-out xl:px-4 xl:py-3"
        :class="[panelBorder, isTurn && playerActive ? 'turn-ring' : '']"
        :style="isTurn && playerActive ? { '--seat': seat.hex } : {}">

        <!--
            Anchored popover. It follows the panel's own position: to the RIGHT
            below xl, where the panel is a tall left column; ABOVE from xl, where
            it spans the full width at the bottom.
        -->
        <div v-if="activeModal !== ''"
            class="absolute top-1/2 left-full z-[120] ml-2 w-max max-w-[calc(100vw-3rem)] -translate-y-1/2
                   xl:top-auto xl:bottom-full xl:left-1/2 xl:ml-0 xl:-translate-x-1/2 xl:translate-y-0">
            <TransactionModal :transaction-type="activeModal" :card-type="selectedType"
                :available="hand[selectedType] ?? 1" :points="points" :busy="busy" :popover="true"
                @confirm="onConfirm" @cancel="closeModal" />
            <div class="mx-auto -mt-0.5 hidden h-1 w-16 rounded-b bg-gray-light xl:block"></div>
        </div>

        <!-- Empty seat. A bare scrim read as "disabled" rather than "nobody
             here"; the dashed token matches the lobby placeholders. -->
        <div v-if="isEmpty"
            class="absolute inset-0 z-[100] flex flex-col items-center justify-center gap-3 rounded-[1.5rem] bg-gray-dark/75 backdrop-blur-[2px]">
            <SeatToken :seat-index="-1" size="lg" />
            <div class="flex flex-col items-center gap-0.5">
                <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Empty seat</span>
                <span class="text-xs text-gray-light">Waiting for a player</span>
            </div>
        </div>

        <div v-else-if="isOut"
            class="absolute inset-0 z-[100] flex flex-col items-center justify-center gap-2 rounded-[1.5rem] bg-gray-dark/70 backdrop-blur-[2px]">
            <span class="text-lg font-bold tracking-wide" :class="seat.text">{{ playerName }}</span>
            <span class="rounded-full border-2 px-3 py-0.5 text-xs font-bold uppercase tracking-widest"
                :class="[outState.tone, outState.border, 'bg-rose-400/10']">{{ outState.label }}</span>
            <span class="text-xs text-gray-light">{{ outState.note }}</span>
        </div>

        <!-- ══ own panel ══════════════════════════════════════════════
            CSS Grid with named areas, NOT flex-wrap plus order.

            The wrap-and-reorder version put six items on one nowrap line at xl,
            each with its own flex-basis and shrink behaviour, and the controls
            were last in that chain — so whenever the row was tight they were
            the ones squeezed, moved or overlapped. Grid gives every group a
            declared cell that cannot be pushed by a sibling, and the same DOM
            serves both arrangements with no order juggling.
        -->
        <div v-if="isOwn" class="own-grid">

            <div class="a-id flex min-w-0 items-center gap-2">
                <SeatToken :seat-index="seatIndex" size="md" :filled="isTurn && playerActive" />
                <h1 class="truncate text-lg font-bold tracking-wide whitespace-nowrap text-gray-2x-light xl:text-xl">
                    Your Cards
                </h1>
            </div>

            <!-- points and residence travel together in both layouts -->
            <div class="a-meta flex items-center justify-end gap-2">
                <CardDeck v-if="points > 0" :key="`pts-${points}`" :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <span v-else class="px-1 text-sm font-bold text-gray-light">0 pts</span>

                <div
                    class="flex shrink-0 items-center gap-1 rounded-[1rem] border-4 border-purple-light bg-purple-dark px-2">
                    <span class="text-xs font-bold text-purple-light">Residence</span>
                    <div class="-mx-1">
                        <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                        <div v-else class="m-1 h-7 w-7 bg-purple-light" :style="{
                            mask: `url(/cancel.png) no-repeat center / contain`,
                            '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                        }"></div>
                    </div>
                </div>
            </div>

            <div class="a-hand relative flex min-w-0 justify-between overflow-hidden rounded-[1rem] border-1 px-3 py-1.5 transition-colors duration-300 ease-in-out"
                :class="handState ? handState.well : 'border-gray-light outline-0'">
                <button v-if="handState" type="button" aria-label="Cancel" @click="emit('cancelOperation')"
                    class="absolute top-0 right-0 z-10 flex cursor-pointer items-center justify-center p-2 leading-none text-gray-x-light transition-colors duration-200 ease-in-out hover:text-rose-400">🗙</button>

                <!-- overflow-x-auto: a full hand of six types would otherwise
                     widen the cell instead of scrolling -->
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

            <!-- caption above, number in the box: the box then shrinks to the
                 number, which is the width this reclaims -->
            <div class="a-stats grid grid-cols-3 gap-2 xl:flex">
                <div v-for="stat in stats" :key="stat.key" class="flex flex-col items-center gap-0.5">
                    <span :class="[statLabel, stat.caption]">{{ stat.label }}</span>
                    <div :class="[statBox, stat.tone]">{{ stat.value }}</div>
                </div>
            </div>

            <!--
                z-10 so the controls sit above anything that might bleed into
                this cell, and their own stacking context is explicit rather
                than implied by document order.
            -->
            <div class="a-actions relative z-10 flex gap-2">
                <button v-for="action in ACTIONS" :key="action.key" type="button" :disabled="!canAct" :class="[
                    BTN_BASE,
                    'flex-1 xl:flex-none',
                    canAct ? [BTN_ENABLED, action.hover] : BTN_DISABLED,
                    activeAction === action.key ? action.active : 'text-gray-dark bg-gray-2x-light',
                ]" @click="onAction(action.key)">{{ action.label }}</button>

                <button type="button" :disabled="!canAct" :class="[
                    BTN_BASE,
                    'flex-1 bg-rose-400/50 text-gray-2x-light xl:flex-none',
                    canAct ? [BTN_ENABLED, 'hover:bg-rose-500/50'] : BTN_DISABLED,
                ]" @click="onEndTurn">
                    {{ busy ? '…' : 'End Turn' }}
                </button>
            </div>
        </div>

        <!-- ══ opponent panel ═════════════════════════════════════════
            A separate block. The two shapes genuinely diverged once the own
            panel became a single wide row: an opponent card is narrow, has no
            controls and no timers, so forcing it through the same layout logic
            is what scrambled it.
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
                class="relative flex min-h-[4.25rem] min-w-0 items-center overflow-hidden rounded-[1rem] border-1 border-gray-light px-3 py-1.5">
                <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto">
                    <CardDeck v-for="type in heldTypes" :key="`${type}-${hand[type]}`" :content-small="true">
                        <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false" />
                    </CardDeck>
                </div>
                <span v-else class="text-sm text-gray-light">No cards</span>
            </div>
        </template>
    </section>
</template>

<style scoped>
/* ── own-panel layout ──────────────────────────────────────────────
   Five groups, two arrangements. Every group has a declared cell, so none can
   be squeezed or displaced by a sibling the way flex items can.

   minmax(0, 1fr) rather than a bare 1fr on the hand column: 1fr carries an
   implicit min-content floor, so a wide hand would push the track past its
   share and steal room from the controls. The 0 minimum is the grid equivalent
   of min-w-0 on a flex item.
────────────────────────────────────────────────────────────────── */
.own-grid {
    display: grid;
    gap: 0.5rem;
    align-items: center;
    grid-template-columns: auto minmax(0, 1fr);
    grid-template-areas:
        "id      meta"
        "hand    hand"
        "stats   stats"
        "actions actions";
}

@media (min-width: 1280px) {
    .own-grid {
        gap: 0.75rem;
        grid-template-columns: auto minmax(0, 1fr) auto auto auto;
        grid-template-areas: "id hand meta stats actions";
    }
}

.a-id { grid-area: id; }
.a-meta { grid-area: meta; }
.a-hand { grid-area: hand; }
.a-stats { grid-area: stats; }
.a-actions { grid-area: actions; }

/* ── turn indicator ───────────────────────────────────────────────
   box-shadow rather than an extra element or a border change: it costs no
   layout, so the panel does not shift when the turn moves, and the --seat
   variable set inline lets one rule serve all four seat colours.
────────────────────────────────────────────────────────────────── */
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

/* ── scrollbar ────────────────────────────────────────────────────── */
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