<script setup lang="ts">
import { computed } from 'vue';
import PointCard from './Cards/Currency/PointCard.vue';
import BankerCard from './Cards/BankerCard.vue';
import RiceCard from './Cards/Food/RiceCard.vue';
import WheatCard from './Cards/Food/WheatCard.vue';
import TowerCard from './Cards/Properties/TowerCard.vue';
import HouseCard from './Cards/Properties/HouseCard.vue';
import MansionCard from './Cards/Properties/MansionCard.vue';
import InvestCard from './Cards/InvestCard.vue';
import { ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';
import CardDeck from './CardDeck.vue';

const activeModal = ref('null')

</script>

<template>
    <div class="overflow-hidden relative p-4 min-w-md border-2 border-gray-light rounded-[1.75rem] bg-gray-x-dark">
        <div class="flex justify-between">
            <div class="w-full">
                <h1 class="text-3xl text-gray-2x-light font-bold pb-4 tracking-wide text-center"> Bank </h1>
                <div class="flex justify-between ml-6">
                    <CardDeck :count-color="'gray-x-light'">
                        <PointCard v-for="value in 30" />
                    </CardDeck>
                </div>
            </div>
            <BankerCard @activate-modal="activeModal = $event" />
        </div>
        <div class="p-4 mt-6 rounded-[1rem] border-1 border-gray-light">
            <h1 class="text-gray-2x-light text-2xl pb-4 font-bold tracking-wide text-center">Cards</h1>
            <div class="grid grid-cols-3">
                <CardDeck>
                    <HouseCard v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <MansionCard v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <TowerCard v-for="value in 2"/>
                </CardDeck>
                <CardDeck>
                    <RiceCard v-for="value in 8"/>
                </CardDeck>
                <CardDeck>
                    <WheatCard v-for="value in 8"/>
                </CardDeck>
                <CardDeck>
                    <InvestCard v-for="value in 2"/>
                </CardDeck>
            </div>
        </div>
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = null" />
    </div>
</template>