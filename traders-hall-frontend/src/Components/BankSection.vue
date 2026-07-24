<script setup>
import { ref, computed, watch } from 'vue';
import Card from './Card.vue';
import BankerModal from './Modals/BankerModal.vue';
import BankerCard from './Cards/BankerCard.vue';
import CardDeck from './CardDeck.vue';
import TransactionModal from './Modals/TransactionModal.vue';

const props = defineProps({
    buyingActive: { type: Boolean, default: false },
    // { cardType: quantity } straight from the projection
    pools: { type: Object, default: () => ({}) },
    // an action is in flight; the modal locks so a double-click cannot fire twice
    busy: { type: Boolean, default: false },
    // the buyer's balance, so the modal can cap the stepper at what they can afford
    points: { type: Number, default: 0 },
})
const emit = defineEmits(['cancel', 'confirm'])

/*
  Collapse state.

  Two independent reasons to be open, tracked separately on purpose: buying
  forces it open, and the player can pin it open themselves. Merging them into
  one boolean means cancelling a purchase would slam the panel shut on someone
  who had deliberately opened it to look at stock.
*/
const pinnedOpen = ref(false)
const expanded = computed(() => props.buyingActive || pinnedOpen.value)

// Opening to buy should not silently pin it — the panel closes again when the
// purchase ends, which is what makes the collapse worth having.
watch(() => props.buyingActive, (active) => {
    if (!active) pinnedOpen.value = false
})

const ORDER = ['house', 'mansion', 'tower', 'rice', 'wheat', 'invest']

/*
  Buyable stock in a fixed order. Object key order follows whatever the server
  serialised, so without this the grid would reshuffle between polls.
*/
const cardStock = computed(() =>
    ORDER.filter((type) => (props.pools[type] ?? 0) > 0).map((type) => ({
        type,
        count: props.pools[type],
    }))
)

// The rail lists every type including sold-out ones, greyed: "the bank has no
// houses left" is information, and a disappearing row is not.
const railStock = computed(() =>
    ORDER.map((type) => ({ type, count: props.pools[type] ?? 0 }))
)

const pointStock = computed(() => props.pools.point ?? 0)

const buyingType = ref('')
const activeModal = ref('')

function openBuy(type) {
    buyingType.value = type
    activeModal.value = 'buy'
}

function onConfirm(payload) {
    emit('confirm', { type: payload.cardType, quantity: payload.quantity })
    activeModal.value = ''
}

/*
  Closing the buy modal MUST also emit `cancel`.

  Clearing only the local activeModal left the parent's activeAction at 'buy',
  so buyingActive stayed true and this panel stayed EXPANDED — and an expanded
  panel is `absolute top-0 bottom-0 right-full` with live pointer events, i.e.
  a ~450px column covering the full game height. At xl the player's action
  buttons sit at the right of the bottom row, directly underneath it, so they
  silently stopped receiving clicks. Below xl the panel is far from them, which
  is why the narrow layout seemed fine.
*/
function closeBuy() {
    activeModal.value = ''
    emit('cancel')
}

</script>

<template>
    <div class="relative flex shrink-0 items-stretch">

        <!--
            Slide and fade, NOT the grid-column width trick used elsewhere in
            this app. `1fr` resolves against a definite container width, and an
            absolutely positioned box with only `right` set is shrink-to-fit —
            its width depends on its content, which would depend on the
            fraction. That circularity collapses the panel to nothing.

            Overlaying removes the need for a width animation anyway: the panel
            keeps its natural size and simply moves into place.

            w-max is REQUIRED, not decorative. With `right` set and `left: auto`
            the width is shrink-to-fit, and shrink-to-fit clamps to the space
            available inside the containing block — which is zero here, because
            the element's right edge sits exactly at that block's left edge. An
            explicit max-content width is definite, so the clamp never applies.
        -->
        <!--
            aria-hidden and inert when collapsed, not just transparent: an
            invisible element still receives clicks, and this one spans the full
            game height. pointer-events-none covers the mouse; `inert` also
            takes it out of the tab order and off the accessibility tree, so a
            keyboard user cannot land inside a panel nobody can see.
        -->
        <div class="absolute top-0 right-full bottom-0 z-150 mr-2 w-max transition-all duration-300 ease-out"
            :inert="!expanded" :aria-hidden="!expanded"
            :class="expanded
                ? 'translate-x-0 opacity-100'
                : 'pointer-events-none translate-x-6 opacity-0'">
            <div>
                <!--
                    flex-col with the cards well as flex-1 min-h-0, rather than
                    justify-between: a flex item defaults to min-height:auto and
                    refuses to shrink below its content, so the grid would push
                    the panel taller instead of scrolling inside it.
                -->
                <!--
                    relative + max-w so the modals below have something real to
                    cover. They used to sit on the section root, but that root is
                    now just the 4rem rail — the panel is absolute — so an
                    inset-0 modal was rendering 64px wide.

                    max-w keeps the panel inside the viewport however many card
                    types exist; the cards well scrolls rather than overflowing.
                -->
                <div
                    class="relative flex h-full max-h-full w-max min-h-0 max-w-[calc(100vw-7rem)] flex-col rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark p-4 shadow-2xl shadow-black/60 overflow-hidden">

                    <TransactionModal v-if="activeModal === 'buy'" :transaction-type="'buy'" :card-type="buyingType"
                        :available="pools[buyingType] ?? 1" :points="points" :busy="busy" @confirm="onConfirm"
                        @cancel="closeBuy" />
                    <BankerModal v-if="activeModal === 'bankerModal'" @close-modal="activeModal = ''" />

                    <div class="flex shrink-0 justify-between gap-6">
                        <div>
                            <h1 class="pb-4 text-center text-3xl font-bold tracking-wide text-gray-2x-light">Bank</h1>
                            <div class="ml-6 flex justify-between">
                                <CardDeck v-if="pointStock > 0" :key="`point-${pointStock}`">
                                    <Card v-for="n in pointStock" :key="n" :card-type="'point'" />
                                </CardDeck>
                                <span v-else class="py-8 text-sm font-bold text-gray-light">Out of points</span>
                            </div>
                        </div>
                        <BankerCard @activate-modal="activeModal = $event" />
                    </div>

                    <div class="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1rem] border-1 p-4 outline-teal-light transition duration-200 ease-in-out"
                        :class="buyingActive ? 'border-teal-light outline-4 -outline-offset-4 bg-gray-light/30' : 'border-gray-light outline-0'">
                        <button v-if="buyingActive" @click="emit('cancel')"
                            class="absolute top-0 right-0 z-50 flex items-center justify-center p-4 leading-none text-gray-x-light transition duration-200 ease-in-out hover:cursor-pointer hover:text-rose-400">🗙</button>

                        <!-- the heading stays put; only the grid below scrolls -->
                        <h1 class="shrink-0 pb-4 text-center text-2xl font-bold tracking-wide text-gray-2x-light">
                            Cards {{ buyingActive? '' : '🛈' }}</h1>

                        <!--
                            grid-cols-3 compiles to repeat(3, minmax(0, 1fr)),
                            and that 0 minimum is what let the columns squeeze
                            the decks when the panel opened on a narrower screen.
                            max-content columns never compress: the cards stay
                            the size they are at xl and the well scrolls instead.

                            auto-rows-min stops rows stretching to fill the track
                            when there are fewer than three, which would leave
                            the decks floating in the middle of a tall cell.
                        -->
                        <div v-if="cardStock.length"
                            class="scroll-slim grid min-h-0 flex-1 auto-rows-min grid-cols-[repeat(3,max-content)] gap-2 overflow-auto pr-2">
                            <CardDeck v-for="stock in cardStock" :key="`${stock.type}-${stock.count}`">
                                <Card v-for="n in stock.count" :key="`${stock.type}-${n}`" :card-type="stock.type"
                                    :buying="buyingActive" @buy="openBuy(stock.type)" />
                            </CardDeck>
                        </div>
                        <p v-else class="py-8 text-center text-sm text-gray-light">The bank is empty</p>
                    </div>
                </div>
            </div>
        </div>

        <!--
            The rail. Always mounted, so the stock counts stay readable while
            collapsed — which is the point of collapsing rather than hiding.
        -->
        <div
            class="relative z-50 flex w-16 shrink-0 flex-col items-center gap-3 rounded-[1.5rem] border-2 border-gray-light bg-gray-x-dark py-4">

            <button type="button"
                :aria-label="expanded ? 'Collapse the bank' : 'Expand the bank'"
                :title="buyingActive ? 'Open while buying' : expanded ? 'Collapse' : 'Expand'"
                :disabled="buyingActive" @click="pinnedOpen = !pinnedOpen"
                class="flex h-9 w-9 items-center justify-center rounded-lg border-2 border-gray-light text-lg font-bold text-gray-x-light transition duration-200 ease-in-out"
                :class="buyingActive
                    ? 'opacity-40 cursor-not-allowed'
                    : 'cursor-pointer hover:border-teal-light hover:text-teal-light'">
                <span class="transition-transform duration-300" :class="expanded ? '' : 'rotate-180'">›</span>
            </button>

            <!-- writing-mode turns the label upright without a transform, so it
                 still occupies a real vertical box instead of overlapping -->
            <span class="bank-label text-xs font-bold uppercase tracking-[0.3em] text-gray-x-light">Bank</span>

            <div class="flex flex-col items-center gap-1">
                <Card :card-type="'point'" :large="false" :selected="true" />
                <span class="text-xs font-bold tabular-nums text-teal-light">{{ pointStock }}</span>
            </div>

            <div class="h-px w-8 bg-gray-light"></div>

            <div class="flex flex-col items-center gap-2">
                <div v-for="stock in railStock" :key="stock.type"
                    class="flex flex-col items-center gap-0.5 transition duration-200"
                    :class="stock.count === 0 ? 'opacity-30' : ''"
                    :title="`${stock.count} ${stock.type}`">
                    <Card :card-type="stock.type" :large="false" :selected="stock.count > 0" />
                    <span class="text-xs font-bold tabular-nums"
                        :class="stock.count === 0 ? 'text-gray-light' : 'text-gray-2x-light'">
                        {{ stock.count }}
                    </span>
                </div>
            </div>
        </div>

    </div>
</template>

<style scoped>
.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    width: 10px;
}

.scroll-slim::-webkit-scrollbar-track {
    background: transparent;
}

/* content-box clip plus a transparent border is what makes the thumb read as
   inset and pill-shaped: the border reserves padding the background skips */
.scroll-slim::-webkit-scrollbar-thumb {
    background: color-mix(in oklab, var(--color-gray-x-light) 28%, transparent);
    background-clip: content-box;
    border: 3px solid transparent;
    border-radius: 999px;
}

.scroll-slim::-webkit-scrollbar-thumb:hover {
    background: color-mix(in oklab, var(--color-teal-light) 55%, transparent);
    background-clip: content-box;
}

.bank-label {
    writing-mode: vertical-rl;
    text-orientation: mixed;
}

@media (prefers-reduced-motion: reduce) {
    .grid,
    .transition-transform {
        transition: none;
    }
}
</style>