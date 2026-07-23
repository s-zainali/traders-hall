import { useAuthStore } from '../stores/auth'

/**
 * fetch wrapper: attaches the access token, and on a 401 refreshes once and
 * replays the request.
 *
 * The retry is not an edge case. Access tokens last 15 minutes, so expiry
 * WILL happen mid-session; without this the user gets logged out at random
 * quarter-hour intervals. With it, expiry is invisible.
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

  if (response.status === 401 && auth.refreshToken) {
    const refreshed = await auth.refresh()
    if (refreshed) response = await send()
    else auth.clear()
  }

  return response
}

/**
 * Same, but parses JSON and throws on failure.
 *
 * FastAPI nests its payload under `detail`, and our handlers put a
 * { code, message } object there — so the readable text is at
 * body.detail.message. The fallbacks cover plain-string details (FastAPI's
 * own errors) and responses with no body at all.
 */
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options)

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message =
      (typeof detail === 'string' ? detail : detail?.message) ??
      body?.message ??
      `HTTP ${response.status}`
    const error = new Error(message)
    error.status = response.status
    error.code = detail?.code            // e.g. GAME_FULL, NOT_HOST
    throw error
  }

  // 204 No Content has no body to parse
  return response.status === 204 ? null : response.json()
}