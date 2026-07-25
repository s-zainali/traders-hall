<script setup>
import { computed } from 'vue'
import Card from './Card.vue'
import SeatToken from './SeatToken.vue'
import { useCardTypesStore } from '../stores/cardTypes'

const props = defineProps({
    offers: { type: Array, default: () => [] },
    myPlayerId: { type: String, default: '' },
    // SPENDABLE balance — points minus anything already reserved against
    // another claim. Claiming spends against this, so the affordability check
    // has to use it too or the panel offers a claim the server will refuse.
    myPoints: { type: Number, default: 0 },
    myHand: { type: Object, default: () => ({}) },
    // Housing eligibility. A room offer can only be taken by someone with
    // nowhere to live; a room REQUEST can only be answered by someone with a
    // spare room. Both are checked server-side — this is so the panel can say
    // which, rather than letting the click fail.
    myResidenceCardType: { type: String, default: null },
    myRoomsFree: { type: Number, default: 0 },
    busy: { type: Boolean, default: false },
})

const emit = defineEmits(['claim', 'unclaim', 'decline', 'confirm', 'cancel'])

const cardTypes = useCardTypesStore()

function titleOf(code) {
    return cardTypes.get(code) ?.title ?? code
}

const STEPS = ['Posted', 'Claimed', 'Settled']

const turnsLabel = (n) => (n === 1 ? '1 turn' : `${n} turns`)

// Four kinds, each with its own badge. rent_out is a room going spare; rent_ask
// is someone looking for one. They read very differently at the table and used
// to render identically — as a broken Trade with a blank card, because a rent
// offer has no want card to draw.
const KIND_BADGE = {
    sell: { label: 'Sell', cls: 'border-rose-400/50 bg-rose-400/15 text-rose-400' },
    trade: { label: 'Trade', cls: 'border-amber-400/50 bg-amber-400/15 text-amber-400' },
    rent_out: { label: 'To let', cls: 'border-teal-light/50 bg-teal-dark/30 text-teal-light' },
    rent_ask: { label: 'Wanted', cls: 'border-purple-light/50 bg-purple-dark/30 text-purple-light' },
}

/**
 * What a claimant actually pays.
 *
 * pricePoints is PER UNIT — a 2-card offer at 3 each costs 6. The server sends
 * the total so nothing here has to multiply, but the fallback keeps the panel
 * correct against a response that predates that field. Comparing a balance
 * against the unit price, as this did, under-reported the cost of every
 * multi-card offer and let players claim things they could not pay for.
 */
function totalOf(offer) {
    return offer.totalPricePoints ?? (offer.pricePoints ?? 0) * offer.offerQuantity
}

const rows = computed(() =>
    props.offers.map((o) => {
        const mine = o.posterPlayerId === props.myPlayerId
        const claims = o.claims ?? []
        const claimedByMe = claims.some((c) => c.playerId === props.myPlayerId)
        // An offer with claims stays OPEN: more players may still put a hand up
        // right until the poster accepts one.
        const claimed = claims.length > 0
        const isSell = o.kind === 'sell'
        const isRentOut = o.kind === 'rent_out'
        const isRentAsk = o.kind === 'rent_ask'
        const isRent = isRentOut || isRentAsk
        const total = isSell ? totalOf(o) : null

        let blocked = ''
        if (!mine && !claimed) {
            if (isSell && props.myPoints < total) {
                blocked = `Need ${total} points`
            } else if (isRentOut && props.myResidenceCardType) {
                // Taking a room means moving in, so you must have nowhere to live.
                blocked = 'You already have a home'
            } else if (isRentAsk && props.myRoomsFree < 1) {
                blocked = 'No spare room'
            } else if (!isSell && !isRent && (props.myHand[o.wantCardType] ?? 0) < o.wantQuantity) {
                blocked = `Need ${o.wantQuantity} ${titleOf(o.wantCardType)}`
            }
        }

        return {
            ...o,
            mine,
            claims,
            claimedByMe,
            claimed,
            // The poster must say who when several are waiting. With one there
            // is nothing to choose, so the pick is implicit.
            needsPick: claims.length > 1,
            isSell,
            isRent,
            isRentOut,
            isRentAsk,
            badge: KIND_BADGE[o.kind] ?? KIND_BADGE.trade,
            // Rent is the whole payment for one room, so it is never multiplied
            // the way a per-unit sell price is.
            // Split rather than one string. "2 every 3 turns" set inline wrapped
            // onto two lines at this width and read as a sentence; the amount is
            // the headline and the frequency is a caption under it.
            rentEvery: isRent ? turnsLabel(o.rentIntervalTurns) : '',
            total,
            // Only worth spelling out the unit price when there is more than
            // one card; for a single card the total IS the unit price and the
            // extra line is noise.
            showsUnitPrice: isSell && o.offerQuantity > 1,
            blocked,
            step: claimed ? 1 : 0,
        }
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
                        :class="offer.badge.cls">
                        {{ offer.badge.label }}
                    </span>
                </div>

                <!-- A room request names no property, so there is no left-hand
                     card to draw: it shows the rent alone. -->
                <div v-if="offer.isRentAsk" class="flex items-center gap-2">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">Wants a room</span>
                    <span class="text-lg font-bold text-purple-light">→</span>
                    <!-- The number sits after the point card, the same way a
                         card count does elsewhere, so it needs no label. -->
                    <div class="flex items-center gap-1">
                        <Card :card-type="'point'" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-teal-light">{{ offer.pricePoints }}</span>
                    </div>
                </div>

                <div v-else class="flex items-center gap-2">
                    <div class="flex items-center gap-1">
                        <Card :card-type="offer.offerCardType" :selected="true" :large="false" />
                        <span v-if="!offer.isRent"
                            class="text-sm font-bold tabular-nums text-gray-2x-light">×{{ offer.offerQuantity }}</span>
                        <span v-else class="text-[10px] font-bold uppercase tracking-widest text-gray-x-light">1 room</span>
                    </div>

                    <span class="text-lg font-bold"
                        :class="offer.isSell ? 'text-rose-400' : offer.isRent ? 'text-teal-light' : 'text-amber-400'">→</span>

                    <!-- Rent and frequency together. One without the other is a
                         blind offer, which is what these were. -->
                    <div v-if="offer.isRent" class="flex items-center gap-1">
                        <Card :card-type="'point'" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-teal-light">{{ offer.pricePoints }}</span>
                    </div>

                    <!-- The TOTAL is the headline, because that is the number
                         the claimant is agreeing to pay. The unit price sits
                         underneath as the explanation for it. -->
                    <div v-else-if="offer.isSell" class="flex items-center gap-1">
                        <Card :card-type="'point'" :selected="true" :large="false" />
                        <div class="flex flex-col leading-tight">
                            <span class="text-sm font-bold tabular-nums text-teal-light">{{ offer.total }}</span>
                            <span v-if="offer.showsUnitPrice" class="text-[10px] tabular-nums text-gray-light">
                                {{ offer.pricePoints }} each
                            </span>
                        </div>
                    </div>
                    <div v-else class="flex items-center gap-1">
                        <Card :card-type="offer.wantCardType" :selected="true" :large="false" />
                        <span class="text-sm font-bold tabular-nums text-gray-2x-light">×{{ offer.wantQuantity }}</span>
                    </div>
                </div>

                <!-- Frequency on its own line: it qualifies the whole deal
                     rather than either side of it, and inline it was competing
                     with the two numbers it sits between. -->
                <span v-if="offer.isRent"
                    class="text-[10px] font-bold uppercase tracking-widest tabular-nums text-gray-x-light">
                    every {{ offer.rentEvery }}
                </span>

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

                <!--
                    Everyone waiting, one row each. The poster accepts or
                    declines a NAMED player rather than "the claimant", because
                    an offer can now collect several and picking between them is
                    the decision.
                -->
                <div v-if="offer.claimed" class="flex flex-col gap-1">
                    <div v-for="claim in offer.claims" :key="claim.playerId"
                        class="flex items-center gap-2 rounded-lg border-2 px-2 py-1"
                        :class="claim.playerId === myPlayerId
                            ? 'border-teal-light/50 bg-teal-dark/20'
                            : 'border-amber-400/40 bg-amber-400/10'">
                        <SeatToken :seat-index="claim.seatIndex" size="sm" />
                        <span class="min-w-0 flex-1 truncate text-xs font-bold text-gray-2x-light">
                            {{ claim.playerId === myPlayerId ? 'You' : claim.playerName }}
                            <!-- which room a landlord offered, when answering a request -->
                            <span v-if="claim.cardType" class="text-gray-x-light">
                                · {{ titleOf(claim.cardType) }}
                            </span>
                        </span>

                        <template v-if="offer.mine">
                            <button type="button" :disabled="busy"
                                :aria-label="`Decline ${claim.playerName}`"
                                @click="emit('decline', { offerId: offer.id, playerId: claim.playerId })"
                                class="cursor-pointer rounded-lg border-2 border-gray-light px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                                No
                            </button>
                            <button type="button" :disabled="busy"
                                :aria-label="`Accept ${claim.playerName}`"
                                @click="emit('confirm', { offerId: offer.id, playerId: claim.playerId })"
                                class="cursor-pointer rounded-lg border-2 border-emerald-400 bg-emerald-400 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-gray-dark transition-colors duration-200 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40">
                                Accept
                            </button>
                        </template>
                    </div>
                </div>

                <button v-if="offer.mine" type="button" :disabled="busy" @click="emit('cancel', offer.id)"
                    class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                    Withdraw
                </button>

                <button v-if="!offer.mine && offer.claimedByMe" type="button" :disabled="busy" @click="emit('unclaim', offer.id)"
                    class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40">
                    Withdraw claim
                </button>

                <!-- Others' claims never block you: the offer is still open and
                     you can put your own hand up alongside theirs. -->
                <button v-else-if="!offer.mine" type="button" :disabled="busy || !!offer.blocked"
                    @click="emit('claim', offer.id)"
                    class="w-full rounded-xl border-2 py-1.5 text-sm font-bold transition-colors duration-200"
                    :class="offer.blocked
                        ? 'cursor-not-allowed border-gray-light text-gray-light opacity-60'
                        : 'cursor-pointer border-teal-light bg-teal-light text-gray-dark hover:brightness-110'">
                    {{ offer.blocked
                        || (offer.isSell ? `Claim for ${offer.total}`
                            : offer.isRentOut ? 'Take the room'
                            : offer.isRentAsk ? 'Offer a room' : 'Claim') }}
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