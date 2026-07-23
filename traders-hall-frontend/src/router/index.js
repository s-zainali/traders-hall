import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import LandingView from '../views/LandingView.vue'
import AuthView from '../views/AuthView.vue'
import LobbyView from '../views/LobbyView.vue'
import GameView from '../views/GameView.vue'

const routes = [
  {
    path: '/',
    name: 'landing',
    component: LandingView,
    // signed-in users have no use for the marketing page
    meta: { redirectIfAuthed: true },
  },
  {
    path: '/auth',
    name: 'auth',
    component: AuthView,
    meta: { redirectIfAuthed: true },
  },
  {
    path: '/lobby',
    name: 'lobby',
    component: LobbyView,
    meta: { requiresAuth: true },
  },
  {
    path: '/game/:code',
    name: 'game',
    component: GameView,
    props: true,          // :code becomes a prop on GameView
    meta: { requiresAuth: true },
  },
  // anything else falls back to the landing page
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  // createWebHistory gives clean URLs (/lobby, not /#/lobby). Needs the server
  // to serve index.html for unknown paths — Vite's dev server already does.
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    // remember where they were headed so login can send them back
    return { name: 'auth', query: { next: to.fullPath } }
  }

  if (to.meta.redirectIfAuthed && auth.isAuthenticated) {
    return { name: 'lobby' }
  }

  return true
})