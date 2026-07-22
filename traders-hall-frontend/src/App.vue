<script setup>
import { ref } from 'vue';
import BankSection from './Components/BankSection.vue'
import CardDeck from './Components/CardDeck.vue';
import Header from './Components/Header.vue';
import PlayerCardHolder from './Components/PlayerCardHolder.vue';

const buyingActive = ref(false)
const sellActive = ref(false)
const tradeActive = ref(false)

</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark p-6 flex gap-6">
        <div class="flex flex-col w-full">
            <Header />
            <div class="flex-grow py-4">
                <div class="flex gap-4 w-full ">
                    <PlayerCardHolder v-for="value in 3" :player-type="'opponent'" class="flex-1" />
                </div>
            </div>
            <PlayerCardHolder :active-action="buyingActive ? 'buy' : sellActive ? 'sell' : tradeActive ? 'trade' : ''"
                @buy="buyingActive = true" @sell="sellActive = true" @trade="tradeActive = true" @cancel-operation="sellActive=false,tradeActive=false" />
        </div>
        <BankSection v-model:buying-active="buyingActive" @cancel="buyingActive = false" />
    </div>
</template>

<style scoped></style>