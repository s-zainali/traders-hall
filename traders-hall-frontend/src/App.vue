<script setup>
import BankSection from './Components/BankSection.vue'
import Header from './Components/Header.vue';

</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark p-6">
        <div class="flex gap-6 justify-between">
            <Header />
            <BankSection />
        </div>
    </div>
</template>

<style scoped></style>
