<script setup>
/**
 * Decorative background for the landing page only. Layers, back to front:
 *   aurora → dot matrix → perspective floor → glows → drifting cards
 *   → corner brackets → light sweeps → scanlines → grain → vignette
 *
 * Everything animates on its own timer. No pointer tracking, no listeners,
 * no props — pure CSS ambience.
 */

/*
  Right-hand floaters are anchored with `right`, not `left: 90%`.

  A card at left:90% starts at 90% of the width and then adds its own 6–8rem,
  so it always sticks out past the right edge. Anchoring from the right instead
  means the offset is measured from the edge inward, and the card can never
  exceed it no matter how wide the viewport is.
*/
const floaters = [
  { top: '12%', left: '8%',   size: 'lg', color: 'purple', rotate: -14, delay: '0s',   duration: '13s' },
  { top: '62%', left: '4%',   size: 'md', color: 'cream',  rotate: 9,   delay: '-4s',  duration: '16s' },
  { top: '22%', right: '14%', size: 'lg', color: 'teal',   rotate: 12,  delay: '-8s',  duration: '14s' },
  { top: '68%', right: '6%',  size: 'md', color: 'purple', rotate: -8,  delay: '-2s',  duration: '17s' },
  { top: '44%', right: '2%',  size: 'sm', color: 'cream',  rotate: 18,  delay: '-11s', duration: '11s' },
  { top: '80%', left: '46%',  size: 'sm', color: 'teal',   rotate: -20, delay: '-6s',  duration: '18s' },
  { top: '6%',  left: '52%',  size: 'sm', color: 'purple', rotate: 22,  delay: '-14s', duration: '12s' },
]

const sizes = { sm: 'w-16 h-22', md: 'w-24 h-32', lg: 'w-32 h-44' }

// Full literal class strings — Tailwind's scanner cannot see interpolated ones.
const palettes = {
  purple: 'bg-purple-dark/40 border-purple-light/40',
  cream: 'bg-cream-dark/25 border-cream-light/30',
  teal: 'bg-teal-dark/35 border-teal-light/40',
}

// Only pass the anchor that was declared, so `left: undefined` never lands in
// the style object and quietly beats the `right` value.
function place(f) {
  return f.left !== undefined ? { top: f.top, left: f.left } : { top: f.top, right: f.right }
}
</script>

<template>
  <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">

    <!-- aurora: three oversized blurred blobs on long, mismatched cycles, so
         the colour field never visibly repeats -->
    <div class="aurora aurora-a"></div>
    <div class="aurora aurora-b"></div>
    <div class="aurora aurora-c"></div>

    <!-- fine technical texture, faded out toward the edges -->
    <div class="absolute inset-0 dots"></div>

    <!-- horizon lines receding to a vanishing point: gives the page ground -->
    <div class="absolute inset-x-0 bottom-0 h-[45vh] floor-wrap">
      <div class="floor"></div>
    </div>

    <!-- deliberately NOT inset-0 — see .glow-layer -->
    <div class="glow-layer absolute"></div>

    <!-- drifting cards: each on its own loop, offset by a negative delay so
         they start mid-cycle instead of all rising together -->
    <div
      v-for="(f, i) in floaters"
      :key="i"
      class="floater absolute rounded-2xl border-4 backdrop-blur-[2px]"
      :class="[sizes[f.size], palettes[f.color]]"
      :style="{
        ...place(f),
        '--rot': `${f.rotate}deg`,
        animationDelay: f.delay,
        animationDuration: f.duration,
      }"
    ></div>

    <!-- framing accents, so the viewport reads as composed rather than cropped -->
    <span class="bracket bracket-tl"></span>
    <span class="bracket bracket-tr"></span>
    <span class="bracket bracket-bl"></span>
    <span class="bracket bracket-br"></span>

    <div class="absolute inset-x-0 top-1/4 h-px sweep-line"></div>
    <div class="absolute inset-x-0 top-2/3 h-px sweep-line sweep-line-delayed"></div>

    <div class="absolute inset-0 scanlines"></div>
    <div class="absolute inset-0 grain"></div>
    <div class="absolute inset-0 vignette"></div>
  </div>
</template>

<style scoped>
/* ── aurora ───────────────────────────────────────────────── */

.aurora {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.32;
  will-change: transform;
}

.aurora-a {
  width: 46rem; height: 34rem;
  top: -12rem; left: -10rem;
  background: radial-gradient(circle, var(--color-purple-light), transparent 65%);
  animation: aurora-a 34s ease-in-out infinite alternate;
}
.aurora-b {
  width: 40rem; height: 40rem;
  top: -6rem; right: -12rem;
  background: radial-gradient(circle, var(--color-teal-light), transparent 65%);
  animation: aurora-b 41s ease-in-out infinite alternate;
}
.aurora-c {
  width: 52rem; height: 30rem;
  bottom: -14rem; left: 25%;
  background: radial-gradient(circle, var(--color-cream-dark), transparent 68%);
  animation: aurora-c 47s ease-in-out infinite alternate;
  opacity: 0.2;
}

@keyframes aurora-a {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to   { transform: translate3d(6rem, 4rem, 0) scale(1.18); }
}
@keyframes aurora-b {
  from { transform: translate3d(0, 0, 0) scale(1.1); }
  to   { transform: translate3d(-5rem, 6rem, 0) scale(0.92); }
}
@keyframes aurora-c {
  from { transform: translate3d(0, 0, 0) scale(0.95); }
  to   { transform: translate3d(-7rem, -3rem, 0) scale(1.15); }
}

/* ── dot matrix ───────────────────────────────────────────── */

/*
  One tiny radial-gradient tiled by background-size. The mask fades it toward
  the edges so it reads as texture rather than a printed grid.
*/
.dots {
  background-image: radial-gradient(
    circle at 1px 1px,
    color-mix(in oklab, var(--color-gray-2x-light) 22%, transparent) 1px,
    transparent 0
  );
  background-size: 34px 34px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 40%, black 30%, transparent 75%);
}

/* ── perspective floor ────────────────────────────────────── */

.floor-wrap {
  perspective: 340px;
  mask-image: linear-gradient(to top, black 0%, transparent 85%);
  overflow: hidden;
}

/*
  rotateX tips a flat grid away from the viewer; the repeating gradients then
  converge toward a vanishing point on their own. Animating background-position
  makes the grid appear to travel forward.
*/
.floor {
  position: absolute;
  inset: -50% -50% 0 -50%;
  transform: rotateX(72deg);
  transform-origin: 50% 100%;
  background-image:
    repeating-linear-gradient(
      to right,
      color-mix(in oklab, var(--color-teal-light) 30%, transparent) 0 1px,
      transparent 1px 5rem
    ),
    repeating-linear-gradient(
      to bottom,
      color-mix(in oklab, var(--color-teal-light) 22%, transparent) 0 1px,
      transparent 1px 5rem
    );
  animation: floor-travel 9s linear infinite;
  opacity: 0.5;
}

@keyframes floor-travel {
  from { background-position: 0 0, 0 0; }
  to   { background-position: 0 0, 0 5rem; }
}

/* ── glows ────────────────────────────────────────────────── */

/*
  Oversized on purpose. glow-drift translates this layer by ±1.5%, and at
  inset-0 it is exactly viewport-sized — so sliding left leaves an uncovered
  strip on the right where the bare page colour shows through as a dark band.
  Extending 10% past every edge means there is always spare coverage to move
  into. Same reason .aurora and .floor are larger than their containers.
*/
.glow-layer {
  inset: -10%;
  background:
    radial-gradient(60rem 40rem at 15% 20%, color-mix(in oklab, var(--color-purple-light) 20%, transparent), transparent 70%),
    radial-gradient(50rem 35rem at 85% 25%, color-mix(in oklab, var(--color-teal-light) 18%, transparent), transparent 70%),
    radial-gradient(70rem 45rem at 50% 100%, color-mix(in oklab, var(--color-cream-dark) 10%, transparent), transparent 70%);
  animation: glow-drift 24s ease-in-out infinite alternate;
}

@keyframes glow-drift {
  from { transform: translate3d(-1.5%, -1%, 0) scale(1); }
  to   { transform: translate3d(1.5%, 1%, 0) scale(1.06); }
}

/* ── drifting cards ───────────────────────────────────────── */

/*
  Tilt and drift must share ONE transform: a second transform declaration
  replaces the first rather than composing with it. The --rot custom property
  lets every card keep its own angle while sharing one keyframe.
*/
.floater {
  transform: rotate(var(--rot));
  animation-name: float;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
  opacity: 0.55;
  will-change: transform;
}

/* travel roughly doubled, rotation doubled, and the durations above cut by a
   third — noticeably livelier without becoming distracting */
@keyframes float {
  from { transform: translate3d(-14px, -28px, 0) rotate(calc(var(--rot) - 3deg)); }
  to   { transform: translate3d(14px, 28px, 0) rotate(calc(var(--rot) + 3deg)); }
}

/* ── corner brackets ──────────────────────────────────────── */

.bracket {
  position: absolute;
  width: 3.5rem;
  height: 3.5rem;
  border-color: color-mix(in oklab, var(--color-teal-light) 45%, transparent);
  opacity: 0.5;
}
.bracket-tl { top: 1.25rem; left: 1.25rem;  border-top: 2px solid; border-left: 2px solid;  border-top-left-radius: 1rem; }
.bracket-tr { top: 1.25rem; right: 1.25rem; border-top: 2px solid; border-right: 2px solid; border-top-right-radius: 1rem; }
.bracket-bl { bottom: 1.25rem; left: 1.25rem;  border-bottom: 2px solid; border-left: 2px solid;  border-bottom-left-radius: 1rem; }
.bracket-br { bottom: 1.25rem; right: 1.25rem; border-bottom: 2px solid; border-right: 2px solid; border-bottom-right-radius: 1rem; }

/* ── sweeping light lines ─────────────────────────────────── */

.sweep-line {
  background: linear-gradient(
    to right,
    transparent,
    color-mix(in oklab, var(--color-teal-light) 55%, transparent),
    transparent
  );
  animation: line-sweep 14s ease-in-out infinite;
  opacity: 0;
}
.sweep-line-delayed { animation-delay: 7s; }

@keyframes line-sweep {
  0%        { transform: translateX(-100%); opacity: 0; }
  15%, 70%  { opacity: 0.5; }
  100%      { transform: translateX(100%); opacity: 0; }
}

/* ── overlays ─────────────────────────────────────────────── */

.scanlines {
  background: repeating-linear-gradient(
    to bottom,
    transparent 0 3px,
    rgb(0 0 0 / 0.12) 3px 4px
  );
  opacity: 0.35;
  mix-blend-mode: multiply;
}

/* A few hundred bytes of SVG noise, so large flat gradients do not band. */
.grain {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
  opacity: 0.04;
  mix-blend-mode: overlay;
}

.vignette {
  background: radial-gradient(85% 70% at 50% 45%, transparent 38%, var(--color-gray-dark) 100%);
}

@media (prefers-reduced-motion: reduce) {
  .aurora,
  .glow-layer,
  .floater,
  .floor,
  .sweep-line { animation: none; }
  .sweep-line { opacity: 0.25; }
}
</style>