<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AmbientBackground from '../Components/AmbientBackground.vue'
import PoweredByZain from '../Components/PoweredByZain.vue'
const route = useRoute()
const showAmbient = computed(() => route.meta.ambient === true)

// h-[100dvh] is a DEFINITE height; min-h-[100dvh] is a floor the content can
// exceed. Percentage heights and flex overflow only work against the former,
// which is why the lobby list grew instead of scrolling.
const fitViewport = computed(() => route.meta.fitViewport === true)
</script>

<template>
  <div
    class="relative flex flex-col overflow-hidden bg-gray-dark"
    :class="fitViewport ? 'h-[100dvh]' : 'min-h-[100dvh]'"
  >
    <AmbientBackground v-if="showAmbient" />

    <div
      class="relative z-10 flex flex-col"
      :class="fitViewport ? 'h-full min-h-0' : 'min-h-[100dvh]'"
    >
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" class="min-h-0 flex-1" />
        </Transition>
      </RouterView>

      <PoweredByZain />
    </div>
  </div>
</template>

<style scoped>
.page-enter-active,
.page-leave-active {
  transition: opacity 250ms ease, transform 250ms ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active { transition: none; }
}
</style>