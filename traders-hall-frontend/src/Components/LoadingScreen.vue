<script setup>
defineProps({
  message: { type: String, default: 'Loading…' },
  error: { type: String, default: '' },
})
defineEmits(['retry'])
</script>

<template>
  <div class="min-h-[100dvh] bg-gray-dark flex flex-col items-center justify-center gap-6 p-6">
    <h1 class="text-3xl text-gray-2x-light font-bold tracking-widest">Traders Hall</h1>

    <template v-if="error">
      <p class="text-rose-400 font-bold">{{ error }}</p>
      <button
        class="px-6 py-3 rounded-xl font-bold cursor-pointer bg-gray-2x-light text-gray-dark
               hover:scale-105 transition duration-300 ease-in-out"
        @click="$emit('retry')"
      >Retry</button>
    </template>

    <template v-else>
      <!-- three dots, staggered by animation-delay -->
      <div class="flex gap-2">
        <span
          v-for="i in 3"
          :key="i"
          class="h-3 w-3 rounded-full bg-teal-light animate-bounce"
          :style="{ animationDelay: `${(i - 1) * 150}ms` }"
        ></span>
      </div>
      <p class="text-gray-x-light font-bold tracking-wide">{{ message }}</p>
    </template>
  </div>
</template>