<script setup>
import { computed, ref } from 'vue'
const props = defineProps({
    title: String,
    iconUrl: String,
    color: String,
    bgColor: String,
    hasBorder: Boolean,
    cost: Number,
})

const isHovered = ref(false)
const isSelected = ref(false)
const background = computed(() => `var(--color-${isHovered.value || isSelected.value ? props.bgColor : props.color})`)
const accent = computed(() => `var(--color-${isHovered.value || isSelected.value ? props.color : props.bgColor})`)

</script>

<template>
    <div class="flex flex-col">
        <div class="w-[120px] h-[180px] rounded-xl p-6 flex flex-col items-center border-4 justify-between shrink-0 cursor-pointer hover:scale-110 transition duration-300 ease-in-out"
            :style="{ borderColor: accent, backgroundColor: background }" @mouseenter="isHovered = true"
            @mouseleave="isHovered = false" @click="isSelected = !isSelected">
            <span class="font-bold text-lg uppercase pb-6" :style="{ color: accent }">{{ title }}</span>
    
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
        <div class="flex items-center justify-center px-6 pt-4">
            <span v-if="isHovered"  class="font-bold text-lg h-6" :style="{color: background}">{{ cost }} {{ cost === 1? 'Point' : 'Points' }}</span>
            <span class="h-6"></span>
        </div>
    </div>
</template>