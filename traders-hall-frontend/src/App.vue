<script setup>
import BankSection from './Components/BankSection.vue'
import CardDeck from './Components/CardDeck.vue';
import Header from './Components/Header.vue';
import PlayerCardHolder from './Components/PlayerCardHolder.vue';

</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark p-6 flex gap-6">
        <div class="flex flex-col w-full">
            <Header />
            <div class="flex-grow"></div>
            <PlayerCardHolder/>
        </div>
        <BankSection />
    </div>
</template>

<style scoped></style>
