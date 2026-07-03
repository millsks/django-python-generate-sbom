// Base REST client. All network calls route through src/api/ (AD-5); components
// never call fetch directly. The Authorization header carries the org API key.
const API_BASE = '/api/v1'

export interface RequestOptions {
  method?: string
  body?: unknown
  apiKey?: string
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options.apiKey) {
    headers.Authorization = `Api-Key ${options.apiKey}`
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}
