<script setup lang="ts">
import { computed } from 'vue';
import Card from './Card.vue';
import { ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';
import BankerCard from './Cards/BankerCard.vue';
import CardDeck from './CardDeck.vue';

const activeModal = ref('null')

</script>

<template>
    <div class="relative p-4 border-2 border-gray-light rounded-[1.5rem] bg-gray-x-dark w-max shrink-0 flex flex-col justify-between overflow-hidden">
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
        <div class="p-4 mt-6 rounded-[1rem] border-1 border-gray-light">
            <h1 class="text-gray-2x-light text-2xl pb-4 font-bold tracking-wide text-center">Cards</h1>
            <div class="grid grid-cols-3 gap-2">
                <CardDeck>
                    <Card :cardType="'house'" v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'mansion'" v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'tower'" v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'rice'" v-for="value in 8"/>
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'wheat'" v-for="value in 8"/>
                </CardDeck>
                <CardDeck>
                    <Card :cardType="'invest'" v-for="value in 2"/>
                </CardDeck>
            </div>
        </div>
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = null" />
    </div>
</template>