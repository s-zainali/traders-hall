<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import BankSection from '../Components/BankSection.vue'
import Header from '../Components/Header.vue'
import PlayerCardHolder from '../Components/PlayerCardHolder.vue'
import LoadingScreen from '../Components/LoadingScreen.vue'
import EventLog from '../Components/EventLog.vue'
import OffersPanel from '../Components/OffersPanel.vue'
import SeizureModal from '../Components/Modals/SeizureModal.vue'
import OutcomeModal from '../Components/Modals/OutcomeModal.vue'
import DiceSection from '../Components/DiceSection.vue'
import { useCardTypesStore } from '../stores/cardTypes'
import { useGamesStore } from '../stores/games'

const props = defineProps({ code: { type: String, required: true } })

const router = useRouter()
const cardTypes = useCardTypesStore()
const games = useGamesStore()

const { loaded, error: cardError } = storeToRefs(cardTypes)
const {
    state, hasLoadedState, stateError, acting, actionError, events, sendingChat, offers,
} = storeToRefs(games)

async function load() {
    await Promise.all([
        cardTypes.fetchAll(),
        games.fetchState(props.code),
        games.fetchEvents(props.code),
        games.fetchOffers(props.code),
    ])
}

const POLL_MS = 2000
let pollTimer = null
let inFlight = false

async function poll() {
    if (inFlight || acting.value || document.hidden) return
    inFlight = true
    try {
        /*
          Events first, then state.

          The other order made observers a poll behind on anything that changed
          another player's row: state was read, THEN the event that explained it
          arrived, so the dice row only caught up on the following cycle — up to
          two seconds later, and longer if the observer was mid-action, because
          poll() skips entirely while acting.

          Reading events first means a new event and the state that produced it
          land in the same tick.
        */
        await games.fetchEvents(props.code)
        await games.fetchState(props.code, { silent: true })
        await games.fetchOffers(props.code)
    } finally {
        inFlight = false
    }
}

const startPolling = () => {
    stopPolling()
    pollTimer = setInterval(poll, POLL_MS)
}

const stopPolling = () => {
    clearInterval(pollTimer)
    pollTimer = null
}

function onVisibility() {
    if (document.hidden) stopPolling()
    else {
        poll()
        startPolling()
    }
}

onMounted(() => {
    load()
    startPolling()
    document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
    stopPolling()
    document.removeEventListener('visibilitychange', onVisibility)
    games.clearState()
})

const me = computed(() => state.value?.you ?? null)
const isMyTurn = computed(() => me.value?.isMyTurn ?? false)

const seatByPlayer = computed(() =>
    Object.fromEntries((state.value?.players ?? []).map((p) => [p.id, p.seatIndex]))
)
const nameByPlayer = computed(() =>
    Object.fromEntries((state.value?.players ?? []).map((p) => [p.id, p.displayName]))
)

const seats = computed(() => {
    const s = state.value
    if (!s) return []
    return Array.from({ length: s.game.maxPlayers }, (_, i) => {
        const player = s.players.find((p) => p.seatIndex === i) ?? null
        return {
            seatIndex: i,
            seatStatus: player?.status ?? 'empty',
            name: player?.displayName ?? 'Empty seat',
            isMe: player !== null && player.seatIndex === me.value?.seatIndex,
            isTurn: player !== null && player.id === s.game.currentPlayerId,
            hand: player?.hand ?? {},
            points: player?.points ?? 0,
            foodDue: player?.foodDue ?? 0,
            rentDue: player?.rentDue ?? 0,
            // Debt is public, so an opponent's countdown renders on their panel
            // exactly as your own does.
            loanOutstanding: player?.loanOutstanding ?? 0,
            loanDue: player?.loanDue ?? 0,
            mortgageCardType: player?.mortgageCardType ?? null,
            mortgageOutstanding: player?.mortgageOutstanding ?? 0,
            mortgageDue: player?.mortgageDue ?? 0,
            residenceCardType: player?.residenceCardType ?? null,
            residenceLandlordId: player?.residenceLandlordId ?? null,
            roomsTotal: player?.roomsTotal ?? 0,
            roomsFree: player?.roomsFree ?? 0,
            // Resolved here rather than sent: the landlord's seat index and name
            // are already in the public player list, and the token needs both.
            landlordSeatIndex:
                s.players.find((p) => p.id === player?.residenceLandlordId)?.seatIndex ?? -1,
            landlordName:
                s.players.find((p) => p.id === player?.residenceLandlordId)?.displayName ?? '',
        }
    })
})

const opponentSeats = computed(() => seats.value.filter((s) => !s.isMe))
const mine = computed(() => seats.value.find((s) => s.isMe) ?? null)

/*
  Spendable balance, not the raw total: points reserved against an open market
  claim cannot be spent on a purchase, a repayment or a redemption. Gating the
  controls on the raw number offers actions the server would refuse.
*/
const availablePoints = computed(() => me.value?.availablePoints ?? 0)

const activeAction = ref('')
const startAction = (action) => (activeAction.value = action)
const cancelAction = () => (activeAction.value = '')

async function onBuy({ type, quantity }) {
    if (await games.buyFromBank(props.code, type, quantity)) cancelAction()
}

async function onTransaction(payload) {
    let ok = false
    payload = payload.payload

    if (payload.kind === 'sell-to-bank') {
        ok = await games.sellToBank(props.code, payload.cardType, payload.quantity)
    } else if (payload.kind === 'sell-offer') {
        ok = await games.sellOffer(
            props.code, payload.cardType, payload.quantity, payload.pricePoints
        )
    } else if (payload.kind === 'trade-offer') {
        ok = await games.tradeOffer(
            props.code, payload.cardType, payload.quantity,
            payload.wantCardType, payload.wantQuantity
        )
    }

    if (ok) cancelAction()
}

const onClaimOffer = (id) => games.claimOffer(props.code, id)
const onUnclaimOffer = (id) => games.unclaimOffer(props.code, id)
const onDeclineOffer = ({ offerId, playerId }) => games.declineOffer(props.code, offerId, playerId)
const onConfirmOffer = ({ offerId, playerId }) => games.confirmOffer(props.code, offerId, playerId)
const onCancelOffer = (id) => games.cancelOffer(props.code, id)

/*
  Eating. Routed through runCredit's sibling guard for the same reason: a click
  that silently does nothing is the worst failure mode, and this handler is one
  more place a stale store would produce exactly that.
*/
/*
  Housing. Routed through the same guard as credit: a click that silently does
  nothing is the failure mode worth engineering against.
*/
const onMoveIn = (cardType) =>
    runCredit('move in', games.moveIn && (() => games.moveIn(props.code, cardType)))
const onLeaveResidence = () =>
    runCredit('leave', games.leaveResidence && (() => games.leaveResidence(props.code)))
const onRentOut = ({ cardType, rentPoints, intervalTurns }) =>
    runCredit('let a room', games.rentOut && (() => games.rentOut(props.code, cardType, rentPoints, intervalTurns)))
const onRespondMoveOut = ({ agreementId, accept }) =>
    runCredit('answer', games.respondMoveOut && (() => games.respondMoveOut(props.code, agreementId, accept)))
const onResolveMoveOut = (leave) =>
    runCredit('move out', games.resolveMoveOut && (() => games.resolveMoveOut(props.code, leave)))
const onRollIncome = () =>
    runCredit('roll', games.rollIncome && (() => games.rollIncome(props.code)))

const onSeize = (picks) =>
    runCredit('seize', games.seizeCards && (() => games.seizeCards(props.code, picks)))
const onWaiveSeizure = () =>
    runCredit('waive', games.waiveSeizure && (() => games.waiveSeizure(props.code)))

const onEvict = (agreementId) =>
    runCredit('evict', games.evictTenant && (() => games.evictTenant(props.code, agreementId)))

const onPayRent = () =>
    runCredit('pay rent', games.payRent && (() => games.payRent(props.code)))

const onInvest = ({ cardType, principal, yieldPercent, termTurns }) =>
    runCredit('invest', games.postInvest
        && (() => games.postInvest(props.code, cardType, principal, yieldPercent, termTurns)))

/*
  Property types somebody at the table owns, for the invest picker. Derived from
  the public hands rather than sent: an investor can stake any property in play,
  and every client already has the hands.
*/
const investableProperties = computed(() => {
    const counts = {}
    for (const p of state.value?.players ?? []) {
        for (const [code, n] of Object.entries(p.hand ?? {})) {
            const card = cardTypes.get(code)
            if (!card || card.category !== 'property' || n < 1) continue
            counts[code] = (counts[code] ?? 0) + 1
        }
    }
    return Object.entries(counts).map(([code, owners]) => ({
        code, owners, title: cardTypes.get(code)?.title ?? code,
    }))
})


const onRentAsk = ({ rentPoints, intervalTurns }) =>
    runCredit('request a room', games.rentAsk && (() => games.rentAsk(props.code, rentPoints, intervalTurns)))

// The landlord's name is not on `you` — only their id — so resolve it from the
// public player list every client already holds.
const myLandlord = computed(() => {
    const id = me.value?.residenceLandlordId
    if (!id) return null
    return state.value?.players.find((p) => p.id === id) ?? null
})

// Derived rather than sent: a count over the same public list.
const myTenantCount = computed(
    () => (state.value?.players ?? []).filter((p) => p.residenceLandlordId === me.value?.playerId).length
)

/*
  The rent AMOUNT is not in the projection — YouBlock carries rent_due (the
  countdown) but not rent_points. Passing 0 means the modal shows the countdown
  and omits the figure, which is honest; adding rent_points to YouBlock is a
  two-line backend change that makes it appear.
*/
/*
  The rent lives on the TENANCY, not on the player — there is no me.rentPoints,
  so this read was always undefined and fell through to 0. That is why the
  residence modal showed no amount and told tenants that leaving would cost them
  "0 rent".
*/
const myRentPoints = computed(() => me.value?.tenancy?.rentPoints ?? 0)

const onEat = ({ cardType }) =>
    runCredit('eat', games.eatFood && (() => games.eatFood(props.code, cardType)))

/*
  Credit. These deliberately do NOT cancelAction(): the desk lives inside the
  bank panel and stays open after each one, so the player can watch the balance
  move and repay again without reopening it.

  Every one runs through `runCredit`, which exists because a click that does
  NOTHING is the worst possible failure. If the store method is missing — a
  stale stores/games.js after a partial file update — calling it throws a
  TypeError that dies inside the event handler: no request, no message, no
  clue. Routing through here turns any such failure into the same toast the
  server errors use, naming the cause.
*/
async function runCredit(label, call) {
    try {
        if (typeof call !== 'function') {
            throw new Error(`${label} is unavailable — stores/games.js looks out of date`)
        }
        await call()
    } catch (e) {
        games.actionError = e?.message ?? `${label} failed`
    }
}

const onBorrow = (amount) =>
    runCredit('borrow', games.borrow && (() => games.borrow(props.code, amount)))
const onRepay = (amount) =>
    runCredit('repay', games.repayLoan && (() => games.repayLoan(props.code, amount)))
const onMortgage = (cardType) =>
    runCredit('mortgage', games.openMortgage && (() => games.openMortgage(props.code, cardType)))
const onRedeem = () =>
    runCredit('redeem', games.redeemMortgage && (() => games.redeemMortgage(props.code)))

async function onEndTurn() {
    cancelAction()
    await games.endTurn(props.code)
}

watch(
    () => state.value?.game.stateVersion,
    (next, prev) => {
        if (prev !== undefined && next !== prev) cancelAction()
    }
)

watch(isMyTurn, (turn) => {
    if (!turn) cancelAction()
})

/*
  Elimination no longer bounces you straight to the lobby. You are shown WHY, and
  leave when you choose to — being ejected mid-turn with no explanation is the
  worst possible way to find out you lost.
*/
const eliminated = computed(() => me.value?.status === 'eliminated')

const won = computed(
    () => state.value?.game.status === 'completed'
        && state.value?.game.winnerPlayerId === me.value?.playerId
)

const outcomeReason = computed(() => {
    const mineId = me.value?.playerId
    if (!mineId) return ''
    // The elimination event carries the cause; the state only carries the fact.
    const hit = [...events.value]
        .reverse()
        .find((e) => e.event_type === 'player.eliminated'
            && e.payload?.player_id === mineId)
    return hit?.payload?.reason ?? ''
})

const outcomeCreditor = computed(() => {
    const mineId = me.value?.playerId
    const hit = [...events.value]
        .reverse()
        .find((e) => e.event_type === 'player.eliminated'
            && e.payload?.player_id === mineId)
    const id = hit?.payload?.creditor_player_id
    if (!id) return ''
    return state.value?.players.find((p) => p.id === id)?.displayName ?? ''
})

function leaveToLobby() {
    games.clearState()
    router.push({ name: 'lobby' })
}

watch(
    () => mine.value?.seatStatus,
    (status) => {
        // Resignation still leaves immediately; only elimination gets a screen.
        if (status === 'resigned') {
            games.clearState()
            router.push({ name: 'lobby' })
        }
    }
)

watch(
    () => state.value?.game.status,
    (status, prev) => {
        // A completed game shows its result rather than vanishing. Anything else
        // that is not in progress — abandoned, closed — still returns to lobby.
        if (!status || status === 'in_progress' || status === 'completed') return
        if (prev !== undefined) router.push({ name: 'lobby' })
    }
)
</script>

<template>
    <LoadingScreen v-if="!hasLoadedState || !loaded" message="Loading your game..." :error="stateError ?? cardError ?? ''"
        @retry="load" />

    <div v-else class="relative flex h-[100dvh] gap-2 bg-gray-dark p-2 md:gap-3 md:p-3 xl:gap-6 xl:p-6">

        <div class="scroll-slim flex min-h-0 min-w-0 flex-1 flex-col gap-2 overflow-y-auto md:gap-3
                    xl:gap-4 xl:overflow-hidden">

            <Header :game-code="code" />

            <div class="game-grid min-h-0 flex-1">

                <!--
                    Opponents scroll horizontally at every width below xl and each
                    takes a third of the rail. Letting them share the space evenly
                    meant a fourth player made all four too narrow to read; a fixed
                    share keeps every panel legible and moves the cost to a scroll,
                    which is the right trade for a table that can grow.
                -->
                <div class="scroll-slim area-opp flex min-w-0 gap-2 overflow-x-auto pb-1 md:gap-3
                            xl:flex-col xl:gap-3 xl:overflow-x-hidden xl:overflow-y-auto xl:pb-0 xl:pr-1">
                    <PlayerCardHolder v-for="seat in opponentSeats" :key="seat.seatIndex" :player-type="'opponent'"
                        :seat-index="seat.seatIndex" :player-name="seat.name" :seat-status="seat.seatStatus"
                        :is-turn="seat.isTurn" :hand="seat.hand" :points="seat.points" :food-due="seat.foodDue"
                        :rent-due="seat.rentDue" :loan-due="seat.loanDue" :loan-outstanding="seat.loanOutstanding"
                        :mortgage-card-type="seat.mortgageCardType" :mortgage-outstanding="seat.mortgageOutstanding"
                        :mortgage-due="seat.mortgageDue" :residence="seat.residenceCardType ?? ''"
                        :rooms-total="seat.roomsTotal" :rooms-free="seat.roomsFree"
                        :is-tenant="!!seat.residenceLandlordId" :landlord-name="seat.landlordName"
                        :landlord-seat-index="seat.landlordSeatIndex"
                        class="w-[19rem] shrink-0 lg:w-[calc((100%-1.5rem)/3)] lg:min-w-[17rem]
                               xl:w-full xl:min-w-0 xl:flex-none" />
                </div>

                <div class="area-log flex min-h-0 min-w-0 flex-col gap-2 md:gap-3">
                <EventLog class="min-h-0 min-w-0 flex-1" :events="events" :seat-by-player="seatByPlayer"
                    :name-by-player="nameByPlayer" :sending="sendingChat"
                    @send="(text) => games.sendChat(code, text)" />

                </div>

                <!--
                    Dice sit under the player's own panel below xl, where the
                    stats row leaves a column of dead space, and under the log
                    from xl where the own panel spans the full width instead.
                -->
                <DiceSection class="area-dice" :can-roll="me?.canRollIncome ?? false"
                    :blocked-reason="me?.rollBlockedReason ?? ''" :dice="me?.lastDice ?? []"
                    :income="me?.lastIncome ?? 0" :busy="acting"
                    @roll="onRollIncome" :isMyTurn="isMyTurn" />

                <OffersPanel class="area-offers min-h-0 min-w-0" :offers="offers" :my-player-id="me?.playerId ?? ''"
                    :my-points="availablePoints" :my-hand="me?.hand ?? {}"
                    :my-residence-card-type="me?.residenceCardType ?? null" :my-rooms-free="me?.roomsFree ?? 0"
                    :busy="acting" @claim="onClaimOffer"
                    @unclaim="onUnclaimOffer" @decline="onDeclineOffer" @confirm="onConfirmOffer"
                    @cancel="onCancelOffer" />

                <PlayerCardHolder class="area-own min-w-0" :active-action="activeAction"
                    :seat-index="mine?.seatIndex ?? -1" :player-name="mine?.name ?? ''"
                    :seat-status="mine?.seatStatus ?? 'empty'" :is-turn="isMyTurn" :hand="mine?.hand ?? {}"
                    :points="mine?.points ?? 0" :food-due="mine?.foodDue ?? 0" :rent-due="mine?.rentDue ?? 0"
                    :loan-due="mine?.loanDue ?? 0" :loan-outstanding="mine?.loanOutstanding ?? 0"
                    :mortgage-card-type="mine?.mortgageCardType ?? null"
                    :mortgage-outstanding="mine?.mortgageOutstanding ?? 0" :mortgage-due="mine?.mortgageDue ?? 0"
                    :residence="mine?.residenceCardType ?? ''" :rooms-total="mine?.roomsTotal ?? 0"
                    :rooms-free="mine?.roomsFree ?? 0" :is-tenant="!!me?.residenceLandlordId"
                    :rooms-by-card="me?.roomsByCard ?? {}" :rooms-pending-by-card="me?.roomsPendingByCard ?? {}"
                    :moveout-status="me?.tenancy?.moveoutStatus ?? null"
                    :moveout-buyout="me?.tenancy?.moveoutBuyout ?? 0"
                    :available-points="availablePoints" :tenants="me?.tenants ?? []" :investable-properties="investableProperties"
                    :residence-landlord-id="me?.residenceLandlordId ?? null"
                    :landlord-name="myLandlord?.displayName ?? ''"
                    :landlord-seat-index="myLandlord?.seatIndex ?? -1" :rent-points="myRentPoints"
                    :busy="acting" @buy="startAction('buy')" @sell="startAction('sell')" @trade="startAction('trade')"
                    @eat="onEat" @move-in="onMoveIn" @leave-residence="onLeaveResidence" @rent-out="onRentOut"
                    @rent-ask="onRentAsk" @pay-rent="onPayRent" @invest="onInvest" @respond-move-out="onRespondMoveOut"
                    @resolve-move-out="onResolveMoveOut" @evict="onEvict" @cancel-operation="cancelAction"
                    @transaction="onTransaction" @end-turn="onEndTurn" />
            </div>
        </div>

        <BankSection :buying-active="activeAction === 'buy'" :pools="state.bank" :points="availablePoints"
            :hand="me?.hand ?? {}" :can-act="isMyTurn" :loan-outstanding="me?.loanOutstanding ?? 0"
            :loan-due="me?.loanDue ?? 0" :mortgage-card-type="me?.mortgageCardType ?? null"
            :mortgage-outstanding="me?.mortgageOutstanding ?? 0" :mortgage-due="me?.mortgageDue ?? 0" :busy="acting"
            @cancel="cancelAction" @confirm="onBuy" @borrow="onBorrow" @repay="onRepay" @mortgage="onMortgage"
            @redeem="onRedeem" />

        <!-- Frozen: nothing else on the board can be acted on, so it covers. -->
        <SeizureModal v-if="me?.seizure" :seizure="me.seizure" :busy="acting" @seize="onSeize"
            @waive="onWaiveSeizure" />

        <!-- Outcome sits above the freeze: if you are out, the freeze is not
             your problem any more. -->
        <OutcomeModal v-if="eliminated || won" :outcome="won ? 'won' : 'eliminated'"
            :reason="outcomeReason" :seat-index="mine?.seatIndex ?? -1"
            :player-name="mine?.name ?? ''" :creditor-name="outcomeCreditor"
            @leave="leaveToLobby" />

        <Transition name="toast">
            <div v-if="actionError"
                class="fixed bottom-6 left-1/2 z-[200] -translate-x-1/2 rounded-xl border-2 border-rose-400 bg-gray-x-dark px-5 py-3 shadow-2xl shadow-black/50">
                <div class="flex items-center gap-3">
                    <span class="text-sm font-bold text-rose-400">{{ actionError }}</span>
                    <button type="button" @click="games.actionError = null"
                        class="cursor-pointer text-gray-x-light transition-colors duration-200 hover:text-gray-2x-light">✕</button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<style scoped>
.game-grid {
    display: grid;
    gap: 0.5rem;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto auto minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
        "opp"
        "dice"
        "own"
        "log"
        "offers";
}

@media (min-width: 768px) {
    .game-grid {
        gap: 0.75rem;
        grid-template-columns: 22rem minmax(0, 1fr);
        grid-template-rows: auto auto minmax(0, 1fr);
        grid-template-areas:
            "opp    opp"
            "dice   log"
            "own    log";
    }
}

/*
  Opponents span the top. Below them the log takes the middle column and offers
  the right, both running to the bottom of the grid.

  The last row is the only flexible track, so a cell spanning all three rows
  still only grows by that row's share — which is why offers used to stop short.
  own and dice are content-sized in their own rows; log and offers get the
  stretch.
*/
@media (min-width: 1024px) {
    .game-grid {
        grid-template-columns: 22rem minmax(0, 1fr) 18rem;
        /*
          Opponents get row 1 to THEMSELVES across all three columns, so the rail
          is the full width of the page. Offers starts in row 2, under them,
          beside the log — previously it spanned row 1 as well, which pulled it
          up level with the opponents and stole a third of their width.
        */
        /*
          dice is auto so it ends at its content — a flexible track left a band
          of empty panel under it. own takes the remaining height in that column,
          while log and offers span both rows and reach the bottom.
        */
        grid-template-rows: auto auto minmax(0, 1fr);
        grid-template-areas:
            "opp  opp opp"
            "dice log offers"
            "own  log offers";
    }
}

/*
  Widest: opponents become a rail on the far right, offers sits between the log
  column and that rail, and the player's own panel spans the bottom.
*/
@media (min-width: 1280px) {
    .game-grid {
        gap: 1rem;
        grid-template-columns: minmax(0, 1fr) 19rem 21rem;
        grid-template-rows: minmax(0, 1fr) auto auto;
        grid-template-areas:
            "log  offers opp"
            "dice offers opp"
            "own  own    own";
    }
}

.area-opp {
    grid-area: opp;
}

.area-dice {
    grid-area: dice;
}

.area-own {
    grid-area: own;
}

.area-log {
    grid-area: log;
}

.area-offers {
    grid-area: offers;
}

.toast-enter-active,
.toast-leave-active {
    transition: opacity 200ms ease, transform 200ms ease;
}

.toast-enter-from,
.toast-leave-to {
    opacity: 0;
    transform: translate(-50%, 12px);
}

.scroll-slim {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in oklab, var(--color-gray-x-light) 30%, transparent) transparent;
}

.scroll-slim::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

.scroll-slim::-webkit-scrollbar-track {
    background: transparent;
}

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

@media (prefers-reduced-motion: reduce) {

    .toast-enter-active,
    .toast-leave-active {
        transition: none;
    }
}
</style>