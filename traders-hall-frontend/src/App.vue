<script setup>
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from './Components/BankSection.vue'
import Header from './Components/Header.vue'
import PlayerCardHolder from './Components/PlayerCardHolder.vue'
import LoadingScreen from './Components/LoadingScreen.vue'
import { useCardTypesStore } from './stores/cardTypes.js'

const cardTypes = useCardTypesStore()
// storeToRefs keeps reactivity when destructuring state/getters off a store.
// Plain destructuring would copy the current values and never update.
const { loaded, error } = storeToRefs(cardTypes)

onMounted(() => cardTypes.fetchAll())

const buyingActive = ref(false)
const sellActive = ref(false)
const tradeActive = ref(false)
</script>

<template>
  <!-- Nothing below renders until the catalogue is in memory, so no child ever
       has to handle a missing card type. That is the whole point of the gate. -->
  <LoadingScreen
    v-if="!loaded"
    message="Loading card catalogue…"
    :error="error ?? ''"
    @retry="cardTypes.fetchAll()"
  />

  <div v-else class="min-h-[100dvh] bg-gray-dark p-6 flex gap-6">
    <div class="flex flex-col w-full">
      <Header />
      <div class="flex-grow py-4">
        <div class="flex gap-4 w-full">
          <PlayerCardHolder :player-type="'opponent'" class="flex-1 min-w-0" />
          <PlayerCardHolder :player-type="'opponent'" class="flex-1 min-w-0" />
          <PlayerCardHolder :player-type="'opponent'" class="flex-1 min-w-0" />
        </div>
      </div>
      <PlayerCardHolder
        @buy="buyingActive = true"
        @sell="sellActive = true"
        @trade="tradeActive = true"
      />
    </div>
    <BankSection v-model:buying-active="buyingActive" />
  </div>
</template>

<style scoped></style>