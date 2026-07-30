<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { seatStyle } from '../seats'
import SeatToken from './SeatToken.vue'
import Card from './Card.vue'

const props = defineProps({
    // raw events, oldest first, straight from /games/{code}/events
    events: { type: Array, default: () => [] },
    // seat_index by player id, so a line can be coloured by who did it
    seatByPlayer: { type: Object, default: () => ({}) },
    nameByPlayer: { type: Object, default: () => ({}) },
    sending: { type: Boolean, default: false },
})
const emit = defineEmits(['send'])

const tab = ref('log')          // 'log' | 'chat'
const draft = ref('')
const scroller = ref(null)

const CHAT = 'chat.message'

/* ── line grammar ─────────────────────────────────────────────────
   A line is a list of PARTS rather than a string, so the cards involved can
   render as actual cards. "bought 2 rice" tells you less at a glance than the
   rice card itself does — the whole table is colour-coded by card type, and a
   log written in prose throws that away.

   Four part kinds, which between them cover every event:
     text  plain words
     card  a card chip with a count
     pts   a points chip with a number
     name  another player, in their seat colour
────────────────────────────────────────────────────────────────── */
const T = (v) => ({ t: 'text', v })
const C = (code, qty = 1) => ({ t: 'card', code, qty })
const P = (v) => ({ t: 'pts', v })
const N = (id) => ({ t: 'name', id })

const turns = (n) => (n === 1 ? '1 turn' : `${n} turns`)

/**
 * How a rent offer reads.
 *
 * rent_out is a landlord advertising a room; rent_ask is a homeless player
 * saying what they will pay. Both carry a rent AND an interval, and a line that
 * shows one without the other is a blind offer — which is what these looked like
 * while they fell through to the trade branch and rendered "for ×" and a blank
 * card, because a rent offer has no want_card_type to draw.
 */
const rentParts = (p, verbPrefix) =>
    p.kind === 'rent_out'
        ? [T(verbPrefix + ' a room in'), C(p.card_type, 1), T('to let for'), P(p.price_points),
        T(`every ${turns(p.rent_interval_turns)}`)]
        : [T(verbPrefix + ' a room, paying'), P(p.price_points),
        T(`every ${turns(p.rent_interval_turns)}`)]

const isRentKind = (kind) => kind === 'rent_out' || kind === 'rent_ask'

/*
  How each event type renders. Keeping this as data rather than a chain of
  v-if branches means adding an event type is one entry, and the colour and the
  wording cannot drift apart.
*/
/**
 * Drawn icons, not glyphs.
 *
 * The log used a mix of geometric characters and emoji. Emoji render at
 * whatever weight and hue the platform font decides — the padlock came out
 * gold on Linux, a colour that appears nowhere in this palette — and the
 * geometric ones sat on a text baseline while the card chips beside them did
 * not.
 *
 * These are paths on a 16x16 box at stroke-width 1.6, matching the mortgage
 * padlock on the card decks, and they take their colour from the row's tone
 * through currentColor.
 */
const ICONS = {
  buy: 'M8 2v7M5 6.5 8 9.5l3-3M3 11v2a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-2',
  sell: 'M8 9.5v-7M5 5.5 8 2.5l3 3M3 11v2a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-2',
  turn: 'M13 8a5 5 0 1 1-1.8-3.9M13 2v3h-3',
  flag: 'M4 14V3M4 3h8l-1.6 2.6L12 8H4',
  offer: 'M3 5h10M3 8h10M3 11h6',
  claim: 'M4 3h8v11l-4-3-4 3z',
  undo: 'M6 5 3 8l3 3M3 8h7a3 3 0 0 1 0 6',
  cross: 'M4 4l8 8M12 4l-8 8',
  swap: 'M3 6h9L9.5 3.5M13 10H4l2.5 2.5',
  food: 'M13 3c0 5-3.5 8-9 9 0-5 3.5-8 9-9zM4 12l4-4',
  warn: 'M8 2.5 14 13H2zM8 6.5v2.6M8 11.2v.1',
  home: 'M2.5 8 8 3l5.5 5M4 7.5V13h8V7.5',
  plusCircle: 'M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11M8 5.5v5M5.5 8h5',
  minusCircle: 'M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11M5.5 8h5',
  bank: 'M2.5 6.5 8 3l5.5 3.5M4.5 7.5v4.5M7 7.5v4.5M9 7.5v4.5M11.5 7.5v4.5M2.5 13.5h11',
  lock: 'M5 7V5.2a3 3 0 0 1 6 0V7M3.5 7h9v6h-9z',
  unlock: 'M5 7V5.2a3 3 0 0 1 5.7-1.4M3.5 7h9v6h-9z',
  // stroke-linecap round turns a zero-length segment into a dot
  dot: 'M8 8h.01',
}

const KINDS = {
    // ── bank trades ──────────────────────────────────────────────
    'cards.bought': {
        icon: 'buy',
        tone: 'text-emerald-400',
        parts: (p) => [T('bought'), C(p.card_type, p.quantity), T('from the bank for'), P(p.total_cost)],
    },
    'cards.sold': {
        icon: 'sell',
        tone: 'text-rose-400',
        parts: (p) => [T('sold'), C(p.card_type, p.quantity), T('to the bank for'), P(p.total_value)],
    },

    // ── turn flow ────────────────────────────────────────────────
    'turn.ended': {
        icon: 'turn',
        tone: 'text-teal-light',
        parts: (p) => [T(`ended their turn — round ${p.turn_number}`)],
    },
    'game.ended': {
        icon: 'flag',
        tone: 'text-amber-400',
        parts: () => [T('the game ended')],
    },

    // ── marketplace ──────────────────────────────────────────────
    // price_points is per unit, so the TOTAL is what the claimant actually pays
    // and therefore what the log should show.
    'offer.posted': {
        icon: 'offer',
        tone: 'text-gray-2x-light',
        parts: (p) => {
            if (isRentKind(p.kind)) return rentParts(p, p.kind === 'rent_out' ? 'offered' : 'wants')
            if (p.kind === 'sell') {
                return [T('offered'), C(p.card_type, p.quantity), T('for'),
                P(p.total_price_points ?? p.price_points)]
            }
            return [T('offered'), C(p.card_type, p.quantity), T('for'),
            C(p.want_card_type, p.want_quantity)]
        },
    },
    'offer.claimed': {
        icon: 'claim',
        tone: 'text-amber-400',
        parts: (p) => [T('claimed an offer from'), N(p.poster_player_id)],
    },
    'offer.claim_withdrawn': {
        icon: 'undo',
        tone: 'text-gray-x-light',
        parts: () => [T('withdrew their claim')],
    },
    'offer.declined': {
        icon: 'cross',
        tone: 'text-rose-400',
        parts: (p) => [T('declined the claim from'), N(p.declined_player_id)],
    },
    'offer.settled': {
        icon: 'swap',
        tone: 'text-emerald-400',
        parts: (p) => {
            if (isRentKind(p.kind)) {
                return [T('let a room in'), C(p.card_type, 1), T('to'), N(p.tenant_player_id ?? p.with_player_id),
                T('for'), P(p.rent_points), T(`every ${turns(p.rent_interval_turns)}`)]
            }
            if (p.kind === 'sell') {
                return [T('sold'), C(p.card_type, p.quantity), T('to'), N(p.with_player_id), T('for'),
                P(p.total_price_points ?? p.price_points)]
            }
            return [T('traded'), C(p.card_type, p.quantity), T('to'), N(p.with_player_id), T('for'),
            C(p.want_card_type, p.want_quantity)]
        },
    },
    'offer.cancelled': {
        icon: 'cross',
        tone: 'text-gray-x-light',
        parts: () => [T('withdrew an offer')],
    },

    'income.rolled': {
    icon: 'plusCircle',
    tone: 'text-teal-light',
    parts: (p) => {
      const out = [T(`rolled ${(p.dice ?? []).join(' + ')} =`), T(String(p.total)),
                   T('and took'), P(p.paid)]
      if (p.shortfall) out.push(T(`— the bank was ${p.shortfall} short`))
      return out
    },
  },

  // ── upkeep ───────────────────────────────────────────────────
    'food.eaten': {
        icon: 'food',
        tone: 'text-cream-light',
        parts: (p) => [
            T('ate'),
            C(p.card_type, p.quantity),
            T(`— fed for ${p.food_due} more ${p.food_due === 1 ? 'turn' : 'turns'}`),
        ],
    },
    'food.exhausted': {
        icon: 'warn',
        tone: 'text-amber-400',
        // No actor: upkeep raised this, not the player. subjectOf falls back to
        // payload.player_id so the line still names and colours the right seat.
        parts: () => [T('has run out of food')],
    },

    // ── tenancies ────────────────────────────────────────────────
    'rent.paid': {
        icon: 'home',
        tone: 'text-teal-light',
        parts: (p) => [T('paid'), P(p.rent_points), T('rent to'), N(p.landlord_player_id),
        T(`— next in ${turns(p.next_due_in)}`)],
    },
    'rent.missed': {
        icon: 'warn',
        tone: 'text-rose-400',
        parts: (p) => [T('could not pay'), P(p.rent_points), T('rent to'), N(p.landlord_player_id),
        T(`— ${p.shortfall} short`)],
    },
    'player.eliminated': {
    icon: 'warn',
    tone: 'text-rose-400',
    parts: (p) => {
      const why = {
        starvation: 'starved',
        loan_default: 'was cleaned out by the bank',
        rent_default: 'could not make rent',
      }[p.reason] ?? 'is out'
      const out = [T(`${why} and is out of the game`)]
      if (p.creditor_player_id) out.push(T('— everything went to'), N(p.creditor_player_id))
      const evicted = (p.evicted ?? []).length
      if (evicted) out.push(T(`, ${evicted} tenant${evicted === 1 ? '' : 's'} evicted`))
      return out
    },
  },
  'rent.seizure_opened': {
    icon: 'warn',
    tone: 'text-amber-400',
    parts: (p) => [T('owes'), P(p.debt), T('to'), N(p.landlord_player_id),
                   T('— the game is paused while they choose')],
  },
  'rent.seized': {
    icon: 'swap',
    tone: 'text-amber-400',
    parts: (p) => {
      const out = [T('took')]
      for (const [code, n] of Object.entries(p.cards ?? {})) out.push(C(code, n))
      out.push(T('from'), N(p.player_id), T(`for ${p.debt} owed`))
      return out
    },
  },
  'rent.seizure_waived': {
    icon: 'home',
    tone: 'text-teal-light',
    parts: (p) => [T('let'), N(p.player_id), T(`off ${p.debt} of rent`)],
  },
  'tenancy.moveout_requested': {
    icon: 'undo',
    tone: 'text-amber-400',
    parts: (p) => [T('asked'), N(p.landlord_player_id), T('to let them out of'), C(p.card_type, 1)],
  },
  'tenancy.moveout_accepted': {
    icon: 'home',
    tone: 'text-teal-light',
    parts: (p) => [T('paid'), P(p.amount), T('to'), N(p.landlord_player_id), T('and moved out')],
  },
  'tenancy.moveout_rejected': {
    icon: 'cross',
    tone: 'text-rose-400',
    parts: (p) => [T('refused to release'), N(p.player_id), T('— leaving now costs'), P(p.buyout)],
  },
  'tenancy.moveout_bought_out': {
    icon: 'home',
    tone: 'text-amber-400',
    parts: (p) => [T('paid'), P(p.amount), T('to walk out on'), N(p.landlord_player_id)],
  },
  'tenancy.moveout_withdrawn': {
    icon: 'home',
    tone: 'text-gray-x-light',
    parts: () => [T('decided to stay put')],
  },
  'tenancy.evicted': {
    icon: 'cross',
    tone: 'text-rose-400',
    parts: (p) => [T('evicted'), N(p.player_id), T('from'), C(p.card_type, 1),
                   T(`— ${p.rent_forfeited} rent forfeited`)],
  },
  'tenancy.ended': {
        icon: 'home',
        tone: 'text-gray-x-light',
        parts: (p) => [T('no longer rents'), C(p.card_type, 1), T('from'), N(p.landlord_player_id)],
    },
    'residence.moved_in': {
        icon: 'home',
        tone: 'text-purple-light',
        parts: (p) => [T('moved into'), C(p.card_type, 1)],
    },
    'residence.left': {
        icon: 'home',
        tone: 'text-gray-x-light',
        parts: (p) => [T('left'), C(p.card_type, 1)],
    },

    // ── credit ───────────────────────────────────────────────────
    'loan.borrowed': {
        icon: 'plusCircle',
        tone: 'text-blue-light',
        parts: (p) => [T('borrowed'), P(p.amount), T(`from the bank — due in ${p.due_in_rounds} rounds`)],
    },
    'loan.repaid': {
        icon: 'minusCircle',
        tone: 'text-teal-light',
        // `automatic` distinguishes a player choosing to pay from upkeep collecting
        // on the due date, which reads very differently at the table.
        parts: (p) => [
            T(p.automatic ? 'was charged' : 'repaid'),
            P(p.amount),
            T(p.cleared ? '— loan cleared' : `— ${p.outstanding} still owed`),
        ],
    },
    'loan.defaulted': {
        icon: 'warn',
        tone: 'text-rose-400',
        parts: (p) => {
            const out = [T('defaulted on'), P(p.owed)]
            if (p.seized_points) out.push(T('— the bank took'), P(p.seized_points))
            const cards = Object.entries(p.seized_cards ?? {})
            if (cards.length) {
                out.push(T(p.seized_points ? 'and seized' : '— the bank seized'))
                for (const [code, count] of cards) out.push(C(code, count))
            }
            if (p.written_off) out.push(T(`— ${p.written_off} written off`))
            return out
        },
    },
    'mortgage.opened': {
        icon: 'bank',
        tone: 'text-purple-light',
        parts: (p) => [T('mortgaged'), C(p.card_type, 1), T('for'), P(p.advance), T(`— due in ${p.due_in_rounds} rounds`)],
    },
    'mortgage.redeemed': {
        icon: 'unlock',
        tone: 'text-teal-light',
        parts: (p) => [T(p.automatic ? 'was charged to redeem' : 'redeemed'), C(p.card_type, 1), T('for'), P(p.amount)],
    },
    'mortgage.seized': {
        icon: 'lock',
        tone: 'text-rose-400',
        parts: (p) => [T('lost'), C(p.card_type, 1), T('to the bank —'), P(p.owed), T('unpaid')],
    },
}

const FALLBACK = {
    icon: 'dot',
    tone: 'text-gray-x-light',
    // An unknown type still renders something readable rather than a blank row:
    // a new backend event should never make the log look broken.
    parts: (_p, type) => [T(type.replace(/[._]/g, ' '))],
}

/**
 * Who a line is about.
 *
 * Server-run events — upkeep collecting a loan, the bank seizing a property —
 * carry a null actor because no player chose to do them, and name their subject
 * in the payload instead. Reading actor alone would colour every one of those
 * grey and attribute them to nobody.
 */
function subjectOf(event) {
    return event.actor_player_id ?? event.payload?.player_id ?? null
}

/** A malformed payload should cost one line, not the whole panel. */
function safeParts(kind, payload, type) {
    try {
        return kind.parts(payload, type)
    } catch {
        return FALLBACK.parts(payload, type)
    }
}

const logEntries = computed(() =>
    props.events
        .filter((e) => e.event_type !== CHAT)
        .map((e) => {
            const kind = KINDS[e.event_type] ?? FALLBACK
            const payload = e.payload ?? {}
            return {
                seq: e.seq,
                icon: kind.icon,
                tone: kind.tone,
                parts: safeParts(kind, payload, e.event_type),
                actor: subjectOf(e),
                at: e.created_at,
            }
        })
)

const chatEntries = computed(() =>
    props.events
        .filter((e) => e.event_type === CHAT)
        .map((e) => ({
            seq: e.seq,
            text: e.payload?.text ?? '',
            // the snapshot in the payload survives a player leaving the table
            name: e.payload?.display_name ?? nameOf(e.actor_player_id),
            actor: e.actor_player_id,
            at: e.created_at,
        }))
)

const shown = computed(() => (tab.value === 'log' ? logEntries.value : chatEntries.value))

function seatOf(playerId) {
    return props.seatByPlayer[playerId] ?? -1
}
function nameOf(playerId) {
    return props.nameByPlayer[playerId] ?? 'Someone'
}
function toneOf(playerId) {
    return seatStyle(seatOf(playerId)).text
}
function timeOf(iso) {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/*
  Stick to the bottom only if the reader is already there. Yanking the view down
  while someone is reading back through the log is worse than a missed line.
*/
const AUTOSCROLL_SLACK = 60

async function scrollIfPinned() {
    const el = scroller.value
    if (!el) return
    const pinned = el.scrollHeight - el.scrollTop - el.clientHeight < AUTOSCROLL_SLACK
    await nextTick()
    if (pinned) el.scrollTop = el.scrollHeight
}

watch(() => props.events.length, scrollIfPinned)
watch(tab, async () => {
    await nextTick()
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
})

function send() {
    const text = draft.value.trim()
    if (!text || props.sending) return
    emit('send', text)
    draft.value = ''
}

const tabClass = (name) =>
    tab.value === name
        ? 'bg-gray-2x-light text-gray-dark'
        : 'text-gray-x-light hover:text-gray-2x-light'
</script>

<template>
    <div class="flex min-h-0 flex-col rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4">
        <div class="flex shrink-0 items-center justify-between pb-3">
            <div class="flex gap-1 rounded-xl border-2 border-gray-light bg-gray-dark p-1">
                <button type="button" @click="tab = 'log'" :class="tabClass('log')"
                    class="cursor-pointer rounded-lg px-4 py-1.5 text-sm font-bold transition duration-200 ease-in-out">Log</button>
                <button type="button" @click="tab = 'chat'" :class="tabClass('chat')"
                    class="cursor-pointer rounded-lg px-4 py-1.5 text-sm font-bold transition duration-200 ease-in-out">Chat</button>
            </div>
            <span class="text-xs font-bold uppercase tracking-widest text-gray-x-light">
                {{ shown.length }} {{ tab === 'log' ? 'events' : 'messages' }}
            </span>
        </div>

        <!-- min-h-0 lets this shrink so the LIST scrolls rather than the panel
         growing — the vertical twin of min-w-0 -->
        <div ref="scroller" class="scroll-slim flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-2">
            <p v-if="!shown.length" class="py-8 text-center text-sm text-gray-light">
                {{ tab === 'log' ? 'Nothing has happened yet' : 'No messages yet' }}
            </p>

            <!-- log -->
            <template v-if="tab === 'log'">
                <!--
          items-center and flex-wrap, not items-baseline: a card chip is a box
          with no text baseline of its own, so baseline alignment drops it below
          the line. Wrapping matters because a settled trade can carry two
          chips, two names and a price.
        -->
                <div v-for="entry in shown" :key="entry.seq" class="flex items-center">
                    <div
                        class="flex flex-wrap items-center gap-x-1.5 gap-y-1 rounded-lg px-2 py-1 text-sm hover:bg-gray-dark/60">
                        <!-- currentColor, so one icon set serves every tone -->
                        <svg :class="entry.tone" class="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none"
                            stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
                            aria-hidden="true">
                            <path :d="ICONS[entry.icon] ?? ICONS.dot" />
                        </svg>

                        <!-- Server-run events (upkeep, seizure) have no actor and read as a
                   complete sentence without one. -->
                        <span v-if="entry.actor" :class="toneOf(entry.actor)" class="shrink-0 font-bold">
                            {{ nameOf(entry.actor) }}
                        </span>

                        <template v-for="(part, i) in entry.parts" :key="i">
                            <span v-if="part.t === 'text'" class="text-gray-x-light">{{ part.v }}</span>

                            <span v-else-if="part.t === 'card'" class="inline-flex shrink-0 items-center gap-1">
                                <span class="font-bold tabular-nums text-gray-2x-light">{{ part.qty }}×</span>
                                <!-- zoom, unlike scale, shrinks the measured box too, so the chip
                       sits on the line instead of overhanging it -->
                                <span :style="{ zoom: 0.7 }" class="inline-flex">
                                    <Card :card-type="part.code" :large="false" :selected="true" />
                                </span>
                            </span>

                            <span v-else-if="part.t === 'pts'" class="inline-flex shrink-0 items-center gap-1">
                                <span class="font-bold tabular-nums text-teal-light">{{ part.v }}</span>
                                <span :style="{ zoom: 0.7 }" class="inline-flex">
                                    <Card :card-type="'point'" :large="false" :selected="true" />
                                </span>
                            </span>

                            <span v-else-if="part.t === 'name'" :class="toneOf(part.id)" class="shrink-0 font-bold">
                                {{ nameOf(part.id) }}
                            </span>
                        </template>
                    </div>
                    <div class="ml-auto shrink-0 text-xs tabular-nums text-gray-light">{{ timeOf(entry.at)
                    }}</div>
                </div>
            </template>

            <!-- chat -->
            <template v-else>
                <div v-for="entry in shown" :key="entry.seq" class="flex items-start gap-2 rounded-lg px-2 py-1">
                    <SeatToken :seat-index="seatOf(entry.actor)" size="sm" class="mt-0.5" />
                    <div class="flex min-w-0 flex-1 flex-col">
                        <div class="flex items-baseline gap-2">
                            <span :class="toneOf(entry.actor)" class="text-sm font-bold">{{ entry.name }}</span>
                            <span class="text-xs tabular-nums text-gray-light">{{ timeOf(entry.at) }}</span>
                        </div>
                        <!-- break-words: a long unbroken string would otherwise widen the
                 panel instead of wrapping -->
                        <span class="break-words text-sm text-gray-2x-light">{{ entry.text }}</span>
                    </div>
                </div>
            </template>
        </div>

        <form v-if="tab === 'chat'" class="flex shrink-0 gap-2 pt-3" @submit.prevent="send">
            <input v-model="draft" maxlength="500" placeholder="Say something…" class="min-w-0 flex-1 rounded-xl border-2 border-gray-light bg-gray-dark px-4 py-2
               text-sm text-gray-2x-light transition duration-200 ease-in-out
               placeholder:text-gray-light hover:border-gray-x-light/60
               focus:border-teal-light focus:outline-none" />
            <button type="submit" :disabled="!draft.trim() || sending" class="shrink-0 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light px-5
               text-sm font-bold text-gray-dark transition duration-200 ease-in-out
               hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40">Send</button>
        </form>
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

/* content-box clip plus a transparent border is what makes the thumb look
   inset and pill-shaped: the border reserves padding the background skips */
.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}

.scroll-slim::-webkit-scrollbar-thumb:hover {
    background: color-mix(in oklab, var(--color-teal-light) 55%, transparent);
    background-clip: content-box;
}
</style>