<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AmbientBackground from '../Components/AmbientBackground.vue'
import PoweredByZain from '../Components/PoweredByZain.vue'

/**
 * Wraps every non-game page: optional background, the routed view, then the
 * footer.
 *
 * A LAYOUT ROUTE — the router nests landing/auth/lobby underneath it, so this
 * mounts once and stays mounted while the child swaps. The footer lives here,
 * in one place, instead of being repeated in every view.
 */
const route = useRoute()

// Opt IN, not out: only a route that explicitly asks for the decorated
// background gets one. Everything else is plain gray-dark.
const showAmbient = computed(() => route.meta.ambient === true)
</script>

<template>
  <div class="relative flex min-h-[100dvh] flex-col overflow-hidden bg-gray-dark">
    <AmbientBackground v-if="showAmbient" />

    <!-- z-10 lifts real content above the decorative layers -->
    <div class="relative z-10 flex min-h-[100dvh] flex-col">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" class="flex-1" />
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