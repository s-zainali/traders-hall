<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import SeatToken from '../SeatToken.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * Buying a share of what somebody else's property earns.
 *
 * You put up a stake, take a percentage of every rent that property collects,
 * and it runs for a fixed number of the owner's turns. The stake does NOT come
 * back — it buys the share outright.
 *
 * Only opponents' properties are offered. Investing in your own would be paying
 * yourself a share of your own rent, which is a no-op with extra steps, and the
 * server would refuse it anyway: the claimant of an invest offer is the owner,
 * and you cannot claim your own offer.
 */
const props = defineProps({
    busy: { type: Boolean, default: false },
    canAct: { type: Boolean, default: false },
    availablePoints: { type: Number, default: 0 },
    /*
      Opponents who own property, each with what they hold:
        { playerId, name, seatIndex, cards: [{ code, count }] }
      Built by the parent from the public hands, which every client already has.
    */
    owners: { type: Array, default: () => [] },
})

const emit = defineEmits(['closeModal', 'invest'])

const cardTypes = useCardTypesStore()

const target = ref('')          // card code
const targetOwner = ref('')     // whose, for the summary line
const principal = ref(1)
const percent = ref(20)
const term = ref(5)

/*
  The same property type can be held by several owners, and an offer names a
  TYPE rather than a person — any owner of it can take the stake. Selecting an
  owner's card therefore picks the type; the owner shown is who prompted it.
*/
const options = computed(() =>
    props.owners.flatMap((o) =>
        o.cards.map((c) => ({
            key: `${o.playerId}:${c.code}`,
            playerId: o.playerId,
            name: o.name,
            seatIndex: o.seatIndex,
            code: c.code,
            count: c.count,
            title: cardTypes.get(c.code)?.title ?? c.code,
        }))
    )
)

watch(
    options,
    (list) => {
        if (!list.some((o) => o.code === target.value && o.playerId === targetOwner.value)) {
            target.value = list[0]?.code ?? ''
            targetOwner.value = list[0]?.playerId ?? ''
        }
    },
    { immediate: true }
)

function choose(option) {
    target.value = option.code
    targetOwner.value = option.playerId
}

const chosen = computed(
    () => options.value.find((o) => o.code === target.value && o.playerId === targetOwner.value)
        ?? null
)

const maxPrincipal = computed(() => Math.max(1, props.availablePoints))

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const stepPrincipal = (d) => (principal.value = clamp(principal.value + d, 1, maxPrincipal.value))
// 5% steps. Finer is false precision on rents of two or three points, where a
// single percentage point changes nothing once the share is rounded down.
const stepPercent = (d) => (percent.value = clamp(percent.value + d * 5, 5, 100))
const stepTerm = (d) => (term.value = clamp(term.value + d, 1, 20))

watch(maxPrincipal, (max) => (principal.value = clamp(principal.value, 1, max)))

const canConfirm = computed(
    () => !props.busy && props.canAct && !!target.value && principal.value >= 1
)

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const turnsLabel = (n) => (n === 1 ? '1 turn' : `${n} turns`)

const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const stepperClass = 'flex w-max overflow-hidden rounded-2xl border-2 border-gray-x-light'
const stepButton =
    'flex h-9 w-9 items-center justify-center bg-gray-light text-xl font-bold text-gray-2x-light ' +
    'cursor-pointer transition duration-200 ease-in-out hover:bg-gray-x-light hover:text-gray-dark ' +
    'disabled:cursor-not-allowed disabled:opacity-30'
const countClass =
    'flex w-14 items-center justify-center bg-gray-dark font-bold tabular-nums text-gray-2x-light'
const actionButton =
    'cursor-pointer rounded-xl px-5 py-2.5 font-bold transition duration-200 ease-in-out ' +
    'disabled:cursor-not-allowed disabled:opacity-40'
const blueBtn = 'border-2 border-blue-light bg-blue-light text-gray-dark hover:brightness-110'
</script>

<template>
    <div role="dialog" aria-modal="true" aria-labelledby="invest-title"
        class="scroll-slim relative flex max-h-full w-[23rem] max-w-full flex-col gap-4 overflow-y-auto rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-6 shadow-2xl shadow-black/60">

        <button type="button" aria-label="Close" @click="emit('closeModal')"
            class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">✕</button>

        <header class="flex items-center gap-3 pr-10">
            <span class="flex h-11 w-11 shrink-0 items-center justify-center">
                <Card :card-type="'invest'" :selected="true" :large="false" />
            </span>
            <div class="flex min-w-0 flex-col gap-0.5">
                <h2 id="invest-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                    Invest
                </h2>
                <p class="text-sm text-gray-x-light">Buy a share of someone else's rent.</p>
            </div>
        </header>

        <!-- ── whose property ── -->
        <section v-if="options.length" class="flex flex-col gap-2">
            <span :class="labelClass">Whose property</span>

            <div v-for="owner in owners" :key="owner.playerId" class="flex flex-col gap-1.5">
                <span class="flex items-center gap-2">
                    <SeatToken :seat-index="owner.seatIndex" size="sm" />
                    <span class="truncate text-xs font-bold text-gray-2x-light">{{ owner.name }}</span>
                </span>

                <div class="flex flex-wrap gap-2">
                    <button v-for="c in owner.cards" :key="`${owner.playerId}:${c.code}`" type="button"
                        @click="choose({ code: c.code, playerId: owner.playerId })"
                        class="flex cursor-pointer items-center gap-2 rounded-xl border-2 px-3 py-2 transition duration-200 ease-in-out"
                        :class="target === c.code && targetOwner === owner.playerId
                            ? 'border-blue-light bg-blue-dark/30'
                            : 'border-gray-light opacity-60 hover:opacity-100'">
                        <Card :card-type="c.code" :selected="true" :large="false" />
                        <span class="flex flex-col items-start leading-tight">
                            <span class="text-sm font-bold text-gray-2x-light">
                                {{ cardTypes.get(c.code)?.title ?? c.code }}
                            </span>
                            <span class="text-[10px] tabular-nums text-gray-light">×{{ c.count }}</span>
                        </span>
                    </button>
                </div>
            </div>
        </section>

        <p v-else class="text-sm text-gray-light">
            No opponent owns a property yet. There is nothing to invest in.
        </p>

        <!-- ── terms ── -->
        <div class="flex flex-wrap gap-4 border-t-1 border-gray-light pt-4">
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

        <!--
            The deal as one line of cards, so what is being exchanged is legible
            without reading any of the labels above.
        -->
        <div v-if="chosen"
            class="flex flex-wrap items-center gap-2 rounded-xl border-2 border-blue-light/40 bg-blue-dark/10 px-4 py-3">
            <span class="flex items-center gap-1">
                <Card :card-type="'point'" :selected="true" :large="false" />
                <span class="text-sm font-bold tabular-nums text-teal-light">{{ principal }}</span>
            </span>

            <svg class="h-4 w-4 shrink-0 text-blue-light" viewBox="0 0 16 16" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                aria-hidden="true">
                <path d="M2.5 8h11M9.5 4 13.5 8l-4 4" />
            </svg>

            <span class="flex items-center gap-1">
                <Card :card-type="chosen.code" :selected="true" :large="false" />
                <span class="rounded-lg border-2 border-blue-light/50 bg-blue-dark/30 px-1.5 py-0.5 text-sm font-bold tabular-nums text-blue-light">
                    {{ percent }}%
                </span>
            </span>

            <span class="w-full text-[10px] font-bold uppercase tracking-widest text-gray-x-light">
                of every rent · {{ turnsLabel(term) }}
            </span>
        </div>

        <!-- Stated before the button, not after: an empty room earns nothing and
             the stake does not come back. -->
        <p class="rounded-xl border-2 border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs leading-relaxed text-gray-x-light">
            Your stake is not returned, and any owner of that property can take it. If the room sits
            empty it earns you nothing.
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

<style scoped>
.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    width: 10px;
}

.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}
</style>