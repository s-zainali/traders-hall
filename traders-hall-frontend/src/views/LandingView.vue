<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'

/*
  The hero fan. Built from plain divs rather than <Card>, deliberately: the
  landing page must render before the card catalogue has been fetched (and for
  visitors who are not signed in at all), so it cannot depend on the store.
  Same masked-icon technique, no data dependency.
*/
const heroCards = [
  { icon: '/wheat.png',     accent: 'cream-dark',  bg: 'cream-light',  rotate: -22, x: -170, y: 28,  z: 1 },
  { icon: '/home.png',     accent: 'purple-dark', bg: 'purple-light', rotate: -11, x: -88,  y: 6,   z: 2 },
  { icon: '/star.png',     accent: 'teal-dark',   bg: 'teal-light',   rotate: 0,   x: 0,    y: -8,  z: 3 },
  { icon: '/mansion.png',  accent: 'purple-dark', bg: 'purple-light', rotate: 11,  x: 88,   y: 6,   z: 2 },
  { icon: '/investor.png', accent: 'blue-dark',   bg: 'blue-light',   rotate: 22,  x: 170,  y: 28,  z: 1 },
]

const features = [
  {
    title: 'Build an estate',
    body: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Acquire houses, mansions and towers, then invest to turn them into income.',
    accent: 'text-purple-light',
    border: 'hover:border-purple-light/60',
    glow: 'group-hover:shadow-purple-light/20',
    step: '01',
  },
  {
    title: 'Trade or starve',
    body: 'Sed do eiusmod tempor incididunt ut labore. Rice and wheat keep you alive. Run out and you are out of the game.',
    accent: 'text-cream-light',
    border: 'hover:border-cream-light/60',
    glow: 'group-hover:shadow-cream-light/20',
    step: '02',
  },
  {
    title: 'Outlast everyone',
    body: 'Ut enim ad minim veniam, quis nostrud exercitation. There is no points target. The last trader still standing takes the hall.',
    accent: 'text-teal-light',
    border: 'hover:border-teal-light/60',
    glow: 'group-hover:shadow-teal-light/20',
    step: '03',
  },
]

const stats = [
  { value: '2–4', label: 'Players' },
  { value: '7', label: 'Card types' },
  { value: '∞', label: 'Ways to go broke' },
]

/*
  Scroll reveal. One IntersectionObserver for every [data-reveal] element rather
  than one per element — cheaper, and it lets the stagger be computed from the
  element's index inside its own group.
*/
const observer = ref(null)

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const targets = document.querySelectorAll('[data-reveal]')

  if (reduced) {
    targets.forEach((el) => el.classList.add('revealed'))
    return
  }

  observer.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('revealed')
        observer.value.unobserve(entry.target)   // reveal once, then stop watching
      })
    },
    { threshold: 0.15, rootMargin: '0px 0px -60px 0px' }
  )

  targets.forEach((el) => observer.value.observe(el))
})

onUnmounted(() => observer.value?.disconnect())
</script>

<template>
  <div class="flex flex-col">

    <header class="flex items-center justify-between p-6">
      <span class="font-bold tracking-widest text-gray-2x-light ml-4">TRADERS HALL</span>
      <RouterLink
        :to="{ name: 'auth' }"
        class="rounded-xl border-2 border-gray-light px-5 py-2 font-bold text-gray-x-light
               transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light"
      >Sign in</RouterLink>
    </header>

    <main class="flex flex-col items-center gap-12 px-6 pt-10 pb-20 text-center">

      <!-- hero fan: each card deals in with its own delay -->
      <div class="relative h-56 w-full max-w-2xl">
        <!--
          Two elements on purpose. The SLOT runs the deal-in animation; the CARD
          owns the hover transition. Sharing one element makes them fight: an
          animation with fill-mode:forwards keeps its final value applied, and
          animated values outrank transitions in the cascade, so the hover could
          not interpolate — it snapped.
        -->
        <div
          v-for="(c, i) in heroCards"
          :key="i"
          class="hero-slot absolute left-1/2 top-6"
          :style="{
            '--x': `${c.x}px`,
            '--y': `${c.y}px`,
            zIndex: c.z,
            animationDelay: `${i * 90}ms`,
          }"
        >
          <div
            class="hero-card h-40 w-28 rounded-2xl border-4 shadow-2xl shadow-black/50"
            :style="{
              '--rot': `${c.rotate}deg`,
              backgroundColor: `var(--color-${c.bg})`,
              borderColor: `var(--color-${c.accent})`,
            }"
          >
            <div class="flex h-full w-full items-center justify-center p-5">
              <div
                class="h-full w-full"
                :style="{
                  backgroundColor: `var(--color-${c.accent})`,
                  mask: `url(${c.icon}) no-repeat center / contain`,
                  '-webkit-mask': `url(${c.icon}) no-repeat center / contain`,
                }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-col items-center gap-6">
        <span
          class="intro intro-1 rounded-full border-2 border-teal-light/40 bg-teal-dark/20 px-4 py-1.5
                 text-xs font-bold uppercase tracking-widest text-teal-light"
        >Now in development</span>

        <h1 class="intro intro-2 max-w-4xl text-6xl font-bold tracking-widest sm:text-7xl">
          <span class="title-shimmer">Traders Hall</span>
        </h1>

        <p class="intro intro-3 max-w-xl text-lg leading-relaxed text-gray-x-light">
          Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
          incididunt ut labore et dolore magna aliqua. Buy, sell, trade and invest — and
          make sure you can still pay the rent when the turn comes around.
        </p>
      </div>

      <div class="intro intro-4 flex flex-wrap items-center justify-center gap-4">
        <RouterLink
          :to="{ name: 'auth' }"
          class="cta group relative overflow-hidden rounded-xl border-2 border-teal-light bg-teal-light
                 px-8 py-3.5 font-bold text-gray-dark transition duration-300 ease-in-out
                 hover:brightness-130 hover:scale-101 active:scale-[0.99]
                 focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2"
        >
          <span class="relative z-10">Start playing</span>
          <!-- a light sweep that crosses the button on hover -->
          <span class="sweep pointer-events-none absolute inset-0 z-0" aria-hidden="true"></span>
        </RouterLink>

        <a
          href="#how-it-works"
          class="rounded-xl border-2 border-gray-light px-8 py-3.5 font-bold text-gray-x-light
                 transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light"
        >How it works</a>
      </div>

      <!-- stats strip -->
      <div class="intro intro-5 grid grid-cols-3 items-center justify-center gap-px overflow-hidden
                  rounded-2xl border-2 border-gray-light bg-gray-light">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="flex min-w-36 flex-col items-center gap-1 bg-gray-x-dark/90 px-8 py-5 backdrop-blur-sm"
        >
          <span class="text-3xl font-bold text-gray-2x-light">{{ stat.value }}</span>
          <span class="text-xs font-bold uppercase tracking-widest text-gray-x-light">{{ stat.label }}</span>
        </div>
      </div>
    </main>

    <section id="how-it-works" class="px-6 pb-16">
      <h2
        data-reveal
        class="reveal mb-8 text-center text-xs font-bold uppercase tracking-[0.4em] text-gray-x-light"
      >How it works</h2>

      <div class="mx-auto grid max-w-5xl gap-4 sm:grid-cols-3">
        <div
          v-for="(feature, i) in features"
          :key="feature.title"
          data-reveal
          class="reveal group flex flex-col gap-3 rounded-[1.5rem] border-2 border-gray-light
                 bg-gray-x-dark/80 p-6 backdrop-blur-sm transition duration-300 ease-in-out
                 hover:-translate-y-1 hover:shadow-2xl"
          :class="[feature.border, feature.glow]"
          :style="{ transitionDelay: `${i * 80}ms` }"
        >
          <span class="text-xs font-bold tracking-widest text-gray-light">{{ feature.step }}</span>
          <h3 class="text-xl font-bold tracking-wide" :class="feature.accent">{{ feature.title }}</h3>
          <p class="text-sm leading-relaxed text-gray-x-light">{{ feature.body }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── entrance ─────────────────────────────────────────────── */

/*
  SLOT: owns the deal-in. Each card starts stacked at the centre and slides out
  to its position in the fan, staggered by index so it reads as dealing rather
  than a group fade. Only translate here — no rotation, no hover.
*/
.hero-slot {
  transform: translate(-50%, 40px) scale(0.85);
  opacity: 0;
  animation: deal 700ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes deal {
  from {
    transform: translate(-50%, 40px) scale(0.85);
    opacity: 0;
  }
  to {
    transform: translate(calc(-50% + var(--x)), var(--y)) scale(1);
    opacity: 1;
  }
}

/*
  CARD: owns tilt and hover. The transition lives on the base rule, not inside
  :hover, so it runs in BOTH directions — declaring it only under :hover gives
  a smooth lift and an instant drop.
*/
.hero-card {
  transform: rotate(var(--rot));
  transform-origin: 50% 90%;
  transition:
    transform 350ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 350ms ease,
    filter 350ms ease;
}

.hero-slot:hover {
  z-index: 20;
}

.hero-slot:hover .hero-card {
  transform: rotate(var(--rot)) translateY(-22px) scale(1.07);
  filter: brightness(1.08);
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.7);
}

/* text and controls follow the cards in */
.intro {
  opacity: 0;
  animation: rise 600ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.intro-1 { animation-delay: 550ms; }
.intro-2 { animation-delay: 650ms; }
.intro-3 { animation-delay: 750ms; }
.intro-4 { animation-delay: 850ms; }
.intro-5 { animation-delay: 950ms; }

@keyframes rise {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── title ────────────────────────────────────────────────── */

/*
  background-clip: text paints the gradient through the glyphs. The oversized
  background plus an animated position is what makes the sheen travel across
  the word instead of sitting still.
*/
.title-shimmer {
  background: linear-gradient(
    100deg,
    var(--color-gray-2x-light) 0%,
    var(--color-gray-2x-light) 35%,
    var(--color-teal-light) 50%,
    var(--color-gray-2x-light) 65%,
    var(--color-gray-2x-light) 100%
  );
  background-size: 250% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: title-sheen 6s ease-in-out infinite;
}

@keyframes title-sheen {
  0%, 100% { background-position: 120% 50%; }
  50%      { background-position: -20% 50%; }
}

/* ── CTA sweep ────────────────────────────────────────────── */

.sweep {
  background: linear-gradient(
    100deg,
    transparent 30%,
    rgb(255 255 255 / 0.45) 50%,
    transparent 70%
  );
  transform: translateX(-100%);
}
.cta:hover .sweep {
  animation: sweep 700ms ease-out;
}

@keyframes sweep {
  to { transform: translateX(100%); }
}

/* ── scroll reveal ────────────────────────────────────────── */

.reveal {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 500ms ease, transform 500ms cubic-bezier(0.22, 1, 0.36, 1);
}
.reveal.revealed {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .hero-slot,
  .intro,
  .title-shimmer {
    animation: none;
    opacity: 1;
  }
  .hero-slot {
    transform: translate(calc(-50% + var(--x)), var(--y));
  }
  .hero-card { transition: none; }
  .title-shimmer {
    color: var(--color-gray-2x-light);
    background: none;
  }
  .reveal { transition: none; }
}
</style>