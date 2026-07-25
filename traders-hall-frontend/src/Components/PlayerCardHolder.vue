<script setup>
import { computed, ref } from 'vue'
import Card from './Card.vue'
import CardDeck from './CardDeck.vue'
import SeatToken from './SeatToken.vue'
import TransactionModal from './Modals/TransactionModal.vue'
import EatModal from './Modals/EatModal.vue'
import ResidenceModal from './Modals/ResidenceModal.vue'
import { seatStyle } from '../seats'
import { useCardTypesStore } from '../stores/cardTypes'

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

    // ── credit ────────────────────────────────────────────────────
    // Public for every seat, not just your own: a rival two rounds from
    // default is information the whole table should be able to act on.
    /** rounds until the loan falls due; meaningless when nothing is owed */
    loanDue: { type: Number, default: 0 },
    loanOutstanding: { type: Number, default: 0 },
    mortgageCardType: { type: String, default: null },
    mortgageOutstanding: { type: Number, default: 0 },
    mortgageDue: { type: Number, default: 0 },

    residence: { type: String, default: '' },
    onRent: { type: Boolean, default: false },
    // Housing. `residence` is the card code lived in; these describe capacity as
    // a landlord, which is public — a spare room is what makes someone eligible
    // to answer a request.
    roomsTotal: { type: Number, default: 0 },
    roomsFree: { type: Number, default: 0 },
    isTenant: { type: Boolean, default: false },
    // Lettable rooms per property type, and rooms already promised by a live
    // offer. Both come from the server, because capacity is derived there — the
    // hand alone cannot tell you how many rooms are still free.
    roomsByCard: { type: Object, default: () => ({}) },
    roomsPendingByCard: { type: Object, default: () => ({}) },
    residenceLandlordId: { type: String, default: null },
    landlordName: { type: String, default: '' },
    landlordSeatIndex: { type: Number, default: -1 },
    rentPoints: { type: Number, default: 0 },
    /** an action is in flight; controls lock so a double-click cannot fire twice */
    busy: { type: Boolean, default: false },
})

const emit = defineEmits([
    'buy', 'sell', 'trade', 'eat', 'residence',
    'moveIn', 'leaveResidence', 'rentOut', 'rentAsk',
    'cancelOperation', 'transaction', 'endTurn',
])

const cardTypes = useCardTypesStore()

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

/* ── credit ──────────────────────────────────────────────────────── */

const hasLoan = computed(() => props.loanOutstanding > 0)
const hasMortgage = computed(() => props.mortgageOutstanding > 0)
const hasDebt = computed(() => hasLoan.value || hasMortgage.value)
const debtTotal = computed(() => props.loanOutstanding + props.mortgageOutstanding)

// Whichever obligation lands first sets the urgency, since that is the one
// about to cost the player something.
const debtSoonest = computed(() => {
    const live = [
        hasLoan.value ? props.loanDue : null,
        hasMortgage.value ? props.mortgageDue : null,
    ].filter((n) => n !== null)
    return live.length ? Math.min(...live) : null
})

// Full literal class strings: Tailwind's scanner cannot see an interpolated
// name, so a computed `text-${tone}-400` would never be generated.
function urgencyText(rounds) {
    if (rounds === null) return 'text-gray-light'
    if (rounds <= 1) return 'text-rose-400'
    if (rounds <= 2) return 'text-amber-400'
    return 'text-teal-light'
}
function urgencyBox(rounds) {
    if (rounds === null) return 'border-gray-light bg-gray-dark text-gray-light'
    if (rounds <= 1) return 'border-rose-400 bg-rose-400/20 text-rose-400'
    if (rounds <= 2) return 'border-amber-400 bg-amber-400/20 text-amber-400'
    return 'border-teal-light bg-teal-dark text-teal-light'
}

const debtTone = computed(() => urgencyText(debtSoonest.value))

/** "1 round" / "3 rounds" — the strip has room for the word, so it uses it. */
const roundsLabel = (n) => (n === 1 ? '1 round' : `${n} rounds`)

const debtTitle = computed(() => {
    if (!hasDebt.value) return ''
    const parts = []
    if (hasLoan.value) parts.push(`Loan ${props.loanOutstanding}, due in ${props.loanDue}`)
    if (hasMortgage.value) {
        parts.push(`Mortgage ${props.mortgageOutstanding} on ${props.mortgageCardType}, due in ${props.mortgageDue}`)
    }
    return parts.join(' · ')
})

/** The mortgaged card is locked: it cannot be sold, traded or offered. */
const isMortgaged = (type) => hasMortgage.value && type === props.mortgageCardType

/* ── eating ──────────────────────────────────────────────────────
   Eating is available whenever a food card is in hand and it is your turn —
   there is no "eat mode" in the action bar, because a meal has no counterparty
   to negotiate with. It therefore has to yield to the market modes: a food card
   during a sell must stay sellable, or the player can never sell their wheat.
────────────────────────────────────────────────────────────────── */

const isEdible = (type) => {
    const card = cardTypes.get(type)
    return !!card && card.category === 'food' && card.nutritionTurns > 0
}

const canEat = (type) =>
    isOwn.value &&
    canAct.value &&
    props.activeAction === '' &&
    !isMortgaged(type) &&
    isEdible(type)

function openEat(type) {
    if (!canEat(type)) return
    selectedType.value = type
    activeModal.value = 'eat'
}

function onEat(payload) {
    emit('eat', payload)
    activeModal.value = ''
}

/* ── letting a room ──────────────────────────────────────────────
   Clicking an owned property opens the let-a-room popover for THAT property
   only. Same shape as eating: no mode in the action bar, and it yields to the
   market modes so a property stays sellable during a sell.
────────────────────────────────────────────────────────────────── */

const freeRoomsFor = (type) => props.roomsByCard[type] ?? 0
const pendingRoomsFor = (type) => props.roomsPendingByCard[type] ?? 0

const canLet = (type) =>
    isOwn.value &&
    canAct.value &&
    props.activeAction === '' &&
    !isMortgaged(type) &&
    freeRoomsFor(type) > 0

function openLet(type) {
    if (!canLet(type)) return
    selectedType.value = type
    activeModal.value = 'let'
}

// The residence popover shares the same anchor, so it goes through activeModal
// rather than a separate flag — one open-modal-at-a-time falls out of that.
function openResidence() {
    if (!isOwn.value) return
    activeModal.value = 'residence'
}

function onHousing(event, payload) {
    emit(event, payload)
    activeModal.value = ''
}

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
//
// The loan box shows ROUNDS REMAINING, like food and rent beside it, with the
// amount owed as a caption underneath. It counts down to whichever bank
// obligation lands FIRST — loan or mortgage — because that is the one about to
// cost something; the tooltip breaks the two apart. An em dash rather than a
// zero when nothing is owed: "Loan 0" reads as "due right now", which is the
// one thing it must never be confused with.
const stats = computed(() => [
    { key: 'food', label: 'Food', value: props.foodDue, note: '', title: '', caption: 'text-cream-dark', tone: 'border-cream-light bg-cream-dark text-cream-light' },
    { key: 'rent', label: 'Rent', value: props.rentDue, note: '', title: '', caption: 'text-purple-dark', tone: 'border-purple-light bg-purple-dark text-purple-light' },
    {
        key: 'loan',
        label: 'Loan',
        value: hasDebt.value ? debtSoonest.value : '—',
        note: hasDebt.value ? `${debtTotal.value} owed` : '',
        title: debtTitle.value,
        caption: hasDebt.value ? urgencyText(debtSoonest.value) : 'text-teal-dark',
        tone: hasDebt.value ? urgencyBox(debtSoonest.value) : 'border-gray-light bg-gray-dark text-gray-light',
    },
])

/* ── behaviour ────────────────────────────────────────────────────── */

function openModal(type) {
    // A mortgaged card is collateral: the server refuses to sell, trade or
    // offer it, so the modal should not open on it in the first place.
    if (isMortgaged(type)) return
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
        <div v-if="activeModal !== ''" class="absolute top-1/2 left-full z-[120] ml-2 w-max max-w-[calc(100vw-3rem)] -translate-y-1/2
                   xl:top-auto xl:bottom-full xl:left-1/2 xl:ml-0 xl:-translate-x-1/2 xl:translate-y-0">
            <!-- Two modals share this anchor. Eating is not a transaction, so it
                 gets its own component rather than a fourth mode inside one. -->
            <ResidenceModal v-if="activeModal === 'let' || activeModal === 'residence'"
                :mode="activeModal === 'let' ? 'let' : 'residence'" :card-type="selectedType"
                :rooms-free-for-card="freeRoomsFor(selectedType)"
                :rooms-pending-for-card="pendingRoomsFor(selectedType)" :residence-card-type="residence || null"
                :residence-landlord-id="residenceLandlordId" :landlord-name="landlordName"
                :landlord-seat-index="landlordSeatIndex" :rent-points="rentPoints" :rent-due="rentDue"
                :rooms-by-card="roomsByCard" :busy="busy" :can-act="canAct" @close-modal="closeModal"
                @move-in="(t) => onHousing('moveIn', t)" @leave="onHousing('leaveResidence')"
                @rent-out="(p) => onHousing('rentOut', p)" @rent-ask="(p) => onHousing('rentAsk', p)" />
            <EatModal v-else-if="activeModal === 'eat'" :card-type="selectedType"
                :available="hand[selectedType] ?? 1" :food-due="foodDue" :busy="busy" :popover="true"
                @confirm="onEat($event)" @cancel="closeModal" />
            <TransactionModal v-else-if="activeModal === 'sell' || activeModal === 'trade'" :transaction-type="activeModal" :card-type="selectedType"
                :available="hand[selectedType] ?? 1" :points="points" :busy="busy" :popover="true" @confirm="onConfirm($event)"
                @cancel="closeModal" />
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
                <h1 class="truncate text-lg font-bold tracking-wide whitespace-nowrap xl:text-xl" :class="seat.text">
                    {{ playerName }}
                </h1>
                <!--
                    The debt badge used to live here and was overrun by the
                    points deck: a deck of five point cards is wide, `a-meta`
                    sits in the 1fr track next door, and a shrink-0 pill in an
                    auto-width track cannot get out of its way. Debt now rides
                    on the Loan stat instead — a cell that already has room and
                    is already about exactly this.
                -->
            </div>

            <!-- points and residence travel together in both layouts -->
            <div class="a-meta flex items-center justify-end gap-2">
                <CardDeck v-if="points > 0" :key="`pts-${points}`" :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <span v-else class="px-1 text-sm font-bold text-gray-light">0 pts</span>

                <!--
                    The residence box is the way into all of housing: where you
                    live, leaving, letting a room, asking for one. A button
                    rather than a decorated div, so it is keyboard reachable and
                    reads as clickable.
                -->
                <button type="button" :disabled="busy"
                    :aria-label="residence !== '' ? 'Manage your residence' : 'Find somewhere to live'"
                    :title="residence !== '' ? 'Manage residence' : 'You live nowhere'"
                    @click="openResidence""
                    class="flex shrink-0 cursor-pointer items-center gap-1 rounded-[1rem] border-4 bg-purple-dark px-2 transition duration-200 ease-in-out disabled:cursor-not-allowed disabled:opacity-50"
                    :class="residence !== ''
                        ? 'border-purple-light hover:brightness-125'
                        : 'border-purple-light/50 hover:border-purple-light'">
                    <span class="flex flex-col items-start leading-tight">
                        <span class="text-xs font-bold text-purple-light">Residence</span>
                        <!-- Capacity only when there is any: a player owning no
                             property has nothing to report here. -->
                        <span v-if="roomsTotal > 0" class="text-[10px] font-bold tabular-nums"
                            :class="roomsFree > 0 ? 'text-teal-light' : 'text-gray-x-light'">
                            {{ roomsFree }} free
                        </span>
                        <span v-else-if="isTenant" class="text-[10px] font-bold text-gray-x-light">rented</span>
                    </span>
                    <div class="-mx-1">
                        <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                        <div v-else class="m-1 h-7 w-7 bg-purple-light" :style="{
                            mask: `url(/cancel.png) no-repeat center / contain`,
                            '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                        }"></div>
                    </div>
                </button>
            </div>
            <div class="flex">
                <span class="card-label rotate-180 text-center uppercase text-gray-x-light tracking-[0.3rem] text-xs font-bold mb-1">cards</span>
                <div class="a-hand relative flex min-w-0 justify-between overflow-hidden rounded-[1rem] border-1 px-3 py-1.5 transition-colors duration-300 ease-in-out"
                    :class="handState ? handState.well : 'border-gray-light outline-0'">
                    <button v-if="handState" type="button" aria-label="Cancel" @click="emit('cancelOperation')"
                        class="absolute top-0 right-0 z-10 flex cursor-pointer items-center justify-center p-2 leading-none text-gray-x-light transition-colors duration-200 ease-in-out hover:text-rose-400">🗙</button>
    
                    <!-- overflow-x-auto: a full hand of six types would otherwise
                         widen the cell instead of scrolling -->
    
                    <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto">
                        <!-- :key is required: without it Vue patches these decks in
                                 place by index, which mixes card types between decks -->
                        <div v-for="type in heldTypes" :key="`${type}-${hand[type]}`"
                            class="relative shrink-0 rounded-[1rem] p-1 transition duration-200 ease-in-out"
                            :class="isMortgaged(type) ? 'outline-2 -outline-offset-1 outline-rose-400/70' : ''">
                            <!--
                                The mortgaged deck is dimmed, ringed and badged
                                rather than hidden: the card is still yours, it
                                just cannot move until the debt clears. Removing
                                it would read as "the bank already took it".

                                The ring reuses the outline idiom the sell and
                                trade wells already use, and the badge is a
                                2px-bordered square holding a drawn glyph — not
                                a round emoji pill. Nothing else here is a round
                                pill, and an emoji renders at whatever weight
                                and hue the platform font decides, which is why
                                it read as foreign.

                                p-1 is what keeps both off the card's own border
                                and inside the well: the badge sits at THIS box's
                                corner rather than hanging outside it, and the
                                well is overflow-hidden, so anything that hung
                                out was being sliced.
                            -->
                            <CardDeck :content-small="true" :class="isMortgaged(type) ? 'opacity-60' : ''">
                                <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false"
                                    :class="handState && !isMortgaged(type) ? 'cursor-pointer' : ''"
                                    :selling="activeAction === 'sell' && !isMortgaged(type)"
                                    :trading="activeAction === 'trade' && !isMortgaged(type)"
                                    :eating="canEat(type)" :letting="canLet(type)"
                                    @sell="openModal(type)" @trade="openModal(type)" @eat="openEat(type)"
                                    @let="openLet(type)" />
                            </CardDeck>
                            <span v-if="isMortgaged(type)"
                                :title="`Mortgaged for ${mortgageOutstanding}, due in ${mortgageDue} round(s)`"
                                class="pointer-events-none absolute top-0 right-0 z-10 flex h-4 w-4 items-center justify-center rounded-md border-2 border-rose-400 bg-gray-x-dark">
                                <svg viewBox="0 0 10 10" class="h-2.5 w-2.5 text-rose-400" fill="none"
                                    stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true">
                                    <path d="M3 4.4V3.2a2 2 0 0 1 4 0v1.2" />
                                    <rect x="2" y="4.4" width="6" height="4.2" rx="1" />
                                </svg>
                            </span>
                        </div>
                    </div>
                    <span v-else class="py-2 text-sm text-gray-light">No cards</span>
                </div>
            </div>

            <!-- caption above, number in the box: the box then shrinks to the
                 number, which is the width this reclaims -->
            <div class="a-stats grid grid-cols-3 gap-2 xl:flex">
                <div v-for="stat in stats" :key="stat.key" :title="stat.title"
                    class="flex flex-col items-center gap-0.5">
                    <span :class="[statLabel, stat.caption]">{{ stat.label }}</span>
                    <div :class="[statBox, stat.tone]">{{ stat.value }}</div>
                    <!-- the amount, under the countdown. Spelled out rather than
                         packed into the box, so neither number has to be
                         abbreviated to share the space. -->
                    <span v-if="stat.note" class="text-[10px] font-bold tabular-nums" :class="stat.caption">
                        {{ stat.note }}
                    </span>
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
                    
                    <!--
                        A tenancy is marked by the LANDLORD's own seat token in
                        the corner, not a word: the table already reads players
                        by colour and glyph, so the token says both "rented" and
                        "from whom" in the space a label would need for one.
                    -->
                    <div class="relative flex items-center rounded-lg border-2 px-1 transition-colors duration-200"
                        :class="isTenant ? 'border-teal-light bg-teal-dark/30' : 'border-purple-light bg-purple-dark'">
                        <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                        <div v-else class="m-1 h-6 w-6 bg-purple-light" :style="{
                            mask: `url(/cancel.png) no-repeat center / contain`,
                            '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                        }"></div>

                        <span v-if="isTenant" :title="`Renting from ${landlordName || 'another player'}`"
                            class="pointer-events-none absolute -top-1.5 -right-1.5 z-10 flex items-center justify-center rounded-full border-2 border-gray-x-dark bg-gray-x-dark">
                            <SeatToken :seat-index="landlordSeatIndex" size="sm" :filled="true" />
                        </span>
                    </div>
                </div>
            </div>

            <!--
                A full-width strip rather than a chip in the header row.

                That header already carries a token, a truncating name, a turn
                pill, a points deck and the residence box; a debt badge squeezed
                in beside them had to shorten itself to "2·5r" to fit, which is
                not something anyone can read. Given its own row it has room to
                say what it means, and it only exists when there is debt.
            -->
            <div v-if="hasDebt" :title="debtTitle"
                class="flex items-center justify-between gap-2 rounded-lg border-2 px-2 py-1"
                :class="debtSoonest <= 1
                    ? 'border-rose-400 bg-rose-400/10'
                    : debtSoonest <= 2 ? 'border-amber-400 bg-amber-400/10' : 'border-teal-light bg-teal-dark/20'">
                <span class="text-[10px] font-bold uppercase tracking-widest tabular-nums" :class="debtTone">
                    Owes {{ debtTotal }}
                </span>
                <span class="text-[10px] font-bold uppercase tracking-widest tabular-nums" :class="debtTone">
                    Due in {{ roundsLabel(debtSoonest) }}
                </span>
            </div>

            <div class="flex">
                <span class="card-label rotate-180 text-center uppercase text-gray-x-light tracking-[0.3rem] text-xs font-bold mb-1">cards</span>
                <div
                    class="relative flex min-h-[4.25rem] min-w-0 items-center overflow-hidden rounded-[1rem] border-1 border-gray-light px-3 py-1.5">
                    <div v-if="heldTypes.length" class="scroll-slim flex gap-2 overflow-x-auto">
                        <div v-for="type in heldTypes" :key="`${type}-${hand[type]}`"
                            class="relative shrink-0 rounded-[1rem] p-1 transition duration-200 ease-in-out"
                            :class="isMortgaged(type) ? 'outline-2 -outline-offset-1 outline-rose-400/70' : ''">
                            <CardDeck :content-small="true" :class="isMortgaged(type) ? 'opacity-60' : ''">
                                <Card v-for="n in hand[type]" :key="`${type}-${n}`" :card-type="type" :large="false" />
                            </CardDeck>
                            <span v-if="isMortgaged(type)"
                                :title="`Mortgaged for ${mortgageOutstanding}, due in ${mortgageDue} round(s)`"
                                class="pointer-events-none absolute top-0 right-0 z-10 flex h-4 w-4 items-center justify-center rounded-md border-2 border-rose-400 bg-gray-x-dark">
                                <svg viewBox="0 0 10 10" class="h-2.5 w-2.5 text-rose-400" fill="none"
                                    stroke="currentColor" stroke-width="1.4" stroke-linecap="round" aria-hidden="true">
                                    <path d="M3 4.4V3.2a2 2 0 0 1 4 0v1.2" />
                                    <rect x="2" y="4.4" width="6" height="4.2" rx="1" />
                                </svg>
                            </span>
                        </div>
                    </div>
                    <span v-else class="text-sm text-gray-light">No cards</span>
                </div>
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

.a-id {
    grid-area: id;
}

.a-meta {
    grid-area: meta;
}

.a-hand {
    grid-area: hand;
}

.a-stats {
    grid-area: stats;
}

.a-actions {
    grid-area: actions;
}

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

.card-label {
    writing-mode: vertical-lr;
    text-orientation: mixed;
}
</style>