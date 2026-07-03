// Base REST client. All network calls route through src/api/ (AD-5); components
// never call fetch directly. Session cookies are sent on every request; unsafe
// methods carry the Django CSRF token. The Authorization header carries the org
// API key when one is supplied (programmatic access).
const API_BASE = '/api/v1'

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

export interface RequestOptions {
  method?: string
  body?: unknown
  apiKey?: string
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options.apiKey) {
    headers.Authorization = `Api-Key ${options.apiKey}`
  }
  if (!SAFE_METHODS.includes(method)) {
    const csrf = getCookie('csrftoken')
    if (csrf) {
      headers['X-CSRFToken'] = csrf
    }
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
