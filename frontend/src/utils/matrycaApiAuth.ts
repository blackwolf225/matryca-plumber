/** Shared Matryca Plumber UI API base URL and zero-trust token handling. */

export const MATRYCA_API_BASE =
  import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

let cachedAuthToken: string | null = null

export function invalidateMatrycaAuthToken(): void {
  cachedAuthToken = null
}

async function fetchFreshSessionToken(): Promise<string> {
  const response = await fetch(`${MATRYCA_API_BASE}/api/auth/session`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const session = (await response.json()) as { token: string }
  cachedAuthToken = session.token
  return cachedAuthToken
}

export async function resolveMatrycaAuthToken(): Promise<string | null> {
  if (cachedAuthToken) {
    return cachedAuthToken
  }
  try {
    return await fetchFreshSessionToken()
  } catch {
    return null
  }
}

function buildAuthenticatedHeaders(init: RequestInit | undefined, token: string | null): Headers {
  const headers = new Headers(init?.headers)
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json')
  }
  if (token) {
    headers.set('X-Matryca-Token', token)
  }
  return headers
}

/** JSON GET/POST with ``X-Matryca-Token``; on 401, refresh session once and retry. */
export async function matrycaFetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const token = await resolveMatrycaAuthToken()
  let response = await fetch(url, {
    ...init,
    headers: buildAuthenticatedHeaders(init, token),
  })
  if (response.status === 401) {
    invalidateMatrycaAuthToken()
    const refreshed = await resolveMatrycaAuthToken()
    response = await fetch(url, {
      ...init,
      headers: buildAuthenticatedHeaders(init, refreshed),
    })
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return (await response.json()) as T
}

/** Raw fetch with auth header and single 401 → session refresh retry. */
export async function matrycaAuthenticatedFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = await resolveMatrycaAuthToken()
  let response = await fetch(url, {
    ...init,
    headers: buildAuthenticatedHeaders(init, token),
  })
  if (response.status === 401) {
    invalidateMatrycaAuthToken()
    const refreshed = await resolveMatrycaAuthToken()
    response = await fetch(url, {
      ...init,
      headers: buildAuthenticatedHeaders(init, refreshed),
    })
  }
  return response
}
