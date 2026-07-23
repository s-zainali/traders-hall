import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const ACCESS_KEY = 'th.access'
const REFRESH_KEY = 'th.refresh'

export const useAuthStore = defineStore('auth', () => {
  // Seeded from localStorage so a page reload keeps you logged in.
  const accessToken = ref(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref(localStorage.getItem(REFRESH_KEY))
  const user = ref(null)
  const ready = ref(false)      // true once we've settled whether a session exists
  const error = ref(null)

  const isAuthenticated = computed(() => user.value !== null)

  // Refresh tokens are single-use (the server rotates them). Two concurrent
  // 401s must NOT each call /refresh — the second would present an already
  // revoked token and log the user out. Sharing one in-flight promise means
  // every caller awaits the same refresh.
  let refreshPromise = null

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  }

  function clear() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  async function post(path, body) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail?.detail?.message ?? `HTTP ${response.status}`)
    }
    return response.status === 204 ? null : response.json()
  }

  async function login(identifier, password) {
    error.value = null
    try {
      const tokens = await post('/api/v1/auth/login', { identifier, password })
      setTokens(tokens.access_token, tokens.refresh_token)
      await fetchMe()
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }
  
  async function register(username, password, email, displayName) {
    error.value = null
    try {
      const tokens = await post('/api/v1/auth/register', {
        username,
        password,
        email: email || null,        // '' would fail EmailStr validation
        display_name: displayName || null,
      })
      setTokens(tokens.access_token, tokens.refresh_token)
      await fetchMe()
      return true
    } catch (e) {
      error.value = e.message
      return false
    }
  }

  async function refresh() {
    if (!refreshToken.value) return false
    if (refreshPromise) return refreshPromise   // join the in-flight one

    refreshPromise = (async () => {
      try {
        const tokens = await post('/api/v1/auth/refresh', {
          refresh_token: refreshToken.value,
        })
        setTokens(tokens.access_token, tokens.refresh_token)
        return true
      } catch {
        clear()
        return false
      } finally {
        refreshPromise = null
      }
    })()

    return refreshPromise
  }

  async function fetchMe() {
    if (!accessToken.value) return null
    const { apiJson } = await import('../api/client')
    try {
      user.value = await apiJson('/api/v1/auth/me')
    } catch {
      user.value = null
    }
    return user.value
  }

  async function logout() {
    if (refreshToken.value) {
      await post('/api/v1/auth/logout', { refresh_token: refreshToken.value })
        .catch(() => {})   // clear locally regardless of what the server says
    }
    clear()
  }

  /** Called once at startup: do we have a usable session? */
  async function init() {
    if (accessToken.value) await fetchMe()
    ready.value = true
  }

  return {
    accessToken, refreshToken, user, ready, error, isAuthenticated,
    register, login, logout, refresh, fetchMe, init, clear,
  }
})