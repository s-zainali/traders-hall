<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { seatStyle } from '../seats'
import SeatToken from './SeatToken.vue'

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

/*
  How each event type renders. Keeping this as data rather than a chain of
  v-if branches means adding an event type is one entry, and the colour and the
  wording cannot drift apart.
*/
const KINDS = {
  'cards.bought': {
    icon: '▲',
    tone: 'text-emerald-400',
    line: (p) => `bought ${p.quantity}× ${p.card_type} for ${p.total_cost} pts`,
  },
  'cards.sold': {
    icon: '▼',
    tone: 'text-rose-400',
    line: (p) => `sold ${p.quantity}× ${p.card_type} for ${p.total_value} pts`,
  },
  'turn.ended': {
    icon: '⟳',
    tone: 'text-teal-light',
    line: (p) => `ended their turn — round ${p.turn_number}`,
  },
  'game.ended': {
    icon: '★',
    tone: 'text-amber-400',
    line: () => 'the game ended',
  },
}

const FALLBACK = {
  icon: '·',
  tone: 'text-gray-x-light',
  // An unknown type still renders something readable rather than a blank row:
  // a new backend event should never make the log look broken.
  line: (_p, type) => type.replace(/[._]/g, ' '),
}

const logEntries = computed(() =>
  props.events
    .filter((e) => e.event_type !== CHAT)
    .map((e) => {
      const kind = KINDS[e.event_type] ?? FALLBACK
      return {
        seq: e.seq,
        icon: kind.icon,
        tone: kind.tone,
        text: kind.line(e.payload ?? {}, e.event_type),
        actor: e.actor_player_id,
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
  <div
    class="flex min-h-0 flex-col rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4"
  >
    <div class="flex shrink-0 items-center justify-between pb-3">
      <div class="flex gap-1 rounded-xl border-2 border-gray-light bg-gray-dark p-1">
        <button
          type="button" @click="tab = 'log'" :class="tabClass('log')"
          class="cursor-pointer rounded-lg px-4 py-1.5 text-sm font-bold transition duration-200 ease-in-out"
        >Log</button>
        <button
          type="button" @click="tab = 'chat'" :class="tabClass('chat')"
          class="cursor-pointer rounded-lg px-4 py-1.5 text-sm font-bold transition duration-200 ease-in-out"
        >Chat</button>
      </div>
      <span class="text-xs font-bold uppercase tracking-widest text-gray-x-light">
        {{ shown.length }} {{ tab === 'log' ? 'events' : 'messages' }}
      </span>
    </div>

    <!-- min-h-0 lets this shrink so the LIST scrolls rather than the panel
         growing — the vertical twin of min-w-0 -->
    <div
      ref="scroller"
      class="scroll-slim flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-2"
    >
      <p v-if="!shown.length" class="py-8 text-center text-sm text-gray-light">
        {{ tab === 'log' ? 'Nothing has happened yet' : 'No messages yet' }}
      </p>

      <!-- log -->
      <template v-if="tab === 'log'">
        <div
          v-for="entry in shown"
          :key="entry.seq"
          class="flex items-baseline gap-2 rounded-lg px-2 py-1 text-sm hover:bg-gray-dark/60"
        >
          <span :class="entry.tone" class="w-3 shrink-0 text-center font-bold">{{ entry.icon }}</span>
          <span :class="toneOf(entry.actor)" class="shrink-0 font-bold">{{ nameOf(entry.actor) }}</span>
          <span class="min-w-0 flex-1 text-gray-x-light">{{ entry.text }}</span>
          <span class="shrink-0 text-xs tabular-nums text-gray-light">{{ timeOf(entry.at) }}</span>
        </div>
      </template>

      <!-- chat -->
      <template v-else>
        <div
          v-for="entry in shown"
          :key="entry.seq"
          class="flex items-start gap-2 rounded-lg px-2 py-1"
        >
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
      <input
        v-model="draft" maxlength="500" placeholder="Say something…"
        class="min-w-0 flex-1 rounded-xl border-2 border-gray-light bg-gray-dark px-4 py-2
               text-sm text-gray-2x-light transition duration-200 ease-in-out
               placeholder:text-gray-light hover:border-gray-x-light/60
               focus:border-teal-light focus:outline-none"
      />
      <button
        type="submit" :disabled="!draft.trim() || sending"
        class="shrink-0 cursor-pointer rounded-xl border-2 border-teal-light bg-teal-light px-5
               text-sm font-bold text-gray-dark transition duration-200 ease-in-out
               hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
      >Send</button>
    </form>
  </div>
</template>

<style scoped>
.scroll-slim {
  scrollbar-width: thin;
  scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}
.scroll-slim::-webkit-scrollbar { width: 10px; }
.scroll-slim::-webkit-scrollbar-track { background: transparent; }
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