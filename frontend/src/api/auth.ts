// Auth API calls (register now; login lands in Story 2.2).
import { apiRequest } from './client'

export interface RegisterResponse {
  user: { id: number; email: string }
  org: { slug: string; name: string }
}

export function register(email: string, password: string): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>('/auth/register/', {
    method: 'POST',
    body: { email, password },
  })
}
