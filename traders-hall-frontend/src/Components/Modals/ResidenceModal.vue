<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import SeatToken from '../SeatToken.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * Housing, from the residence box.
 *
 * One modal with sections rather than several, because every path here answers
 * the same question — where do you live and who pays whom — and which sections
 * apply is decided by state, not by which button was pressed:
 *
 *   housed          → status, and Leave
 *   homeless + own  → Move in
 *   homeless        → Request a room (broadcast, any landlord may answer)
 *   spare capacity  → Let a room (one offer per room)
 *
 * A landlord who lives in their own tower sees status, Leave AND Let a room at
 * once, which is exactly right: those are three separate things they can do.
 */
const props = defineProps({
    busy: { type: Boolean, default: false },
    // housing is turn-gated on the server; disabling here shows the player why
    canAct: { type: Boolean, default: false },

    // { cardType: quantity } — raw counts from the projection
    hand: { type: Object, default: () => ({}) },

    residenceCardType: { type: String, default: null },
    // set alongside a residence = renting; null alongside one = own property
    residenceLandlordId: { type: String, default: null },
    landlordName: { type: String, default: '' },
    landlordSeatIndex: { type: Number, default: -1 },

    // terms of the tenancy the player is IN, if any
    rentPoints: { type: Number, default: 0 },
    rentDue: { type: Number, default: 0 },

    roomsTotal: { type: Number, default: 0 },
    roomsOccupied: { type: Number, default: 0 },
    roomsFree: { type: Number, default: 0 },
    // lettable rooms per property type, already net of tenants, the owner
    // themselves, and rooms promised by live offers
    roomsByCard: { type: Object, default: () => ({}) },

    // how many tenants this player is landlord to, for the summary line
    tenantCount: { type: Number, default: 0 },
})

const emit = defineEmits(['closeModal', 'moveIn', 'leave', 'rentOut', 'rentAsk'])

const cardTypes = useCardTypesStore()

const isHoused = computed(() => !!props.residenceCardType)
const isTenant = computed(() => isHoused.value && !!props.residenceLandlordId)
const isOwnerOccupier = computed(() => isHoused.value && !props.residenceLandlordId)

function titleOf(code) {
    return cardTypes.get(code)?.title ?? code
}
function roomsOf(code) {
    return cardTypes.get(code)?.rooms ?? 0
}

/* ── move in ─────────────────────────────────────────────────────── */

/**
 * Own properties with a room going spare.
 *
 * roomsByCard is already net of tenants, of the owner themselves and of rooms
 * promised by live offers, so it needs no further filtering — which is the point
 * of computing capacity server-side rather than guessing from the hand.
 */
const movableInto = computed(() =>
    Object.entries(props.roomsByCard)
        .filter(([, free]) => free > 0)
        .map(([code, free]) => ({ code, free, title: titleOf(code), rooms: roomsOf(code) }))
)

const moveTarget = ref('')
watch(movableInto, (list) => {
    if (!list.some((c) => c.code === moveTarget.value)) moveTarget.value = list[0]?.code ?? ''
}, { immediate: true })

/* ── let a room ──────────────────────────────────────────────────── */

const letTarget = ref('')
const letRent = ref(1)
const letInterval = ref(3)

watch(movableInto, (list) => {
    if (!list.some((c) => c.code === letTarget.value)) letTarget.value = list[0]?.code ?? ''
}, { immediate: true })

/* ── request a room ──────────────────────────────────────────────── */

const askRent = ref(1)
const askInterval = ref(3)

function clamp(v, lo, hi) {
    return Math.min(hi, Math.max(lo, v))
}
const stepLetRent = (d) => (letRent.value = clamp(letRent.value + d, 1, 99))
const stepLetInterval = (d) => (letInterval.value = clamp(letInterval.value + d, 1, 20))
const stepAskRent = (d) => (askRent.value = clamp(askRent.value + d, 1, 99))
const stepAskInterval = (d) => (askInterval.value = clamp(askInterval.value + d, 1, 20))

/* ── behaviour ───────────────────────────────────────────────────── */

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const locked = computed(() => props.busy || !props.canAct)
const turnNote = computed(() => (props.canAct ? '' : 'Only on your turn'))

const dueTone = computed(() =>
    props.rentDue <= 1 ? 'text-rose-400' : props.rentDue <= 2 ? 'text-amber-400' : 'text-teal-light'
)
const turnsLabel = (n) => (n === 1 ? '1 turn' : `${n} turns`)

/* ── class vocabulary, shared with the other modals in this app ──── */
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
    'flex items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'
const actionButton =
    'px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
    'disabled:opacity-40 disabled:cursor-not-allowed ' +
    'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'

const purpleBtn = 'bg-purple-light text-gray-dark border-2 border-purple-light hover:brightness-110'
const tealBtn = 'bg-teal-light text-gray-dark border-2 border-teal-light hover:brightness-110'
const ghostBtn =
    'border-2 border-gray-light text-gray-x-light hover:border-rose-400 hover:text-rose-400'

const pickerBtn = 'flex cursor-pointer items-center gap-2 rounded-xl border-2 px-3 py-2 transition duration-200 ease-in-out'
const pickerOn = 'border-purple-light bg-purple-dark/30'
const pickerOff = 'border-gray-light opacity-60 hover:opacity-100'
const sectionClass = 'flex shrink-0 flex-col gap-3 border-t-1 border-gray-light pt-5'
</script>

<template>
    <div class="absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 p-4 backdrop-blur-sm"
        @click.self="emit('closeModal')">

        <div role="dialog" aria-modal="true" aria-labelledby="residence-title"
            class="scroll-slim relative flex max-h-full w-[23rem] max-w-full flex-col gap-5 overflow-y-auto p-6">

            <button type="button" aria-label="Close" @click="emit('closeModal')"
                class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light">✕</button>

            <header class="flex flex-col gap-0.5 pr-10">
                <h2 id="residence-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
                    Residence
                </h2>
                <p class="text-sm text-gray-x-light">
                    {{ isTenant ? 'You rent a room.' : isOwnerOccupier ? 'You live in your own property.'
                        : 'You have nowhere to live.' }}
                </p>
            </header>

            <!-- ── where you live ──────────────────────────────────── -->
            <div v-if="isHoused" :class="[wellClass, 'shrink-0 justify-between gap-3 px-4 py-3']">
                <span class="flex items-center gap-2">
                    <Card :card-type="residenceCardType" :selected="true" :large="false" />
                    <span class="flex flex-col leading-tight">
                        <span class="text-sm font-bold text-gray-2x-light">{{ titleOf(residenceCardType) }}</span>
                        <span v-if="isTenant" class="flex items-center gap-1 text-xs text-gray-x-light">
                            <SeatToken :seat-index="landlordSeatIndex" size="sm" />
                            {{ landlordName }}
                        </span>
                        <span v-else class="text-xs text-gray-x-light">Yours</span>
                    </span>
                </span>
                <span v-if="isTenant" class="flex flex-col items-end leading-tight">
                    <span class="text-lg font-bold tabular-nums text-teal-light">{{ rentPoints }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest" :class="dueTone">
                        due in {{ turnsLabel(rentDue) }}
                    </span>
                </span>
            </div>

            <!-- Capacity summary. Shown to any owner, since it is the number
                 every other section depends on. -->
            <div v-if="roomsTotal > 0" class="flex shrink-0 items-center justify-between gap-3 text-xs">
                <span :class="labelClass">Your rooms</span>
                <span class="font-bold tabular-nums text-gray-2x-light">
                    {{ roomsOccupied }} / {{ roomsTotal }} used
                    <span v-if="tenantCount" class="text-gray-x-light">
                        · {{ tenantCount }} {{ tenantCount === 1 ? 'tenant' : 'tenants' }}
                    </span>
                </span>
            </div>

            <!-- ── move in ─────────────────────────────────────────── -->
            <section v-if="!isHoused && movableInto.length" :class="sectionClass">
                <h3 :class="labelClass">Move in</h3>
                <p class="text-xs leading-relaxed text-gray-x-light">
                    Occupy a room in a property you own. It costs nothing, but it uses a room you could
                    otherwise let.
                </p>
                <div class="flex flex-wrap gap-2">
                    <button v-for="opt in movableInto" :key="opt.code" type="button" :class="[
                        pickerBtn, moveTarget === opt.code ? pickerOn : pickerOff,
                    ]" @click="moveTarget = opt.code">
                        <Card :card-type="opt.code" :selected="true" :large="false" />
                        <span class="flex flex-col items-start leading-tight">
                            <span class="text-sm font-bold text-gray-2x-light">{{ opt.title }}</span>
                            <span class="text-xs tabular-nums text-teal-light">{{ opt.free }} free</span>
                        </span>
                    </button>
                </div>
                <button type="button" :class="[actionButton, purpleBtn, 'w-full']"
                    :disabled="locked || !moveTarget" @click="emit('moveIn', moveTarget)">
                    Move in
                </button>
            </section>

            <!-- ── leave ───────────────────────────────────────────── -->
            <section v-if="isHoused" :class="sectionClass">
                <h3 :class="labelClass">Leave</h3>
                <p class="text-xs leading-relaxed text-gray-x-light">
                    {{ isTenant
                        ? 'Ends the tenancy and frees your landlord\'s room. No penalty and no notice.'
                        : 'Vacate your own property, freeing the room to let.' }}
                </p>
                <button type="button" :class="[actionButton, ghostBtn, 'w-full']" :disabled="locked"
                    @click="emit('leave')">
                    Leave residence
                </button>
            </section>

            <!-- ── let a room ──────────────────────────────────────── -->
            <section v-if="roomsFree > 0" :class="sectionClass">
                <h3 :class="labelClass">Let a room</h3>
                <p class="text-xs leading-relaxed text-gray-x-light">
                    One room per offer. You set the rent and how often it falls due; the property stays
                    yours and stays sellable.
                </p>

                <div class="flex flex-wrap gap-2">
                    <button v-for="opt in movableInto" :key="opt.code" type="button" :class="[
                        pickerBtn, letTarget === opt.code ? pickerOn : pickerOff,
                    ]" @click="letTarget = opt.code">
                        <Card :card-type="opt.code" :selected="true" :large="false" />
                        <span class="flex flex-col items-start leading-tight">
                            <span class="text-sm font-bold text-gray-2x-light">{{ opt.title }}</span>
                            <span class="text-xs tabular-nums text-teal-light">{{ opt.free }} free</span>
                        </span>
                    </button>
                </div>

                <div class="flex flex-wrap gap-4">
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Rent</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="letRent <= 1"
                                aria-label="Lower rent" @click="stepLetRent(-1)">−</button>
                            <div :class="[countClass, 'w-12']">{{ letRent }}</div>
                            <button type="button" :class="stepButton" aria-label="Raise rent"
                                @click="stepLetRent(1)">+</button>
                        </div>
                    </div>
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Every</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="letInterval <= 1"
                                aria-label="Shorter interval" @click="stepLetInterval(-1)">−</button>
                            <div :class="[countClass, 'w-12']">{{ letInterval }}</div>
                            <button type="button" :class="stepButton" aria-label="Longer interval"
                                @click="stepLetInterval(1)">+</button>
                        </div>
                    </div>
                </div>

                <p class="text-xs font-bold tabular-nums text-teal-light">
                    {{ letRent }} every {{ turnsLabel(letInterval) }}
                </p>

                <button type="button" :class="[actionButton, tealBtn, 'w-full']"
                    :disabled="locked || !letTarget"
                    @click="emit('rentOut', { cardType: letTarget, rentPoints: letRent, intervalTurns: letInterval })">
                    Post room
                </button>
            </section>

            <!-- ── request a room ──────────────────────────────────── -->
            <section v-if="!isHoused" :class="sectionClass">
                <h3 :class="labelClass">Request a room</h3>
                <p class="text-xs leading-relaxed text-gray-x-light">
                    Broadcast what you will pay. Every player sees it, but only those with a spare room can
                    accept — and they choose which property.
                </p>

                <div class="flex flex-wrap gap-4">
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Offer</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="askRent <= 1"
                                aria-label="Lower offer" @click="stepAskRent(-1)">−</button>
                            <div :class="[countClass, 'w-12']">{{ askRent }}</div>
                            <button type="button" :class="stepButton" aria-label="Raise offer"
                                @click="stepAskRent(1)">+</button>
                        </div>
                    </div>
                    <div class="flex flex-col gap-1">
                        <span :class="labelClass">Every</span>
                        <div :class="[stepperClass, 'shrink-0']">
                            <button type="button" :class="stepButton" :disabled="askInterval <= 1"
                                aria-label="Shorter interval" @click="stepAskInterval(-1)">−</button>
                            <div :class="[countClass, 'w-12']">{{ askInterval }}</div>
                            <button type="button" :class="stepButton" aria-label="Longer interval"
                                @click="stepAskInterval(1)">+</button>
                        </div>
                    </div>
                </div>

                <p class="text-xs font-bold tabular-nums text-teal-light">
                    {{ askRent }} every {{ turnsLabel(askInterval) }}
                </p>

                <button type="button" :class="[actionButton, tealBtn, 'w-full']" :disabled="locked"
                    @click="emit('rentAsk', { rentPoints: askRent, intervalTurns: askInterval })">
                    Post request
                </button>
            </section>

            <!-- Nothing available: own nothing, live nowhere, cannot let. Say so
                 rather than showing an empty modal. -->
            <p v-if="!isHoused && !movableInto.length && roomsFree === 0"
                :class="[sectionClass, 'text-sm text-gray-light']">
                Buy a property to live in one, or post a request and wait for a landlord.
            </p>

            <footer class="flex shrink-0 items-center justify-between gap-3 border-t-1 border-gray-light pt-4">
                <span v-if="turnNote" class="text-xs font-bold text-gray-light">{{ turnNote }}</span>
                <button type="button" :class="[actionButton, 'ml-auto border-2 border-gray-light text-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light']"
                    @click="emit('closeModal')">Close</button>
            </footer>
        </div>
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

.scroll-slim::-webkit-scrollbar-track {
    background: transparent;
}

.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}
</style>