<script setup lang="ts">
import Card from './Card.vue';
import { reactive, ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';
import BankerCard from './Cards/BankerCard.vue';
import CardDeck from './CardDeck.vue';
import TransactionModal from './Modals/TransactionModal.vue';

// `buyingActive` had no `type`, so Vue skipped Boolean casting on it
const props = defineProps({ buyingActive: { type: Boolean, default: false } })
const emit = defineEmits(['cancel', 'confirm'])

// six near-identical CardDeck blocks collapsed into data
const bankCards = reactive({
    'house': 2,
    'mansion': 2,
    'tower': 2,
    'rice': 8,
    'wheat': 8,
    'invest': 2,
})

const buyingType = ref('')
const activeModal = ref('')   // was ref('null') — the string, not the value

function openBuy(type: string) {
    buyingType.value = type
    activeModal.value = 'buy'
}

function onConfirm(payload) {
    emit('confirm', { type: buyingType.value, payload })
    activeModal.value = ''
    emit('cancel')
}
</script>

<template>
    <div
        class="relative p-4 border-2 border-gray-light rounded-[1.5rem] bg-gray-x-dark w-max shrink-0 flex flex-col justify-between overflow-hidden">

        <!-- modals sit at the panel root so they overlay the whole section and
             aren't clipped by the cards well's overflow-hidden -->
        <TransactionModal v-if="activeModal === 'buy'" :transaction-type="'buy'" :card-type="buyingType"
            :available="bankCards[buyingType] ?? 1" @confirm="onConfirm" @cancel="activeModal = ''" />
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = ''" />

        <div class="flex gap-6 justify-between">
            <div>
                <h1 class="text-3xl text-gray-2x-light font-bold pb-4 tracking-wide text-center"> Bank </h1>
                <div class="flex justify-between ml-6">
                    <CardDeck>
                        <Card v-for="n in 30" :key="n" :card-type="'point'" />
                    </CardDeck>
                </div>
            </div>
            <BankerCard @activate-modal="activeModal = $event" />
        </div>

        <div class="relative p-4 mt-6 rounded-[1rem] border-1 outline-teal-light overflow-hidden transition duration-200 ease-in-out"
            :class="buyingActive ? 'border-teal-light outline-4 -outline-offset-4 bg-gray-light/30' : 'border-gray-light outline-0'">
            <button v-if="buyingActive" @click="emit('cancel')"
                class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

            <h1 class="text-gray-2x-light text-2xl pb-4 font-bold tracking-wide text-center">Cards</h1>
            <div class="grid grid-cols-3 gap-2">
                <CardDeck v-for="(count, type) in bankCards" :key="type">
                    <Card v-for="n in count" :key="`${type}-${n}`" :card-type="type" :buying="buyingActive"
                        @buy="openBuy(type)" />
                </CardDeck>
            </div>
        </div>
    </div>
</template>