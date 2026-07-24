<script setup>
import { computed, ref } from 'vue'
import { useCardTypesStore } from '../stores/cardTypes'

const props = defineProps({
    cardType: { type: String, required: true },
    large: { type: Boolean, default: true },
    selected: { type: Boolean, default: false },
    buying: { type: Boolean, default: false },
    selling: { type: Boolean, default: false },
    trading: { type: Boolean, default: false },
})

const emit = defineEmits(['buy', 'sell', 'trade', 'details'])

const cardTypes = useCardTypesStore()

const UNKNOWN_CARD = {
    title: '',
    iconUrl: '',
    accentColor: 'gray-light',
    backgroundColor: 'gray-dark',
    baseCost: undefined,
}

const isHovered = ref(false)

const info = computed(() => cardTypes.get(props.cardType) ?? UNKNOWN_CARD)

const title = computed(() => info.value.title)
const iconUrl = computed(() => info.value.iconUrl)
const color = computed(() => info.value.accentColor)
const bgColor = computed(() => info.value.backgroundColor)
const cost = computed(() => info.value.baseCost)

const isSelected = computed(() => props.selected)
const isActive = computed(() => isHovered.value || isSelected.value)
const interactive = computed(() => props.buying || props.selling || props.trading)

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
        <div class="flex h-[7rem] w-[5.5rem] shrink-0 cursor-pointer flex-col items-center justify-between rounded-xl border-4 p-3 transition duration-300 ease-in-out hover:scale-110"
            :style="{ borderColor: accent, backgroundColor: background }" @mouseenter="isHovered = true"
            @mouseleave="isHovered = false" @click="onClick">
            <span class="pb-2 text-sm font-bold uppercase" :style="{ color: accent }">{{ title }}</span>
            <div class="h-full w-full">
                <div class="h-full w-full" :style="{
                    backgroundColor: accent,
                    mask: `url(${iconUrl}) no-repeat center / contain`,
                    '-webkit-mask': `url(${iconUrl}) no-repeat center / contain`,
                }"></div>
            </div>
        </div>
        <div v-if="cost !== undefined" class="mb-1 flex items-center justify-center pt-3">
            <span v-if="isHovered" class="h-4 text-md font-bold" :style="{ color: background }">{{ title === 'Point' ? ''
                : cost }} {{ cost ? cost === 1 ? 'Point' : 'Points' : '' }}</span>
            <span class="h-4"></span>
        </div>
    </div>

    <div v-else :style="{ backgroundColor: background, borderColor: accent }"
        class="shrink-0 rounded-xl border-2 p-2 transition-colors duration-200 ease-in-out"
        :class="interactive ? 'cursor-pointer' : ''"
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