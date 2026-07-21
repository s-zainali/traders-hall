<script setup>
const emit = defineEmits(['closeModal'])
</script>
<template>
    <div class="absolute w-full h-full top-0 left-0 bg-gray-light/40 backdrop-blur-sm">
        <div class="relative w-full h-full flex justify-center items-center">
            <span class="absolute top-0 right-0 p-4 text-gray-x-light inline-block leading-none hover:cursor-pointer" @click="emit('closeModal')">🗙</span>
            <button>Loan</button>
            <button>Mortgage Loan</button>
        </div>
    </div>
</template>