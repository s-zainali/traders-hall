<script setup>
defineProps({
    // `zoom` (not `scale`) shrinks the layout box too, so the compact variant
    // takes proportionally less space instead of leaving a full-size gap.
    compact: { type: Boolean, default: false },
    semiCompact : {type: Boolean, default: false}
})

</script>

<template>
    <footer class="relative select-none group bg-transparent" :style="compact ? { zoom: 0.7 } : semiCompact? {zoom:0.8} :{}">
        <div class="flex flex-col items-center gap-2">
            <span class="text-[10px] font-black uppercase tracking-[0.4em] text-white/25">
                Concept by
            </span>

            <div class="flex items-center gap-3">
                <span class="h-px w-14 bg-gradient-to-l to-transparent from-white/15"></span>
                <span class="w-1 h-1 rotate-45 bg-white/20"></span>

                <span
                    class="mesum-wordmark tracking-wide px-1 transition-transform duration-300 group-hover:scale-120 cursor-pointer" :class="compact? 'text-3xl': 'text-3xl'">
                    Mesum
                </span>

                <span class="w-1 h-1 rotate-45 bg-white/20"></span>
                <span class="h-px w-14 bg-gradient-to-l from-transparent to-white/15"></span>
            </div>
        </div>

        <!-- soft ambient glow behind the signature, revealed on hover -->
        <div
            class="pointer-events-none absolute left-1/2 bottom-4 -translate-x-1/2 w-32 h-8 rounded-full bg-pink-500/15 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-700">
        </div>
    </footer>
</template>

<style scoped>
@font-face {
    font-family: 'Alex Brush';
    src: url('../assets/fonts/AlexBrush-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
    font-display: swap;
}

.mesum-wordmark {
    font-family: 'Alex Brush', cursive, sans-serif;
    background: linear-gradient(135deg, #f472b6 0%, #c084fc 50%, #818cf8 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    filter: drop-shadow(0 2px 6px rgba(192, 132, 252, 0.25));
}
</style>