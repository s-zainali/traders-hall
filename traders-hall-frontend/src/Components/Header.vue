<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

defineProps({ gameCode: { type: String, default: '' } })

const auth = useAuthStore()
const router = useRouter()
const { user } = storeToRefs(auth)

// Leaving mid-game is destructive, so confirm rather than firing on one click.
const confirming = ref(false)

async function confirmLogout() {
    confirming.value = false
    await auth.logout()
    router.push({ name: 'landing' })
}
</script>

<template>
    <div class="h-min p-4 bg-gray-x-dark rounded-[1.5rem] border-2 border-gray-light
                flex items-center justify-between gap-4">

        <div class="w-48 flex items-center gap-3">
            <RouterLink :to="{ name: 'lobby' }"
                class="rounded-lg border-2 border-gray-light px-3 py-1.5 text-sm font-bold text-gray-x-light
                       transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light">
                ← Lobby
            </RouterLink>
            <span v-if="gameCode" class="font-bold tracking-[0.2em] text-teal-light">{{ gameCode }}</span>
        </div>

        <h1 class="text-3xl text-gray-2x-light tracking-widest font-bold text-center">Traders Hall</h1>

        <div class="w-48 flex items-center justify-end gap-3">
            <div v-if="user" class="flex items-center gap-3">
                <div class="flex flex-col items-end leading-tight">
                    <span class="font-bold text-gray-2x-light">{{ user.display_name }}</span>
                    <span class="text-xs text-gray-x-light">@{{ user.username }}</span>
                </div>

                <button type="button" aria-label="Log out" title="Log out" @click="confirming = true"
                    class="h-9 w-9 flex items-center justify-center rounded-lg cursor-pointer
                           bg-gray-dark border-2 border-gray-light text-gray-x-light
                           hover:border-rose-400 hover:text-rose-400 transition duration-200 ease-in-out">
                    ⏻
                </button>
            </div>
        </div>

        <div v-if="confirming"
            class="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-gray-dark/90 backdrop-blur-sm"
            @click.self="confirming = false">
            <div role="dialog" aria-modal="true"
                class="flex flex-col gap-5 p-8 bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem]">
                <div class="flex flex-col gap-1">
                    <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">Log out?</h2>
                    <p class="text-sm text-gray-x-light">You will need to sign in again to keep playing.</p>
                </div>
                <div class="flex justify-end gap-3">
                    <button type="button" @click="confirming = false"
                        class="px-6 py-3 rounded-xl font-bold cursor-pointer text-gray-x-light
                               border-2 border-gray-light hover:border-gray-x-light hover:text-gray-2x-light
                               transition duration-200 ease-in-out">Cancel</button>
                    <button type="button" @click="confirmLogout"
                        class="px-6 py-3 rounded-xl font-bold cursor-pointer bg-rose-400 text-gray-dark
                               border-2 border-rose-400 hover:bg-rose-300 hover:border-rose-300
                               transition duration-200 ease-in-out">Log out</button>
                </div>
            </div>
        </div>
    </div>
</template>