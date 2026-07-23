import { useAuthStore } from '../stores/auth'

/**
 * fetch wrapper: attaches the access token, and on a 401 tries one refresh
 * then replays the request.
 */
export async function apiFetch(path, options = {}) {
  const auth = useAuthStore()

  const send = () =>
    fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(auth.accessToken ? { Authorization: `Bearer ${auth.accessToken}` } : {}),
        ...options.headers,
      },
    })

  let response = await send()

  // Access tokens last 15 minutes, so this is routine, not exceptional.
  if (response.status === 401 && auth.refreshToken) {
    const refreshed = await auth.refresh()
    if (refreshed) response = await send()
    else auth.clear()
  }

  return response
}

/** Same, but parses JSON and throws on failure. */
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body?.detail?.message ?? `HTTP ${response.status}`)
  }
  return response.status === 204 ? null : response.json()
}