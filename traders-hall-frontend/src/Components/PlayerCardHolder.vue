<script setup lang="ts">
import { computed, ref } from 'vue';

const buttonClass = 'bg-gray-2x-light text-gray-dark w-30 py-2 mx-2 rounded-lg cursor-pointer font-bold hover:scale-105 transition duration-300 ease-in-out'
const indicatorClass = 'py-4 w-50 rounded-xl font-bold border-4 px-4 flex justify-between'
const foodDue = ref(0)
const rentDue = ref(0)
</script>

<template>
    <div>
        <div class="flex flex-col p-4 gap-2 bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem]">
            <div class="flex justify-between items-center">
                <div class="flex items-center">
                    <div class="h-15 w-15 bg-gray-2x-light" :style="{
                        mask: `url(/user.png) no-repeat center / contain`,
                        '-webkit-mask': `url(/user.png) no-repeat center / contain`,
                    }"></div>
                    <h1 class="text-2xl text-gray-2x-light font-bold tracking-wide ml-2">Your Cards</h1>
                </div>
                <div>
                    <button :class="buttonClass" class="hover:bg-emerald-400">Buy</button>
                    <button :class="buttonClass" class="hover:bg-rose-400 ">Sell</button>
                    <button :class="buttonClass" class="hover:bg-amber-300 ">Trade</button>
                </div>
            </div>
            <div class="flex justify-between">
                <div class="p-2 border-1 border-gray-light rounded-[1rem] min-w-[100px]">
                    <slot />
                </div>
                <div class="flex flex-col justify-evenly items-center">
                    <div :class="indicatorClass" class="bg-cream-light text-cream-dark border-cream-dark">
                        <span>Food Due</span>
                        <span >{{ foodDue }} turns</span>
                        <!-- <span :class="foodDue > 2 ? 'text-emerald-400' : foodDue === 2 ? 'text-amber-300' : 'text-rose-400'">{{ foodDue }} turns</span> -->
                    </div>
                    <div :class="indicatorClass" class="bg-purple-light text-purple-dark border-purple-dark">
                        <span >Rent Due</span>
                        <span>{{ rentDue }} turns</span>
                        <!-- <span :class="rentDue > 2 ? 'text-emerald-400' : rentDue === 2 ? 'text-amber-300' : 'text-rose-400'">{{ rentDue }} turns</span> -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>