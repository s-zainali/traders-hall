<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import SeatToken from '../SeatToken.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * Buying a share of what one room earns.
 *
 * You put up a principal, take a percentage of every rent payment that property
 * collects, and it runs for a fixed number of the landlord's turns. The
 * principal does NOT come back — it buys the share outright.
 *
 * Which means a room with no tenant earns nothing and the stake is simply lost.
 * That risk is stated on the face of the modal rather than left for the player
 * to discover after paying, because nothing else in the game can cost you
 * everything for a decision somebody else fails to make.
 */
const props = defineProps({
    busy: { type: Boolean, default: false },
    canAct: { type: Boolean, default: false },
    // spendable balance, so the stepper cannot exceed what can be funded
    availablePoints: { type: Number, default: 0 },
    // every property in the game, with who owns one and whether it is occupied
    properties: { type: Array, default: () => [] },
})

const emit = defineEmits(['closeModal', 'invest'])

const cardTypes = useCardTypesStore()

const target = ref('')
const principal = ref(1)
const percent = ref(20)
const term = ref(5)

watch(
    () => props.properties,
    (list) => {
        if (!list.some((p) => p.code === target.value)) target.value = list[0]?.code ?? ''
    },
    { immediate: true }
)

const chosen = computed(() => props.properties.find((p) => p.code === target.value) ?? null)

const maxPrincipal = computed(() => Math.max(1, props.availablePoints))

function clamp(v, lo, hi) {
    return Math.min(hi, Math.max(lo, v))
}
const stepPrincipal = (d) => (principal.value = clamp(principal.value + d, 1, maxPrincipal.value))
// 5% steps: finer than that is false precision on rents of two or three points,
// where a percentage point changes nothing after rounding.
const stepPercent = (d) => (percent.value = clamp(percent.value + d * 5, 5, 100))
const stepTerm = (d) => (term.value = clamp(term.value + d, 1, 20))

watch(maxPrincipal, (max) => (principal.value = clamp(principal.value, 1, max)))

const titleOf = (code) => cardTypes.get(code)?.title ?? code

/*
  What this pays if the room stays let at a typical rent. Illustrative, not a
  promise — the rent is whatever the landlord agreed with their tenant, and the
  share is rounded down each time.
*/
const SAMPLE_RENT = 3
const perPayment = computed(() => Math.floor((SAMPLE_RENT * percent.value) / 100))

const canConfirm = computed(
    () => !props.busy && props.canAct && !!target.value && principal.value >= 1
)

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const wellClass =
    'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'
const stepperClass = 'flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max'
const stepButton =
    'w-9 h-9 flex items-center justify-center text-xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed'
const countClass =
    'flex w-14 items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'
const actionButton =
    'px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:cursor-not-allowed disabled:opacity-40'
const blueBtn = 'bg-blue-light text-gray-dark border-2 border-blue-light hover:brightness-110'
</script>

<template>
    <div role="dialog" aria-modal="true" aria-labelledby="invest-title"
        class="relative flex w-max max-w-[22rem] flex-col gap-4 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-6 shadow-2xl shadow-black/60">

        <button type="button" aria-label="Close" @click="emit('closeModal')"
            class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">✕</button>

        <header class="flex flex-col gap-0.5 pr-10">
            <h2 id="invest-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">Invest</h2>
            <p class="text-sm text-gray-x-light">
                Buy a share of what a room earns. Any landlord can take it.
            </p>
        </header>

        <section v-if="properties.length" class="flex flex-col gap-2">
            <span :class="labelClass">Property</span>
            <div class="flex flex-wrap gap-2">
                <button v-for="p in properties" :key="p.code" type="button" @click="target = p.code"
                    class="flex cursor-pointer items-center gap-2 rounded-xl border-2 px-3 py-2 transition duration-200 ease-in-out"
                    :class="target === p.code
                        ? 'border-blue-light bg-blue-dark/30'
                        : 'border-gray-light opacity-60 hover:opacity-100'">
                    <Card :card-type="p.code" :selected="true" :large="false" />
                    <span class="flex flex-col items-start leading-tight">
                        <span class="text-sm font-bold text-gray-2x-light">{{ p.title }}</span>
                        <span class="text-[10px] tabular-nums text-gray-light">
                            {{ p.owners }} {{ p.owners === 1 ? 'owner' : 'owners' }}
                        </span>
                    </span>
                </button>
            </div>
        </section>

        <p v-else class="text-sm text-gray-light">Nobody owns a property to invest in yet.</p>

        <div class="flex flex-wrap gap-4">
            <div class="flex flex-col gap-1">
                <span :class="labelClass">Stake</span>
                <div :class="[stepperClass, 'shrink-0']">
                    <button type="button" :class="stepButton" :disabled="principal <= 1"
                        aria-label="Lower stake" @click="stepPrincipal(-1)">−</button>
                    <div :class="countClass">{{ principal }}</div>
                    <button type="button" :class="stepButton" :disabled="principal >= maxPrincipal"
                        aria-label="Raise stake" @click="stepPrincipal(1)">+</button>
                </div>
            </div>

            <div class="flex flex-col gap-1">
                <span :class="labelClass">Share</span>
                <div :class="[stepperClass, 'shrink-0']">
                    <button type="button" :class="stepButton" :disabled="percent <= 5"
                        aria-label="Lower share" @click="stepPercent(-1)">−</button>
                    <div :class="countClass">{{ percent }}%</div>
                    <button type="button" :class="stepButton" :disabled="percent >= 100"
                        aria-label="Raise share" @click="stepPercent(1)">+</button>
                </div>
            </div>

            <div class="flex flex-col gap-1">
                <span :class="labelClass">For</span>
                <div :class="[stepperClass, 'shrink-0']">
                    <button type="button" :class="stepButton" :disabled="term <= 1"
                        aria-label="Shorter term" @click="stepTerm(-1)">−</button>
                    <div :class="countClass">{{ term }}</div>
                    <button type="button" :class="stepButton" :disabled="term >= 20"
                        aria-label="Longer term" @click="stepTerm(1)">+</button>
                </div>
            </div>
        </div>

        <div :class="[wellClass, 'flex-col items-start gap-1 px-4 py-3']">
            <span class="text-xs text-gray-x-light">
                {{ principal }} now for {{ percent }}% of the rent, for
                {{ term }} {{ term === 1 ? 'turn' : 'turns' }}.
            </span>
            <span class="text-[10px] tabular-nums text-gray-light">
                At a rent of {{ SAMPLE_RENT }} that is {{ perPayment }} a payment.
            </span>
        </div>

        <!-- Stated before the button, not after. An empty room earns nothing and
             the stake does not come back — that is the whole risk. -->
        <p class="rounded-xl border-2 border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs leading-relaxed text-gray-x-light">
            Your stake is not returned. If the room sits empty it earns you nothing.
        </p>

        <footer class="flex items-center justify-between gap-3 border-t-1 border-gray-light pt-4">
            <span v-if="!canAct" class="text-xs font-bold text-gray-light">Only on your turn</span>
            <button type="button" :class="[actionButton, blueBtn, 'ml-auto']" :disabled="!canConfirm"
                @click="emit('invest', {
                    cardType: target,
                    principal,
                    yieldPercent: percent,
                    termTurns: term,
                })">
                Post stake
            </button>
        </footer>
    </div>
</template>