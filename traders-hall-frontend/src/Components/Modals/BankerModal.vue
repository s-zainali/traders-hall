<script setup>
const emit = defineEmits(['closeModal'])
const buttonClass = 'py-6 w-60 bg-gray-2x-light text-gray-dark rounded-lg hover:bg-teal-dark hover:text-gray-2x-light hover:cursor-pointer transition duration-300 ease-in-out font-bold text-xl'
</script>
<template>
    <div class="absolute w-full h-full top-0 left-0 bg-gray-light/40 backdrop-blur-sm">
        <div class="relative w-full h-full">
            <span class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light inline-block leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out" @click="emit('closeModal')">🗙</span>
            <div>
                <h2 class="text-2xl font-bold text-gray-2x-light p-8 pb-2 tracking-widest">Banker Options</h2>
                <p class="text-sm tracking-widest pl-8 text-gray-2x-light">Select from one of the options below</p>
            </div>
            <div class=" absolute top-0 left-0 flex flex-col w-full h-full gap-6 flex justify-center items-center">
                <button :class="buttonClass">Loan</button>
                <button :class="buttonClass">Mortgage Loan</button>
            </div>
        </div>
    </div>
</template>