<script setup>
import { computed, ref } from 'vue'
import Card from './Card.vue'
import SeatToken from './SeatToken.vue'
import { useCardTypesStore } from '../stores/cardTypes'

const props = defineProps({
  offers: { type: Array, default: () => [] },
  myPlayerId: { type: String, default: '' },
  myPoints: { type: Number, default: 0 },
  myHand: { type: Object, default: () => ({}) },
  myResidenceCardType: { type: String, default: null },
  myRoomsFree: { type: Number, default: 0 },
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['claim', 'unclaim', 'decline', 'confirm', 'cancel'])

const cardTypes = useCardTypesStore()

function titleOf(code) {
  return cardTypes.get(code)?.title ?? code
}

const STEPS = ['Posted', 'Claimed']

const turnsLabel = (n) => (n === 1 ? '1 turn' : `${n} turns`)

const KIND_BADGE = {
  sell: { label: 'Sell', cls: 'border-rose-400/50 bg-rose-400/15 text-rose-400' },
  trade: { label: 'Trade', cls: 'border-amber-400/50 bg-amber-400/15 text-amber-400' },
  rent_out: { label: 'To let', cls: 'border-teal-light/50 bg-teal-dark/30 text-teal-light' },
  rent_ask: { label: 'Wanted', cls: 'border-purple-light/50 bg-purple-dark/30 text-purple-light' },
}

const picked = ref({})

function pick(offerId, playerId) {
  picked.value = { ...picked.value, [offerId]: playerId }
}

function selectedFor(offer) {
  const chosen = picked.value[offer.id]
  if (chosen && offer.claims.some((c) => c.playerId === chosen)) return chosen
  return null
}

function claimTitle(claim) {
  return claim.cardType ? `${claim.playerName} · ${titleOf(claim.cardType)}` : claim.playerName
}

function totalOf(offer) {
  return offer.totalPricePoints ?? (offer.pricePoints ?? 0) * offer.offerQuantity
}

const rows = computed(() =>
  props.offers.map((o) => {
    const mine = o.posterPlayerId === props.myPlayerId
    const claims = o.claims ?? []
    const claimedByMe = claims.some((c) => c.playerId === props.myPlayerId)
    const claimed = claims.length > 0
    const isSell = o.kind === 'sell'
    const isRentOut = o.kind === 'rent_out'
    const isRentAsk = o.kind === 'rent_ask'
    const isRent = isRentOut || isRentAsk
    const isTrade = o.kind === 'trade'
    const total = isSell ? totalOf(o) : null

    let blocked = ''
    if (!mine && !claimedByMe) {
      if (isSell && props.myPoints < total) {
        blocked = `Need ${total} points`
      } else if (isRentOut && props.myResidenceCardType) {
        blocked = 'You already have a home'
      } else if (isRentAsk && props.myRoomsFree < 1) {
        blocked = 'No spare room'
      } else if (isTrade && (props.myHand[o.wantCardType] ?? 0) < o.wantQuantity) {
        blocked = `Need ${o.wantQuantity} ${titleOf(o.wantCardType)}`
      }
    }

    return {
      ...o,
      mine,
      claims,
      claimedByMe,
      claimed,
      isSell,
      isRent,
      isRentOut,
      isRentAsk,
      isTrade,
      badge: KIND_BADGE[o.kind] ?? KIND_BADGE.trade,
      rentEvery: isRent ? turnsLabel(o.rentIntervalTurns) : '',
      total,
      showsUnitPrice: isSell && o.offerQuantity > 1,
      blocked,
      step: claimed ? 1 : 0,
    }
  }),
)
</script>

<template>
  <!--
    Fills its grid cell. Whether that cell is tall is the LAYOUT's decision, not
    this component's — an earlier self-start here overrode the grid and pinned
    the panel to its content at every breakpoint, which is the opposite problem.
  -->
  <div class="flex h-full min-h-0 flex-col rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4">
    <div class="flex shrink-0 items-center justify-between pb-3">
      <h2 class="text-sm font-bold uppercase tracking-widest text-gray-x-light">Open offers</h2>
      <span class="text-xs font-bold uppercase tracking-widest text-gray-light">{{
        rows.length
      }}</span>
    </div>

    <div
      v-if="!rows.length"
      class="flex flex-1 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-gray-light py-8 text-center"
    >
      <span class="text-sm font-bold uppercase tracking-widest text-gray-x-light">No offers</span>
      <span class="text-xs text-gray-light">Sell or trade on your turn to post one</span>
    </div>

    <ul v-else class="scroll-slim flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-1">
      <li
        v-for="offer in rows"
        :key="offer.id"
        class="flex flex-col gap-2 rounded-2xl border-2 bg-gray-dark/60 p-3 transition-colors duration-200"
        :class="
          offer.claimed
            ? 'border-amber-400/50'
            : offer.mine
              ? 'border-teal-light/40'
              : 'border-gray-light hover:border-gray-x-light/60'
        "
      >
        <div class="flex items-center gap-2">
          <SeatToken :seat-index="offer.posterSeatIndex" size="sm" />
          <span class="min-w-0 flex-1 truncate text-sm font-bold text-gray-2x-light">
            {{ offer.mine ? 'You' : offer.posterName }}
          </span>
          <span
            class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
            :class="offer.badge.cls"
          >
            {{ offer.badge.label }}
          </span>
        </div>

        <div v-if="offer.isRentAsk" class="flex items-center gap-2">
          <span class="text-xs font-bold text-gray-2x-light">A room</span>
          <svg
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            class="h-4 w-4 shrink-0 text-purple-light"
          >
            <path d="M2.5 8h11M9.5 4 13.5 8l-4 4" />
          </svg>
          <div class="flex items-center gap-1">
            <Card :card-type="'point'" :selected="true" :large="false" />
            <span class="text-sm font-bold tabular-nums text-teal-light">{{
              offer.pricePoints
            }}</span>
          </div>
        </div>

        <div v-else class="flex items-center gap-2">
          <div class="flex items-center gap-1">
            <Card :card-type="offer.offerCardType" :selected="true" :large="false" />
            <span v-if="!offer.isRent" class="text-sm font-bold tabular-nums text-gray-2x-light"
              >×{{ offer.offerQuantity }}</span
            >
          </div>

          <svg
            class="h-4 w-4 shrink-0"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            :class="
              offer.isSell ? 'text-rose-400' : offer.isRent ? 'text-teal-light' : 'text-amber-400'
            "
          >
            <path d="M2.5 8h11M9.5 4 13.5 8l-4 4" />
          </svg>

          <div v-if="offer.isRent" class="flex items-center gap-1">
            <Card :card-type="'point'" :selected="true" :large="false" />
            <span class="text-sm font-bold tabular-nums text-teal-light">{{
              offer.pricePoints
            }}</span>
          </div>

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
            <span class="text-sm font-bold tabular-nums text-gray-2x-light"
              >×{{ offer.wantQuantity }}</span
            >
          </div>
        </div>

        <span
          v-if="offer.isRent"
          class="text-[10px] font-bold uppercase tracking-widest tabular-nums text-teal-light"
        >
          every {{ offer.rentEvery }}
        </span>

        <div class="flex items-center gap-1.5">
          <template v-for="(label, i) in STEPS" :key="label">
            <span
              class="h-1.5 w-1.5 shrink-0 rounded-full transition-colors duration-300"
              :class="
                i <= offer.step ? (i === 1 ? 'bg-amber-400' : 'bg-teal-light') : 'bg-gray-light'
              "
            ></span>
            <span v-if="i < STEPS.length - 1" class="h-px w-3 shrink-0 bg-gray-light"></span>
          </template>
          <span
            class="ml-1 text-[10px] font-bold uppercase tracking-widest"
            :class="offer.claimed ? 'text-amber-400' : 'text-gray-light'"
          >
            {{ STEPS[offer.step] }}
          </span>
          <span
            v-if="offer.claims.length > 1"
            class="text-[10px] font-bold uppercase tracking-widest text-gray-light"
          >
            · {{ offer.claims.length }} waiting
          </span>
        </div>

        <div v-if="offer.claimed" class="flex flex-wrap items-center gap-1.5">
          <button
            v-for="claim in offer.claims"
            :key="claim.playerId"
            type="button"
            :disabled="!offer.mine || busy"
            :title="claimTitle(claim)"
            :aria-label="claimTitle(claim)"
            :aria-pressed="offer.mine && selectedFor(offer) === claim.playerId"
            @click="pick(offer.id, claim.playerId)"
            class="rounded-lg outline-emerald-400 transition duration-200 ease-in-out"
            :class="[
              offer.mine ? 'cursor-pointer' : 'cursor-default',
              offer.mine && selectedFor(offer) === claim.playerId
                ? 'outline-2 outline-offset-2'
                : offer.mine
                  ? 'opacity-50 hover:opacity-100'
                  : '',
            ]"
          >
            <SeatToken
              :seat-index="claim.seatIndex"
              size="sm"
              :filled="claim.playerId === myPlayerId"
            />
          </button>
        </div>

        <div v-if="offer.mine && offer.claimed" class="flex gap-2">
          <button
            type="button"
            :disabled="busy || !selectedFor(offer)"
            @click="emit('decline', { offerId: offer.id, playerId: selectedFor(offer) })"
            class="flex-1 cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Decline
          </button>
          <button
            type="button"
            :disabled="busy || !selectedFor(offer)"
            @click="emit('confirm', { offerId: offer.id, playerId: selectedFor(offer) })"
            class="flex-1 cursor-pointer rounded-xl border-2 border-emerald-400 bg-emerald-400 py-1.5 text-sm font-bold text-gray-dark transition-colors duration-200 hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Accept
          </button>
        </div>

        <button
          v-if="offer.mine"
          type="button"
          :disabled="busy"
          @click="emit('cancel', offer.id)"
          class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Withdraw
        </button>

        <button
          v-else-if="offer.claimedByMe"
          type="button"
          :disabled="busy"
          @click="emit('unclaim', offer.id)"
          class="w-full cursor-pointer rounded-xl border-2 border-gray-light py-1.5 text-sm font-bold text-gray-x-light transition-colors duration-200 hover:border-rose-400 hover:text-rose-400 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Withdraw claim
        </button>

        <button
          v-else
          type="button"
          :disabled="busy || !!offer.blocked"
          @click="emit('claim', offer.id)"
          class="w-full rounded-xl border-2 py-1.5 text-sm font-bold transition-colors duration-200"
          :class="
            offer.blocked
              ? 'cursor-not-allowed border-gray-light text-gray-light opacity-60'
              : 'cursor-pointer border-teal-light bg-teal-light text-gray-dark hover:brightness-110'
          "
        >
          {{
            offer.blocked ||
            (offer.isSell
              ? `Claim for ${offer.total}`
              : offer.isRentOut
                ? 'Take the room'
                : offer.isRentAsk
                  ? 'Offer a room'
                  : 'Claim')
          }}
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