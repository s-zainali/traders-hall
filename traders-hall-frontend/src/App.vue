<script setup>
import Card from './Components/Card.vue';
import RiceCard from './Components/Cards/Food/RiceCard.vue';
import WheatCard from './Components/Cards/Food/WheatCard.vue';
import TowerCard from './Components/Cards/Properties/TowerCard.vue';
import HouseCard from './Components/Cards/Properties/HouseCard.vue';
import MansionCard from './Components/Cards/Properties/MansionCard.vue';
import InvestCard from './Components/Cards/InvestCard.vue';
import BankCard from './Components/BankCard.vue';

</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark p-6">
        <div class="flex gap-6">
            <div class="p-6 rounded-[1rem] border-2 border-gray-light">
                <h1 class="text-cream-light text-3xl pb-6 font-bold">Cards</h1>
                <div class="flex gap-4 flex-wrap">
                    <HouseCard />
                    <MansionCard />
                    <TowerCard />
                    <RiceCard />
                    <WheatCard />
                    <InvestCard />
                </div>
            </div>
            <BankCard />
        </div>
    </div>
</template>

<style scoped></style>
