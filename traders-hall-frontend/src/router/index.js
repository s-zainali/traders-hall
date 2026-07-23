import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import PublicLayout from '../layouts/PublicLayout.vue'
import LandingView from '../views/LandingView.vue'
import AuthView from '../views/AuthView.vue'
import LobbyView from '../views/LobbyView.vue'
import GameView from '../views/GameView.vue'

const routes = [
  {
    // Layout route: PublicLayout supplies the PoweredByZain footer for every
    // child below, and the decorated background for the ones that ask.
    path: '/',
    component: PublicLayout,
    children: [
      {
        // NOTE: child paths have NO leading slash. '/auth' inside children is
        // treated as absolute and silently breaks the nesting.
        path: '',
        name: 'landing',
        component: LandingView,
        // `ambient: true` is the ONLY thing that turns the decorated
        // background on. Every other route is plain gray-dark.
        meta: { redirectIfAuthed: true, ambient: true },
      },
      {
        path: 'auth',
        name: 'auth',
        component: AuthView,
        meta: { redirectIfAuthed: true },
      },
      {
        path: 'lobby',
        name: 'lobby',
        component: LobbyView,
        meta: { requiresAuth: true },
      },
    ],
  },
  {
    // Outside the layout: the game has its own chrome and gets the compact
    // footer inside its Header instead.
    path: '/game/:code',
    name: 'game',
    component: GameView,
    props: true,
    meta: { requiresAuth: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved ?? { top: 0 },
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'auth', query: { next: to.fullPath } }
  }

  if (to.meta.redirectIfAuthed && auth.isAuthenticated) {
    return { name: 'lobby' }
  }

  return true
})