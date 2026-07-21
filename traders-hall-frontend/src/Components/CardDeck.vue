<script setup>
import { computed, useSlots, Fragment, Comment, Text } from 'vue'

const props = defineProps({
  offsetX: { type: Number, default: 7 },     // px each card shifts right
  offsetY: { type: Number, default: 7 },     // px each card shifts down
  maxVisible: { type: Number, default: 5 },  // how many cards are actually rendered/stacked
  countColor: { type: String, required: true }, // theme color token, e.g. "green-light"
})

const slots = useSlots()

// v-for / conditionals wrap children in Fragments; flatten and drop comment/text nodes
function flatten(nodes) {
  return nodes.flatMap((n) => {
    if (n.type === Fragment) return flatten(n.children || [])
    if (n.type === Comment || n.type === Text) return []
    return [n]
  })
}

const allCards = computed(() => flatten(slots.default?.() ?? []))
const total = computed(() => allCards.value.length)
const shown = computed(() => Math.min(total.value, props.maxVisible))
const cards = computed(() => allCards.value.slice(-shown.value)) // keep only the top `shown` cards

const deckPadding = computed(() => ({
  // footprint is bounded to (shown - 1) * offset, no matter how many cards exist
  paddingRight: `${Math.max(0, shown.value - 1) * props.offsetX}px`,
  paddingBottom: `${Math.max(0, shown.value - 1) * props.offsetY}px`,
}))
</script>

<template>
  <div class="inline-flex flex-col items-center gap-2">
    <span class="font-bold" :style="{ color: `var(--color-${countColor})` }">
      {{ total }} {{ total === 1 ? 'card' : 'cards' }}
    </span>
    <div class="relative" :style="deckPadding">
      <div
        v-for="(card, j) in cards"
        :key="card.key ?? j"
        :class="[
          j === 0 ? 'relative' : 'absolute top-0 left-0',
          j === cards.length - 1 ? 'pointer-events-auto' : 'pointer-events-none',
        ]"
        :style="{ transform: `translate(${j * offsetX}px, ${j * offsetY}px)` }"
      >
        <component :is="card" />
      </div>
    </div>
  </div>
</template>