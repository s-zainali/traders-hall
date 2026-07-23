<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { error } = storeToRefs(auth)

const mode = ref('login')          // 'login' | 'register'
const isRegister = computed(() => mode.value === 'register')

// On login this may be a username OR an email, so it is not called `username`.
const identifier = ref('')
const email = ref('')
const password = ref('')
const displayName = ref('')
const submitting = ref(false)

// Mirrors the server's Pydantic rules so the user finds out before a round
// trip. The server still validates — this is convenience, not security.
const identifierError = computed(() => {
    if (!identifier.value) return ''
    // On login the field may legitimately be an email, so the username pattern
    // must not apply. Let the server decide.
    if (!isRegister.value) return ''
    if (identifier.value.length < 3) return 'At least 3 characters'
    if (identifier.value.length > 24) return 'At most 24 characters'
    if (!/^[a-zA-Z0-9_]+$/.test(identifier.value)) return 'Letters, numbers and underscores only'
    return ''
})

const emailError = computed(() => {
    if (!email.value) return ''
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) return 'Enter a valid email'
    return ''
})

const passwordError = computed(() => {
    if (!password.value) return ''
    if (password.value.length < 8) return 'At least 8 characters'
    return ''
})

const canSubmit = computed(() =>
    identifier.value &&
    password.value &&
    !identifierError.value &&
    !emailError.value &&
    !passwordError.value &&
    !submitting.value
)

// A stale "Incorrect username or password" under a field the user is already
// retyping is just noise — clear it as soon as they change something.
watch([identifier, email, password], () => {
    if (error.value) auth.error = null
})

async function submit() {
    if (!canSubmit.value) return
    submitting.value = true
    try {
        const ok = isRegister.value
            ? await auth.register(identifier.value, password.value, email.value, displayName.value)
            : await auth.login(identifier.value, password.value)

        // ?next= is set by the router guard when it bounces an unauthenticated
        // visitor, so a deep link survives the detour through login.
        if (ok) router.push(route.query.next || { name: 'lobby' })
    } finally {
        submitting.value = false
    }
}

function switchMode() {
    mode.value = isRegister.value ? 'login' : 'register'
    auth.error = null
    password.value = ''
}

const fieldClass =
    'w-full px-4 py-3 rounded-xl bg-gray-dark text-gray-2x-light font-bold ' +
    'border-2 border-gray-light placeholder:text-gray-light placeholder:font-normal ' +
    'focus:outline-none focus:border-teal-light transition duration-200 ease-in-out'

const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const optionalClass = 'normal-case tracking-normal font-normal'
</script>

<template>
    <div class="min-h-[100dvh] bg-gray-dark flex items-center justify-center p-6">
        <div class="w-full max-w-md flex flex-col gap-6">

            <RouterLink :to="{ name: 'landing' }"
                class="text-4xl text-gray-2x-light font-bold tracking-widest text-center
                       hover:text-teal-light transition duration-200 ease-in-out">
                Traders Hall
            </RouterLink>

            <div class="flex flex-col gap-5 p-8 bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem]">

                <header class="flex flex-col gap-1">
                    <h2 class="text-2xl font-bold tracking-wide text-gray-2x-light">
                        {{ isRegister ? 'Create account' : 'Sign in' }}
                    </h2>
                    <p class="text-sm text-gray-x-light">
                        {{ isRegister ? 'Pick a name and a password.' : 'Welcome back.' }}
                    </p>
                </header>

                <form class="flex flex-col gap-4" @submit.prevent="submit">

                    <div class="flex flex-col gap-2">
                        <label :class="labelClass" for="identifier">
                            {{ isRegister ? 'Username' : 'Username or email' }}
                        </label>
                        <input id="identifier" v-model="identifier" :class="fieldClass" type="text"
                            :autocomplete="isRegister ? 'username' : 'username email'"
                            :placeholder="isRegister ? 'zain' : 'zain or zain@example.com'"
                            spellcheck="false" autocapitalize="none" />
                        <p v-if="identifierError" class="text-xs text-amber-400">{{ identifierError }}</p>
                    </div>

                    <div v-if="isRegister" class="flex flex-col gap-2">
                        <label :class="labelClass" for="email">
                            Email <span :class="optionalClass">(optional)</span>
                        </label>
                        <input id="email" v-model="email" :class="fieldClass" type="email"
                            autocomplete="email" placeholder="zain@example.com"
                            spellcheck="false" autocapitalize="none" />
                        <p v-if="emailError" class="text-xs text-amber-400">{{ emailError }}</p>
                    </div>

                    <div v-if="isRegister" class="flex flex-col gap-2">
                        <label :class="labelClass" for="displayName">
                            Display name <span :class="optionalClass">(optional)</span>
                        </label>
                        <input id="displayName" v-model="displayName" :class="fieldClass" type="text"
                            autocomplete="nickname" placeholder="Defaults to your username" />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label :class="labelClass" for="password">Password</label>
                        <input id="password" v-model="password" :class="fieldClass" type="password"
                            :autocomplete="isRegister ? 'new-password' : 'current-password'"
                            placeholder="••••••••" />
                        <p v-if="passwordError" class="text-xs text-amber-400">{{ passwordError }}</p>
                    </div>

                    <p v-if="error"
                        class="px-4 py-3 rounded-xl bg-rose-400/20 border-2 border-rose-400/50 text-rose-400 font-bold text-sm">
                        {{ error }}
                    </p>

                    <button type="submit" :disabled="!canSubmit"
                        class="w-full py-3 rounded-xl font-bold cursor-pointer bg-teal-light text-gray-dark
                               border-2 border-teal-light transition duration-200 ease-in-out
                               hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed
                               focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                        {{ submitting ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in' }}
                    </button>
                </form>

                <div class="pt-2 border-t-1 border-gray-light text-center">
                    <button type="button" @click="switchMode"
                        class="text-sm text-gray-x-light hover:text-teal-light cursor-pointer transition duration-200 ease-in-out">
                        {{ isRegister ? 'Already have an account? Sign in' : 'No account? Create one' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>