<script setup>
import Card from '../Components/Card.vue'
import IdeaByMesum from '../Components/IdeaByMesum.vue'
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'

/*
  The hero fan. Built from plain divs rather than <Card>, deliberately: the
  landing page must render before the card catalogue has been fetched (and for
  visitors who are not signed in at all), so it cannot depend on the store.
  Same masked-icon technique, no data dependency.
*/
const heroCards = [
    { icon: '/wheat.png', accent: 'cream-dark', bg: 'cream-light', rotate: -22, x: -170, y: 28, z: 1 },
    { icon: '/home.png', accent: 'purple-dark', bg: 'purple-light', rotate: -11, x: -88, y: 6, z: 2 },
    { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light', rotate: 0, x: 0, y: -8, z: 3 },
    { icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light', rotate: 11, x: 88, y: 6, z: 2 },
    { icon: '/investor.png', accent: 'blue-dark', bg: 'blue-light', rotate: 22, x: 170, y: 28, z: 1 },
]

const features = [
    {
        title: 'Take a roof',
        body: 'A house sleeps one. A mansion two, a tower three. Every room you are not sleeping in is a room you can let — and a tenant pays whether or not you traded well that turn.',
        accent: 'text-purple-light',
        border: 'hover:border-purple-light/60',
        glow: 'group-hover:shadow-purple-light/20',
        step: '01',
    },
    {
        title: 'Trade or starve',
        body: 'Rice keeps you fed for two turns, wheat for five. The bank\'s shelves are finite. Once they are bare, the only grain left on the table is in somebody else\'s hand, at their price.',
        accent: 'text-cream-light',
        border: 'hover:border-cream-light/60',
        glow: 'group-hover:shadow-cream-light/20',
        step: '02',
    },
    {
        title: 'Outlast everyone',
        body: 'There is no score to chase. Miss a meal, miss the rent, default on a loan — the table collects what it is owed, in points and then in cards. The last trader still solvent takes the hall.',
        accent: 'text-teal-light',
        border: 'hover:border-teal-light/60',
        glow: 'group-hover:shadow-teal-light/20',
        step: '03',
    },
]

/*
  The deck, described by what each card DOES rather than what it costs. Prices
  move with the balance pass; the role a card plays does not.

  Icons come from /public by path for the same reason the hero fan does — this
  page renders before the card catalogue is fetched, and for visitors who have
  never signed in.
*/
const deck = [
    { name: 'Point', icon: '/star.png', accent: 'teal-dark', bg: 'teal-light', rot: -5, role: 'Currency. Every price is quoted in them, the bank holds a finite pile, and nobody can print more.' },
    { name: 'House', icon: '/home.png', accent: 'purple-dark', bg: 'purple-light', rot: 3, role: 'One room. The cheapest roof there is, and the cheapest place to put a paying tenant.' },
    { name: 'Mansion', icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light', rot: -4, role: 'Two rooms. Live in one, let the other, and let the other pay for the card.' },
    { name: 'Tower', icon: '/building.png', accent: 'purple-dark', bg: 'purple-light', rot: 5, role: 'Three rooms. A landlord\'s card — if you can carry the cost of holding it.' },
    { name: 'Rice', icon: '/rice.png', accent: 'cream-dark', bg: 'cream-light', rot: -3, role: 'Two turns of food. Enough to get to the next deal, rarely enough to get comfortable.' },
    { name: 'Wheat', icon: '/wheat.png', accent: 'cream-dark', bg: 'cream-light', rot: 4, role: 'Five turns of food. The difference between planning your turns and scrambling through them.' },
    { name: 'Invest', icon: '/investor.png', accent: 'blue-dark', bg: 'blue-light', rot: -5, role: 'Turns an estate from shelter into income. Arriving with the yield rules.' },
]

/*
  Three counters, all running at once. This is the part that makes the game a
  game rather than a market: everything you own has a cost of carry.
*/
const clocks = [
    {
        title: 'Hunger',
        accent: 'text-cream-light',
        border: 'hover:border-cream-light/60',
        body: 'Counts down every turn you take. Eat and it resets to the value of what you ate — never higher, so hoarding meals buys you nothing. Reach zero with an empty hand and you are out.',
    },
    {
        title: 'Rent',
        accent: 'text-teal-light',
        border: 'hover:border-teal-light/60',
        body: 'If you do not own the roof you sleep under, you pay whoever does. The amount and the interval are whatever the two of you agreed — the game sets neither.',
    },
    {
        title: 'Credit',
        accent: 'text-blue-light',
        border: 'hover:border-blue-light/60',
        body: 'The bank lends interest free, and takes property as security. Let a loan run past its term and it collects: your points first, then whatever it can seize to cover the rest.',
    },
]

/*
  Mock postings for the floor section, drawn as the real offers panel draws them.
  Plain data and plain divs: this renders before any card catalogue is fetched,
  and for visitors who have never signed in.
*/
const showcase = [
    {
        who: 'Mesum', seat: 'purple-light', badge: 'Sell',
        badgeCls: 'border-rose-400/50 bg-rose-400/15 text-rose-400',
        arrow: 'text-rose-400',
        give: { icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light' },
        qty: '×1',
        get: { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light' },
        amount: '3',
        note: '',
        hands: ['teal-light', 'cream-light'],
        rot: -2,
    },
    {
        who: 'Bilal', seat: 'teal-light', badge: 'To let',
        badgeCls: 'border-teal-light/50 bg-teal-dark/30 text-teal-light',
        arrow: 'text-teal-light',
        give: { icon: '/building.png', accent: 'purple-dark', bg: 'purple-light' },
        qty: '',
        get: { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light' },
        amount: '2',
        note: 'every 3 turns',
        hands: ['purple-light'],
        rot: 1.5,
    },
    {
        who: 'You', seat: 'cream-light', badge: 'Trade',
        badgeCls: 'border-amber-400/50 bg-amber-400/15 text-amber-400',
        arrow: 'text-amber-400',
        give: { icon: '/wheat.png', accent: 'cream-dark', bg: 'cream-light' },
        qty: '×2',
        get: { icon: '/rice.png', accent: 'cream-dark', bg: 'cream-light' },
        amount: '',
        note: '',
        hands: [],
        rot: -1,
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

        <header class="grid items-start grid-cols-3 p-6">
            <span class="font-bold tracking-widest text-gray-2x-light ml-4 mt-3">TRADERS HALL</span>
            <IdeaByMesum />
            <RouterLink :to="{ name: 'auth' }" class="justify-self-end rounded-xl max-w-35 border-2 border-gray-light px-5 py-2 font-bold text-gray-x-light
               transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light">Sign in
            </RouterLink>
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
                <div v-for="(c, i) in heroCards" :key="i" class="hero-slot absolute left-1/2 top-6" :style="{
                    '--x': `${c.x}px`,
                    '--y': `${c.y}px`,
                    zIndex: c.z,
                    animationDelay: `${i * 90}ms`,
                }">
                    <div class="hero-card h-40 w-28 rounded-2xl border-4 shadow-2xl shadow-black/50" :style="{
                        '--rot': `${c.rotate}deg`,
                        backgroundColor: `var(--color-${c.bg})`,
                        borderColor: `var(--color-${c.accent})`,
                    }">
                        <div class="flex h-full w-full items-center justify-center p-5">
                            <div class="h-full w-full" :style="{
                                backgroundColor: `var(--color-${c.accent})`,
                                mask: `url(${c.icon}) no-repeat center / contain`,
                                '-webkit-mask': `url(${c.icon}) no-repeat center / contain`,
                            }"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex flex-col items-center gap-6">
                <span class="intro intro-1 rounded-full border-2 border-teal-light/40 bg-teal-dark/20 px-4 py-1.5
                 text-xs font-bold uppercase tracking-widest text-teal-light">Now in development</span>

                <h1 class="intro intro-2 max-w-4xl text-6xl font-bold tracking-widest sm:text-7xl">
                    <span class="title-shimmer">Traders Hall</span>
                </h1>

                <p class="intro intro-3 max-w-xl text-lg leading-relaxed text-gray-x-light">
                    Two to four traders, one bank, and a table where the only fixed prices are the
                    bank's. Buy property, corner the grain, name your own rent — and make sure you
                    can still eat when the turn comes back around.
                </p>
            </div>

            <div class="intro intro-4 flex flex-wrap items-center justify-center gap-4">
                <RouterLink :to="{ name: 'auth' }" class="cta group relative overflow-hidden rounded-xl border-2 border-teal-light bg-teal-light
                 px-8 py-3.5 font-bold text-gray-dark transition duration-300 ease-in-out
                 hover:brightness-130 hover:scale-101 active:scale-[0.99]
                 focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                    <span class="relative z-10">Start playing</span>
                    <!-- a light sweep that crosses the button on hover -->
                    <span class="sweep pointer-events-none absolute inset-0 z-0" aria-hidden="true"></span>
                </RouterLink>

                <a href="#how-it-works" class="rounded-xl border-2 border-gray-light px-8 py-3.5 font-bold text-gray-x-light
                 transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light">How it
                    works</a>
            </div>

            <!-- stats strip -->
            <div class="intro intro-5 grid grid-cols-3 items-center justify-center gap-px overflow-hidden
                  rounded-2xl border-2 border-gray-light bg-gray-light">
                <div v-for="stat in stats" :key="stat.label"
                    class="flex min-w-36 flex-col items-center gap-1 bg-gray-x-dark/90 px-8 py-5">
                    <span class="text-3xl font-bold text-gray-2x-light">{{ stat.value }}</span>
                    <span class="text-xs font-bold uppercase tracking-widest text-gray-x-light">{{ stat.label }}</span>
                </div>
            </div>
        </main>

        <section id="how-it-works" class="px-6 pb-16">
            <h2 data-reveal
                class="reveal mb-8 text-center text-lg font-bold uppercase tracking-[0.4em] text-gray-x-light">How it
                works</h2>

            <div class="mx-auto grid max-w-5xl gap-4 sm:grid-cols-3">
                <div v-for="(feature, i) in features" :key="feature.title" data-reveal class="reveal group flex flex-col gap-3 rounded-[1.5rem] border-2 border-gray-light
                 bg-gray-x-dark/80 p-6 transition duration-300 ease-in-out
                 hover:-translate-y-1 hover:shadow-2xl" :class="[feature.border, feature.glow]"
                    :style="{ transitionDelay: `${i * 80}ms` }">
                    <span class="text-xs font-bold tracking-widest text-gray-light">{{ feature.step }}</span>
                    <h3 class="text-xl font-bold tracking-wide" :class="feature.accent">{{ feature.title }}</h3>
                    <p class="text-sm leading-relaxed text-gray-x-light">{{ feature.body }}</p>
                </div>
            </div>
        </section>

        <section id="deck" class="border-t-1 border-gray-light/40 px-6 py-16">
            <div class="mx-auto max-w-7xl">
                <h2 data-reveal class="reveal text-center text-lg font-bold uppercase tracking-[0.4em] text-gray-x-light">
                    The deck
                </h2>
                <p data-reveal class="reveal mx-auto mt-4 max-w-2xl text-center text-lg leading-relaxed text-gray-x-light">
                    Seven cards. No filler, no draw pile, nothing you will forget the purpose of by
                    round three.
                </p>

                <div class="mt-12 flex flex-wrap justify-center gap-4">
                    <div v-for="(card, i) in deck" :key="card.name" data-reveal class="deck-slot w-[15.5rem]"
                        :style="{ '--delay': `${i * 70}ms` }">
                        <article class="deck-card flex h-full flex-col items-center gap-4 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/80 px-6 pt-7 pb-6 text-center"
                            :style="{ '--accent': `var(--color-${card.accent})`, '--rot': `${card.rot}deg` }">
                            <div class="deck-face flex h-32 w-24 shrink-0 items-center justify-center rounded-2xl border-4 p-5 shadow-xl shadow-black/40"
                                :style="{
                                    backgroundColor: `var(--color-${card.bg})`,
                                    borderColor: `var(--color-${card.accent})`,
                                }">
                                <div class="h-full w-full" :style="{
                                    backgroundColor: `var(--color-${card.accent})`,
                                    mask: `url(${card.icon}) no-repeat center / contain`,
                                    '-webkit-mask': `url(${card.icon}) no-repeat center / contain`,
                                }"></div>
                            </div>

                            <h3 class="deck-name text-sm font-bold uppercase tracking-[0.3em] text-gray-2x-light">
                                {{ card.name }}
                            </h3>

                            <span class="deck-rule h-0.5 w-8 rounded-full bg-gray-light"></span>

                            <p class="text-sm leading-relaxed text-gray-x-light">{{ card.role }}</p>
                        </article>
                    </div>
                </div>
            </div>
        </section>

        <section id="clocks" class="border-t-1 border-gray-light/40 px-6 py-16">
            <div class="mx-auto max-w-5xl">
                <h2 data-reveal class="reveal text-center text-lg font-bold uppercase tracking-[0.4em] text-gray-x-light">
                    Three clocks
                </h2>
                <p data-reveal class="reveal mx-auto mt-4 max-w-2xl text-center text-lg leading-relaxed text-gray-x-light">
                    Everything you own has a cost of carry. Owning the most is not the same as
                    lasting the longest.
                </p>

                <div class="mt-10 grid gap-4 sm:grid-cols-3">
                    <div v-for="(clock, i) in clocks" :key="clock.title" data-reveal
                        class="reveal flex flex-col gap-3 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/80 p-6 transition duration-300 ease-in-out hover:-translate-y-1"
                        :class="clock.border" :style="{ transitionDelay: `${i * 80}ms` }">
                        <h3 class="text-xl font-bold tracking-wide" :class="clock.accent">{{ clock.title }}</h3>
                        <p class="text-sm leading-relaxed text-gray-x-light">{{ clock.body }}</p>
                    </div>
                </div>
            </div>
        </section>

        <section id="market" class="border-t-1 border-gray-light/40 px-6 py-16">
            <div class="mx-auto grid max-w-5xl items-center gap-12 lg:grid-cols-2">
                <div data-reveal class="reveal flex flex-col gap-5">
                    <h2 class="text-lg font-bold uppercase tracking-[0.4em] text-gray-x-light">The floor</h2>
                    <h3 class="text-4xl font-bold leading-tight tracking-wide text-gray-2x-light">
                        You choose who you<br class="hidden sm:block" /> deal with
                    </h3>
                    <p class="text-lg leading-relaxed text-gray-x-light">
                        Put something on the floor and anyone can raise a hand for it. Usually several
                        do. You see every one of them — who they are, what they are holding — and you
                        decide which of them walks away with it.
                    </p>
                    <p class="text-lg leading-relaxed text-gray-x-light">
                        Cards for points. Cards for cards. A spare room at a rent you set, for as long
                        as you both keep to it. And if you are sleeping rough, say what you will pay
                        and wait for a landlord to take you up on it.
                    </p>
                </div>

                <div data-reveal class="reveal flex flex-col gap-3">
                    <div v-for="(o, i) in showcase" :key="o.who" class="post-slot" :style="{ '--rot': `${o.rot}deg` }">
                        <article class="post flex flex-col gap-3 rounded-[1.25rem] border-2 border-gray-light bg-gray-x-dark/90 p-4 shadow-xl shadow-black/30">

                            <div class="flex items-center gap-2">
                                <span class="h-5 w-5 shrink-0 rounded-md border-2"
                                    :style="{ borderColor: `var(--color-${o.seat})`, backgroundColor: `color-mix(in oklab, var(--color-${o.seat}) 30%, transparent)` }"></span>
                                <span class="min-w-0 flex-1 truncate text-sm font-bold text-gray-2x-light">{{ o.who }}</span>
                                <span class="rounded-full border-2 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                                    :class="o.badgeCls">{{ o.badge }}</span>
                            </div>

                            <div class="flex items-center gap-2">
                                <span class="flex h-9 w-7 items-center justify-center rounded-lg border-2 p-1.5"
                                    :style="{ backgroundColor: `var(--color-${o.give.bg})`, borderColor: `var(--color-${o.give.accent})` }">
                                    <span class="h-full w-full" :style="{
                                        backgroundColor: `var(--color-${o.give.accent})`,
                                        mask: `url(${o.give.icon}) no-repeat center / contain`,
                                        '-webkit-mask': `url(${o.give.icon}) no-repeat center / contain`,
                                    }"></span>
                                </span>
                                <span v-if="o.qty" class="text-sm font-bold tabular-nums text-gray-2x-light">{{ o.qty }}</span>

                                <svg class="h-4 w-4 shrink-0" :class="o.arrow" viewBox="0 0 16 16" fill="none"
                                    stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                                    aria-hidden="true">
                                    <path d="M2.5 8h11M9.5 4 13.5 8l-4 4" />
                                </svg>

                                <span class="flex h-9 w-7 items-center justify-center rounded-lg border-2 p-1.5"
                                    :style="{ backgroundColor: `var(--color-${o.get.bg})`, borderColor: `var(--color-${o.get.accent})` }">
                                    <span class="h-full w-full" :style="{
                                        backgroundColor: `var(--color-${o.get.accent})`,
                                        mask: `url(${o.get.icon}) no-repeat center / contain`,
                                        '-webkit-mask': `url(${o.get.icon}) no-repeat center / contain`,
                                    }"></span>
                                </span>
                                <span v-if="o.amount" class="text-sm font-bold tabular-nums text-teal-light">{{ o.amount }}</span>
                            </div>

                            <span v-if="o.note"
                                class="text-[10px] font-bold uppercase tracking-widest text-teal-light">{{ o.note }}</span>

                            <div v-if="o.hands.length" class="flex items-center gap-2">
                                <span class="text-[10px] font-bold uppercase tracking-widest text-gray-light">Hands up</span>
                                <span v-for="(h, j) in o.hands" :key="j" class="h-4 w-4 rounded-md border-2"
                                    :style="{ borderColor: `var(--color-${h})`, backgroundColor: `color-mix(in oklab, var(--color-${h}) 30%, transparent)` }"></span>
                            </div>
                        </article>
                    </div>
                </div>
            </div>
        </section>

        <section class="px-6 pb-20 pt-6">
            <div data-reveal
                class="reveal mx-auto flex max-w-3xl flex-col items-center gap-6 rounded-[2rem] border-2 border-teal-light/40 bg-teal-dark/10 px-8 py-14 text-center">
                <h2 class="text-4xl font-bold tracking-wide text-gray-2x-light sm:text-5xl">
                    The hall is open
                </h2>
                <p class="max-w-xl text-lg leading-relaxed text-gray-x-light">
                    Make an account, send the code to three people who will not forgive you for
                    raising the rent, and deal.
                </p>
                <RouterLink :to="{ name: 'auth' }"
                    class="cta group relative overflow-hidden rounded-xl border-2 border-teal-light bg-teal-light px-8 py-3.5 font-bold text-gray-dark transition duration-300 ease-in-out hover:brightness-130 hover:scale-101 active:scale-[0.99] focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                    <span class="relative z-10">Start playing</span>
                    <span class="sweep pointer-events-none absolute inset-0 z-0" aria-hidden="true"></span>
                </RouterLink>
            </div>
        </section>

        <footer class="border-t-1 border-gray-light/40 px-6 py-10">
            <div class="mx-auto flex max-w-5xl flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
                <span class="font-bold tracking-widest text-gray-2x-light">TRADERS HALL</span>
                <div class="flex flex-col gap-1 text-xs font-bold uppercase tracking-widest text-gray-light sm:flex-row sm:gap-6">
                    <span>Concept by <span class="text-purple-light">Mesum</span></span>
                    <span>Built by <span class="text-teal-light">Zain</span></span>
                </div>
            </div>
        </footer>
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

.intro-1 {
    animation-delay: 550ms;
}

.intro-2 {
    animation-delay: 650ms;
}

.intro-3 {
    animation-delay: 750ms;
}

.intro-4 {
    animation-delay: 850ms;
}

.intro-5 {
    animation-delay: 950ms;
}

@keyframes rise {
    from {
        opacity: 0;
        transform: translateY(16px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* ── title ────────────────────────────────────────────────── */

/*
  background-clip: text paints the gradient through the glyphs. The oversized
  background plus an animated position is what makes the sheen travel across
  the word instead of sitting still.
*/
.title-shimmer {
    background: linear-gradient(100deg,
            var(--color-gray-2x-light) 0%,
            var(--color-gray-2x-light) 35%,
            var(--color-teal-light) 50%,
            var(--color-gray-2x-light) 65%,
            var(--color-gray-2x-light) 100%);
    background-size: 250% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: title-sheen 6s ease-in-out infinite;
}

@keyframes title-sheen {

    0%,
    100% {
        background-position: 120% 50%;
    }

    50% {
        background-position: -20% 50%;
    }
}

/* ── CTA sweep ────────────────────────────────────────────── */

.sweep {
    background: linear-gradient(100deg,
            transparent 30%,
            rgb(255 255 255 / 0.45) 50%,
            transparent 70%);
    transform: translateX(-100%);
}

.cta:hover .sweep {
    animation: sweep 700ms ease-out;
}

@keyframes sweep {
    to {
        transform: translateX(100%);
    }
}

/* ── the deck ─────────────────────────────────────────────── */

/*
  Same split as the hero fan, for the same reason. The SLOT owns the scroll
  entrance and carries the stagger; the CARD owns the hover.

  Sharing one element is what made this flicker: the stagger was an inline
  transition-delay, and a delay applies to EVERY transition on the element — so
  the last card sat still for 400ms before responding to a hover, and again on
  the way out. Worse, Tailwind's `transition` utility and the scoped rule were
  both declaring transition-property and overwriting each other.

  --delay is set per card inline; nothing else on the slot transitions, so it
  cannot leak.
*/
.deck-slot {
    opacity: 0;
    transform: translateY(28px);
    transition:
        opacity 550ms ease,
        transform 550ms cubic-bezier(0.22, 1, 0.36, 1);
    transition-delay: var(--delay, 0ms);
}

.deck-slot.revealed {
    opacity: 1;
    transform: translateY(0);
    /*
      Released once the entrance is done. Holding will-change permanently pins a
      compositor layer per card for the life of the page; holding it only while
      the slot is actually moving is the whole point of the hint.
    */
    will-change: auto;
}

.deck-slot:not(.revealed) {
    will-change: transform, opacity;
}

.deck-card {
    height: 100%;
    transition:
        transform 350ms cubic-bezier(0.22, 1, 0.36, 1),
        border-color 250ms ease,
        box-shadow 350ms ease;
}

/*
  Hover is triggered from the SLOT, never from the card — the same rule the hero
  fan follows, and the reason this flickered when it did not.

  The card lifts 8px on hover. With :hover on the card itself, a cursor near the
  lower edge is left behind as the card moves away: hover ends, the card drops
  back under the cursor, hover fires again, and it oscillates for as long as you
  hold still. The slot's box never moves, so the hover region is stable no
  matter what the card inside it does.

  The glow is mixed from the card's own accent rather than picked from literal
  Tailwind classes. Seven cards across four palettes would otherwise need every
  combination spelled out, since the scanner cannot read an interpolated class
  name.
*/
.deck-slot:hover .deck-card {
    transform: translateY(-8px);
    border-color: color-mix(in oklab, var(--accent) 65%, transparent);
    box-shadow: 0 28px 55px -20px color-mix(in oklab, var(--accent) 65%, transparent);
}

/*
  Each face rests at a slight angle and straightens under the cursor — the deck
  looks dealt rather than laid out, and picking one up squares it.
*/
.deck-face {
    transform: rotate(var(--rot));
    transition: transform 400ms cubic-bezier(0.22, 1, 0.36, 1);
}

.deck-slot:hover .deck-face {
    transform: rotate(0deg) scale(1.07) translateY(-2px);
}

.deck-rule {
    transition: width 350ms cubic-bezier(0.22, 1, 0.36, 1), background-color 350ms ease;
}

.deck-slot:hover .deck-rule {
    width: 3.5rem;
    background-color: var(--accent);
}

.deck-name {
    transition: color 250ms ease;
}

.deck-slot:hover .deck-name {
    color: var(--accent);
}

/* ── the floor ────────────────────────────────────────────── */

/*
  Postings sit at a slight angle, as if dropped on a table rather than laid out
  in a list. Hover squares one up and brings it forward.

  Trigger on the SLOT again: the post moves under hover, so hovering the post
  itself would leave the cursor behind and oscillate.
*/
.post-slot {
    perspective: 900px;
}

.post {
    transform: rotate(var(--rot));
    transition:
        transform 400ms cubic-bezier(0.22, 1, 0.36, 1),
        border-color 250ms ease,
        box-shadow 400ms ease;
}

.post-slot:hover {
    z-index: 5;
}

.post-slot:hover .post {
    transform: rotate(0deg) translateY(-4px) scale(1.03);
    border-color: color-mix(in oklab, var(--color-teal-light) 55%, transparent);
    box-shadow: 0 24px 45px -18px rgb(0 0 0 / 0.65);
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

    .hero-card {
        transition: none;
    }

    .title-shimmer {
        color: var(--color-gray-2x-light);
        background: none;
    }

    .reveal {
        transition: none;
    }

    .deck-slot {
        opacity: 1;
        transform: none;
        transition: none;
    }

    .deck-card,
    .deck-face,
    .deck-rule,
    .deck-name {
        transition: none;
    }

    .deck-face {
        transform: none;
    }

    .post {
        transform: none;
        transition: none;
    }
}
</style>