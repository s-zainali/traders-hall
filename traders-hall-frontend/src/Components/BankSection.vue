<script setup>
import Card from './Card.vue';
import { computed, ref } from 'vue';
import BankerModal from './Modals/BankerModal.vue';
import BankerCard from './Cards/BankerCard.vue';
import CardDeck from './CardDeck.vue';
import TransactionModal from './Modals/TransactionModal.vue';

const props = defineProps({
    buyingActive: { type: Boolean, default: false },
    // { cardType: quantity } straight from the projection. Was a hardcoded
    // `reactive` literal here, which meant every player saw a different bank.
    pools: { type: Object, default: () => ({}) },
    // an action is in flight; the modal locks so a double-click cannot fire twice
    busy: { type: Boolean, default: false },
    // the buyer's balance, so the modal can cap the stepper at what they can afford
    points: { type: Number, default: 0 },
})
const emit = defineEmits(['cancel', 'confirm'])

// Points are the bank's cash, shown separately from the card grid.
const pointStock = computed(() => props.pools.point ?? 0)

/*
  Buyable stock, in a stable order. Object key order follows insertion, which
  is whatever the server serialised — so an explicit order stops the grid
  reshuffling between polls.
*/
const ORDER = ['house', 'mansion', 'tower', 'rice', 'wheat', 'invest']
const cardStock = computed(() =>
    ORDER.filter((type) => (props.pools[type] ?? 0) > 0).map((type) => ({
        type,
        count: props.pools[type],
    }))
)

const buyingType = ref('')
const activeModal = ref('')

function openBuy(type) {
    buyingType.value = type
    activeModal.value = 'buy'
}

function onConfirm(quantity) {
    // GameView needs both halves; it has no way to know which deck was clicked.
    emit('confirm', { type: buyingType.value, quantity })
    activeModal.value = ''
}
</script>

<template>
    <div
        class="relative p-4 border-2 border-gray-light rounded-[1.5rem] bg-gray-x-dark w-max shrink-0 flex flex-col justify-between overflow-hidden h-full">

        <!-- modals sit at the panel root so they overlay the whole section and
             aren't clipped by the cards well's overflow-hidden -->
        <TransactionModal v-if="activeModal === 'buy'" :transaction-type="'buy'" :card-type="buyingType"
            :available="pools[buyingType] ?? 1" :points="points" :busy="busy" @confirm="onConfirm"
            @cancel="activeModal = ''" />
        <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = ''" />

        <div class="flex gap-6 justify-between">
            <div>
                <h1 class="text-3xl text-gray-2x-light font-bold pb-4 tracking-wide text-center"> Bank </h1>
                <div class="flex justify-between ml-6">
                    <!-- CardDeck caps how many it stacks, so a large pool is
                         cheap to render; v-if avoids an empty stub at zero -->
                    <CardDeck v-if="pointStock > 0">
                        <Card v-for="n in pointStock" :key="n" :card-type="'point'" />
                    </CardDeck>
                    <span v-else class="py-8 text-sm font-bold text-gray-light">Out of points</span>
                </div>
            </div>
            <BankerCard @activate-modal="activeModal = $event" />
        </div>

        <div class="relative p-4 h-full rounded-[1rem] border-1 outline-teal-light overflow-hidden transition duration-200 ease-in-out"
            :class="buyingActive ? 'border-teal-light outline-4 -outline-offset-4 bg-gray-light/30' : 'border-gray-light outline-0'">
            <button v-if="buyingActive" @click="emit('cancel')"
                class="flex justify-center items-center z-50 absolute top-0 right-0 p-4 text-gray-x-light leading-none hover:cursor-pointer hover:text-rose-400 transition duration-200 ease-in-out">🗙</button>

            <h1 class="text-gray-2x-light text-2xl pb-4 font-bold tracking-wide text-center">Cards</h1>

            <div v-if="cardStock.length" class="grid grid-cols-3 grid-rows-2 justify-items-center gap-2">
                <!-- BankSection -->
                <CardDeck v-for="stock in cardStock" :key="`${stock.type}-${stock.count}`">
                    <Card v-for="n in stock.count" :key="`${stock.type}-${n}`" :card-type="stock.type"
                        :buying="buyingActive" @buy="openBuy(stock.type)" />
                </CardDeck>
            </div>
            <p v-else class="py-8 text-center text-sm text-gray-light">The bank is empty</p>
        </div>
    </div>
</template>