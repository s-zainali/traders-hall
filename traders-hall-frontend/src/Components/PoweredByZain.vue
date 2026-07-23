<script setup>
defineProps({
    // `zoom` (not `scale`) shrinks the layout box too, so the compact variant
    // takes proportionally less space instead of leaving a full-size gap.
    compact: { type: Boolean, default: false },
})

const year = new Date().getFullYear()
</script>

<template>
    <footer
        class="relative select-none group bg-transparent"
        :class="compact ? 'mt-0 pb-0' : 'mt-14 pb-6'"
        :style="compact ? { zoom: 0.5 } : {}"
    >
        <!-- hairline divider -->
        <div
            v-if="!compact"
            class="mx-auto max-w-sm h-px bg-gradient-to-r from-transparent via-white/15 to-transparent mb-6"
        ></div>

        <div class="flex flex-col items-center gap-2">
            <span class="text-[8px] font-black uppercase tracking-[0.4em] text-white/25">
                Powered by
            </span>

            <div class="flex items-center gap-3">
                <span class="h-px w-14 bg-gradient-to-r from-transparent to-white/15"></span>
                <span class="w-1 h-1 rotate-45 bg-white/20"></span>

                <a
                    href="https://www.linkedin.com/in/s-zain-ali/"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="zain-wordmark text-xl font-black uppercase tracking-[0.3em] pl-[0.3em] transition-transform duration-300 group-hover:scale-105"
                >
                    Zain
                </a>

                <span class="w-1 h-1 rotate-45 bg-white/20"></span>
                <span class="h-px w-14 bg-gradient-to-l from-transparent to-white/15"></span>
            </div>

            <span v-if="!compact" class="text-[9px] font-mono text-white/20 tracking-wider">
                Zain Software Solutions · {{ year }}
            </span>
        </div>

        <!-- soft ambient glow behind the wordmark, revealed on hover -->
        <div
            v-if="!compact"
            class="pointer-events-none absolute left-1/2 bottom-10 -translate-x-1/2 w-40 h-10 rounded-full bg-indigo-500/20 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"
        ></div>
    </footer>
</template>

<style scoped>
.zain-wordmark {
    background: linear-gradient(110deg,
            #818cf8 0%,
            #34d399 30%,
            #38bdf8 55%,
            #c084fc 75%,
            #818cf8 100%);
    background-size: 220% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: zain-shimmer 5s linear alternate infinite;
}

.group:hover .zain-wordmark {
    animation-duration: 2.5s;
}

@keyframes zain-shimmer {
    0% {
        background-position: 0% 50%;
    }

    100% {
        background-position: -220% 50%;
    }
}

@media (prefers-reduced-motion: reduce) {
    .zain-wordmark {
        animation: none;
    }
}
</style>