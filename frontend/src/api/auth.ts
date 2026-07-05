// Auth API calls: register, login, logout, and the current-user identity check.
import { apiRequest } from './client'

export interface OrgSummary {
  slug: string
  name: string
}

// The authenticated user's identity, independent of any org membership (Story 2.6).
export interface CurrentUser {
  id: number
  email: string
}

// Identity signal for the session: resolves with the current user when authenticated,
// rejects with an ApiError (403) when not. Decoupled from the active-org lookup so a
// logged-in user with zero orgs is still recognised as authenticated.
export function getMe(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/auth/me/')
}

export interface RegisterResponse {
  user: { id: number; email: string }
  // Registration creates no org (Story 2.6 — zero-org users); always null today.
  org: OrgSummary | null
}

export function register(email: string, password: string): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/auth/register/', {
    method: 'POST',
    body: { email, password },
  })
}

export function login(email: string, password: string): Promise<{ org: OrgSummary | null }> {
  return apiRequest<{ org: OrgSummary | null }>('/auth/login/', {
    method: 'POST',
    body: { email, password },
  })
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout/', { method: 'POST' })
}
