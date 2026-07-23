<script setup>
import { computed, reactive, ref } from 'vue';
import Card from './Card.vue';
import CardDeck from './CardDeck.vue';
import TransactionModal from './Modals/TransactionModal.vue';

const props = defineProps({
    playerType: { type: String, default: 'player' },
    activeAction: { type: String, default: '' },
    playerName: { type: String, default: 'Player' },
})
const emit = defineEmits(['buy', 'sell', 'trade', 'cancelOperation', 'transaction'])

// NOTE: no bg-* here. The background is chosen per-state below so exactly one
// background utility is ever present, avoiding a stylesheet-order conflict.
const buttonClass = 'w-18 py-2 rounded-lg cursor-pointer font-bold hover:scale-105 transition duration-300 ease-in-out hover:text-gray-2x-light'
const indicatorClass = 'py-2 w-30 rounded-xl font-bold border-4 px-4 flex flex-col justify-between'

const actions = [
    { key: 'buy', label: 'Buy', hover: 'hover:bg-emerald-400/50', active: 'bg-emerald-400/60 text-gray-2x-light' },
    { key: 'sell', label: 'Sell', hover: 'hover:bg-rose-400/70', active: 'bg-rose-400/60 text-gray-2x-light' },
    { key: 'trade', label: 'Trade', hover: 'hover:bg-amber-300/70', active: 'bg-amber-300/60 text-gray-2x-light' },
]

// per-action chrome for the hand well and the panel border; full literal class
// strings so Tailwind generates them
const HAND_STATES = {
    sell: {
        well: 'outline-rose-400/50 border-rose-400/5 outline-4 -outline-offset-4 bg-gray-light/30',
        panel: 'border-rose-400/50',
    },
    trade: {
        well: 'outline-amber-400/50 border-amber-400/5 outline-4 -outline-offset-4 bg-gray-light/30',
        panel: 'border-amber-400/50',
    },
}
const handState = computed(() => HAND_STATES[props.activeAction] ?? null)

const playerCards = reactive({
    'house': 2,
    'mansion': 0,
    'tower': 0,
    'invest': 1,
    'wheat': 0,
    'rice': 1,
})

// ONE ref for the card under action. Previously sell wrote `sellingType` and
// trade wrote `tradingType`, but the modal only ever read `sellingType` — so
// trading always showed whatever sell had left behind.
const selectedType = ref('')

const points = ref(2)

const foodDue = ref(0)
const rentDue = ref(0)
const loanDue = ref(0)

const onRent = ref(false)
const residence = ref('')

const activeModal = ref('')

// the action already says whether this is a sell or a trade
function openModal(type) {
    selectedType.value = type
    activeModal.value = props.activeAction
}

function onConfirm(payload) {
    emit('transaction', { action: activeModal.value, type: selectedType.value, payload })
    activeModal.value = ''
    emit('cancelOperation')
}

</script>

<template>
    <div class="relative flex flex-col p-4 gap-2 bg-gray-x-dark border-2 rounded-[1.5rem] overflow-hidden"
        :class="activeModal && handState ? handState.panel : 'border-gray-light'">
        <TransactionModal v-if="activeModal !== ''" :transaction-type="activeModal" :card-type="selectedType"
            :available="playerCards[selectedType] ?? 1" @confirm="onConfirm" @cancel="activeModal = ''" />
        <div class="flex justify-between items-center gap-4" :class="playerType === 'player' ? '' : 'flex-col-reverse'">
            <div class="flex items-center">
                <div class="bg-gray-2x-light" :class="playerType === 'player' ? 'h-15 w-15' : 'h-5 w-5'" :style="{
                    mask: `url(/user.png) no-repeat center / contain`,
                    '-webkit-mask': `url(/user.png) no-repeat center / contain`,
                }"></div>
                <h1 class="text-2xl text-gray-2x-light font-bold tracking-wide ml-2"
                    :class="playerType === 'player' ? '' : 'text-xl'">{{ playerType === 'player' ? 'Your' : '' }} Cards
                </h1>
            </div>
            <div class="flex gap-4 items-center"
                :class="playerType === 'player' ? 'justify-end' : 'w-full justify-between'">
                <CardDeck :content-small="true">
                    <Card v-for="n in points" :key="n" :card-type="'point'" :large="false" />
                </CardDeck>
                <h1 v-if="playerType !== 'player'"
                    class="text-lg px-2 py-2 text-gray-2x-light font-bold tracking-wide">{{ playerName }}</h1>
                <div class="flex px-2  bg-purple-dark border-4 border-purple-light rounded-[1rem]">
                    <span v-if="onRent">On Rent</span>
                    <div class="flex gap-2 items-center">
                        <span v-if="playerType === 'player'"
                            class="font-bold text-sm text-purple-light ">Residence</span>
                        <div class="-mx-2">
                            <Card v-if="residence !== ''" :selected="true" :card-type="residence" :large="false" />
                            <div v-else class="h-9 w-9 bg-purple-light m-1" :style="{
                                mask: `url(/cancel.png) no-repeat center / contain`,
                                '-webkit-mask': `url(/cancel.png) no-repeat center / contain`,
                            }"></div>
                        </div>
                    </div>
                </div>
                <div v-if="playerType === 'player'" class="flex gap-4">
                    <button v-for="action in actions" :key="action.key" :class="[
                        buttonClass,
                        action.hover,
                        activeAction === action.key ? action.active : 'text-gray-dark bg-gray-2x-light',
                    ]" @click="activeAction === '' ? $emit(action.key) : ''">{{ action.label }}</button>
                    <button v-if="playerType === 'player'"
                        class="bg-rose-400/50 w-30 py-3 rounded-xl font-bold hover:bg-rose-500/50 cursor-pointer transition duration-300 ease-in-out hover:scale-110 text-gray-2x-light">End Turn</button>
                </div>
            </div>
        </div>
        <div class="flex justify-between gap-4 items-center">
            <div class="relative p-2 border-1 rounded-[1rem] min-w-[100px] flex justify-between px-4 w-full max-w-md overflow-hidden transition duration-300 ease-in-out"
                :class="handState ? handState.well : 'border-gray-light outline-0'">
                <button v-if="handState" @click="emit('cancelOperation')"
                    class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>
                <div class="flex gap-2">
                    <!-- :key is required here: without it Vue patches these decks in
                         place by index, which mixes card types between decks -->
                    <CardDeck v-for="type in Object.keys(playerCards)" :key="type" :content-small="true">
                        <Card v-for="n in playerCards[type]" :key="`${type}-${n}`" :card-type="type" :large="false"
                            :class="handState ? 'cursor-pointer' : ''" :selling="activeAction === 'sell'"
                            :trading="activeAction === 'trade'" @sell="openModal(type)" @trade="openModal(type)" />
                    </CardDeck>
                </div>
                <!-- <button class="w-5 px-4 hover:cursor-pointer">
                    <div class="h-5 w-5 bg-gray-x-light" :style="{
                        mask: `url(/up-arrow.png) no-repeat center / contain`,
                        '-webkit-mask': `url(/up-arrow.png) no-repeat center / contain`,
                    }"></div>
                </button> -->
            </div>

            <div v-if="playerType === 'player'" class="flex justify-evenly items-center gap-4">
                <div :class="indicatorClass" class="bg-cream-dark text-cream-light border-cream-light">
                    <span>Food Due</span>
                    <span>{{ foodDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="bg-purple-dark text-purple-light border-purple-light">
                    <span>Rent Due</span>
                    <span>{{ rentDue }} turns</span>
                </div>
                <div :class="indicatorClass" class="bg-teal-dark text-teal-light border-teal-light">
                    <span>Loan Due</span>
                    <span>{{ loanDue }} turns</span>
                </div>
            </div>
        </div>
    </div>
</template>