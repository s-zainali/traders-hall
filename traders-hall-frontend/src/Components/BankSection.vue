<script setup lang="ts">
import Card from './Card.vue';
import { ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';
import BankerCard from './Cards/BankerCard.vue';
import CardDeck from './CardDeck.vue';
import TransactionModal from './Modals/TransactionModal.vue';

const props = defineProps({buyingActive: { default: false }})
const emit = defineEmits(['cancel', 'confirm'])

const buyingType = ref('')

const activeModal = ref('null')

</script>

<template>
    <div
        class="relative p-4 border-2 border-gray-light rounded-[1.5rem] bg-gray-x-dark w-max shrink-0 flex flex-col justify-between overflow-hidden">
        <div class="flex gap-6 justify-between">
            <div>
                <h1 class="text-3xl text-gray-2x-light font-bold pb-4 tracking-wide text-center"> Bank </h1>
                <div class="flex justify-between ml-6">
                    <CardDeck :count-color="'gray-x-light'">
                        <Card :cardType="'point'" v-for="value in 30" />
                    </CardDeck>
                </div>
            </div>
            <BankerCard @activate-modal="activeModal = $event" />
        </div>
        <div class="relative p-4 mt-6 rounded-[1rem] border-1 outline-teal-dark overflow-hidden transition duration-200 ease-in-out"
            :class="props.buyingActive ? 'border-teal-dark outline-4 -outline-offset-4 bg-gray-light/30' : 'border-gray-light outline-0'">
            <TransactionModal v-if="activeModal === 'buy'" :card-type="buyingType" @confirm="" @cancel="activeModal = '', emit('cancel')"/>
            <button v-if="props.buyingActive" @click="emit('cancel')"
                class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

            <h1 class="text-gray-2x-light text-2xl pb-4 font-bold tracking-wide text-center">Cards</h1>
            <div class="grid grid-cols-3 gap-2">
                <CardDeck>
                    <Card :cardType="'house'" @buy="activeModal = 'buy', buyingType = 'house'" :buying="buyingActive"
                        v-for="value in 2" />
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'mansion'" @buy="activeModal = 'buy', buyingType = 'mansion'" :buying="buyingActive"
                        v-for="value in 2" />
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'tower'" @buy="activeModal = 'buy', buyingType = 'tower'" :buying="buyingActive"
                        v-for="value in 2" />
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'rice'" @buy="activeModal = 'buy', buyingType = 'rice'" :buying="buyingActive"
                        v-for="value in 8" />
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'wheat'" @buy="activeModal = 'buy', buyingType = 'wheat'" :buying="buyingActive"
                        v-for="value in 8" />
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'invest'" @buy="activeModal = 'buy', buyingType = 'invest'" :buying="buyingActive"
                        v-for="value in 2" />
                </CardDeck>
            </div>
        </div>

        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = null" />
    </div>
</template>