<script setup>
import { onMounted, onUnmounted } from 'vue'

const emit = defineEmits(['closeModal', 'select'])

// data-driven so adding a third option is one entry, not another copied button
const options = [
    { key: 'loan', label: 'Loan', description: 'Borrow points from the bank.' },
    { key: 'mortgage', label: 'Mortgage Loan', description: 'Borrow against a property you own.' },
]

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
    <!-- backdrop: click outside to dismiss -->
    <div class="absolute inset-0 z-[100] flex items-center justify-center p-6 bg-gray-dark/90 backdrop-blur-sm"
        @click.self="emit('closeModal')">

        <div role="dialog" aria-modal="true" aria-labelledby="banker-title"
            class="relative flex flex-col gap-6 p-8 w-max max-w-full bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem] shadow-2xl shadow-black/50">

            <button type="button" aria-label="Close" @click="emit('closeModal')"
                class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

            <header class="flex items-center gap-4 pr-10">
                <div class="h-12 w-12 shrink-0 bg-teal-light" :style="{
                    mask: `url(/investor.png) no-repeat center / contain`,
                    '-webkit-mask': `url(/investor.png) no-repeat center / contain`,
                }"></div>
                <div class="flex flex-col gap-1">
                    <h2 id="banker-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">Banker options</h2>
                    <p class="text-sm text-gray-x-light">Select one of the options below.</p>
                </div>
            </header>

            <div class="flex flex-col gap-3 border-t-1 border-gray-light pt-6">
                <button v-for="option in options" :key="option.key" type="button" @click="emit('select', option.key)"
                    class="group flex items-center justify-between gap-8 w-full py-4 px-6 rounded-xl cursor-pointer
                           bg-gray-dark border-2 border-gray-light text-left transition duration-200 ease-in-out
                           hover:border-teal-light hover:bg-teal-dark/20
                           focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                    <span class="flex flex-col gap-0.5">
                        <span class="text-lg font-bold text-gray-2x-light group-hover:text-teal-light transition duration-200 ease-in-out">
                            {{ option.label }}
                        </span>
                        <span class="text-sm text-gray-x-light">{{ option.description }}</span>
                    </span>
                    <span class="text-2xl font-bold text-gray-light group-hover:text-teal-light group-hover:translate-x-1 transition duration-200 ease-in-out">›</span>
                </button>
            </div>
        </div>
    </div>
</template>