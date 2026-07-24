<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import Card from '../Card.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

const props = defineProps({
    cardType: { type: String, required: true },
    available: { type: Number, default: 99 },
    transactionType: { type: String, default: 'buy' },
    // request in flight — the confirm button locks so a double-click cannot
    // submit the same purchase twice
    busy: { type: Boolean, default: false },
    // buy only: what the player can actually afford
    points: { type: Number, default: 0 },
    /*
      Popover mode: no backdrop, no centring, content only. The parent anchors
      it above the panel. Used for sell and trade, which now render inside a
      card holder far narrower than a centred dialog wants to be.
    */
    popover: { type: Boolean, default: false },
})

/*
 * confirm payload:
 *   buy / sell -> quantity (Number)
 *   trade      -> { give: { type, quantity }, get: { type, quantity } }
 */
const emit = defineEmits(['confirm', 'cancel'])

const cardTypes = useCardTypesStore()

const destination = ref('bank')
const unitPrice = ref(1)

const quantity = ref(1)          // buy / sell, and the "give" side of a trade
const getQuantity = ref(1)       // trade only: how many of the wanted card
const getType = ref('')          // trade only: which card is wanted back

function clamp(value: number, max: number) {
    return Math.min(max, Math.max(1, value))
}
function step(delta: number) {
    quantity.value = clamp(quantity.value + delta, maxQuantity.value)
}
function stepGet(delta: number) {
    getQuantity.value = clamp(getQuantity.value + delta, 99)
}

// Escape closes, like any modal
function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') emit('cancel')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

// Everything that varies per transaction type, in one place. Class strings are
// full literals so Tailwind's scanner generates all variants.
const TYPES = {
    buy: {
        heading: 'Buy card',
        subheading: 'Choose how many you want.',
        confirm: 'Buy',
        pointsLabel: 'Cost',
        confirmClass: 'bg-emerald-400 text-gray-dark border-2 border-emerald-400 hover:bg-emerald-300 hover:border-emerald-300',
    },
    sell: {
        heading: 'Sell card',
        subheading: 'Choose how many to sell.',
        confirm: 'Sell',
        pointsLabel: 'Points earned',
        confirmClass: 'bg-rose-400 text-gray-dark border-2 border-rose-400 hover:bg-rose-300 hover:border-rose-300',
    },
    trade: {
        heading: 'Trade cards',
        subheading: 'Pick what you want in return.',
        confirm: 'Trade',
        pointsLabel: '',
        confirmClass: 'bg-amber-400 text-gray-dark border-2 border-amber-400 hover:bg-amber-300 hover:border-amber-300',
    },
}

const type = computed(() => TYPES[props.transactionType] ?? TYPES.buy)
const isTrade = computed(() => props.transactionType === 'trade')

// Layout keys on how much room the host has, not on the action: buy renders in
// the roomy BankSection, sell and trade inside the cramped PlayerCardHolder.
// compact = anything that is not the roomy bank dialog
const isCompact = computed(() => props.popover || props.transactionType !== 'buy')

// Unlike `scale`, `zoom` participates in layout: the wrapper's measured box
// shrinks too, so the modal actually gets shorter instead of just drawing
// smaller inside a full-height box.
/*
  The card preview scales with the shell. The bank dialog has room for a
  full-size card; the popover sits above a slim panel, so it takes a middle
  size rather than the tiny one the old inline sell modal used.
*/
const previewZoom = computed(() => {
    if (props.popover) return 0.85
    return isCompact.value ? 0.6 : 1
})


// Card data comes from the store (fetched from /api/v1/config/card-types), so
// the price shown here is the same number the server charges.
const isBuy = computed(() => props.transactionType === 'buy')
const isSell = computed(() => props.transactionType === 'sell')
const toPlayer = computed(() => isSell.value && destination.value === 'player')

function stepPrice(delta) {
    unitPrice.value = Math.min(99, Math.max(1, unitPrice.value + delta))
}

const totalPrice = computed(() => unitPrice.value * quantity.value)

// Buying charges base_cost; selling pays sell_value. Equal today, but reading
// the right column now means changing the spread is a migration rather than a
// frontend hunt.
const unitPoints = computed(() => {
    const card = cardTypes.get(props.cardType)
    if (!card) return 0
    return isSell.value ? card.sellValue : card.baseCost
})
const totalPoints = computed(() => unitPoints.value * quantity.value)
const showPoints = computed(() => !isTrade.value && unitPoints.value > 0)

/*
  How many the player can afford. The server enforces this — the check here
  exists so the stepper stops at a reachable number instead of letting someone
  pick 5 and get rejected.
*/
const affordable = computed(() => {
    if (!isBuy.value || unitPoints.value === 0) return props.available
    return Math.min(props.available, Math.floor(props.points / unitPoints.value))
})
const maxQuantity = computed(() => Math.max(1, affordable.value))
const cannotAfford = computed(() => isBuy.value && totalPoints.value > props.points)

/** Title for a card code, safe if the catalogue somehow lacks it. */
function titleOf(code: string) {
    return cardTypes.get(code)?.title ?? code
}

// What can be asked for in return: anything tradeable except the card given.
// Driven by the is_tradeable column now, not a hardcoded `!== 'point'` — so
// making a card untradeable is a migration, not a frontend edit.
const tradeableTypes = computed(() =>
    cardTypes.all
        .filter((c) => c.isTradeable && c.code !== props.cardType)
        .map((c) => c.code))

const canConfirm = computed(() => {
    if (props.busy) return false
    if (isTrade.value) return getType.value !== ''
    if (toPlayer.value) return quantity.value >= 1 && unitPrice.value >= 1
    return !cannotAfford.value && quantity.value >= 1
})

const blocker = computed(() => {
    if (isTrade.value && !getType.value) return 'Choose a card to receive'
    return ''
})

function confirm() {
    if (!canConfirm.value) return
    if (isTrade.value) {
        emit('confirm', {
            kind: 'trade-offer',
            cardType: props.cardType,
            quantity: quantity.value,
            wantCardType: getType.value,
            wantQuantity: getQuantity.value,
        })
        return
    }

    if (toPlayer.value) {
        emit('confirm', {
            kind: 'sell-offer',
            cardType: props.cardType,
            quantity: quantity.value,
            pricePoints: unitPrice.value,
        })
        return
    }

    emit('confirm', {
        kind: isBuy.value ? 'buy' : 'sell-to-bank',
        cardType: props.cardType,
        quantity: quantity.value,
    })
}

const wellClass =
    'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'

const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'

const stepperClass = 'flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max'

const stepButton =
    'w-10 h-10 flex items-center justify-center text-2xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'

// narrower variant so a stepper sitting under a card doesn't out-width the column
const stepButtonSm =
    'w-8 h-8 flex items-center justify-center text-xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'

const countClass =
    'flex items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'

// popover matches the bank dialog's control sizing, not the cramped inline one.
// Declared AFTER both button strings: a const is in the temporal dead zone
// until its own line executes, so referencing them earlier throws at setup.
const stepper = computed(() => (props.popover ? stepButton : stepButtonSm))

/**
 * The deal in words. A trade has four moving parts spread across two columns —
 * a one-line restatement is how the player checks they built what they meant
 * before committing, and it is the only place both sides appear together.
 */
const tradeSummary = computed(() => {
    if (!getType.value) return null
    return {
        give: `${quantity.value}× ${titleOf(props.cardType)}`,
        get: `${getQuantity.value}× ${titleOf(getType.value)}`,
    }
})

const DESTINATIONS = [
    { key: 'bank', label: 'To bank' },
    { key: 'player', label: 'Post offer' },
]

const segClass =
    'flex-1 cursor-pointer rounded-lg py-2 text-sm font-bold transition-colors duration-200'

const actionButton =
    'min-w-24 px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:opacity-40 disabled:cursor-not-allowed ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'
</script>

<template>
    <div :class="popover
            ? ''
            : 'absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 backdrop-blur-sm ' + (isCompact ? 'p-3' : 'p-6')"
        @click.self="popover || emit('cancel')">

        <div role="dialog" aria-modal="true" aria-labelledby="transaction-title"
            class="relative flex max-w-full flex-col"
            :class="popover
                ? 'gap-5 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-6 shadow-2xl shadow-black/60'
                : (isCompact ? 'gap-4 p-4 w-full' : 'gap-6 p-6 w-max')">

            <button type="button" aria-label="Close" @click="emit('cancel')"
                class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">✕</button>

            <header class="flex flex-col gap-0.5 pr-10">
                <h2 id="transaction-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                    {{ type.heading }}
                </h2>
                <p class="text-sm text-gray-x-light">
                    {{ toPlayer ? 'Name your price. Any player can take it.'
                        : isTrade ? 'Post what you want in return. Any player can take it.'
                        : type.subheading }}
                </p>
            </header>

            <div v-if="isSell" class="flex gap-1 rounded-xl border-2 border-gray-light bg-gray-dark p-1">
                <button v-for="d in DESTINATIONS" :key="d.key" type="button" :class="[
                    segClass,
                    destination === d.key
                        ? 'bg-gray-2x-light text-gray-dark'
                        : 'text-gray-x-light hover:text-gray-2x-light',
                ]" @click="destination = d.key">
                    {{ d.label }}
                </button>
            </div>

            <div v-if="isTrade" class="flex items-stretch justify-center gap-3">

                <section class="flex w-[10.5rem] flex-col items-center gap-2">
                    <h3 :class="labelClass">You give</h3>
                    <div
                        class="flex h-[7.5rem] w-full items-center justify-center rounded-2xl border-2 border-gray-light bg-gray-dark">
                        <div :style="{ zoom: 0.62 }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                    <div :class="stepperClass">
                        <button type="button" :class="stepper" :disabled="quantity <= 1"
                            aria-label="Decrease quantity given" @click="step(-1)">−</button>
                        <div :class="[countClass, 'w-12 text-lg']">{{ quantity }}</div>
                        <button type="button" :class="stepper" :disabled="quantity >= available"
                            aria-label="Increase quantity given" @click="step(1)">+</button>
                    </div>
                    <p class="text-xs text-gray-x-light">{{ available }} available</p>
                </section>

                <div class="flex items-center">
                    <span class="text-2xl font-bold text-amber-400 select-none" aria-hidden="true">⇄</span>
                </div>

                <section class="flex w-[10.5rem] flex-col items-center gap-2">
                    <h3 :class="labelClass">You get</h3>
                    <div
                        class="grid h-[7.5rem] w-full grid-cols-3 content-center justify-items-center gap-1.5 rounded-2xl border-2 border-gray-light bg-gray-dark p-2">
                        <button v-for="t in tradeableTypes" :key="t" type="button"
                            :aria-label="`Trade for ${titleOf(t)}`" :aria-pressed="getType === t" @click="getType = t"
                            class="cursor-pointer rounded-xl outline-amber-400 transition duration-200 ease-in-out"
                            :class="getType === t ? 'outline-3 scale-110' : 'outline-0 opacity-45 hover:opacity-90'">
                            <Card :card-type="t" :selected="true" :large="false" />
                        </button>
                    </div>
                    <div :class="stepperClass">
                        <button type="button" :class="stepper" :disabled="getQuantity <= 1 || !getType"
                            aria-label="Decrease quantity wanted" @click="stepGet(-1)">−</button>
                        <div :class="[countClass, 'w-12 text-lg']">{{ getQuantity }}</div>
                        <button type="button" :class="stepper" :disabled="!getType" aria-label="Increase quantity wanted"
                            @click="stepGet(1)">+</button>
                    </div>
                    <p class="text-xs font-bold" :class="getType ? 'text-amber-400' : 'text-gray-light'">
                        {{ getType ? titleOf(getType) : 'Pick a card' }}
                    </p>
                </section>
            </div>

            <div v-else class="flex items-center" :class="popover ? 'gap-5' : (isCompact ? 'gap-4' : 'gap-6')">

                <section class="flex flex-col gap-2">
                    <h3 :class="labelClass">Card</h3>
                    <div :class="[wellClass, popover ? 'p-4' : (isCompact ? 'p-2' : 'p-4')]">
                        <div :style="{ zoom: previewZoom }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                </section>

                <div class="flex flex-col gap-2">
                    <section class="flex flex-col gap-2">
                        <h3 :class="labelClass">Quantity</h3>
                        <div :class="stepperClass">
                            <button type="button" :class="stepper" :disabled="quantity <= 1"
                                aria-label="Decrease quantity" @click="step(-1)">−</button>
                            <div :class="[countClass, 'w-14 text-lg']">{{ quantity }}</div>
                            <button type="button" :class="stepper" :disabled="quantity >= maxQuantity"
                                aria-label="Increase quantity" @click="step(1)">+</button>
                        </div>
                        <p class="text-xs text-gray-x-light">{{ available }} available</p>
                        <p v-if="isBuy && affordable < available" class="text-xs font-bold text-amber-400">
                            You can afford {{ affordable }}
                        </p>
                    </section>

                    <section v-if="toPlayer" class="flex flex-col gap-2">
                        <h3 :class="labelClass">Price each</h3>
                        <div :class="stepperClass">
                            <button type="button" :class="stepper" :disabled="unitPrice <= 1"
                                aria-label="Decrease price" @click="stepPrice(-1)">−</button>
                            <div :class="[countClass, 'w-14 text-lg']">{{ unitPrice }}</div>
                            <button type="button" :class="stepper" aria-label="Increase price"
                                @click="stepPrice(1)">+</button>
                        </div>
                    </section>

                    <section v-else-if="showPoints" class="flex flex-col gap-2">
                        <h3 :class="labelClass">{{ type.pointsLabel }}</h3>
                        <div :class="[wellClass, 'gap-2 p-2']">
                            <Card :card-type="'point'" :selected="true" :large="false" />
                            <span class="text-lg font-bold tabular-nums text-teal-light">{{ totalPoints }}</span>
                        </div>
                    </section>
                </div>
            </div>

            <p v-if="isTrade && tradeSummary"
                class="rounded-xl border-2 border-amber-400/40 bg-amber-400/10 px-4 py-2 text-center text-sm font-bold text-gray-2x-light">
                {{ tradeSummary.give }}
                <span class="px-2 text-amber-400">→</span>
                {{ tradeSummary.get }}
                <span class="text-gray-x-light">— open to anyone</span>
            </p>

            <p v-else-if="toPlayer"
                class="rounded-xl border-2 border-rose-400/40 bg-rose-400/10 px-4 py-2 text-center text-sm font-bold text-gray-2x-light">
                {{ quantity }}× {{ titleOf(cardType) }}
                <span class="px-2 text-rose-400">→</span>
                {{ totalPrice }} pts
                <span class="text-gray-x-light">— open to anyone</span>
            </p>

            <footer class="flex items-center justify-end gap-2 border-t-1 border-gray-light pt-4">
                <p v-if="blocker" class="mr-auto text-xs font-bold text-gray-light">{{ blocker }}</p>

                <button type="button" :class="actionButton"
                    class="border-2 border-gray-light text-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light"
                    @click="emit('cancel')">Cancel</button>

                <button type="button" :class="[actionButton, type.confirmClass]" :disabled="!canConfirm"
                    @click="confirm">
                    <span class="flex items-center justify-center gap-2">
                        <span v-if="busy"
                            class="h-4 w-4 animate-spin rounded-full border-2 border-gray-dark/30 border-t-gray-dark"></span>
                        {{ busy ? '' : (toPlayer ? 'Post offer' : isTrade ? 'Post offer' : type.confirm) }}
                        {{ busy || isTrade || toPlayer ? '' : quantity }}
                    </span>
                </button>
            </footer>
        </div>
    </div>
</template>