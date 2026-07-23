<script setup>
import { computed } from 'vue'
import { seatStyle } from '../seats'

/**
 * The badge that identifies a seat: coloured frame + token glyph.
 *
 * Inline SVG rather than image files, so this cannot break on a missing asset
 * and the glyph inherits currentColor — one component, four colours, nothing
 * extra to keep in sync.
 */
const props = defineProps({
  seatIndex: { type: Number, default: -1 },
  size: { type: String, default: 'md' },      // 'sm' | 'md' | 'lg'
  filled: { type: Boolean, default: false },  // solid colour instead of tinted
})

const seat = computed(() => seatStyle(props.seatIndex))
const isEmpty = computed(() => props.seatIndex < 0)

const boxes = {
  sm: 'h-7 w-7 rounded-lg border-2',
  md: 'h-10 w-10 rounded-xl border-2',
  lg: 'h-14 w-14 rounded-2xl border-4',
}
const glyphs = { sm: 'h-4 w-4', md: 'h-5 w-5', lg: 'h-7 w-7' }
</script>

<template>
  <div
    class="flex shrink-0 items-center justify-center transition duration-200 ease-in-out"
    :class="[
      boxes[size],
      isEmpty
        ? 'border-dashed border-gray-light bg-transparent text-gray-light'
        : filled
          ? [seat.border, seat.bgSolid, 'text-gray-dark']
          : [seat.borderSoft, seat.bgSoft, seat.text],
    ]"
    :title="isEmpty ? 'Empty seat' : seat.name"
  >
    <svg :class="glyphs[size]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <!-- crown -->
      <path v-if="seat.token === 'crown'"
        d="M3 8l4 3 5-7 5 7 4-3-2 11H5L3 8zm2 13h14v2H5v-2z" />
      <!-- diamond -->
      <polygon v-else-if="seat.token === 'diamond'"
        points="12,2 22,12 12,22 2,12" />
      <!-- shield -->
      <path v-else-if="seat.token === 'shield'"
        d="M12 2l8 3.5v6c0 4.8-3.4 8.8-8 10.5-4.6-1.7-8-5.7-8-10.5v-6L12 2z" />
      <!-- anchor -->
      <path v-else-if="seat.token === 'anchor'"
        d="M11 2h2v3h2v2h-2v11.9c2.6-.4 4.6-2.4 5-5h3c-.5 4.4-4.2 7.6-9 7.6S3.5 18.3 3 13.9h3c.4 2.6 2.4 4.6 5 5V7H9V5h2V2z" />
      <!-- empty: a dot, so the badge is never a blank box -->
      <circle v-else cx="12" cy="12" r="3" />
    </svg>
  </div>
</template>