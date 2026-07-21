<script setup>
const emit = defineEmits(['activateModal'])
</script>

<template>
    <div class="absolute top-0 right-0 mt-4 mr-4 p-4 border-2 border-gray-x-light rounded-[1rem] flex flex-col justify-center h-min">
        <div class="flex justify-center">
            <!-- inner stays a pure mask -->
            <div class="h-30 w-30 bg-gray-2x-light" :style="{
                mask: `url(/accountant.png) no-repeat center / contain`,
                '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
            }"></div>
        </div>
        <span class="text-gray-2x-light font-bold tracking-wide">Loan Manager</span>
        <button
            class="font-bold text-gray-dark bg-gray-2x-light px-4 py-2 mt-4 rounded-lg hover:cursor-pointer hover:bg-teal-dark hover:text-gray-2x-light transition duration-300 ease-in-out" @click="$emit('activateModal', 'bankerModal')">Interact</button>
    </div>
</template>