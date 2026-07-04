// Base REST client. All network calls route through src/api/ (AD-5); components
// never call fetch directly. Session cookies are sent on every request; unsafe
// methods carry the Django CSRF token. The Authorization header carries the org
// API key when one is supplied (programmatic access).
const API_BASE = '/api/v1'

const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

// Carries the server's error envelope ({ error, code }) so callers can show the
// actual reason a request failed instead of a generic message.
export class ApiError extends Error {
  status: number
  code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// Build an ApiError from a failed response, preferring the server's error message.
async function toApiError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`
  let code: string | undefined
  try {
    const body = (await response.json()) as { error?: string; detail?: string; code?: string }
    message = body.error ?? body.detail ?? message
    code = body.code
  } catch {
    // Non-JSON error body (e.g. an HTML error page); keep the status message.
  }
  return new ApiError(message, response.status, code)
}

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
    throw await toApiError(response)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

// Multipart POST for file uploads. The browser sets the multipart Content-Type
// (with boundary), so we must not set it ourselves; the CSRF token still applies.
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const csrf = getCookie('csrftoken')
  if (csrf) {
    headers['X-CSRFToken'] = csrf
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  })
  if (!response.ok) {
    throw await toApiError(response)
  }
  return (await response.json()) as T
}
