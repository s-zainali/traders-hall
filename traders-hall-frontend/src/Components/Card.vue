<script setup>
import { computed, ref, reactive } from 'vue'
const props = defineProps({
    cardType: { type: String, required: true },
    large: { type: Boolean, default: true },
    selected: {type:Boolean, default:false},
    buying: {type:Boolean, default:false},
})

const emit = defineEmits(['buy', 'details'])

const isHovered = ref(false)
const isSelected = ref(props.selected)
const background = computed(() => `var(--color-${isHovered.value || isSelected.value ? bgColor : color})`)
const accent = computed(() => `var(--color-${isHovered.value || isSelected.value ? color : bgColor})`)

const cards = reactive({
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
})

const title = cards[props.cardType].title
const iconUrl = cards[props.cardType].iconUrl
const color = cards[props.cardType].accentColor
const bgColor = cards[props.cardType].backgroundColor
const cost = cards[props.cardType].cost

</script>

<template>
    <div v-if="large" class="flex flex-col items-center">
        <div class="w-[5.5rem] h-[7rem] rounded-xl p-3 flex flex-col items-center border-4 justify-between shrink-0 cursor-pointer hover:scale-110 transition duration-300 ease-in-out"
            :style="{ borderColor: accent, backgroundColor: background }" @mouseenter="isHovered = true"
            @mouseleave="isHovered = false" @click="buying? emit('buy') : emit('details')">
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
            <span v-if="isHovered" class="font-bold text-md h-4 " :style="{ color: background }">{{title === 'Point'? '': cost }} {{ cost ? cost
                === 1 ? 'Point' : 'Points': '' }}</span>
            <span class="h-4"></span>
        </div>
    </div>
    <div v-else :style="{backgroundColor: background, borderColor: accent}" class="p-2 rounded-xl border-2" @mouseenter="isHovered = true"
    @mouseleave="isHovered = false">
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