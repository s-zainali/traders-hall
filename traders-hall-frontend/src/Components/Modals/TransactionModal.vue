<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import Card from '../Card.vue';

const props = defineProps({
    cardType: { type: String, required: true },
    available: { type: Number, default: 99 },
    transactionType: { type: String }
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
    <div class="absolute inset-0 z-[100] flex items-center justify-center p-6 bg-gray-dark/90 backdrop-blur-sm"
        @click.self="emit('cancel')">
        <!-- panel: the dialog is its own surface, not content floating on the blur -->
        <div role="dialog" aria-modal="true" aria-labelledby="transaction-title"
            class="flex gap-6 p-6 w-max max-w-full " :class="transactionType === 'buy' ? 'flex-col' : ''">
            <header class="flex flex-col gap-1" :class="transactionType==='sell' ? 'justify-center items-center' : ''">
                <h2 id="transaction-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">Buy card</h2>
                <p class="text-sm text-gray-x-light">Choose how many you want.</p>
            </header>

            <div class="flex items-stretch gap-6">
                <!-- selected card -->
                <section class="flex flex-col gap-3">
                    <h3 class="text-xs font-bold uppercase tracking-widest text-gray-x-light">Selected card</h3>
                    <div
                        class="flex items-center justify-center p-4 rounded-[1rem] bg-gray-dark border-1 border-gray-light">
                        <Card :card-type="cardType" :selected="true" />
                    </div>
                </section>

                <!-- quantity -->
                <section class="flex flex-col gap-3 justify-center">
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
                </section>
            </div>

            <footer class="flex justify-center gap-3 pt-2 border-t-1 border-gray-light"
                :class="transactionType === 'buy' ? '' : 'flex-col'">
                <button type="button" :class="actionButton"
                    class="text-gray-x-light border-2 border-gray-light hover:border-gray-x-light hover:text-gray-2x-light"
                    @click="emit('cancel')">Cancel</button>

                <button type="button" :class="actionButton"
                    class="bg-emerald-400 text-gray-dark border-2 border-emerald-400 hover:bg-emerald-300 hover:border-emerald-300"
                    @click="emit('confirm', quantity)">Buy {{ quantity }}</button>
            </footer>
        </div>
    </div>
</template>