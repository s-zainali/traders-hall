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

// Startup: settle whether a stored token is still good, so we know which view
// to show.
onMounted(() => auth.init())

// Card types load once signed in. A watcher rather than an onMounted call,
// because authentication can happen later (a login) as well as at startup;
// immediate:true covers the already-authenticated case.
watch(isAuthenticated, (value) => {
    if (value) cardTypes.fetchAll()
}, { immediate: true })

// ONE ref for the current mode: '' | 'buy' | 'sell' | 'trade'.
// Three separate booleans could all be true at once, and nothing kept them in
// sync — that is what broke sell/trade and left the buy ring stuck on.
const activeAction = ref('')

function startAction(action) {
    activeAction.value = action
}

function cancelAction() {
    activeAction.value = ''
}
</script>

<template>
    <!-- 1. still deciding whether we have a session -->
    <LoadingScreen v-if="!ready" message="Starting up…" />

    <!-- 2. no session: sign in or register -->
    <AuthView v-else-if="!isAuthenticated" />

    <!-- 3. signed in, catalogue not here yet -->
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

            <!--
                active-action drives the hand ring, the 🗙, and whether cards are
                clickable at all. Without it the cards emit `details` instead of
                `sell`/`trade`, so the modal never opens.
            -->
            <PlayerCardHolder
                :active-action="activeAction"
                @buy="startAction('buy')"
                @sell="startAction('sell')"
                @trade="startAction('trade')"
                @cancel-operation="cancelAction"
            />
        </div>

        <!--
            BankSection emits `cancel` from its 🗙, not `update:buyingActive`, so
            v-model never heard it and the ring stayed on. Plain prop + explicit
            handler instead.
        -->
        <BankSection
            :buying-active="activeAction === 'buy'"
            @cancel="cancelAction"
        />
    </div>
</template>

<style scoped></style>