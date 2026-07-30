<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import Card from '../Card.vue'
import { useCardTypesStore } from '../../stores/cardTypes'

/**
 * The bank's credit desk: one unsecured loan and one mortgage per player.
 *
 * Laid out as a SINGLE COLUMN, deliberately. This renders inside the bank
 * panel, which is `w-max` shrink-to-fit and `overflow-hidden` — a two-column
 * grid overflows that box and gets clipped, taking the confirm buttons with it.
 * The sibling TransactionModal renders in the same slot and solves it the same
 * way: content column on the blurred backdrop, no card chrome of its own.
 *
 * Both halves are status-or-form, never both: an active debt replaces its own
 * borrow control with a repay control. There is nothing to choose between, so
 * a disabled "borrow" beside a live loan would only invite a refused click.
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
      Mirrors LOAN_MAX_PRINCIPAL in app/domain/config.py, and LOAN_TERM_ROUNDS
      alongside it. The server is authoritative and returns the real limit in
      the error detail, so drift costs a rejected request rather than a wrong
      game state — but these ARE duplicated constants. Serving the credit terms
      from /api/v1/config would remove them.
    */
  maxLoan: { type: Number, default: 5 },
  loanTerm: { type: Number, default: 5 },
})

const emit = defineEmits(['closeModal', 'borrow', 'repay', 'mortgage', 'redeem'])

const cardTypes = useCardTypesStore()

const hasLoan = computed(() => props.loanOutstanding > 0)
const hasMortgage = computed(() => props.mortgageOutstanding > 0)

/* ── loan ─────────────────────────────────────────────────────────── */

const borrowAmount = ref(1)
const repayAmount = ref(1)

// Never offer more than the bank lends: a stepper that stops at a reachable
// number is friendlier than letting someone pick 8 and get a 422 back.
const maxBorrow = computed(() => Math.max(1, props.maxLoan))

// Repayment is capped by what is owed AND by what can actually be paid, so the
// control cannot express an impossible amount.
const maxRepay = computed(() => Math.max(1, Math.min(props.loanOutstanding, props.availablePoints)))

const canRepayAnything = computed(() => hasLoan.value && props.availablePoints >= 1)

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
        c.code !== props.mortgageCardType,
    )
    .map((c) => ({ code: c.code, title: c.title, advance: c.sellValue })),
)

const chosenAdvance = computed(
  () => mortgageable.value.find((c) => c.code === chosenProperty.value)?.advance ?? 0,
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
  { immediate: true },
)

const canRedeem = computed(
  () => hasMortgage.value && props.availablePoints >= props.mortgageOutstanding,
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

/*
  Why a control is unavailable, in the control's own words.

  A greyed button with no explanation is indistinguishable from a broken one —
  which is exactly how the last version read when it was clipped out of view.
*/
const loanBlocker = computed(() => {
  if (!props.canAct) return 'Only on your turn'
  if (hasLoan.value && !canRepayAnything.value) return 'No free points to repay with'
  return ''
})

const mortgageBlocker = computed(() => {
  if (!props.canAct) return 'Only on your turn'
  if (hasMortgage.value && !canRedeem.value) return `Need ${props.mortgageOutstanding} free points`
  if (!hasMortgage.value && !mortgageable.value.length) return 'No free property to mortgage'
  return ''
})

const roundsLabel = (n) => (n === 1 ? '1 round' : `${n} rounds`)

const dueTone = (rounds) =>
  rounds <= 1 ? 'text-rose-400' : rounds <= 2 ? 'text-amber-400' : 'text-teal-light'

/* ── class vocabulary ─────────────────────────────────────────────
   Borrowed verbatim from TransactionModal so the two modals in this panel are
   visibly the same kind of object. Full literal strings, as ever: Tailwind
   cannot see an interpolated class name.
────────────────────────────────────────────────────────────────── */
const labelClass = 'text-xs font-bold uppercase tracking-widest text-gray-x-light'

const wellClass =
  'flex items-center justify-center rounded-[1rem] bg-gray-dark border-1 border-gray-light'

const stepperClass = 'flex rounded-2xl overflow-hidden border-2 border-gray-x-light w-max'

const stepButton =
  'w-10 h-10 flex items-center justify-center text-2xl font-bold text-gray-2x-light bg-gray-light ' +
  'cursor-pointer hover:bg-gray-x-light hover:text-gray-dark transition duration-200 ease-in-out ' +
  'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-gray-light disabled:hover:text-gray-2x-light ' +
  'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:-outline-offset-2'

const countClass =
  'flex items-center justify-center font-bold text-gray-2x-light bg-gray-dark tabular-nums'

const actionButton =
  'min-w-24 px-5 py-2.5 rounded-xl font-bold cursor-pointer transition duration-200 ease-in-out ' +
  'disabled:opacity-40 disabled:cursor-not-allowed ' +
  'focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2'

const borrowClass =
  'bg-emerald-400 text-gray-dark border-2 border-emerald-400 hover:bg-emerald-300 hover:border-emerald-300'
const repayClass = 'bg-teal-light text-gray-dark border-2 border-teal-light hover:brightness-110'
const mortgageClass =
  'bg-purple-light text-gray-dark border-2 border-purple-light hover:brightness-110'
</script>

<template>
  <!--
        Backdrop matches TransactionModal exactly: absolute over the panel,
        blurred, click-outside to dismiss. min-h-0 plus an inner scroll means
        the content can never be clipped by the panel's overflow-hidden — the
        failure that made the old two-column version unusable.
    -->
  <div
    class="absolute inset-0 z-[100] flex items-center justify-center bg-gray-dark/90 p-4 backdrop-blur-sm"
    @click.self="emit('closeModal')"
  >
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="banker-title"
      class="scroll-slim relative flex max-h-full w-[21rem] max-w-full flex-col gap-5 overflow-y-auto p-6"
    >
      <button
        type="button"
        aria-label="Close"
        @click="emit('closeModal')"
        class="absolute top-3 right-3 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg text-gray-x-light transition-colors duration-200 hover:bg-gray-light/40 hover:text-gray-2x-light"
      >
        ✕
      </button>

      <header class="flex items-center gap-3 pr-10">
        <div
          class="h-10 w-10 shrink-0 bg-teal-light"
          :style="{
            mask: `url(/accountant.png) no-repeat center / contain`,
            '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
          }"
        ></div>
        <div class="flex min-w-0 flex-col gap-0.5">
          <h2 id="banker-title" class="text-2xl font-bold tracking-wide text-gray-2x-light">
            Loan Manager
          </h2>
          <p class="text-sm text-gray-x-light">One loan and one mortgage at a time.</p>
        </div>
      </header>

      <!-- Spendable, not the raw total: reserved points cannot pay a debt
                 any more than they can buy a card. -->
      <div :class="[wellClass, 'shrink-0 justify-between gap-2 px-4 py-2']">
        <span :class="labelClass">Available</span>
        <span class="flex items-center gap-2">
          <span class="text-xl font-bold tabular-nums text-teal-light">{{ availablePoints }}</span>
          <Card :card-type="'point'" :selected="true" :large="false" />
        </span>
      </div>

      <!-- ── loan ────────────────────────────────────────────── -->
      <section class="flex shrink-0 flex-col gap-3 border-t-1 border-gray-light pt-5">
        <div class="flex items-baseline justify-between gap-4">
          <h3 :class="labelClass">Loan</h3>
          <span v-if="hasLoan" class="text-xs font-bold" :class="dueTone(loanDue)">
            due in {{ roundsLabel(loanDue) }}
          </span>
        </div>

        <template v-if="hasLoan">
          <div :class="[wellClass, 'justify-between gap-2 px-4 py-2']">
            <span class="text-sm text-gray-x-light">Outstanding</span>
            <span class="text-2xl font-bold tabular-nums text-rose-400">{{ loanOutstanding }}</span>
          </div>

          <p class="text-xs leading-relaxed text-gray-x-light">
            Unpaid at zero, the bank takes your points and seizes property to cover the rest.
          </p>

          <!-- shrink-0 on both: a flex item defaults to shrinking
                         below its content, which is what collapsed the stepper
                         to a sliver in the old two-column layout. -->
          <div class="flex items-center justify-between gap-3">
            <div :class="[stepperClass, 'shrink-0']">
              <button
                type="button"
                :class="stepButton"
                :disabled="repayAmount <= 1"
                aria-label="Decrease repayment"
                @click="stepRepay(-1)"
              >
                −
              </button>
              <div :class="[countClass, 'w-14 text-lg']">{{ repayAmount }}</div>
              <button
                type="button"
                :class="stepButton"
                :disabled="repayAmount >= maxRepay"
                aria-label="Increase repayment"
                @click="stepRepay(1)"
              >
                +
              </button>
            </div>
            <button
              type="button"
              :class="[actionButton, repayClass, 'shrink-0']"
              :disabled="locked || !canRepayAnything"
              @click="emit('repay', repayAmount)"
            >
              Repay
            </button>
          </div>
        </template>

        <template v-else>
          <p class="text-xs leading-relaxed text-gray-x-light">
            Borrow up to {{ maxLoan }} points, interest free, repayable over
            {{ roundsLabel(loanTerm) }}.
          </p>

          <div class="flex items-center justify-between gap-3">
            <div :class="[stepperClass, 'shrink-0']">
              <button
                type="button"
                :class="stepButton"
                :disabled="borrowAmount <= 1"
                aria-label="Decrease amount"
                @click="stepBorrow(-1)"
              >
                −
              </button>
              <div :class="[countClass, 'w-14 text-lg']">{{ borrowAmount }}</div>
              <button
                type="button"
                :class="stepButton"
                :disabled="borrowAmount >= maxBorrow"
                aria-label="Increase amount"
                @click="stepBorrow(1)"
              >
                +
              </button>
            </div>
            <button
              type="button"
              :class="[actionButton, borrowClass, 'shrink-0']"
              :disabled="locked"
              @click="emit('borrow', borrowAmount)"
            >
              Borrow
            </button>
          </div>
        </template>

        <p v-if="loanBlocker" class="text-xs font-bold text-gray-light">{{ loanBlocker }}</p>
      </section>

      <!-- ── mortgage ────────────────────────────────────────── -->
      <section class="flex shrink-0 flex-col gap-3 border-t-1 border-gray-light pt-5">
        <div class="flex items-baseline justify-between gap-4">
          <h3 :class="labelClass">Mortgage</h3>
          <span v-if="hasMortgage" class="text-xs font-bold" :class="dueTone(mortgageDue)">
            due in {{ roundsLabel(mortgageDue) }}
          </span>
        </div>

        <template v-if="hasMortgage">
          <div :class="[wellClass, 'justify-between gap-2 px-4 py-2']">
            <span class="flex items-center gap-2">
              <Card :card-type="mortgageCardType" :selected="true" :large="false" />
              <span class="text-sm text-gray-x-light">{{ titleOf(mortgageCardType) }}</span>
            </span>
            <span class="text-2xl font-bold tabular-nums text-rose-400">{{
              mortgageOutstanding
            }}</span>
          </div>

          <p class="text-xs leading-relaxed text-gray-x-light">
            The card stays in your hand but cannot be sold or traded. Unredeemed at zero, the bank
            takes it.
          </p>

          <button
            type="button"
            :class="[actionButton, repayClass, 'w-full']"
            :disabled="locked || !canRedeem"
            @click="emit('redeem')"
          >
            Redeem for {{ mortgageOutstanding }}
          </button>
        </template>

        <template v-else-if="mortgageable.length">
          <p class="text-xs leading-relaxed text-gray-x-light">
            Raise points against a property. You keep the card, but it is locked until you redeem
            it.
          </p>

          <!-- Cards, not a text list: the property IS a card and the
                         table already reads them by colour. -->
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in mortgageable"
              :key="option.code"
              type="button"
              :aria-label="`Mortgage ${option.title} for ${option.advance}`"
              :aria-pressed="chosenProperty === option.code"
              @click="chosenProperty = option.code"
              class="flex cursor-pointer items-center gap-2 rounded-xl border-2 px-3 py-2 transition duration-200 ease-in-out"
              :class="
                chosenProperty === option.code
                  ? 'border-purple-light bg-purple-dark/30'
                  : 'border-gray-light opacity-60 hover:opacity-100'
              "
            >
              <Card :card-type="option.code" :selected="true" :large="false" />
              <span class="flex flex-col items-start leading-tight">
                <span class="text-sm font-bold text-gray-2x-light">{{ option.title }}</span>
                <span class="text-xs tabular-nums text-teal-light">+{{ option.advance }}</span>
              </span>
            </button>
          </div>

          <button
            type="button"
            :class="[actionButton, mortgageClass, 'w-full']"
            :disabled="locked || !chosenProperty"
            @click="emit('mortgage', chosenProperty)"
          >
            Mortgage for {{ chosenAdvance }}
          </button>
        </template>

        <template v-else>
          <p class="text-sm text-gray-light">You own no property to mortgage.</p>
        </template>

        <p v-if="mortgageBlocker" class="text-xs font-bold text-gray-light">
          {{ mortgageBlocker }}
        </p>
      </section>

      <footer class="flex shrink-0 justify-end border-t-1 border-gray-light pt-4">
        <button
          type="button"
          :class="actionButton"
          class="border-2 border-gray-light text-gray-x-light hover:border-gray-x-light hover:text-gray-2x-light"
          @click="emit('closeModal')"
        >
          Close
        </button>
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
