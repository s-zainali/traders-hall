<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import Card from './Card.vue';
import CardDeck from './CardDeck.vue';

const buttonClass = 'bg-gray-2x-light text-gray-dark w-21 py-2 mx-2 rounded-lg cursor-pointer font-bold hover:scale-105 transition duration-300 ease-in-out'
const indicatorClass = 'py-2 w-35 rounded-xl font-bold border-4 px-4 flex flex-col justify-between'
const playerCards = reactive({
    'house': 5,
    'mansion': 5,
    'tower': 5,
    'invest': 5,
    'wheat': 5,
    'rice': 5,
    'point': 5,
})

const foodDue = ref(0)
const rentDue = ref(0)

const onRent = ref(false)
const residence = ref('house')

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
                <div class="flex gap-8 items-center">
                    <div class="flex px-4 py-2 bg-purple-dark border-4 border-purple-light rounded-xl">
                        <span v-if="onRent">On Rent</span>
                        <div class="flex gap-4">
                            <span class="font-bold text-lg text-purple-light">Current Residence</span>
                            <div>
                                <div></div>
                                <Card v-if="residence !== ''" :card-type="residence" :large="false" />
                                <div v-else class="h-7 w-7 bg-purple-light" :style="{
                                    mask: `url(/cancel.png) no-repeat center / contain`,
                                    '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                                }"></div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <button :class="buttonClass" class="hover:bg-emerald-400">Buy</button>
                        <button :class="buttonClass" class="hover:bg-rose-400 ">Sell</button>
                        <button :class="buttonClass" class="hover:bg-amber-300 ">Trade</button>
                    </div>
                </div>
            </div>
            <div class="flex justify-between">
                <div class="p-2 border-1 border-gray-light rounded-[1rem] min-w-[100px] flex gap-2 px-4">
                    <CardDeck v-for="type in Object.keys(playerCards)" :content-small="true">
                        <Card v-for="count in playerCards[type]" :card-type="type" :large="false" />
                    </CardDeck>
                </div>
                <div class="flex justify-evenly items-center gap-4">
                    <div :class="indicatorClass" class="bg-cream-dark text-cream-light border-cream-light">
                        <span>Food Due</span>
                        <span>{{ foodDue }} turns</span>
                        <!-- <span :class="foodDue > 2 ? 'text-emerald-400' : foodDue === 2 ? 'text-amber-300' : 'text-rose-400'">{{ foodDue }} turns</span> -->
                    </div>
                    <div :class="indicatorClass" class="bg-purple-dark text-purple-light border-purple-light">
                        <span>Rent Due</span>
                        <span>{{ rentDue }} turns</span>
                        <!-- <span :class="rentDue > 2 ? 'text-emerald-400' : rentDue === 2 ? 'text-amber-300' : 'text-rose-400'">{{ rentDue }} turns</span> -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>