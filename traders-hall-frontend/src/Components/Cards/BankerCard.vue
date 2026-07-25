<script setup>
import { computed } from 'vue'

/**
 * The entry point to the credit desk.
 *
 * It carries a summary rather than just a button, because a debt with two
 * rounds left is something the player needs to see WITHOUT opening anything —
 * a countdown hidden behind a modal is a countdown nobody watches.
 */
const props = defineProps({
    loanOutstanding: { type: Number, default: 0 },
    loanDue: { type: Number, default: 0 },
    mortgageOutstanding: { type: Number, default: 0 },
    mortgageDue: { type: Number, default: 0 },
})

defineEmits(['activateModal'])

const hasDebt = computed(
    () => props.loanOutstanding > 0 || props.mortgageOutstanding > 0
)

// Whichever obligation lands first drives the frame, so the card's colour
// always reflects the most urgent thing outstanding.
const soonest = computed(() => {
    const live = [
        props.loanOutstanding > 0 ? props.loanDue : null,
        props.mortgageOutstanding > 0 ? props.mortgageDue : null,
    ].filter((n) => n !== null)
    return live.length ? Math.min(...live) : null
})

const frame = computed(() => {
    if (soonest.value === null) return 'border-gray-x-light bg-gray-light/50'
    if (soonest.value <= 1) return 'border-rose-400 bg-rose-400/10'
    if (soonest.value <= 2) return 'border-amber-400 bg-amber-400/10'
    return 'border-teal-light bg-teal-dark/20'
})

const tone = (rounds) =>
    rounds <= 1 ? 'text-rose-400' : rounds <= 2 ? 'text-amber-400' : 'text-teal-light'

/** "1 round" / "3 rounds" — the card has room for the word, so it uses it. */
const roundsLabel = (n) => (n === 1 ? '1 round' : `${n} rounds`)

const microLabel = 'text-[10px] font-bold uppercase tracking-widest text-gray-x-light'
</script>

<template>
    <div class="flex h-min flex-col justify-center rounded-[1rem] border-2 p-4 transition duration-200 ease-in-out"
        :class="frame">
        <div class="flex justify-center">
            <!-- inner stays a pure mask -->
            <div class="h-30 w-30 bg-gray-2x-light" :style="{
                mask: `url(/accountant.png) no-repeat center / contain`,
                '-webkit-mask': `url(/accountant.png) no-repeat center / contain`,
            }"></div>
        </div>

        <span class="font-bold tracking-wide text-gray-2x-light">Loan Manager</span>

        <!--
            Each debt gets a label and a spelled-out line. The previous
            "3 · 3r" packed an amount and a countdown into one field with
            nothing to say which was which; the card is wide enough for words,
            so it uses them.
        -->
        <div v-if="hasDebt" class="mt-3 flex flex-col gap-2">
            <div v-if="loanOutstanding > 0" class="flex flex-col gap-0.5">
                <span :class="microLabel">Loan</span>
                <div class="flex items-baseline justify-between gap-2">
                    <span class="text-xs font-bold tabular-nums" :class="tone(loanDue)">
                        {{ loanOutstanding }} owed
                    </span>
                    <span class="text-[10px] font-bold tabular-nums" :class="tone(loanDue)">
                        {{ roundsLabel(loanDue) }} left
                    </span>
                </div>
            </div>

            <div v-if="mortgageOutstanding > 0" class="flex flex-col gap-0.5">
                <span :class="microLabel">Mortgage</span>
                <div class="flex items-baseline justify-between gap-2">
                    <span class="text-xs font-bold tabular-nums" :class="tone(mortgageDue)">
                        {{ mortgageOutstanding }} owed
                    </span>
                    <span class="text-[10px] font-bold tabular-nums" :class="tone(mortgageDue)">
                        {{ roundsLabel(mortgageDue) }} left
                    </span>
                </div>
            </div>
        </div>

        <button
            class="mt-4 rounded-lg bg-gray-2x-light px-4 py-2 font-bold text-gray-dark transition duration-300 ease-in-out hover:cursor-pointer hover:bg-teal-dark hover:text-gray-2x-light"
            @click="$emit('activateModal', 'bankerModal')">
            {{ hasDebt ? 'Manage' : 'Interact' }}
        </button>
    </div>
</template>