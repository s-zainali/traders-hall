<script setup lang="ts">

</script>

<template>
    <div>
        <div class="flex flex-col p-4 gap-2 bg-gray-x-dark border-2 border-gray-light rounded-[1.5rem]">
            <div class="flex items-center">
                <div class="h-15 w-15 bg-gray-2x-light" :style="{
                    mask: `url(/user.png) no-repeat center / contain`,
                    '-webkit-mask': `url(/user.png) no-repeat center / contain`,
                }"></div>
                <h1 class="text-2xl text-gray-2x-light font-bold tracking-wide">Your Cards</h1>
            </div>
            <div class="p-2 border-1 border-gray-light rounded-[1rem]">
                <slot />
            </div>
        </div>
    </div>
</template>