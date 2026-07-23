<script setup>
import { ref, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import BankSection from './Components/BankSection.vue'
import Header from './Components/Header.vue'
import PlayerCardHolder from './Components/PlayerCardHolder.vue'
import LoadingScreen from './Components/LoadingScreen.vue'
import AuthView from './Components/AuthView.vue'
import { useAuthStore } from './stores/auth'
import { useCardTypesStore } from './stores/cardTypes'

const auth = useAuthStore()
const cardTypes = useCardTypesStore()

const { ready, isAuthenticated } = storeToRefs(auth)
const { loaded, error: cardError } = storeToRefs(cardTypes)

// Startup: settle whether a stored token is still good. Only then do we know
// which of the three views to show.
onMounted(() => auth.init())

// Card types are only fetched once signed in — the endpoint will require auth
// soon, and there is no reason to load a catalogue for a logged-out visitor.
// A watcher rather than an onMounted call, because authentication can happen
// later (after a login) as well as at startup.
watch(isAuthenticated, (value) => {
    if (value) cardTypes.fetchAll()
}, { immediate: true })

const buyingActive = ref(false)
const sellActive = ref(false)
const tradeActive = ref(false)
</script>

<template>
    <!-- 1. still deciding whether we have a session -->
    <LoadingScreen v-if="!ready" message="Starting up…" />

    <!-- 2. no session: sign in or register -->
    <AuthView v-else-if="!isAuthenticated" />

    <!-- 3. signed in, but the catalogue has not arrived yet -->
    <LoadingScreen v-else-if="!loaded" message="Loading card catalogue…" :error="cardError ?? ''"
        @retry="cardTypes.fetchAll()" />

    <!-- 4. ready to play -->
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
            <PlayerCardHolder @buy="buyingActive = true" @sell="sellActive = true"
                @trade="tradeActive = true" />
        </div>
        <BankSection v-model:buying-active="buyingActive" />
    </div>
</template>

<style scoped></style>