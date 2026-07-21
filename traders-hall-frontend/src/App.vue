<script setup>
import BankSection from './Components/BankSection.vue'
import CardDeck from './Components/CardDeck.vue';
import Header from './Components/Header.vue';
import PlayerCardHolder from './Components/PlayerCardHolder.vue';

import PointCard from './Components/Cards/Currency/PointCard.vue';
import WheatCard from './Components/Cards/Food/WheatCard.vue';
import RiceCard from './Components/Cards/Food/RiceCard.vue';

</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark p-6">
        <div class="flex gap-6 justify-between">
            <div class="flex flex-col w-full">
                <Header />
                <div class="flex-grow"></div>
                <PlayerCardHolder>
                    <CardDeck>
                        <PointCard v-for="value in 2"/>
                    </CardDeck>
                    <CardDeck>
                        <WheatCard/>
                    </CardDeck>
                    <CardDeck>
                        <RiceCard/>
                    </CardDeck>
                </PlayerCardHolder>
            </div>
            <BankSection />
        </div>

    </div>
</template>

<style scoped></style>
