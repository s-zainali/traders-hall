<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import Card, { cards } from '../Card.vue';

const props = defineProps({
    cardType: { type: String, required: true },
    available: { type: Number, default: 99 },
    transactionType: { type: String },
})

const emit = defineEmits(['confirm', 'cancel'])

const quantity = ref(1)

const canDecrease = computed(() => quantity.value > 1)
const canIncrease = computed(() => quantity.value < props.available)

function step(delta: number) {
    quantity.value = Math.min(props.available, Math.max(1, quantity.value + delta))
}

// Escape closes, like any modal
function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') emit('cancel')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const isSell = computed(() => props.transactionType === 'sell')

// Unlike `scale`, `zoom` participates in layout: the wrapper's measured box
// shrinks too, so the modal actually gets shorter instead of just drawing
// smaller inside a full-height box. Tune this to taste.
const PREVIEW_ZOOM = 0.6
const previewZoom = computed(() => (isSell.value ? PREVIEW_ZOOM : 1))

// cost comes from the selected card itself, not from the parent
const unitPoints = computed(() => cards[props.cardType]?.cost ?? 0)
const totalPoints = computed(() => unitPoints.value * quantity.value)

const heading = computed(() => (isSell.value ? 'Sell card' : 'Buy card'))
const subheading = computed(() =>
    isSell.value ? 'Choose how many to sell.' : 'Choose how many you want.')
const confirmLabel = computed(() => (isSell.value ? 'Sell' : 'Buy'))
const pointsLabel = computed(() => (isSell.value ? 'Points earned' : 'Cost'))

// full literal strings so Tailwind's scanner picks both variants up
const confirmClass = computed(() =>
    isSell.value
        ? 'bg-rose-400 text-gray-dark border-2 border-rose-400 hover:bg-rose-300 hover:border-rose-300'
        : 'bg-emerald-400 text-gray-dark border-2 border-emerald-400 hover:bg-emerald-300 hover:border-emerald-300')

const wellClass =
    'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'

const stepButton =
    'w-10 h-10 flex items-center justify-center text-2xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'

const actionButton =
    'w-25 py-3 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'
</script>

<template>
    <!-- backdrop: click outside to dismiss -->
    <div class="absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 backdrop-blur-sm"
        :class="isSell ? 'p-3' : 'p-3'" @click.self="emit('cancel')">

        <div role="dialog" aria-modal="true" aria-labelledby="transaction-title" class="flex max-w-full" :class="transactionType === 'buy'
            ? 'flex-col gap-6 p-6 w-max'
            : isSell ? 'gap-4 p-4 w-full justify-between items-center' : 'gap-6 p-4 h-full'">

            <header class="flex flex-col gap-1" :class="isSell ? 'justify-center items-start' : ''">
                <h2 id="transaction-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">{{ heading }}
                </h2>
                <p class="text-sm text-gray-x-light">{{ subheading }}</p>
            </header>

            <div class="flex items-center" :class="isSell ? 'gap-4' : 'gap-6'">
                <!-- selected card -->
                <section class="flex flex-col gap-2">
                    <h3 class="text-xs font-bold uppercase tracking-widest text-gray-x-light">Selected card</h3>
                    <div :class="[wellClass, isSell ? 'p-2' : 'p-4']">
                        <!-- zoom shrinks the layout box, not just the pixels -->
                        <div :style="{ zoom: previewZoom }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                </section>

                <!-- quantity -->
                <section class="flex flex-col gap-3 justify-center">
                    <div>
                        <h3 class="text-xs font-bold uppercase tracking-widest text-gray-x-light">Quantity</h3>

                        <div class="flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max">
                            <button type="button" :class="stepButton" :disabled="!canDecrease"
                                aria-label="Decrease quantity" @click="step(-1)">−</button>

                            <div
                                class="w-20 flex items-center justify-center text-xl font-bold text-gray-2x-light bg-gray-dark tabular-nums">
                                {{ quantity }}
                            </div>

                            <button type="button" :class="stepButton" :disabled="!canIncrease"
                                aria-label="Increase quantity" @click="step(1)">+</button>
                        </div>

                        <p class="text-sm text-gray-x-light">{{ available }} available</p>
                    </div>
                    <div>
                        <section v-if="unitPoints > 0" class="flex flex-col gap-2">
                            <h3 class="text-xs font-bold uppercase tracking-widest text-gray-x-light">{{ pointsLabel }}
                            </h3>
                            <div :class="[wellClass, isSell ? 'p-2 gap-2' : 'p-4 gap-3']">
                                <Card :card-type="'point'" :selected="true" :large="false" />
                                <span class="font-bold text-teal-light tabular-nums"
                                    :class="isSell ? 'text-xl' : 'text-2xl'">{{ totalPoints }}</span>
                            </div>
                        </section>
                    </div>

                </section>
            </div>

            <footer class="flex justify-center gap-3"
                :class="isSell ? 'flex-col pl-4 border-l-1 border-gray-light' : 'pt-2 border-t-1 border-gray-light'">
                <button type="button" :class="actionButton"
                    class="text-gray-x-light border-2 border-gray-light hover:border-gray-x-light hover:text-gray-2x-light"
                    @click="emit('cancel')">Cancel</button>

                <button type="button" :class="[actionButton, confirmClass]" @click="emit('confirm', quantity)">{{
                    confirmLabel }} {{ quantity }}</button>
            </footer>
        </div>
    </div>
</template>