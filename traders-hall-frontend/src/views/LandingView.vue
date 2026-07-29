<script setup>
import SeatToken from '../Components/SeatToken.vue'
import { SEATS } from '../seats'
import IdeaByMesum from '../Components/IdeaByMesum.vue'
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'

const heroCards = [
    { icon: '/wheat.png', accent: 'cream-dark', bg: 'cream-light', rotate: -22, x: -170, y: 28, z: 1 },
    { icon: '/home.png', accent: 'purple-dark', bg: 'purple-light', rotate: -11, x: -88, y: 6, z: 2 },
    { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light', rotate: 0, x: 0, y: -8, z: 3 },
    { icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light', rotate: 11, x: 88, y: 6, z: 2 },
    { icon: '/investor.png', accent: 'blue-dark', bg: 'blue-light', rotate: 22, x: 170, y: 28, z: 1 },
]

const steps = [
    {
        n: '01',
        title: 'Get a roof',
        accent: 'text-purple-light',
        tint: 'purple-light',
        body: 'A house sleeps one. A mansion two, a tower three. Live in a room you own, or rent one off somebody who has a spare. Any room you are not using, you can rent out.',
        visual: 'rooms',
    },
    {
        n: '02',
        title: 'Keep eating',
        accent: 'text-cream-light',
        tint: 'cream-light',
        body: 'You get hungry every turn. Rice feeds you for two turns, wheat for five. Eating early does not stack. A meal just resets the counter. And the bank only has so much food.',
        visual: 'food',
    },
    {
        n: '03',
        title: 'Do not go broke',
        accent: 'text-teal-light',
        tint: 'teal-light',
        body: 'No score, no finish line. Owe the bank or your landlord and cannot pay? They take your points, then your cards. Last player left wins.',
        visual: 'last',
    },
]

const rooms = [
    { icon: '/home.png', pips: 1 },
    { icon: '/mansion.png', pips: 2 },
    { icon: '/building.png', pips: 3 },
]

const meals = [
    { icon: '/rice.png', turns: 2 },
    { icon: '/wheat.png', turns: 5 },
]

const WINNER = 2

const seats = SEATS.map((seat) => ({
    index: seat.index,
    name: seat.name,
    hex: seat.hex,
    out: seat.index !== WINNER,
}))

const deck = [
    { name: 'Point', icon: '/star.png', accent: 'teal-dark', bg: 'teal-light', rot: -5, role: 'Money. Everything costs points. The bank has a fixed pile and nobody can make more.' },
    { name: 'House', icon: '/home.png', accent: 'purple-dark', bg: 'purple-light', rot: 3, role: 'One room. Cheapest place to live, and the cheapest place to put a tenant.' },
    { name: 'Mansion', icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light', rot: -4, role: 'Two rooms. Live in one, rent out the other.' },
    { name: 'Tower', icon: '/building.png', accent: 'purple-dark', bg: 'purple-light', rot: 5, role: 'Three rooms. The best card to own, if you can afford it.' },
    { name: 'Rice', icon: '/rice.png', accent: 'cream-dark', bg: 'cream-light', rot: -3, role: 'Feeds you two turns. Cheap, and gone quickly.' },
    { name: 'Wheat', icon: '/wheat.png', accent: 'cream-dark', bg: 'cream-light', rot: 4, role: 'Feeds you five turns. Worth holding on to.' },
    { name: 'Invest', icon: '/investor.png', accent: 'blue-dark', bg: 'blue-light', rot: -5, role: 'Turns property into income. Coming soon.' },
]

const clocks = [
    {
        title: 'Hunger',
        accent: 'text-cream-light',
        dial: 'var(--color-cream-light)',
        left: 3,
        total: 5,
        unit: 'turns fed',
        body: 'Ticks down every turn. Eat and it resets to whatever you ate, never higher. Wheat gets you five turns, rice two.',
        zero: 'Nothing left to eat, and you are out.',
    },
    {
        title: 'Rent',
        accent: 'text-purple-light',
        dial: 'var(--color-purple-light)',
        left: 1,
        total: 3,
        unit: 'turns to pay',
        body: 'Do not own your room? You pay whoever does. The two of you agree the price and how often. The game sets neither.',
        zero: 'Your landlord takes what they are owed.',
    },
    {
        title: 'Credit',
        accent: 'text-teal-light',
        dial: 'var(--color-teal-light)',
        left: 4,
        total: 5,
        unit: 'rounds left',
        body: 'The bank lends up to five points and charges nothing for them. It only cares about the date.',
        zero: 'It takes your points, then your property.',
    },
]

const showcase = [
    {
        who: 'Mesum', seatIndex: 1, badge: 'Sell',
        badgeCls: 'border-rose-400/50 bg-rose-400/15 text-rose-400',
        arrow: 'text-rose-400',
        give: { icon: '/mansion.png', accent: 'purple-dark', bg: 'purple-light' },
        qty: '×1',
        get: { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light' },
        amount: '3',
        note: '',
        hands: [2, 3],
        rot: -2,
    },
    {
        who: 'Bilal', seatIndex: 2, badge: 'To let',
        badgeCls: 'border-teal-light/50 bg-teal-dark/30 text-teal-light',
        arrow: 'text-teal-light',
        give: { icon: '/building.png', accent: 'purple-dark', bg: 'purple-light' },
        qty: '',
        get: { icon: '/star.png', accent: 'teal-dark', bg: 'teal-light' },
        amount: '2',
        note: 'every 3 turns',
        hands: [1],
        rot: 1.5,
    },
    {
        who: 'You', seatIndex: 0, badge: 'Trade',
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

                        <div class="relative h-56 w-full max-w-2xl">
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
                    Two to four players and one bank. Buy property, trade food, charge your own rent.
                    Try not to go broke first.
                </p>
            </div>

            <div class="intro intro-4 flex flex-wrap items-center justify-center gap-4">
                <RouterLink :to="{ name: 'auth' }" class="cta group relative overflow-hidden rounded-xl border-2 border-teal-light bg-teal-light
                 px-8 py-3.5 font-bold text-gray-dark transition duration-300 ease-in-out
                 hover:brightness-130 hover:scale-101 active:scale-[0.99]
                 focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                    <span class="relative z-10">Start playing</span>
                                        <span class="sweep pointer-events-none absolute inset-0 z-0" aria-hidden="true"></span>
                </RouterLink>

                <a href="#how-it-works" class="rounded-xl border-2 border-gray-light px-8 py-3.5 font-bold text-gray-x-light
                 transition duration-200 ease-in-out hover:border-gray-x-light hover:text-gray-2x-light">How it
                    works</a>
            </div>

                        <div class="intro intro-5 grid grid-cols-3 items-center justify-center gap-px overflow-hidden
                  rounded-2xl border-2 border-gray-light bg-gray-light mt-12">
                <div v-for="stat in stats" :key="stat.label"
                    class="flex min-w-36 flex-col items-center gap-1 bg-gray-x-dark/90 px-8 py-5">
                    <span class="text-3xl font-bold text-gray-2x-light">{{ stat.value }}</span>
                    <span class="text-xs font-bold uppercase tracking-widest text-gray-x-light">{{ stat.label }}</span>
                </div>
            </div>
        </main>

        <section id="how-it-works" class="px-6 py-20">
            <div class="mx-auto max-w-5xl">
                <h2 data-reveal class="reveal text-center text-xs font-bold uppercase tracking-[0.4em] text-gray-x-light">
                    How it works
                </h2>
                <p data-reveal
                    class="reveal mx-auto mt-5 max-w-2xl text-center text-3xl font-bold leading-tight tracking-wide text-gray-2x-light sm:text-4xl">
                    Three things to worry about
                </p>
                <p data-reveal class="reveal mx-auto mt-4 max-w-xl text-center text-lg leading-relaxed text-gray-x-light">
                    On your turn you can buy, sell, eat, borrow, or rent out a room. Do as much as you
                    can afford. Then you pass, and your clocks tick.
                </p>

                                <div class="relative mt-16 flex flex-col gap-16 sm:gap-20">
                    <span aria-hidden="true"
                        class="spine pointer-events-none absolute top-0 bottom-0 left-[1.4rem] w-px lg:left-1/2"></span>

                    <div v-for="(step, i) in steps" :key="step.n" data-reveal class="step-slot relative"
                        :style="{ '--delay': `${i * 120}ms`, '--tint': `var(--color-${step.tint})` }">

                        <div class="grid items-center gap-8 lg:grid-cols-[1fr_auto_1fr] lg:gap-10">

                                                        <div class="order-2 lg:order-none" :class="i % 2 === 0 ? 'lg:col-start-1' : 'lg:col-start-3'">
                                <div class="vignette flex min-h-[11rem] items-center justify-center gap-4 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/70 px-6 py-8">

                                                                        <template v-if="step.visual === 'rooms'">
                                        <div v-for="(r, j) in rooms" :key="j" class="flex flex-col items-center gap-3"
                                            :style="{ '--i': j }">
                                            <span class="tilt flex h-[4.5rem] w-13 items-center justify-center rounded-xl border-4 p-3 shadow-lg shadow-black/40"
                                                style="background-color: var(--color-purple-light); border-color: var(--color-purple-dark)">
                                                <span class="h-full w-full" :style="{
                                                    backgroundColor: 'var(--color-purple-dark)',
                                                    mask: `url(${r.icon}) no-repeat center / contain`,
                                                    '-webkit-mask': `url(${r.icon}) no-repeat center / contain`,
                                                }"></span>
                                            </span>
                                            <span class="flex flex-col items-center gap-1.5">
                                                <span class="flex gap-1.5">
                                                    <span v-for="p in r.pips" :key="p"
                                                        class="pip h-2.5 w-2.5 rounded-full border-2 border-purple-light"
                                                        :class="p === 1 ? 'bg-purple-light' : 'bg-transparent'"
                                                        :style="{ '--j': p }"></span>
                                                </span>
                                                <span class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
                                                    {{ r.pips === 1 ? '1 bed' : r.pips + ' beds' }}
                                                </span>
                                            </span>
                                        </div>
                                    </template>

                                                                        <template v-else-if="step.visual === 'food'">
                                        <div v-for="(m, j) in meals" :key="j" class="flex flex-col items-center gap-3"
                                            :style="{ '--i': j }">
                                            <span class="tilt flex h-[4.5rem] w-13 items-center justify-center rounded-xl border-4 p-3 shadow-lg shadow-black/40"
                                                style="background-color: var(--color-cream-light); border-color: var(--color-cream-dark)">
                                                <span class="h-full w-full" :style="{
                                                    backgroundColor: 'var(--color-cream-dark)',
                                                    mask: `url(${m.icon}) no-repeat center / contain`,
                                                    '-webkit-mask': `url(${m.icon}) no-repeat center / contain`,
                                                }"></span>
                                            </span>
                                            <span class="flex flex-col items-center gap-1.5">
                                                <span class="flex gap-1">
                                                    <span v-for="t in m.turns" :key="t"
                                                        class="pip h-2.5 w-1.5 rounded-full bg-cream-light"
                                                        :style="{ '--j': t }"></span>
                                                </span>
                                                <span class="text-[10px] font-bold uppercase tracking-widest text-gray-light">
                                                    {{ m.turns }} turns
                                                </span>
                                            </span>
                                        </div>
                                    </template>

                                                                        <template v-else>
                                        <div class="flex items-end gap-4">
                                            <span v-for="(seat, j) in seats" :key="seat.name"
                                                class="seat flex flex-col items-center gap-2.5"
                                                :class="seat.out ? 'is-out' : 'is-in'"
                                                :style="{ '--seat': seat.hex, '--j': j }">
                                                <span class="seat-mark">
                                                    <SeatToken :seat-index="seat.index" size="lg" />
                                                </span>
                                                <span class="seat-label">{{ seat.out ? 'Out' : 'Wins' }}</span>
                                            </span>
                                        </div>
                                    </template>
                                </div>
                            </div>

                                                        <div class="order-1 flex items-center gap-4 lg:order-none lg:col-start-2 lg:row-start-1 lg:flex-col lg:gap-0">
                                <span
                                    class="node relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border-2 border-gray-light bg-gray-dark text-xs font-bold tracking-widest text-gray-x-light">
                                    {{ step.n }}
                                </span>
                                <h3 class="text-2xl font-bold tracking-wide lg:hidden" :class="step.accent">
                                    {{ step.title }}
                                </h3>
                            </div>

                                                        <div class="order-3 flex flex-col gap-3 lg:order-none"
                                :class="i % 2 === 0 ? 'lg:col-start-3' : 'lg:col-start-1 lg:row-start-1 lg:text-right'">
                                <h3 class="hidden text-3xl font-bold tracking-wide lg:block" :class="step.accent">
                                    {{ step.title }}
                                </h3>
                                <p class="text-base leading-relaxed text-gray-x-light">{{ step.body }}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section id="deck" class="border-t-1 border-gray-light/40 px-6 py-16">
            <div class="mx-auto max-w-7xl">
                <h2 data-reveal class="reveal text-center text-xs font-bold uppercase tracking-[0.4em] text-gray-x-light">
                    The deck
                </h2>
                <p data-reveal class="reveal mx-auto mt-4 max-w-2xl text-center text-lg leading-relaxed text-gray-x-light">
                    Seven cards. That is the whole game.
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
                <h2 data-reveal class="reveal text-center text-xs font-bold uppercase tracking-[0.4em] text-gray-x-light">
                    Three clocks
                </h2>
                <p data-reveal class="reveal mx-auto mt-4 max-w-2xl text-center text-lg leading-relaxed text-gray-x-light">
                    Three counters run at once, and every one of them takes something off you when it
                    reaches zero. Owning the most does not mean lasting the longest.
                </p>

                <div class="mt-12 grid gap-5 sm:grid-cols-3">
                    <div v-for="(clock, i) in clocks" :key="clock.title" data-reveal class="clock-slot"
                        :style="{ '--delay': `${i * 110}ms`, '--dial': clock.dial, '--left': clock.left, '--total': clock.total }">
                        <div class="clock-card flex h-full flex-col items-center gap-4 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark/80 px-6 pb-6 pt-8 text-center">

                            <div class="relative">
                                <svg viewBox="0 0 100 100" class="dial h-28 w-28" aria-hidden="true">
                                    <circle class="dial-track" cx="50" cy="50" r="42" />
                                    <circle class="dial-fill" cx="50" cy="50" r="42" />
                                </svg>

                                <span class="absolute inset-0 flex flex-col items-center justify-center">
                                    <span class="dial-num text-3xl font-bold tabular-nums">{{ clock.left }}</span>
                                    <span class="text-[9px] font-bold uppercase tracking-widest text-gray-light">
                                        of {{ clock.total }}
                                    </span>
                                </span>
                            </div>

                            <span class="text-[10px] font-bold uppercase tracking-[0.25em] text-gray-light">
                                {{ clock.unit }}
                            </span>

                            <h3 class="text-xl font-bold tracking-wide" :class="clock.accent">{{ clock.title }}</h3>

                            <p class="text-sm leading-relaxed text-gray-x-light">{{ clock.body }}</p>

                            <p class="zero mt-auto flex w-full items-start gap-2 rounded-xl border-2 px-3 py-2 text-left text-xs leading-relaxed">
                                <div class=" h-full flex justify-center items-center mr-2">
                                    <span class="zero-tag shrink-0 font-bold uppercase tracking-widest">At zero</span>
                                </div>
                                <span class="text-gray-x-light">{{ clock.zero }}</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <section id="market" class="border-t-1 border-gray-light/40 px-6 py-16">
            <div class="mx-auto grid max-w-5xl items-center gap-12 lg:grid-cols-2">
                <div data-reveal class="reveal flex flex-col gap-5">
                    <h2 class="text-xs font-bold uppercase tracking-[0.4em] text-gray-x-light">The floor</h2>
                    <h3 class="text-4xl font-bold leading-tight tracking-wide text-gray-2x-light">
                        You pick who you<br class="hidden sm:block" /> deal with
                    </h3>
                    <p class="text-lg leading-relaxed text-gray-x-light">
                        Put something up and anyone can go for it. Usually a few people do. You see all
                        of them and you choose.
                    </p>
                    <p class="text-lg leading-relaxed text-gray-x-light">
                        Cards for points. Cards for cards. A spare room at your price. Or if you have
                        nowhere to live, say what you will pay and wait for someone to bite.
                    </p>
                </div>

                <div data-reveal class="reveal flex flex-col gap-3">
                    <div v-for="(o, i) in showcase" :key="o.who" class="post-slot" :style="{ '--rot': `${o.rot}deg` }">
                        <article class="post flex flex-col gap-3 rounded-[1.25rem] border-2 border-gray-light bg-gray-x-dark/90 p-4 shadow-xl shadow-black/30">

                            <div class="flex items-center gap-2">
                                <SeatToken :seat-index="o.seatIndex" size="sm" />
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
                                <SeatToken v-for="h in o.hands" :key="h" :seat-index="h" size="xs" />
                            </div>
                        </article>
                    </div>
                </div>
            </div>
        </section>

        <section class="px-6 pb-24 pt-6">
            <div data-reveal class="reveal mx-auto max-w-4xl flex justify-center">
                <div class="table relative overflow-hidden rounded-[2rem] border-2 border-teal-light/40 px-8 py-16 text-center sm:px-32">

                    <span aria-hidden="true" class="table-light pointer-events-none absolute inset-0"></span>
                    <span aria-hidden="true" class="table-felt pointer-events-none absolute inset-0"></span>

                    <div class="relative z-10 flex flex-col items-center gap-7">

                        <div class="flex items-end gap-5 sm:gap-7">
                            <span v-for="(seat, i) in seats" :key="seat.name"
                                class="chair flex flex-col items-center gap-2.5"
                                :style="{ '--seat': seat.hex, '--j': i }">
                                <SeatToken class="chair-filled-mark" :seat-index="seat.index" />
                                <span class="chair-label">{{ seat.name }}</span>
                            </span>

                            <span class="chair is-empty flex flex-col items-center gap-2.5">
                                <SeatToken class="chair-empty-mark" :seat-index="-1" />
                                <span class="chair-label">You</span>
                            </span>
                        </div>

                        <h2 class="text-4xl font-bold tracking-wide text-gray-2x-light sm:text-5xl">
                            The hall is open
                        </h2>

                        <p class="max-w-md text-lg leading-relaxed text-gray-x-light">
                            Make an account, start a table, and send the code to three friends.
                        </p>

                        <RouterLink :to="{ name: 'auth' }"
                            class="cta group relative mt-1 overflow-hidden rounded-xl border-2 border-teal-light bg-teal-light px-8 py-3.5 font-bold text-gray-dark transition duration-300 ease-in-out hover:brightness-130 hover:scale-101 active:scale-[0.99] focus-visible:outline-2 focus-visible:outline-teal-light focus-visible:outline-offset-2">
                            <span class="relative z-10">Take the seat</span>
                            <span class="sweep pointer-events-none absolute inset-0 z-0" aria-hidden="true"></span>
                        </RouterLink>
                    </div>
                </div>
            </div>
        </section>

    </div>
</template>

<style scoped>

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

.deck-slot:hover .deck-card {
    transform: translateY(-8px);
    border-color: color-mix(in oklab, var(--accent) 65%, transparent);
    box-shadow: 0 28px 55px -20px color-mix(in oklab, var(--accent) 65%, transparent);
}

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

.pip {
    opacity: 0;
    transform: scale(0.4);
}

.step-slot.revealed .pip {
    animation: pip-in 320ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    animation-delay: calc(var(--delay, 0ms) + 260ms + var(--j, 0) * 70ms);
}

@keyframes pip-in {
    to {
        opacity: 1;
        transform: scale(1);
    }
}

.table {
    background-color: color-mix(in oklab, var(--color-teal-dark) 12%, var(--color-gray-x-dark));
}

.table-light {
    background: radial-gradient(
        75% 55% at 50% 28%,
        color-mix(in oklab, var(--color-teal-light) 16%, transparent),
        transparent 70%
    );
}

.table-felt {
    background-image: repeating-conic-gradient(
        color-mix(in oklab, var(--color-teal-light) 7%, transparent) 0% 25%,
        transparent 0% 50%
    );
    background-size: 14px 14px;
    opacity: 0.5;
    mask-image: radial-gradient(80% 70% at 50% 45%, #000, transparent 75%);
}

.chair-filled-mark {
    animation: chair-breathe 4s ease-in-out infinite alternate;
    animation-delay: calc(var(--j, 0) * 600ms);
}

.chair-label {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--color-gray-light);
}

.chair-empty-mark {
    border-style: dashed;
    border-color: var(--color-teal-light);
    background-color: transparent;
    animation: chair-wait 2.4s ease-in-out infinite;
}

.is-empty .chair-label {
    color: var(--color-teal-light);
}

@keyframes chair-breathe {
    from { transform: translateY(0); opacity: 0.8; }
    to   { transform: translateY(-3px); opacity: 1; }
}

@keyframes chair-wait {
    0%, 100% { transform: translateY(0); box-shadow: 0 0 0 0 color-mix(in oklab, var(--color-teal-light) 40%, transparent); }
    50%      { transform: translateY(-4px); box-shadow: 0 0 0 8px color-mix(in oklab, var(--color-teal-light) 0%, transparent); }
}

.spine {
    background: linear-gradient(
        to bottom,
        transparent,
        color-mix(in oklab, var(--color-gray-x-light) 30%, transparent)12%,
        color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) 88%,
        transparent
    );
}

.vignette {
    position: relative;
    overflow: hidden;
    transition: border-color 350ms ease, box-shadow 350ms ease;
}

.vignette::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(
        120% 90% at 15% 110%,
        color-mix(in oklab, var(--tint) 16%, transparent),
        transparent 62%
    );
    pointer-events: none;
}

.step-slot:hover .vignette {
    border-color: color-mix(in oklab, var(--tint) 45%, transparent);
    box-shadow: 0 24px 50px -24px color-mix(in oklab, var(--tint) 45%, transparent);
}

.tilt {
    transform: rotate(calc((var(--i, 0) - 1) * 4deg)) translateY(calc(var(--i, 0) * -2px));
    transition: transform 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.step-slot:hover .tilt {
    transform: rotate(0deg) translateY(-4px) scale(1.04);
}

.seat-label {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    transition: color 400ms ease;
}

.seat-mark {
    position: relative;
    display: inline-flex;
    transition: filter 400ms ease, opacity 400ms ease, transform 400ms cubic-bezier(0.22, 1, 0.36, 1);
}

.is-out .seat-mark {
    filter: grayscale(1);
    opacity: 0.35;
    transform: translateY(4px) scale(0.9);
}

.is-out .seat-mark::after {
    content: '';
    position: absolute;
    inset: -2px;
    border-radius: inherit;
    background: linear-gradient(
        to bottom right,
        transparent calc(50% - 1.5px),
        var(--color-gray-x-light) calc(50% - 1.5px),
        var(--color-gray-x-light) calc(50% + 1.5px),
        transparent calc(50% + 1.5px)
    );
    opacity: 0.55;
}

.is-out .seat-label {
    color: var(--color-gray-light);
}

.is-in .seat-mark :deep(div) {
    border-radius: 0.85rem;
    animation: seat-pulse 2.6s ease-in-out infinite;
}

.is-in .seat-label {
    color: var(--seat);
}

@keyframes seat-pulse {
    0%, 100% {
        box-shadow: 0 0 0 0 color-mix(in oklab, var(--seat) 45%, transparent);
    }
    50% {
        box-shadow: 0 0 0 9px color-mix(in oklab, var(--seat) 0%, transparent);
    }
}

.clock-slot {
    opacity: 0;
    transform: translateY(24px);
    transition:
        opacity 500ms ease,
        transform 500ms cubic-bezier(0.22, 1, 0.36, 1);
    transition-delay: var(--delay, 0ms);
}

.clock-slot:not(.revealed) {
    will-change: transform, opacity;
}

.clock-slot.revealed {
    opacity: 1;
    transform: translateY(0);
    will-change: auto;
}

.clock-card {
    transition: transform 300ms cubic-bezier(0.22, 1, 0.36, 1), border-color 250ms ease;
}

.clock-slot:hover .clock-card {
    border-color: color-mix(in oklab, var(--dial) 55%, transparent);
}

.dial {
    transform: rotate(-90deg);
    overflow: visible;
}

.dial-track,
.dial-fill {
    fill: none;
    stroke-width: 7;
    stroke-linecap: round;
}

.dial-track {
    stroke: color-mix(in oklab, var(--color-gray-light) 55%, transparent);
}

.dial-fill {
    stroke: var(--dial);
    stroke-dasharray: 263.9;
        stroke-dashoffset: 0;
    filter: drop-shadow(0 0 6px color-mix(in oklab, var(--dial) 45%, transparent));
}

.clock-slot.revealed .dial-fill {
    animation: unwind 1100ms cubic-bezier(0.34, 1, 0.42, 1) forwards;
    animation-delay: calc(var(--delay, 0ms) + 220ms);
}

@keyframes unwind {
    from {
        stroke-dashoffset: 0;
    }
    to {
        stroke-dashoffset: calc(263.9px * (1 - var(--left) / var(--total)));
    }
}

.dial-num {
    color: var(--dial);
}

.zero {
    border-color: color-mix(in oklab, var(--dial) 30%, transparent);
    background-color: color-mix(in oklab, var(--dial) 8%, transparent);
}

.zero-tag {
    color: var(--dial);
    font-size: 0.6rem;
}

.clock-slot:hover .clock-card {
    transform: translateY(-4px);
}

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

    .clock-slot {
        opacity: 1;
        transform: none;
        transition: none;
    }

    .clock-card {
        transition: none;
    }

        .clock-slot.revealed .dial-fill {
        animation: none;
        stroke-dashoffset: calc(263.9px * (1 - var(--left) / var(--total)));
    }

    .pip {
        opacity: 1;
        transform: none;
        animation: none;
    }

    .is-in .seat-mark :deep(div) {
        animation: none;
        box-shadow: 0 0 0 4px color-mix(in oklab, var(--seat) 35%, transparent);
    }

    .seat-mark {
        transition: none;
    }

    .tilt {
        transform: none;
        transition: none;
    }

    .chair-filled-mark,
    .chair-empty-mark {
        animation: none;
    }
}
</style>