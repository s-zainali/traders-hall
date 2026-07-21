<script setup lang="ts">
import { computed } from 'vue';
import PointCard from './Cards/Currency/PointCard.vue';

</script>

<template>
    <div class="p-6 min-w-lg border-2 border-gray-light rounded-[1rem]">
        <h1 class="text-3xl text-cream-light font-bold pb-6"> Bank </h1>
        <div class="flex">
            <PointCard />
            <div class="h-full w-full">
                <!-- inner stays a pure mask -->
                <div class="h-full w-full bg-gray-x-light" :style="{
                    mask: `url(/accountant.png) no-repeat center / contain`,
                    '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
                }"></div>
            </div>
        </div>
    </div>
</template>