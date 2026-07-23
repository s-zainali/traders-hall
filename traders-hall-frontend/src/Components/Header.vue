<script setup>
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const { user } = storeToRefs(auth)

// Logging out ends a game session, so confirm rather than firing on one click.
const confirming = ref(false)

async function confirmLogout() {
    confirming.value = false
    await auth.logout()
}
</script>

<template>
    <div class="h-min p-4 bg-gray-x-dark rounded-[1.5rem] border-2 border-gray-light
                flex items-center justify-between gap-4">

        <!-- spacer keeps the title optically centred against the account block -->
        <div class="w-40"></div>

        <h1 class="text-3xl text-gray-2x-light tracking-widest font-bold text-center">Traders Hall</h1>

        <div class="w-40 flex items-center justify-end gap-3">
            <div v-if="user" class="flex items-center gap-3">
                <div class="flex flex-col items-end leading-tight">
                    <span class="font-bold text-gray-2x-light">{{ user.display_name }}</span>
                    <span class="text-xs text-gray-x-light">@{{ user.username }}</span>
                </div>

                <button type="button" aria-label="Log out" title="Log out" @click="confirming = true"
                    class="h-9 w-9 flex items-center justify-center rounded-lg cursor-pointer
                           bg-gray-dark border-2 border-gray-light text-gray-x-light
                           hover:border-rose-400 hover:text-rose-400 transition duration-200 ease-in-out
                           focus-visible:outline-2 focus-visible:outline-rose-400 focus-visible:outline-offset-2">
                    ⏻
                </button>
            </div>
        </div>

        <!-- confirmation overlay -->
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