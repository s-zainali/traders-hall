<script setup>
import { computed, ref } from 'vue'
import { useCardTypesStore } from '../stores/cardTypes'

const props = defineProps({
    // WHICH card this is. Unchanged — the store says what a card type *is*,
    // this prop still selects which one to render.
    cardType: { type: String, required: true },
    large: { type: Boolean, default: true },
    selected: { type: Boolean, default: false },
    buying: { type: Boolean, default: false },
    selling: { type: Boolean, default: false },
    trading: { type: Boolean, default: false },
})

const emit = defineEmits(['buy', 'sell', 'trade', 'details'])

const cardTypes = useCardTypesStore()

// rendered if cardType is empty or unknown, instead of throwing on `.title`
const UNKNOWN_CARD = {
    title: '',
    iconUrl: '',
    accentColor: 'gray-light',
    backgroundColor: 'gray-dark',
    baseCost: undefined,
}

const isHovered = ref(false)

// Reads the store instead of a hardcoded map. Still computed, so it tracks both
// the prop changing AND the catalogue arriving.
const info = computed(() => cardTypes.get(props.cardType) ?? UNKNOWN_CARD)

const title = computed(() => info.value.title)
const iconUrl = computed(() => info.value.iconUrl)
const color = computed(() => info.value.accentColor)
const bgColor = computed(() => info.value.backgroundColor)
const cost = computed(() => info.value.baseCost)

const isSelected = computed(() => props.selected)
const isActive = computed(() => isHovered.value || isSelected.value)

const background = computed(() => `var(--color-${isActive.value ? bgColor.value : color.value})`)
const accent = computed(() => `var(--color-${isActive.value ? color.value : bgColor.value})`)

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
            <div class="h-full w-full">
                <div class="h-full w-full" :style="{
                    backgroundColor: accent,
                    mask: `url(${iconUrl}) no-repeat center / contain`,
                    '-webkit-mask': `url(${iconUrl}) no-repeat center / contain`,
                }"></div>
            </div>
        </div>
        <div v-if="cost !== undefined" class="flex items-center justify-center pt-3 mb-1">
            <span v-if="isHovered" class="font-bold text-md h-4" :style="{ color: background }">{{ title === 'Point' ? '' : cost }} {{ cost ? cost
                === 1 ? 'Point' : 'Points' : '' }}</span>
            <span class="h-4"></span>
        </div>
    </div>
    <div v-else :style="{ backgroundColor: background, borderColor: accent }"
        class="p-2 rounded-xl border-2 transition duration-200 ease-in-out"
        :class="buying || selling || trading ? 'cursor-pointer hover:scale-110' : ''"
        @mouseenter="isHovered = true" @mouseleave="isHovered = false" @click="onClick">
        <div class="h-5 w-5">
            <div class="h-full w-full" :style="{
                backgroundColor: accent,
                mask: `url(${iconUrl}) no-repeat center / contain`,
                '-webkit-mask': `url(${iconUrl}) no-repeat center / contain`,
            }"></div>
        </div>
    </div>
</template>