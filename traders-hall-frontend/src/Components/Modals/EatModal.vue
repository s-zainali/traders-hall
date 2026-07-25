<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * Eating a food card.
 *
 * Its own component rather than a fourth branch inside TransactionModal: that
 * component is about moving cards for value — it carries a bank/player
 * destination toggle, a price stepper, a trade picker and an affordability
 * check, none of which mean anything here. A meal has one card, one count and
 * one outcome. Bolting it on would have added a fifth mode to a file that
 * already has three.
 *
 * The class vocabulary IS shared, deliberately, so the two read as siblings.
 */
const props = defineProps({
    cardType: { type: String, required: true },
    // how many of this card the player holds. The server checks the FREE count
    // (minus offers and collateral), so this is a ceiling, not the truth.
    available: { type: Number, default: 1 },
    // turns of nutrition remaining before the player must eat again
    foodDue: { type: Number, default: 0 },
    busy: { type: Boolean, default: false },
    // rendered as an anchored popover inside the card holder, matching the
    // sell and trade flows
    popover: { type: Boolean, default: true },
})

const emit = defineEmits(['confirm', 'cancel'])

const cardTypes = useCardTypesStore()

const quantity = ref(1)

const card = computed(() => cardTypes.get(props.cardType))
const title = computed(() => card.value?.title ?? props.cardType)

// Nutrition lives on the card type (rice 2, wheat 5), so rebalancing food is a
// migration rather than a frontend edit.
const nutrition = computed(() => card.value?.nutritionTurns ?? 0)

const gained = computed(() => nutrition.value * quantity.value)

// Nutrition ADDS to what is left rather than replacing it, so eating early
// stockpiles instead of wasting. The projected total is shown because that is
// the number the player is actually deciding about.
const projected = computed(() => props.foodDue + gained.value)

const maxQuantity = computed(() => Math.max(1, props.available))

function step(delta) {
    quantity.value = Math.min(maxQuantity.value, Math.max(1, quantity.value + delta))
}

// The hand moves under this component while it is open — an opponent settling a
// trade, or upkeep running — so a stepper left above the new ceiling would
// submit an impossible amount.
watch(maxQuantity, (max) => {
    quantity.value = Math.min(quantity.value, max)
})

function onKeydown(e) {
    if (e.key === 'Escape') emit('cancel')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const canConfirm = computed(
    () => !props.busy && nutrition.value > 0 && quantity.value >= 1
)

/* ── class vocabulary, shared with TransactionModal ───────────────── */
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'

const wellClass =
    'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'

const stepperClass = 'flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max'

const stepButton =
    'w-10 h-10 flex items-center justify-center text-2xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'

const countClass =
    'flex items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'

const actionButton =
    'min-w-24 px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:opacity-40 disabled:cursor-not-allowed ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'

// Cream is the food palette across the app — the FOOD stat box, the rice and
// wheat card faces — so the confirm button belongs to it too.
const eatClass =
    'bg-cream-light text-gray-dark border-2 border-cream-light hover:brightness-110'
</script>

<template>
    <div :class="popover
        ? ''
        : 'absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 p-4 backdrop-blur-sm'"
        @click.self="popover || emit('cancel')">

        <div role="dialog" aria-modal="true" aria-labelledby="eat-title"
            class="relative flex max-w-full flex-col gap-5"
            :class="popover
                ? 'rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-6 shadow-2xl shadow-black/60'
                : 'w-max p-4'">

            <button type="button" aria-label="Close" @click="emit('cancel')"
                class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">✕</button>

            <header class="flex flex-col gap-0.5 pr-10">
                <h2 id="eat-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">Eat</h2>
                <p class="text-sm text-gray-x-light">
                    {{ title }} keeps you fed for {{ nutrition }} more
                    {{ nutrition === 1 ? 'turn' : 'turns' }}.
                </p>
            </header>

            <div class="flex items-center gap-5">
                <section class="flex flex-col gap-2">
                    <h3 :class="labelClass">Card</h3>
                    <div :class="[wellClass, 'p-4']">
                        <div :style="{ zoom: 0.85 }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                </section>

                <div class="flex flex-col gap-3">
                    <section class="flex flex-col gap-2">
                        <h3 :class="labelClass">How many</h3>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="quantity <= 1"
                                aria-label="Eat fewer" @click="step(-1)">−</button>
                            <div :class="[countClass, 'w-14 text-lg']">{{ quantity }}</div>
                            <button type="button" :class="stepButton" :disabled="quantity >= maxQuantity"
                                aria-label="Eat more" @click="step(1)">+</button>
                        </div>
                        <p class="text-xs text-gray-x-light">{{ available }} in hand</p>
                    </section>

                    <!--
                        Before and after, not just the gain. Nutrition stacks on
                        whatever is left, so "+10" alone does not tell the player
                        the thing they actually want to know.
                    -->
                    <section class="flex flex-col gap-2">
                        <h3 :class="labelClass">Food</h3>
                        <div :class="[wellClass, 'gap-2 px-3 py-2']">
                            <span class="text-lg font-bold tabular-nums text-gray-x-light">{{ foodDue }}</span>
                            <span class="text-cream-light">→</span>
                            <span class="text-lg font-bold tabular-nums text-cream-light">{{ projected }}</span>
                        </div>
                    </section>
                </div>
            </div>

            <p class="rounded-xl border-2 border-cream-light/40 bg-cream-light/10 px-4 py-2 text-center text-sm font-bold text-gray-2x-light">
                {{ quantity }}× {{ title }}
                <span class="px-2 text-cream-light">→</span>
                fed for {{ projected }} {{ projected === 1 ? 'turn' : 'turns' }}
            </p>

            <footer class="flex items-center justify-end gap-2 border-t-1 border-gray-light pt-4">
                <button type="button" :class="actionButton"
                    class="border-2 border-gray-light text-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light"
                    @click="emit('cancel')">Cancel</button>

                <button type="button" :class="[actionButton, eatClass]" :disabled="!canConfirm"
                    @click="emit('confirm', { cardType, quantity })">
                    <span class="flex items-center justify-center gap-2">
                        <span v-if="busy"
                            class="h-4 w-4 animate-spin rounded-full border-2 border-gray-dark/30 border-t-gray-dark"></span>
                        {{ busy ? '' : 'Eat' }}
                    </span>
                </button>
            </footer>
        </div>
    </div>
</template>