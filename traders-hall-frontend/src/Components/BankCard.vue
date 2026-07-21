<script setup lang="ts">
import { computed } from 'vue';
import PointCard from './Cards/Currency/PointCard.vue';

</script>

<template>
    <div class="p-6 min-w-lg border-2 border-gray-light rounded-[1rem]">
        <h1 class="text-3xl text-gray-x-light font-bold pb-6"> Bank </h1>
        <div class="flex justify-between">
            <PointCard />
            <div class="p-4 border-2 border-gray-x-light rounded-[0.75rem] flex flex-col justify-center">
                <div class="">
                    <!-- inner stays a pure mask -->
                    <div class="h-30 w-30 bg-gray-x-light" :style="{
                        mask: `url(/accountant.png) no-repeat center / contain`,
                        '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
                    }"></div>
                </div>
                <span class="text-gray-x-light font-bold tracking-wide">Loan Manager</span>
                <button class="bg-gray-x-light px-4 py-2 mt-4 rounded-lg hover:cursor-pointer hover:scale-105 transition duration-300 ease-in-out">Interact</button>
            </div>
        </div>
    </div>
</template>