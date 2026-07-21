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
        <div class="w-[90px] h-[120px] rounded-xl p-3 flex flex-col items-center border-4 justify-between shrink-0 cursor-pointer hover:scale-110 transition duration-300 ease-in-out"
            :style="{ borderColor: accent, backgroundColor: background }" @mouseenter="isHovered = true"
            @mouseleave="isHovered = false" @click="isSelected = !isSelected">
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
            <span v-if="isHovered"  class="font-bold text-md h-4 " :style="{color: background}">{{ cost }} {{cost ? cost === 1? 'Point' : 'Points': '' }}</span>
            <span  class="h-4"></span>
        </div>
    </div>
</template>