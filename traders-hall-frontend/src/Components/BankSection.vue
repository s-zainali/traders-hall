<script setup lang="ts">
import { computed } from 'vue';
import PointCard from './Cards/Currency/PointCard.vue';
import BankerCard from './Cards/BankerCard.vue';
import Card from './Card.vue';
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
    <div class=" max-w-sm overflow-hidden relative p-6 min-w-lg border-2 border-gray-light rounded-[2rem]">
        <h1 class="text-3xl text-gray-2x-light font-bold pb-6"> Bank </h1>
        <div class="flex justify-between">
            <CardDeck>
                <PointCard v-for="value in 30" />
            </CardDeck>
            <BankerCard @activate-modal="activeModal = $event" />
        </div>
        <div class="p-6 rounded-[1rem] border-2 border-gray-light">
            <h1 class="text-gray-2x-light text-3xl pb-6 font-bold">Cards</h1>
            <div class="flex gap-4 flex-wrap">
                <HouseCard />
                <MansionCard />
                <TowerCard />
                <RiceCard />
                <WheatCard />
                <InvestCard />
            </div>
        </div>
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = null" />
    </div>
</template>