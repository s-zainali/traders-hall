<script setup>
import { RouterLink } from 'vue-router'

// Decorative cards drifting behind the content. Declared as data so the
// positions are readable and tweakable rather than buried in markup.
// Colours reference the same theme tokens the real cards use.
const floaters = [
  { top: '12%', left: '8%',  size: 'lg', color: 'purple', rotate: -14, delay: '0s',   duration: '19s' },
  { top: '62%', left: '4%',  size: 'md', color: 'cream',  rotate: 9,   delay: '-4s',  duration: '23s' },
  { top: '22%', left: '78%', size: 'lg', color: 'teal',   rotate: 12,  delay: '-8s',  duration: '21s' },
  { top: '68%', left: '85%', size: 'md', color: 'purple', rotate: -8,  delay: '-2s',  duration: '25s' },
  { top: '44%', left: '90%', size: 'sm', color: 'cream',  rotate: 18,  delay: '-11s', duration: '17s' },
  { top: '80%', left: '46%', size: 'sm', color: 'teal',   rotate: -20, delay: '-6s',  duration: '27s' },
  { top: '6%',  left: '52%', size: 'sm', color: 'purple', rotate: 22,  delay: '-14s', duration: '20s' },
]

const sizes = {
  sm: 'w-16 h-22',
  md: 'w-24 h-32',
  lg: 'w-32 h-44',
}

// Full literal class strings — Tailwind's scanner cannot see interpolated ones.
const palettes = {
  purple: 'bg-purple-dark/40 border-purple-light/40',
  cream: 'bg-cream-dark/25 border-cream-light/30',
  teal: 'bg-teal-dark/35 border-teal-light/40',
}

const features = [
  {
    title: 'Build an estate',
    body: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Acquire houses, mansions and towers, then invest to turn them into income.',
    accent: 'text-purple-light',
  },
  {
    title: 'Trade or starve',
    body: 'Sed do eiusmod tempor incididunt ut labore. Rice and wheat keep you alive. Run out and you are out of the game.',
    accent: 'text-cream-light',
  },
  {
    title: 'Outlast everyone',
    body: 'Ut enim ad minim veniam, quis nostrud exercitation. There is no points target. The last trader still standing takes the hall.',
    accent: 'text-teal-light',
  },
]
</script>

<template>
  <div class="landing relative min-h-[100dvh] overflow-hidden bg-gray-dark">

    <!-- ── background layers, back to front ── -->

    <!-- coloured glows -->
    <div class="pointer-events-none absolute inset-0 glow-layer" aria-hidden="true"></div>

    <!-- drifting cards -->
    <div class="pointer-events-none absolute inset-0" aria-hidden="true">
      <div
        v-for="(f, i) in floaters"
        :key="i"
        class="floater absolute rounded-2xl border-4 backdrop-blur-[2px]"
        :class="[sizes[f.size], palettes[f.color]]"
        :style="{
          top: f.top,
          left: f.left,
          '--rot': `${f.rotate}deg`,
          animationDelay: f.delay,
          animationDuration: f.duration,
        }"
      ></div>
    </div>

    <!-- grain, and a vignette so the edges fall away and the centre reads -->
    <div class="pointer-events-none absolute inset-0 grain" aria-hidden="true"></div>
    <div class="pointer-events-none absolute inset-0 vignette" aria-hidden="true"></div>

    <!-- ── content ── -->
    <div class="relative z-10 flex min-h-[100dvh] flex-col">

      <header class="flex items-center justify-between p-6">
        <span class="font-bold tracking-widest text-gray-2x-light">TRADERS HALL</span>
        <RouterLink
          :to="{ name: 'auth' }"
          class="rounded-xl border-2 border-gray-light px-5 py-2 font-bold text-gray-x-light
                 transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light hover:bg-gray-light"
        >Sign in</RouterLink>
      </header>

      <main class="flex flex-1 flex-col items-center justify-center gap-10 px-6 py-16 text-center">

        <div class="flex flex-col items-center gap-6">
          <span
            class="rounded-full border-2 border-teal-light/40 bg-teal-dark/20 px-4 py-1.5
                   text-xs font-bold uppercase tracking-widest text-teal-light"
          >Now in development</span>

          <h1 class="max-w-4xl text-6xl font-bold tracking-widest text-gray-2x-light sm:text-7xl">
            Traders Hall
          </h1>

          <p class="max-w-xl text-lg leading-relaxed text-gray-x-light">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
            incididunt ut labore et dolore magna aliqua. Buy, sell, trade and invest — and
            make sure you can still pay the rent when the turn comes around.
          </p>
        </div>

        <div class="flex flex-wrap items-center justify-center gap-4">
          <RouterLink
            :to="{ name: 'auth' }"
            class="rounded-xl border-2 border-teal-light bg-teal-light px-8 py-3.5 font-bold text-gray-dark
                   transition duration-200 ease-in-out hover:brightness-110
                   focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2"
          >Start playing</RouterLink>

          <a
            href="#how-it-works"
            class="rounded-xl border-2 border-gray-light px-8 py-3.5 font-bold text-gray-x-light
                   transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light"
          >How it works</a>
        </div>
      </main>

      <section id="how-it-works" class="px-6 pb-20">
        <div class="mx-auto grid max-w-5xl gap-4 sm:grid-cols-3">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="flex flex-col gap-3 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/80 p-6
                   backdrop-blur-sm transition duration-300 ease-in-out hover:border-gray-x-light"
          >
            <h2 class="text-xl font-bold tracking-wide" :class="feature.accent">{{ feature.title }}</h2>
            <p class="text-sm leading-relaxed text-gray-x-light">{{ feature.body }}</p>
          </div>
        </div>
      </section>

      <footer class="border-t-1 border-gray-light/50 px-6 py-6 text-center text-xs text-gray-x-light">
        Lorem ipsum · A game about property, food and staying solvent
      </footer>
    </div>
  </div>
</template>

<style scoped>
/*
  Two stacked radial gradients rather than one flat colour: the eye reads the
  centre as lit and the corners as falling away, which gives the page depth
  without any images to download.
*/
.glow-layer {
  background:
    radial-gradient(60rem 40rem at 15% 20%, color-mix(in oklab, var(--color-purple-light) 22%, transparent), transparent 70%),
    radial-gradient(50rem 35rem at 85% 25%, color-mix(in oklab, var(--color-teal-light) 20%, transparent), transparent 70%),
    radial-gradient(70rem 45rem at 50% 100%, color-mix(in oklab, var(--color-cream-dark) 12%, transparent), transparent 70%);
  animation: glow-drift 24s ease-in-out infinite alternate;
}

@keyframes glow-drift {
  from { transform: translate3d(-1.5%, -1%, 0) scale(1); }
  to   { transform: translate3d(1.5%, 1%, 0) scale(1.06); }
}

/*
  The rotation lives in a CSS variable so each card keeps its own tilt while
  sharing one keyframe animation — otherwise every card would need its own.
*/
.floater {
  transform: rotate(var(--rot));
  animation-name: float;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
  opacity: 0.55;
}

@keyframes float {
  from { transform: rotate(var(--rot)) translateY(-14px); }
  to   { transform: rotate(var(--rot)) translateY(14px); }
}

/*
  An inline SVG turbulence filter: a few hundred bytes of noise that stops the
  large flat gradients from banding on cheaper displays.
*/
.grain {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
  opacity: 0.035;
  mix-blend-mode: overlay;
}

.vignette {
  background: radial-gradient(85% 70% at 50% 45%, transparent 40%, var(--color-gray-dark) 100%);
}

@media (prefers-reduced-motion: reduce) {
  .glow-layer,
  .floater {
    animation: none;
  }
}
</style>