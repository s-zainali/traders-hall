<script setup>
import { computed } from 'vue'
import Card from './Card.vue'
import SeatToken from './SeatToken.vue'
import { useCardTypesStore } from '../stores/cardTypes'

const props = defineProps({
    offers: { type: Array, default: () => [] },
    myPlayerId: { type: String, default: '' },
    myPoints: { type: Number, default: 0 },
    myHand: { type: Object, default: () => ({}) },
    busy: { type: Boolean, default: false },
})

const emit = defineEmits(['claim', 'unclaim', 'decline', 'confirm', 'cancel'])

const cardTypes = useCardTypesStore()

function titleOf(code) {
    return cardTypes.get(code)?.title ?? code
}

const STEPS = ['Posted', 'Claimed', 'Settled']

const rows = computed(() =>
    props.offers.map((o) => {
        const mine = o.posterPlayerId === props.myPlayerId
        const claimedByMe = o.claimedByPlayerId === props.myPlayerId
        const claimed = o.status === 'claimed'
        const isSell = o.kind === 'sell'

        let blocked = ''
        if (!mine && !claimed) {
            if (isSell && props.myPoints < o.pricePoints) {
                blocked = 'Not enough points'
            } else if (!isSell && (props.myHand[o.wantCardType] ?? 0) < o.wantQuantity) {
                blocked = `Need ${o.wantQuantity} ${titleOf(o.wantCardType)}`
            }
        }

        return { ...o, mine, claimedByMe, claimed, isSell, blocked, step: claimed ? 1 : 0 }
    })
)
</script>

<template>
    <div class="flex min-h-0 flex-col rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4">
        <div class="flex shrink-0 items-center justify-between pb-3">
            <h2 class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Open offers</h2>
            <span class="text-xs font-bold uppercase tracking-widest text-gray-light">{{ rows.length }}</span>
        </div>

        <div v-if="!rows.length"
            class="flex flex-1 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-light py-8 text-center">
            <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">No offers</span>
            <span class="text-xs text-gray-light">Sell or trade on your turn to post one</span>
        </div>

        <ul v-else class="scroll-slim flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
            <li v-for="offer in rows" :key="offer.id"
                class="flex flex-col gap-2 rounded-2xl border-2 bg-gray-dark/60 p-3 transition-colors duration-200"
                :class="offer.claimed
                    ? 'border-amber-400/50'
                    : offer.mine ? 'border-teal-light/40' : 'border-gray-light hover:border-gray-x-light/60'">

                <div class="flex items-center gap-2">
                    <SeatToken :seat-index="offer.posterSeatIndex" size="sm" />
                    <span class="min-w-0 flex-1 truncate text-sm font-bold text-gray-2x-light">
                        {{ offer.mine ? 'You' : offer.posterName }}
                    </span>
                    <span class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                        :class="offer.isSell
                            ? 'border-rose-400/50 bg-rose-400/15 text-rose-400'
                            : 'border-amber-400/50 bg-amber-400/15 text-amber-400'">
                        {{ offer.isSell ? 'Sell' : 'Trade' }}
                    </span>
                </div>

                <div class="flex items-center gap-2">
                    <div class="flex items-center gap-1">
                        <Card :card-type="offer.offerCardType" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-gray-2x-light">×{{ offer.offerQuantity }}</span>
                    </div>

                    <span class="text-lg font-bold" :class="offer.isSell ? 'text-rose-400' : 'text-amber-400'">→</span>

                    <div v-if="offer.isSell" class="flex items-center gap-1">
                        <Card :card-type="'point'" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-teal-light">{{ offer.pricePoints }}</span>
                    </div>
                    <div v-else class="flex items-center gap-1">
                        <Card :card-type="offer.wantCardType" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-gray-2x-light">×{{ offer.wantQuantity }}</span>
                    </div>
                </div>

                <div class="flex items-center gap-1.5">
                    <template v-for="(label, i) in STEPS" :key="label">
                        <span class="h-1.5 w-1.5 shrink-0 rounded-full transition-colors duration-300" :class="i <= offer.step
                            ? (i === 2 ? 'bg-emerald-400' : i === 1 ? 'bg-amber-400' : 'bg-teal-light')
                            : 'bg-gray-light'"></span>
                        <span v-if="i < STEPS.length - 1" class="h-px w-3 shrink-0 bg-gray-light"></span>
                    </template>
                    <span class="ml-1 text-[10px] font-bold uppercase tracking-widest"
                        :class="offer.claimed ? 'text-amber-400' : 'text-gray-light'">
                        {{ STEPS[offer.step] }}
                    </span>
                </div>

                <div v-if="offer.claimed"
                    class="flex items-center gap-2 rounded-lg border-2 border-amber-400/40 bg-amber-400/10 px-2 py-1">
                    <SeatToken :seat-index="offer.claimedBySeatIndex ?? -1" size="sm" />
                    <span class="min-w-0 flex-1 truncate text-xs font-bold text-gray-2x-light">
                        {{ offer.claimedByMe ? 'You claimed this' : `${offer.claimedByName} wants this` }}
                    </span>
                </div>

                <div v-if="offer.mine && offer.claimed" class="flex gap-2">
                    <button type="button" :disabled="busy" @click="emit('decline', offer.id)"
                        class="flex-1 cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                        Decline
                    </button>
                    <button type="button" :disabled="busy" @click="emit('confirm', offer.id)"
                        class="flex-1 cursor-pointer rounded-xl border-2 border-emerald-400 bg-emerald-400 py-1.5 text-sm font-bold text-gray-dark transition-colors duration-200 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40">
                        Accept
                    </button>
                </div>

                <button v-else-if="offer.mine" type="button" :disabled="busy" @click="emit('cancel', offer.id)"
                    class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                    Withdraw
                </button>

                <button v-else-if="offer.claimedByMe" type="button" :disabled="busy" @click="emit('unclaim', offer.id)"
                    class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                    Withdraw claim
                </button>

                <div v-else-if="offer.claimed"
                    class="rounded-xl border-2 border-gray-light py-1.5 text-center text-sm font-bold text-gray-light opacity-60">
                    Awaiting {{ offer.posterName }}
                </div>

                <button v-else type="button" :disabled="busy || !!offer.blocked" @click="emit('claim', offer.id)"
                    class="w-full rounded-xl border-2 py-1.5 text-sm font-bold transition-colors duration-200"
                    :class="offer.blocked
                        ? 'cursor-not-allowed border-gray-light text-gray-light opacity-60'
                        : 'cursor-pointer border-teal-light bg-teal-light text-gray-dark hover:brightness-110'">
                    {{ offer.blocked || 'Claim' }}
                </button>
            </li>
        </ul>
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