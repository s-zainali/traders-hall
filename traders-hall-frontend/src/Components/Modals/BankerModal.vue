<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * The bank's credit desk: one unsecured loan and one mortgage per player.
 *
 * Both halves are status-or-form, never both: an active debt replaces its own
 * borrow control with a repay control. There is nothing to choose between, so
 * showing a disabled "borrow" next to a live loan would only invite a click
 * the server would refuse.
 */
const props = defineProps({
    // an action is in flight — every control locks so a double-click cannot
    // submit the same loan twice
    busy: { type: Boolean, default: false },
    // credit is turn-gated on the server; disabling here is so the player can
    // see that from the controls rather than from a rejected request
    canAct: { type: Boolean, default: false },

    // spendable balance: points minus anything reserved against a market claim
    availablePoints: { type: Number, default: 0 },
    // { cardType: quantity } — raw counts, straight from the projection
    hand: { type: Object, default: () => ({}) },

    loanOutstanding: { type: Number, default: 0 },
    loanDue: { type: Number, default: 0 },
    mortgageCardType: { type: String, default: null },
    mortgageOutstanding: { type: Number, default: 0 },
    mortgageDue: { type: Number, default: 0 },

    /*
      Mirrors LOAN_MAX_PRINCIPAL in app/domain/config.py. The server is
      authoritative and returns the real limit in the error detail, so a drift
      here costs a rejected request rather than a wrong game state — but it IS
      a duplicated constant. Serving the credit terms from
      /api/v1/config would remove it.
    */
    maxLoan: { type: Number, default: 5 },
})

const emit = defineEmits(['closeModal', 'borrow', 'repay', 'mortgage', 'redeem'])

const cardTypes = useCardTypesStore()

const hasLoan = computed(() => props.loanOutstanding > 0)
const hasMortgage = computed(() => props.mortgageOutstanding > 0)

/* ── loan ─────────────────────────────────────────────────────────── */

const borrowAmount = ref(1)
const repayAmount = ref(1)

// Never offer more than the bank lends. The stepper stopping at a reachable
// number is friendlier than letting someone pick 8 and get a 422 back.
const maxBorrow = computed(() => Math.max(1, props.maxLoan))

// Repayment is capped by what is owed AND by what can actually be paid, so the
// control cannot express an impossible amount.
const maxRepay = computed(() =>
    Math.max(1, Math.min(props.loanOutstanding, props.availablePoints))
)

const canRepayAnything = computed(
    () => hasLoan.value && props.availablePoints >= 1
)

function clamp(value, max) {
    return Math.min(max, Math.max(1, value))
}
const stepBorrow = (d) => (borrowAmount.value = clamp(borrowAmount.value + d, maxBorrow.value))
const stepRepay = (d) => (repayAmount.value = clamp(repayAmount.value + d, maxRepay.value))

// The outstanding balance moves under this component every time upkeep runs or
// a repayment lands, so a stepper left at a now-impossible number would submit
// one. Re-clamping on change keeps it inside the current bounds.
watch(maxRepay, (max) => {
    repayAmount.value = clamp(repayAmount.value, max)
})

/* ── mortgage ─────────────────────────────────────────────────────── */

const chosenProperty = ref('')

/**
 * Properties that can back a mortgage: owned, and worth something.
 *
 * The projection sends raw hand counts, not free ones, so a card reserved
 * against an open market offer still appears here and the server will refuse
 * it. The mortgaged card itself is excluded explicitly — that is the one case
 * this component can detect on its own.
 */
const mortgageable = computed(() =>
    cardTypes.all
        .filter(
            (c) =>
                c.category === 'property' &&
                c.sellValue > 0 &&
                (props.hand[c.code] ?? 0) > 0 &&
                c.code !== props.mortgageCardType
        )
        .map((c) => ({ code: c.code, title: c.title, advance: c.sellValue }))
)

const chosenAdvance = computed(
    () => mortgageable.value.find((c) => c.code === chosenProperty.value)?.advance ?? 0
)

// Preselect the first option so the common case is one click, and drop a stale
// pick if the hand changes underneath it.
watch(
    mortgageable,
    (list) => {
        if (!list.some((c) => c.code === chosenProperty.value)) {
            chosenProperty.value = list[0]?.code ?? ''
        }
    },
    { immediate: true }
)

const canRedeem = computed(
    () => hasMortgage.value && props.availablePoints >= props.mortgageOutstanding
)

function titleOf(code) {
    return cardTypes.get(code)?.title ?? code
}

/* ── behaviour ────────────────────────────────────────────────────── */

function onKeydown(e) {
    if (e.key === 'Escape') emit('closeModal')
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

const locked = computed(() => props.busy || !props.canAct)

const dueTone = (rounds) =>
    rounds <= 1 ? 'text-rose-400' : rounds <= 2 ? 'text-amber-400' : 'text-gray-x-light'

const roundsLabel = (n) => (n === 1 ? '1 round' : `${n} rounds`)

const cardClass =
    'flex flex-col gap-4 rounded-[1rem] border-2 border-gray-light bg-gray-dark p-5'
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'
const stepperShell = 'flex w-max overflow-hidden rounded-xl border-2 border-gray-x-light'
const stepperBtn =
    'w-9 cursor-pointer bg-gray-x-dark text-lg font-bold text-gray-2x-light ' +
    'transition duration-200 ease-in-out hover:bg-gray-light disabled:cursor-not-allowed disabled:opacity-40'
const countBox =
    'flex w-14 items-center justify-center bg-gray-x-dark py-1.5 text-lg font-bold tabular-nums text-gray-2x-light'
const primaryBtn =
    'cursor-pointer rounded-xl border-2 px-5 py-2.5 font-bold transition duration-200 ease-in-out ' +
    'disabled:cursor-not-allowed disabled:opacity-40'
</script>

<template>
    <!-- backdrop: click outside to dismiss -->
    <div class="absolute inset-0 z-[100] flex items-center justify-center overflow-y-auto p-6 bg-gray-dark/90 backdrop-blur-sm"
        @click.self="emit('closeModal')">

        <div role="dialog" aria-modal="true" aria-labelledby="banker-title"
            class="relative flex w-max max-w-full flex-col gap-6 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-8 shadow-2xl shadow-black/50">

            <button type="button" aria-label="Close" @click="emit('closeModal')"
                class="absolute top-0 right-0 z-50 flex items-center justify-center p-4 leading-none text-gray-x-light transition duration-200 ease-in-out hover:cursor-pointer hover:text-rose-400">🗙</button>

            <header class="flex items-center gap-4 pr-10">
                <div class="h-12 w-12 shrink-0 bg-teal-light" :style="{
                    mask: `url(/accountant.png) no-repeat center / contain`,
                    '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
                }"></div>
                <div class="flex flex-col gap-1">
                    <h2 id="banker-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">Loan Manager</h2>
                    <p class="text-sm text-gray-x-light">
                        {{ canAct ? 'One loan and one mortgage at a time.' : 'Credit is only available on your turn.' }}
                    </p>
                </div>
                <div class="ml-6 flex flex-col items-end leading-tight">
                    <span :class="labelClass">Available</span>
                    <span class="text-xl font-bold tabular-nums text-teal-light">{{ availablePoints }}</span>
                </div>
            </header>

            <div class="grid gap-4 border-t-1 border-gray-light pt-6 md:grid-cols-2">

                <!-- ── loan ────────────────────────────────────────── -->
                <section :class="cardClass">
                    <div class="flex items-baseline justify-between gap-6">
                        <h3 class="text-lg font-bold text-gray-2x-light">Loan</h3>
                        <span v-if="hasLoan" class="text-xs font-bold" :class="dueTone(loanDue)">
                            due in {{ roundsLabel(loanDue) }}
                        </span>
                    </div>

                    <template v-if="hasLoan">
                        <div class="flex items-baseline gap-2">
                            <span class="text-3xl font-bold tabular-nums text-rose-400">{{ loanOutstanding }}</span>
                            <span class="text-sm text-gray-x-light">outstanding</span>
                        </div>

                        <p class="text-xs leading-relaxed text-gray-x-light">
                            Unpaid at zero, the bank takes your points and seizes property to cover the rest.
                        </p>

                        <div class="flex flex-col gap-2">
                            <span :class="labelClass">Repay</span>
                            <div class="flex items-center gap-3">
                                <div :class="stepperShell">
                                    <button type="button" :class="stepperBtn" :disabled="repayAmount <= 1"
                                        aria-label="Decrease repayment" @click="stepRepay(-1)">−</button>
                                    <div :class="countBox">{{ repayAmount }}</div>
                                    <button type="button" :class="stepperBtn" :disabled="repayAmount >= maxRepay"
                                        aria-label="Increase repayment" @click="stepRepay(1)">+</button>
                                </div>
                                <button type="button" :class="[primaryBtn, 'border-teal-light bg-teal-light text-gray-dark hover:brightness-110']"
                                    :disabled="locked || !canRepayAnything"
                                    @click="emit('repay', repayAmount)">Repay</button>
                            </div>
                            <span v-if="!canRepayAnything" class="text-xs font-bold text-rose-400">
                                No free points to repay with
                            </span>
                        </div>
                    </template>

                    <template v-else>
                        <p class="text-xs leading-relaxed text-gray-x-light">
                            Borrow up to {{ maxLoan }} points, interest free. Repayable over
                            {{ roundsLabel(5) }}.
                        </p>

                        <div class="flex flex-col gap-2">
                            <span :class="labelClass">Amount</span>
                            <div class="flex items-center gap-3">
                                <div :class="stepperShell">
                                    <button type="button" :class="stepperBtn" :disabled="borrowAmount <= 1"
                                        aria-label="Decrease amount" @click="stepBorrow(-1)">−</button>
                                    <div :class="countBox">{{ borrowAmount }}</div>
                                    <button type="button" :class="stepperBtn" :disabled="borrowAmount >= maxBorrow"
                                        aria-label="Increase amount" @click="stepBorrow(1)">+</button>
                                </div>
                                <button type="button" :class="[primaryBtn, 'border-emerald-400 bg-emerald-400 text-gray-dark hover:brightness-110']"
                                    :disabled="locked" @click="emit('borrow', borrowAmount)">Borrow</button>
                            </div>
                        </div>
                    </template>
                </section>

                <!-- ── mortgage ────────────────────────────────────── -->
                <section :class="cardClass">
                    <div class="flex items-baseline justify-between gap-6">
                        <h3 class="text-lg font-bold text-gray-2x-light">Mortgage</h3>
                        <span v-if="hasMortgage" class="text-xs font-bold" :class="dueTone(mortgageDue)">
                            due in {{ roundsLabel(mortgageDue) }}
                        </span>
                    </div>

                    <template v-if="hasMortgage">
                        <div class="flex items-baseline gap-2">
                            <span class="text-3xl font-bold tabular-nums text-rose-400">{{ mortgageOutstanding }}</span>
                            <span class="text-sm text-gray-x-light">
                                against your {{ titleOf(mortgageCardType) }}
                            </span>
                        </div>

                        <p class="text-xs leading-relaxed text-gray-x-light">
                            The card stays in your hand but cannot be sold or traded. Unredeemed at zero, the bank
                            takes it.
                        </p>

                        <div class="flex flex-col gap-2">
                            <button type="button" :class="[primaryBtn, 'w-max border-teal-light bg-teal-light text-gray-dark hover:brightness-110']"
                                :disabled="locked || !canRedeem"
                                @click="emit('redeem')">Redeem for {{ mortgageOutstanding }}</button>
                            <span v-if="!canRedeem" class="text-xs font-bold text-rose-400">
                                Need {{ mortgageOutstanding }} free points
                            </span>
                        </div>
                    </template>

                    <template v-else-if="mortgageable.length">
                        <p class="text-xs leading-relaxed text-gray-x-light">
                            Raise points against a property. You keep the card, but it is locked until you redeem it.
                        </p>

                        <div class="flex flex-col gap-2">
                            <span :class="labelClass">Property</span>
                            <div class="flex flex-wrap gap-2">
                                <button v-for="option in mortgageable" :key="option.code" type="button"
                                    @click="chosenProperty = option.code"
                                    class="cursor-pointer rounded-xl border-2 px-4 py-2 text-left transition duration-200 ease-in-out"
                                    :class="chosenProperty === option.code
                                        ? 'border-purple-light bg-purple-dark/30 text-gray-2x-light'
                                        : 'border-gray-light text-gray-x-light hover:border-gray-x-light'">
                                    <span class="block text-sm font-bold">{{ option.title }}</span>
                                    <span class="block text-xs tabular-nums">+{{ option.advance }} pts</span>
                                </button>
                            </div>

                            <button type="button" :class="[primaryBtn, 'mt-2 w-max border-purple-light bg-purple-light text-gray-dark hover:brightness-110']"
                                :disabled="locked || !chosenProperty"
                                @click="emit('mortgage', chosenProperty)">
                                Mortgage for {{ chosenAdvance }}
                            </button>
                        </div>
                    </template>

                    <template v-else>
                        <p class="text-sm text-gray-light">You own no property to mortgage.</p>
                    </template>
                </section>
            </div>
        </div>
    </div>
</template>