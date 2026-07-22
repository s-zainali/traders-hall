<script>
// Plain <script> block: runs at module scope, so named exports here are
// importable by other components while the data stays colocated with the
// component that owns it. `<script setup>` below can read `cards` directly.
export const cards = {
    'house': {
        'title': 'House',
        'iconUrl': '/home.png',
        'accentColor': 'purple-dark',
        'backgroundColor': 'purple-light',
        'cost': 1,
    },
    'mansion': {
        'title': 'Mansion',
        'iconUrl': '/mansion.png',
        'accentColor': 'purple-dark',
        'backgroundColor': 'purple-light',
        'cost': 2,
    },
    'tower': {
        'title': 'Tower',
        'iconUrl': '/building.png',
        'accentColor': 'purple-dark',
        'backgroundColor': 'purple-light',
        'cost': 3,
    },
    'wheat': {
        'title': 'Wheat',
        'iconUrl': '/wheat.png',
        'accentColor': 'cream-dark',
        'backgroundColor': 'cream-light',
        'cost': 1,
    },
    'rice': {
        'title': 'Rice',
        'iconUrl': '/rice.png',
        'accentColor': 'cream-dark',
        'backgroundColor': 'cream-light',
        'cost': 1,
    },
    'invest': {
        'title': 'Invest',
        'iconUrl': '/investor.png',
        'accentColor': 'blue-dark',
        'backgroundColor': 'blue-light',
        'cost': 1,
    },
    'point': {
        'title': 'Point',
        'iconUrl': '/star.png',
        'accentColor': 'teal-dark',
        'backgroundColor': 'teal-light',
        'cost': 0,
    },
}

// rendered when cardType is empty or unknown instead of throwing on `.title`
const UNKNOWN_CARD = {
    title: '',
    iconUrl: '',
    accentColor: 'gray-light',
    backgroundColor: 'gray-dark',
    cost: undefined,
}
</script>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
    cardType: { type: String, required: true },
    large: { type: Boolean, default: true },
    selected: { type: Boolean, default: false },
    buying: { type: Boolean, default: false },
    selling: { type: Boolean, default: false },
    trading: { type: Boolean, default: false },
})

const emit = defineEmits(['buy', 'sell', 'trade', 'details'])

const isHovered = ref(false)

// All of these were read once at setup, which froze the card's identity: if Vue
// ever reused this instance for a different cardType (very easy without :key on
// the parent v-for) it kept rendering the old card. Computed = tracks the prop.
const info = computed(() => cards[props.cardType] ?? UNKNOWN_CARD)
const title = computed(() => info.value.title)
const iconUrl = computed(() => info.value.iconUrl)
const color = computed(() => info.value.accentColor)
const bgColor = computed(() => info.value.backgroundColor)
const cost = computed(() => info.value.cost)

const isSelected = computed(() => props.selected)
const isActive = computed(() => isHovered.value || isSelected.value)

const background = computed(() => `var(--color-${isActive.value ? bgColor.value : color.value})`)
const accent = computed(() => `var(--color-${isActive.value ? color.value : bgColor.value})`)

// single source of truth for click behaviour, shared by both the large and small
// variants — previously this lived inline on the large branch only, so small
// cards (:large="false") were completely inert.
function onClick() {
    if (props.buying) emit('buy')
    else if (props.selling) emit('sell')
    else if (props.trading) emit('trade')
    else emit('details')
}

</script>

<template>
    <div v-if="large" class="flex flex-col items-center">
        <div class="w-[5.5rem] h-[7rem] rounded-xl p-3 flex flex-col items-center border-4 justify-between shrink-0 cursor-pointer hover:scale-110 transition duration-300 ease-in-out"
            :style="{ borderColor: accent, backgroundColor: background }" @mouseenter="isHovered = true"
            @mouseleave="isHovered = false" @click="onClick">
            <span class="font-bold text-sm uppercase pb-2" :style="{ color: accent }">{{ title }}</span>

            <!-- wrapper carries the filter (runs on the masked child) -->
            <div class="h-full w-full">
                <!-- inner stays a pure mask -->
                <div class="h-full w-full" :style="{
                    backgroundColor: accent,
                    mask: `url(${iconUrl}) no-repeat center / contain`,
                    '-webkit-mask': `url(${iconUrl}) no-repeat center / contain`,
                }"></div>
            </div>
        </div>
        <div v-if="cost !== undefined" class="flex items-center justify-center pt-3 mb-1">
            <span v-if="isHovered" class="font-bold text-md h-4 " :style="{ color: background }">{{ title === 'Point' ? '' : cost }} {{ cost ? cost
                === 1 ? 'Point' : 'Points': '' }}</span>
            <span class="h-4"></span>
        </div>
    </div>
    <div v-else :style="{ backgroundColor: background, borderColor: accent }"
        class="p-2 rounded-xl border-2 transition duration-200 ease-in-out"
        :class="buying || selling || trading ? 'cursor-pointer hover:scale-110' : ''"
        @mouseenter="isHovered = true" @mouseleave="isHovered = false" @click="onClick">
        <div class="h-5 w-5">
            <!-- inner stays a pure mask -->
            <div class="h-full w-full" :style="{
                backgroundColor: accent,
                mask: `url(${iconUrl}) no-repeat center / contain`,
                '-webkit-mask': `url(${iconUrl}) no-repeat center / contain`,
            }"></div>
        </div>
    </div>
</template>