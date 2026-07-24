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
})

/*
 * confirm payload:
 *   buy / sell -> quantity (Number)
 *   trade      -> { give: { type, quantity }, get: { type, quantity } }
 */
const emit = defineEmits(['confirm', 'cancel'])

const cardTypes = useCardTypesStore()

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
const isCompact = computed(() => props.transactionType !== 'buy')

// Unlike `scale`, `zoom` participates in layout: the wrapper's measured box
// shrinks too, so the modal actually gets shorter instead of just drawing
// smaller inside a full-height box.
const PREVIEW_ZOOM = 0.6
const previewZoom = computed(() => (isCompact.value ? PREVIEW_ZOOM : 1))

// Card data comes from the store (fetched from /api/v1/config/card-types), so
// the price shown here is the same number the server charges.
const isBuy = computed(() => props.transactionType === 'buy')
const isSell = computed(() => props.transactionType === 'sell')

// Buying charges base_cost; selling pays sell_value. They are equal today, but
// reading the right column now means changing the spread is a migration rather
// than a frontend hunt.
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
    return !cannotAfford.value && quantity.value >= 1
})

function confirm() {
    if (!canConfirm.value) return
    emit('confirm', isTrade.value
        ? {
            give: { type: props.cardType, quantity: quantity.value },
            get: { type: getType.value, quantity: getQuantity.value },
        }
        : quantity.value)
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

const actionButton =
    'w-25 py-3 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:opacity-40 disabled:cursor-not-allowed ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'
</script>

<template>
    <!-- backdrop: click outside to dismiss -->
    <div class="absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 backdrop-blur-sm"
        :class="isCompact ? 'p-3' : 'p-6'" @click.self="emit('cancel')">

        <div role="dialog" aria-modal="true" aria-labelledby="transaction-title" class="relative flex max-w-full"
            :class="isCompact
                ? 'gap-4 p-4 w-full justify-between items-center'
                : 'flex-col gap-6 p-6 w-max'">

            <!-- close, matching the 🗙 on the hand well in PlayerCardHolder -->
            <button v-if="transactionType === 'buy'" type="button" aria-label="Close" @click="emit('cancel')"
                class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

            <header class="flex flex-col gap-1" :class="isCompact ? 'justify-center items-start' : ''">
                <h2 id="transaction-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                    {{ type.heading }}
                </h2>
                <p class="text-sm text-gray-x-light">{{ type.subheading }}</p>
            </header>

            <!-- ── trade: two columns, each card sitting above its own quantity ── -->
            <div v-if="isTrade" class="flex items-center gap-4">

                <section class="flex flex-col items-center gap-2">
                    <h3 :class="labelClass">You give</h3>
                    <div :class="[wellClass, 'p-2']">
                        <!-- zoom shrinks the layout box, not just the pixels -->
                        <div :style="{ zoom: previewZoom }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                    <div :class="stepperClass">
                        <button type="button" :class="stepButtonSm" :disabled="quantity <= 1"
                            aria-label="Decrease quantity given" @click="step(-1)">−</button>
                        <div :class="[countClass, 'w-12 text-lg']">{{ quantity }}</div>
                        <button type="button" :class="stepButtonSm" :disabled="quantity >= available"
                            aria-label="Increase quantity given" @click="step(1)">+</button>
                    </div>
                    <p class="text-xs text-gray-x-light">{{ available }} available</p>
                </section>

                <div class="text-3xl font-bold text-amber-400 self-center px-1 select-none">⇄</div>

                <section class="flex flex-col items-center gap-2">
                    <h3 :class="labelClass">You get</h3>
                    <!-- horizontal chip row: nowrap keeps it on one line -->
                    <div :class="[wellClass, 'p-2 gap-2 flex-nowrap']">
                        <!-- selection ring uses `outline`, which doesn't affect layout,
                             so picking a chip never nudges the row -->
                        <button v-for="t in tradeableTypes" :key="t" type="button"
                            :aria-label="`Trade for ${titleOf(t)}`" :aria-pressed="getType === t" @click="getType = t"
                            class="rounded-xl cursor-pointer outline-amber-400 transition duration-200 ease-in-out hover:scale-110"
                            :class="getType === t ? 'outline-3' : 'outline-0 opacity-60 hover:opacity-100'">
                            <Card :card-type="t" :selected="true" :large="false" />
                        </button>
                    </div>
                    <div :class="stepperClass">
                        <button type="button" :class="stepButtonSm" :disabled="getQuantity <= 1"
                            aria-label="Decrease quantity wanted" @click="stepGet(-1)">−</button>
                        <div :class="[countClass, 'w-12 text-lg']">{{ getQuantity }}</div>
                        <button type="button" :class="stepButtonSm" aria-label="Increase quantity wanted"
                            @click="stepGet(1)">+</button>
                    </div>
                    <p class="text-xs text-gray-x-light">
                        {{ getType ? titleOf(getType) : 'Pick a card' }}
                    </p>
                </section>

            </div>

            <!-- ── buy / sell ── -->
            <div v-else class="flex items-center" :class="isCompact ? 'gap-4' : 'gap-6'">

                <section class="flex flex-col gap-2">
                    <h3 :class="labelClass">Selected card</h3>
                    <div :class="[wellClass, isCompact ? 'p-2' : 'p-4']">
                        <div :style="{ zoom: previewZoom }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                </section>

                <div class="flex gap-2" :class="isCompact ? 'flex-row' : 'flex-col'">
                    <section class="flex flex-col gap-2">
                        <h3 :class="labelClass">Quantity</h3>
                        <div :class="stepperClass">
                            <button type="button" :class="stepButton" :disabled="quantity <= 1"
                                aria-label="Decrease quantity" @click="step(-1)">−</button>
                            <div :class="[countClass, 'w-20 text-xl']">{{ quantity }}</div>
                            <button type="button" :class="stepButton" :disabled="quantity >= maxQuantity"
                                aria-label="Increase quantity" @click="step(1)">+</button>
                        </div>
                        <p class="text-sm text-gray-x-light">{{ available }} available</p>
                        <!-- says WHY the stepper stopped, rather than letting it
                             silently refuse to go higher -->
                        <p v-if="isBuy && affordable < available" class="text-xs font-bold text-amber-400">
                            You can afford {{ affordable }}
                        </p>
                    </section>

                    <section v-if="showPoints" class="flex flex-col gap-2">
                        <h3 :class="labelClass">{{ type.pointsLabel }}</h3>
                        <div :class="[wellClass, isCompact ? 'p-2 gap-2' : 'p-4 gap-3']">
                            <Card :card-type="'point'" :selected="true" :large="false" />
                            <span class="font-bold text-teal-light tabular-nums text-xl">{{ totalPoints }}</span>
                        </div>
                    </section>
                </div>

            </div>

            <footer class="flex justify-center gap-3"
                :class="isCompact ? 'flex-col-reverse pl-4 border-l-1 border-gray-light' : 'pt-2 border-t-1 border-gray-light'">
                <button type="button" :class="actionButton"
                    class="text-gray-x-light border-2 border-gray-light hover:border-gray-x-light hover:text-gray-2x-light"
                    @click="emit('cancel')">Cancel</button>

                <button type="button" :class="[actionButton, type.confirmClass]" :disabled="!canConfirm"
                    @click="confirm">
                    <span class="flex items-center justify-center gap-2">
                        <span v-if="busy"
                            class="h-4 w-4 animate-spin rounded-full border-2 border-gray-dark/30 border-t-gray-dark"></span>
                        {{ busy ? '' : type.confirm }} {{ busy || isTrade ? '' : quantity }}
                    </span>
                </button>
            </footer>
        </div>
    </div>
</template>