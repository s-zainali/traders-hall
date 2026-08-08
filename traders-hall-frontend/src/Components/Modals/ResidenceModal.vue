<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import SeatToken from '../SeatToken.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * Housing, in two modes.
 *
 *   'let'        opened from an owned property card. Letting one of ITS rooms,
 *                and nothing else.
 *   'residence'  opened from the residence box. Where you live, moving into your
 *                own place, asking for a room, leaving.
 *
 * Split because they are different questions asked from different places. A
 * property card is a thing you own and might rent out; the residence box is
 * where you sleep. One combined list meant a landlord with three towers had to
 * scan past their own housing to find the room they wanted to let.
 *
 * One component rather than two because the terms — a rent and an interval —
 * are identical either way, as is every class string. Only the sections differ.
 */
const props = defineProps({
    mode: { type: String, default: 'residence' }, // 'residence' | 'let'
    busy: { type: Boolean, default: false },
    canAct: { type: Boolean, default: false },

    // 'let' mode: the property that was clicked, and its spare capacity
    cardType: { type: String, default: '' },
    roomsFreeForCard: { type: Number, default: 0 },
    roomsPendingForCard: { type: Number, default: 0 },

    // 'residence' mode
    residenceCardType: { type: String, default: null },
    // set alongside a residence = renting; null alongside one = own property
    residenceLandlordId: { type: String, default: null },
    landlordName: { type: String, default: '' },
    landlordSeatIndex: { type: Number, default: -1 },
    rentPoints: { type: Number, default: 0 },
    rentDue: { type: Number, default: 0 },
    // null | 'requested' | 'rejected'. Drives which control the tenant gets,
    // so an impossible action is never offered rather than being refused.
    moveoutStatus: { type: String, default: null },
    moveoutBuyout: { type: Number, default: 0 },
    availablePoints: { type: Number, default: 0 },
    // every live tenancy this player is landlord to
    tenants: { type: Array, default: () => [] },
    // lettable rooms per property type, net of tenants, self, and live offers
    roomsByCard: { type: Object, default: () => ({}) },
})

const emit = defineEmits([
    'closeModal',
    'moveIn',
    'leave',
    'rentOut',
    'rentAsk',
    'respondMoveOut',
    'resolveMoveOut',
    'evict',
])

const cardTypes = useCardTypesStore()

const isLet = computed(() => props.mode === 'let')
const isHoused = computed(() => !!props.residenceCardType)
const isTenant = computed(() => isHoused.value && !!props.residenceLandlordId)

const awaitingLandlord = computed(() => props.moveoutStatus === 'requested')
const wasRefused = computed(() => props.moveoutStatus === 'rejected')
const canAffordBuyout = computed(() => props.availablePoints >= props.moveoutBuyout)

const titleOf = (code) => cardTypes.get(code)?.title ?? code

/** Own properties with a room going spare — the occupy options. */
const occupiable = computed(() =>
    Object.entries(props.roomsByCard)
        .filter(([, free]) => free > 0)
        .map(([code, free]) => ({ code, free, title: titleOf(code) })),
)

const moveTarget = ref('')
watch(
    occupiable,
    (list) => {
        if (!list.some((c) => c.code === moveTarget.value)) moveTarget.value = list[0]?.code ?? ''
    },
    { immediate: true },
)

/* ── terms, shared by both modes ─────────────────────────────────── */
const rent = ref(1)
const interval = ref(3)

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const stepRent = (d) => (rent.value = clamp(rent.value + d, 1, 99))
const stepInterval = (d) => (interval.value = clamp(interval.value + d, 1, 20))

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const locked = computed(() => props.busy || !props.canAct)
const turnNote = computed(() => (props.canAct ? '' : 'Only on your turn'))

const turnsLabel = (n) => (n === 1 ? '1 turn' : `${n} turns`)
const dueTone = computed(() =>
    props.rentDue <= 1 ? 'text-rose-400' : props.rentDue <= 2 ? 'text-amber-400' : 'text-teal-light',
)

/* ── class vocabulary, lifted from TransactionModal ──────────────── */
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const wellClass =
    'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'
const stepperClass = 'flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max'
const stepButton =
    'w-9 h-9 flex items-center justify-center text-xl font-bold text-gray-2x-light bg-gray-light ' +
    'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
    'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'
const countClass =
    'flex w-12 items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'
const actionButton =
    'px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:opacity-40 disabled:cursor-not-allowed ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'
const tealBtn = 'bg-teal-light text-gray-dark border-2 border-teal-light hover:brightness-110'
const purpleBtn = 'bg-purple-light text-gray-dark border-2 border-purple-light hover:brightness-110'
const ghostBtn =
    'border-2 border-gray-light text-gray-x-light hover:border-rose-400 hover:text-rose-400'
const pickerBtn =
    'flex cursor-pointer items-center gap-2 rounded-xl border-2 px-3 py-2 transition duration-200 ease-in-out'
</script>

<template>
    <div role="dialog" aria-modal="true" aria-labelledby="residence-title"
        class="scroll-slim relative flex max-h-full w-[44rem] max-w-full flex-col gap-4 overflow-y-auto rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-6 shadow-2xl shadow-black/60"
        :class="isLet ? 'sm:w-[22rem]' : ''">

        <button type="button" aria-label="Close" @click="emit('closeModal')"
            class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">
            ✕
        </button>

        <header class="flex flex-col gap-0.5 pr-10">
            <h2 id="residence-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                {{ isLet ? 'Let a room' : 'Residence' }}
            </h2>
            <p class="text-sm text-gray-x-light">
                {{
                    isLet
                        ? `One room in your ${titleOf(cardType)}, open to every player.`
                        : isTenant
                            ? 'You rent a room.'
                            : isHoused
                                ? 'Your own property.'
                                : 'You live nowhere.'
                }}
            </p>
        </header>

        <!--
            Two columns: where you live on the left, what you do as a landlord on
            the right. They are separate concerns that happened to share a modal,
            and stacking them meant scrolling past your own housing to reach the
            controls for somebody else's.

            Opening from a property card shows the right column only — that click
            means "let this room", not "review my housing".
        -->
        <div class="grid gap-5" :class="isLet ? 'grid-cols-1' : 'md:grid-cols-2'">

            <!-- ── left: where you live ── -->
            <div v-if="!isLet" class="flex flex-col gap-4">
            <div v-if="isHoused" :class="[wellClass, 'justify-between gap-3 px-4 py-3']">
                <span class="flex items-center gap-2">
                    <Card :card-type="residenceCardType" :selected="true" :large="false" />
                    <span class="flex flex-col leading-tight">
                        <span class="text-sm font-bold text-gray-2x-light">{{
                            titleOf(residenceCardType)
                            }}</span>
                        <span v-if="isTenant" class="flex items-center gap-1 text-xs text-gray-x-light">
                            <SeatToken :seat-index="landlordSeatIndex" size="sm" />{{ landlordName }}
                        </span>
                        <span v-else class="text-xs text-gray-x-light">Yours</span>
                    </span>
                </span>
                <!-- An em dash rather than 0 when the rent figure is unknown: the
                     projection sends the countdown but not yet the amount. -->
                <span v-if="isTenant" class="flex flex-col items-end leading-tight">
                    <span class="text-lg font-bold tabular-nums text-teal-light">{{
                        rentPoints || '—'
                        }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest" :class="dueTone">
                        due in {{ turnsLabel(rentDue) }}
                    </span>
                </span>
            </div>

            <section class="flex flex-col gap-2 border-t-1 border-gray-light pt-4">
                <div class="text-sm tracking-wide text-center"
                    :class="roomsByCard[residenceCardType] === 0 ? 'text-rose-400' : 'text-teal-light'">
                    {{ roomsByCard[residenceCardType] }} rooms free
                </div>
            </section>

            <!-- occupy: only when homeless and holding a property with a spare room -->
            <section v-if="!isHoused && occupiable.length"
                class="flex flex-col gap-2 border-t-1 border-gray-light pt-4">
                <span :class="labelClass">Occupy</span>
                <div class="flex flex-wrap gap-2">
                    <button v-for="opt in occupiable" :key="opt.code" type="button" :class="[
                        pickerBtn,
                        moveTarget === opt.code
                            ? 'border-purple-light bg-purple-dark/30'
                            : 'border-gray-light opacity-60 hover:opacity-100',
                    ]" @click="moveTarget = opt.code">
                        <Card :card-type="opt.code" :selected="true" :large="false" />
                        <span class="flex flex-col items-start leading-tight">
                            <span class="text-sm font-bold text-gray-2x-light">{{ opt.title }}</span>
                            <span class="text-xs tabular-nums text-teal-light">{{ opt.free }} free</span>
                        </span>
                    </button>
                </div>
                <button type="button" :class="[actionButton, purpleBtn, 'w-full']" :disabled="locked || !moveTarget"
                    @click="emit('moveIn', moveTarget)">
                    Move in
                </button>
            </section>


            <!-- request a room: only when homeless -->
            <section v-if="!isHoused" class="flex flex-col gap-3 border-t-1 border-gray-light pt-4">
                <span :class="labelClass">Request a room</span>
                <p class="text-xs leading-relaxed text-gray-x-light">
                    Broadcast what you will pay. Everyone sees it.
                </p>

                <div class="flex gap-4">
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Offer</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="rent <= 1" aria-label="Lower offer"
                                @click="stepRent(-1)">
                                −
                            </button>
                            <div :class="countClass">{{ rent }}</div>
                            <button type="button" :class="stepButton" aria-label="Raise offer" @click="stepRent(1)">
                                +
                            </button>
                        </div>
                    </div>
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Every</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="interval <= 1"
                                aria-label="Shorter interval" @click="stepInterval(-1)">
                                −
                            </button>
                            <div :class="countClass">{{ interval }}</div>
                            <button type="button" :class="stepButton" aria-label="Longer interval"
                                @click="stepInterval(1)">
                                +
                            </button>
                        </div>
                    </div>
                </div>

                <button type="button" :class="[actionButton, tealBtn, 'w-full']" :disabled="locked"
                    @click="emit('rentAsk', { rentPoints: rent, intervalTurns: interval })">
                    Post request
                </button>
            </section>


            <section v-if="isHoused" class="flex flex-col gap-2 border-t-1 border-gray-light pt-4">
                <template v-if="!isTenant">
                    <button type="button" :class="[actionButton, ghostBtn, 'w-full']" :disabled="locked"
                        @click="emit('leave')">
                        Vacate
                    </button>
                    <p class="text-xs text-gray-x-light">Frees the room to let.</p>
                </template>

                <template v-else-if="awaitingLandlord">
                    <div
                        class="flex items-center gap-2 rounded-xl border-2 border-amber-400/50 bg-amber-400/10 px-3 py-2">
                        <span class="text-[10px] font-bold uppercase tracking-widest text-amber-400">Waiting</span>
                        <span class="text-xs text-gray-x-light">
                            {{ landlordName || 'Your landlord' }} has not answered yet.
                        </span>
                    </div>
                    <p class="text-xs text-gray-x-light">
                        Accepting costs you {{ rentPoints }} rent. Refusing lets you buy your way out.
                    </p>
                </template>

                <template v-else-if="wasRefused">
                    <div
                        class="flex items-center gap-2 rounded-xl border-2 border-rose-400/50 bg-rose-400/10 px-3 py-2">
                        <span class="text-[10px] font-bold uppercase tracking-widest text-rose-400">Refused</span>
                        <span class="text-xs text-gray-x-light">Stay, or pay to go.</span>
                    </div>
                    <div class="flex gap-2">
                        <button type="button" :class="[actionButton, ghostBtn, 'flex-1']" :disabled="locked"
                            @click="emit('resolveMoveOut', false)">
                            Stay
                        </button>
                        <button type="button" :class="[actionButton, tealBtn, 'flex-1']"
                            :disabled="locked || !canAffordBuyout" @click="emit('resolveMoveOut', true)">
                            Pay {{ moveoutBuyout }}
                        </button>
                    </div>
                    <p v-if="!canAffordBuyout" class="text-xs font-bold text-rose-400">
                        You need {{ moveoutBuyout }} free points to leave.
                    </p>
                </template>

                <template v-else>
                    <button type="button" :class="[actionButton, ghostBtn, 'w-full']" :disabled="locked"
                        @click="emit('leave')">
                        Ask to leave
                    </button>
                    <p class="text-xs text-gray-x-light">
                        Your landlord decides. Accepting costs you {{ rentPoints }} rent; refusing quotes you a
                        price to go anyway.
                    </p>
                </template>
            </section>


            <p v-if="!isHoused && !occupiable.length" class="text-xs text-gray-light">
                Buy a property to live in one, or post a request and wait.
            </p>
            </div>

            <!-- ── right: being a landlord ── -->
            <div class="flex flex-col gap-4" :class="!isLet ? 'md:border-l-1 md:border-gray-light md:pl-5' : ''">
            <section class="flex flex-col gap-3">
                <span :class="labelClass">Let a room</span>

                <div class="flex items-center gap-4">
                    <div :class="[wellClass, 'p-3']">
                        <div :style="{ zoom: 0.85 }">
                            <Card :card-type="cardType" :selected="true" />
                        </div>
                    </div>
                    <div class="flex flex-col gap-1 leading-tight">
                        <span :class="labelClass">Spare</span>
                        <span class="text-2xl font-bold tabular-nums"
                            :class="roomsFreeForCard > 0 ? 'text-teal-light' : 'text-gray-light'">
                            {{ roomsFreeForCard }}
                        </span>
                        <!-- Rooms already promised explain why capacity looks short
                         of the card's own room count. -->
                        <span v-if="roomsPendingForCard > 0" class="text-[10px] font-bold text-amber-400">
                            {{ roomsPendingForCard }} already offered
                        </span>
                    </div>
                </div>

                <div class="flex gap-4">
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Rent</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="rent <= 1" aria-label="Lower rent"
                                @click="stepRent(-1)">
                                −
                            </button>
                            <div :class="countClass">{{ rent }}</div>
                            <button type="button" :class="stepButton" aria-label="Raise rent" @click="stepRent(1)">
                                +
                            </button>
                        </div>
                    </div>
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Every</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="interval <= 1"
                                aria-label="Shorter interval" @click="stepInterval(-1)">
                                −
                            </button>
                            <div :class="countClass">{{ interval }}</div>
                            <button type="button" :class="stepButton" aria-label="Longer interval"
                                @click="stepInterval(1)">
                                +
                            </button>
                        </div>
                    </div>
                </div>

                <p
                    class="rounded-xl border-2 border-teal-light/40 bg-teal-light/10 px-4 py-2 text-center text-sm font-bold text-gray-2x-light">
                    {{ rent }} pts every {{ turnsLabel(interval) }}
                </p>

                <footer class="flex items-center gap-3">
                    <button type="button" :class="[actionButton, tealBtn, 'w-full']"
                        :disabled="locked || roomsFreeForCard < 1"
                        @click="emit('rentOut', { cardType, rentPoints: rent, intervalTurns: interval })">
                        Post room
                    </button>
                </footer>
            </section>


            <section v-if="tenants.length" class="flex flex-col gap-2 border-t-1 border-gray-light pt-4">
                <span :class="labelClass">Your tenants</span>
                <div v-for="t in tenants" :key="t.agreementId" class="flex flex-col gap-2 rounded-xl border-2 px-3 py-2"
                    :class="t.moveoutStatus === 'requested'
                            ? 'border-amber-400/50 bg-amber-400/10'
                            : 'border-gray-light'
                        ">
                    <div class="flex items-center gap-2">
                        <SeatToken :seat-index="t.tenantSeatIndex" size="sm" />
                        <span class="min-w-0 flex-1 truncate text-xs font-bold text-gray-2x-light">
                            {{ t.tenantName }}
                        </span>
                        <span class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">
                            {{ t.rentPoints }} · {{ turnsLabel(t.turnsUntilDue) }}
                        </span>
                    </div>

                    <div v-if="t.moveoutStatus === 'requested'" class="flex gap-2">
                        <button type="button" :class="[actionButton, ghostBtn, 'flex-1 py-1.5 text-xs']"
                            :disabled="busy"
                            @click="emit('respondMoveOut', { agreementId: t.agreementId, accept: false })">
                            Refuse
                        </button>
                        <button type="button" :class="[actionButton, tealBtn, 'flex-1 py-1.5 text-xs']" :disabled="busy"
                            @click="emit('respondMoveOut', { agreementId: t.agreementId, accept: true })">
                            Let go for {{ t.rentPoints }}
                        </button>
                    </div>

                    <button v-else type="button" :class="[actionButton, ghostBtn, 'w-full py-1.5 text-xs']"
                        :disabled="busy" @click="emit('evict', t.agreementId)">
                        Evict · forfeit {{ t.rentPoints }}
                    </button>
                </div>
            </section>


            </div>
        </div>

        <p v-if="turnNote" class="text-xs font-bold text-gray-light">{{ turnNote }}</p>
    </div>
</template>