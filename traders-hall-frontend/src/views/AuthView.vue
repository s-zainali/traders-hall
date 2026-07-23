<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { error } = storeToRefs(auth)

const mode = ref('login')                       // 'login' | 'register'
const isRegister = computed(() => mode.value === 'register')

// On login this may be a username OR an email, so it is not called `username`.
const identifier = ref('')
const email = ref('')
const password = ref('')
const displayName = ref('')
const submitting = ref(false)
const showPassword = ref(false)

const identifierEl = ref(null)

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

// Simple, honest strength signal — length plus variety. Shown only while
// registering, where it can still change the outcome.
const strength = computed(() => {
    const v = password.value
    if (!v) return 0
    let score = 0
    if (v.length >= 8) score++
    if (v.length >= 12) score++
    if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++
    if (/\d/.test(v)) score++
    if (/[^A-Za-z0-9]/.test(v)) score++
    return Math.min(score, 4)
})

const strengthMeta = computed(() => [
    { label: '', class: '' },
    { label: 'Weak', class: 'bg-rose-400' },
    { label: 'Fair', class: 'bg-amber-400' },
    { label: 'Good', class: 'bg-teal-light' },
    { label: 'Strong', class: 'bg-emerald-400' },
][strength.value])

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

async function setMode(next) {
    if (mode.value === next) return
    mode.value = next
    auth.error = null
    password.value = ''
    await nextTick()
    identifierEl.value?.focus()
}

const fieldClass =
    'peer w-full rounded-xl border-2 border-gray-light bg-gray-dark/80 px-4 py-3.5 font-bold ' +
    'text-gray-2x-light transition duration-200 ease-in-out placeholder:font-normal ' +
    'placeholder:text-gray-light hover:border-gray-x-light/60 focus:border-teal-light focus:outline-none'

const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const optionalClass = 'normal-case tracking-normal font-normal text-gray-light'
</script>

<template>
    <div class="flex flex-1 flex-col">
      <!-- background and footer come from PublicLayout -->

      <header class="p-6">
        <RouterLink
          :to="{ name: 'landing' }"
          class="inline-flex items-center gap-2 text-sm font-bold text-gray-x-light
                 transition duration-200 ease-in-out hover:text-gray-2x-light"
        >
          <span class="text-lg leading-none">←</span> Back
        </RouterLink>
      </header>

      <main class="flex flex-1 items-center justify-center px-6 py-4">
        <div class="flex w-full max-w-md flex-col gap-8">

          <div class="flex flex-col items-center gap-3 text-center">
            <h1 class="text-4xl font-bold tracking-widest text-gray-2x-light">Traders Hall</h1>
            <p class="text-sm text-gray-x-light">
              {{ isRegister ? 'Create an account to take a seat.' : 'Sign in to return to the table.' }}
            </p>
          </div>

          <!--
            The panel is translucent with a blur so the drifting background stays
            faintly visible through it — the screen reads as one composition
            rather than a form pasted on a picture.
          -->
          <div
            class="flex flex-col gap-6 rounded-[1.75rem] border-2 border-gray-light bg-gray-x-dark/85 p-8
                   shadow-2xl shadow-black/40 backdrop-blur-xl"
          >
            <!-- segmented toggle: both options visible, current one obvious -->
            <div class="relative grid grid-cols-2 rounded-xl border-2 border-gray-light bg-gray-dark/60 p-1">
              <div
                class="absolute inset-y-1 w-[calc(50%-0.25rem)] rounded-lg bg-teal-light
                       transition-transform duration-300 ease-out"
                :class="isRegister ? 'translate-x-[calc(100%+0.5rem)]' : 'translate-x-1'"
                aria-hidden="true"
              ></div>
              <button
                type="button" @click="setMode('login')"
                class="relative z-10 cursor-pointer rounded-lg py-2.5 text-sm font-bold transition-colors duration-200"
                :class="!isRegister ? 'text-gray-dark' : 'text-gray-x-light hover:text-gray-2x-light'"
              >Sign in</button>
              <button
                type="button" @click="setMode('register')"
                class="relative z-10 cursor-pointer rounded-lg py-2.5 text-sm font-bold transition-colors duration-200"
                :class="isRegister ? 'text-gray-dark' : 'text-gray-x-light hover:text-gray-2x-light'"
              >Create account</button>
            </div>

            <form class="flex flex-col gap-4" @submit.prevent="submit">

              <div class="flex flex-col gap-2">
                <label :class="labelClass" for="identifier">
                  {{ isRegister ? 'Username' : 'Username or email' }}
                </label>
                <input
                  id="identifier" ref="identifierEl" v-model="identifier" :class="fieldClass" type="text"
                  :autocomplete="isRegister ? 'username' : 'username email'"
                  :placeholder="isRegister ? 'zain' : 'zain or zain@example.com'"
                  spellcheck="false" autocapitalize="none"
                />
                <Transition name="hint">
                  <p v-if="identifierError" class="text-xs font-bold text-amber-400">{{ identifierError }}</p>
                </Transition>
              </div>

              <!-- register-only fields, revealed together -->
              <Transition name="expand">
                <div v-if="isRegister" class="flex flex-col gap-4 overflow-hidden">
                  <div class="flex flex-col gap-2">
                    <label :class="labelClass" for="email">
                      Email <span :class="optionalClass">(optional)</span>
                    </label>
                    <input
                      id="email" v-model="email" :class="fieldClass" type="email" autocomplete="email"
                      placeholder="zain@example.com" spellcheck="false" autocapitalize="none"
                    />
                    <Transition name="hint">
                      <p v-if="emailError" class="text-xs font-bold text-amber-400">{{ emailError }}</p>
                    </Transition>
                  </div>

                  <div class="flex flex-col gap-2">
                    <label :class="labelClass" for="displayName">
                      Display name <span :class="optionalClass">(optional)</span>
                    </label>
                    <input
                      id="displayName" v-model="displayName" :class="fieldClass" type="text"
                      autocomplete="nickname" placeholder="Defaults to your username"
                    />
                  </div>
                </div>
              </Transition>

              <div class="flex flex-col gap-2">
                <label :class="labelClass" for="password">Password</label>
                <div class="relative">
                  <input
                    id="password" v-model="password" :class="[fieldClass, 'pr-14']"
                    :type="showPassword ? 'text' : 'password'"
                    :autocomplete="isRegister ? 'new-password' : 'current-password'"
                    placeholder="••••••••"
                  />
                  <button
                    type="button" tabindex="-1"
                    :aria-label="showPassword ? 'Hide password' : 'Show password'"
                    @click="showPassword = !showPassword"
                    class="absolute right-2 top-1/2 flex h-9 w-10 -translate-y-1/2 cursor-pointer
                           items-center justify-center rounded-lg text-gray-x-light
                           transition duration-200 ease-in-out hover:bg-gray-light/40 hover:text-gray-2x-light"
                  >{{ showPassword ? '🙈' : '👁' }}</button>
                </div>

                <Transition name="hint">
                  <p v-if="passwordError" class="text-xs font-bold text-amber-400">{{ passwordError }}</p>
                </Transition>

                <!-- strength meter: only while registering, where it can still
                     change what the user types -->
                <div v-if="isRegister && password" class="flex items-center gap-3 pt-1">
                  <div class="flex flex-1 gap-1">
                    <span
                      v-for="i in 4" :key="i"
                      class="h-1 flex-1 rounded-full transition-colors duration-300"
                      :class="i <= strength ? strengthMeta.class : 'bg-gray-light'"
                    ></span>
                  </div>
                  <span class="w-14 text-right text-xs font-bold text-gray-x-light">
                    {{ strengthMeta.label }}
                  </span>
                </div>
              </div>

              <Transition name="hint">
                <p
                  v-if="error"
                  class="rounded-xl border-2 border-rose-400/50 bg-rose-400/15 px-4 py-3 text-sm font-bold text-rose-400"
                >{{ error }}</p>
              </Transition>

              <button
                type="submit" :disabled="!canSubmit"
                class="group relative mt-1 w-full cursor-pointer overflow-hidden rounded-xl border-2
                       border-teal-light bg-teal-light py-3.5 font-bold text-gray-dark
                       transition duration-200 ease-in-out hover:brightness-110 active:scale-[0.99]
                       disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:brightness-100
                       focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2"
              >
                <span class="flex items-center justify-center gap-2">
                  <span
                    v-if="submitting"
                    class="h-4 w-4 animate-spin rounded-full border-2 border-gray-dark/30 border-t-gray-dark"
                  ></span>
                  {{ submitting ? 'Please wait' : isRegister ? 'Create account' : 'Sign in' }}
                </span>
              </button>
            </form>
          </div>

          <p class="text-center text-xs leading-relaxed text-gray-x-light/60">
            Lorem ipsum dolor sit amet. By continuing you agree to nothing in particular, yet.
          </p>
        </div>
      </main>

  </div>
</template>

<style scoped>
/* hint text: slide down as it appears, so the layout shift reads as intentional */
.hint-enter-active,
.hint-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}
.hint-enter-from,
.hint-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* register-only block: grid-template-rows 0fr -> 1fr animates to auto height,
   which plain max-height cannot do without hardcoding a guess */
.expand-enter-active,
.expand-leave-active {
  transition: opacity 300ms ease, grid-template-rows 300ms ease;
  display: grid;
  grid-template-rows: 1fr;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  grid-template-rows: 0fr;
}

@media (prefers-reduced-motion: reduce) {
  .hint-enter-active,
  .hint-leave-active,
  .expand-enter-active,
  .expand-leave-active { transition: none; }
}
</style>