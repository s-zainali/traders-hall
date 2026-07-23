<script setup>
import { ref, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import { useCardTypesStore } from '../stores/cardTypes'

// From the /game/:code route via `props: true`
defineProps({ code: { type: String, required: true } })

const cardTypes = useCardTypesStore()
const { loaded, error: cardError } = storeToRefs(cardTypes)

onMounted(() => cardTypes.fetchAll())

// One ref for the current mode: '' | 'buy' | 'sell' | 'trade'.
const activeAction = ref('')
const startAction = (action) => (activeAction.value = action)
const cancelAction = () => (activeAction.value = '')
</script>

<template>
  <LoadingScreen
    v-if="!loaded"
    message="Loading card catalogue…"
    :error="cardError ?? ''"
    @retry="cardTypes.fetchAll()"
  />

  <div v-else class="flex min-h-[100dvh] gap-6 bg-gray-dark p-6">
    <div class="flex w-full flex-col">
      <Header :game-code="code" />

      <div class="flex-grow py-4">
        <div class="flex w-full gap-4">
          <PlayerCardHolder :player-type="'opponent'" class="min-w-0 flex-1" />
          <PlayerCardHolder :player-type="'opponent'" class="min-w-0 flex-1" />
          <PlayerCardHolder :player-type="'opponent'" class="min-w-0 flex-1" />
        </div>
      </div>

      <PlayerCardHolder
        :active-action="activeAction"
        @buy="startAction('buy')"
        @sell="startAction('sell')"
        @trade="startAction('trade')"
        @cancel-operation="cancelAction"
      />
    </div>

    <BankSection :buying-active="activeAction === 'buy'" @cancel="cancelAction" />
  </div>
</template>