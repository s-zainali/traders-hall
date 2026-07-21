<script setup lang="ts">
import { computed } from 'vue';
import PointCard from './Cards/Currency/PointCard.vue';
import BankerCard from './Cards/BankerCard.vue';
import { ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';

const activeModal = ref('null')


</script>

<template>
    <div class="overflow-hidden relative p-6 min-w-lg border-2 border-gray-light rounded-[1rem]">
        <h1 class="text-3xl text-gray-2x-light font-bold pb-6"> Bank </h1>
        <div class="flex justify-between">
            <PointCard />
            <BankerCard @activate-modal="activeModal = $event"/>
        </div>
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = null"/>
    </div>
</template>