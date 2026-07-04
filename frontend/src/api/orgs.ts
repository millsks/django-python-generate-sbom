// Org and membership API calls.
import { apiRequest } from './client'
import type { OrgSummary } from './auth'

export interface OrgListItem extends OrgSummary {
  active: boolean
}

export interface Member {
  user_id: number
  email: string
  role: string
  joined_at: string
}

export interface MembersResponse {
  members: Member[]
  is_admin: boolean
}

export function getOrgs(): Promise<OrgListItem[]> {
  return apiRequest<OrgListItem[]>('/orgs/')
}

export function getActiveOrg(): Promise<OrgSummary> {
  return apiRequest<OrgSummary>('/orgs/me/')
}

export function switchOrg(slug: string): Promise<OrgSummary> {
  return apiRequest<OrgSummary>('/orgs/switch/', { method: 'POST', body: { slug } })
}

export function createOrg(name: string): Promise<OrgSummary> {
  return apiRequest<OrgSummary>('/orgs/create/', { method: 'POST', body: { name } })
}

export function getMembers(): Promise<MembersResponse> {
  return apiRequest<MembersResponse>('/orgs/members/')
}

export function addMember(email: string, tempPassword: string): Promise<Member> {
  return apiRequest<Member>('/orgs/members/', {
    method: 'POST',
    body: { email, temp_password: tempPassword },
  })
}

export function removeMember(userId: number): Promise<void> {
  return apiRequest<void>(`/orgs/members/${userId}/`, { method: 'DELETE' })
}

export function transferAdmin(userId: number): Promise<void> {
  return apiRequest<void>('/orgs/transfer-admin/', { method: 'POST', body: { user_id: userId } })
}

export function leaveOrg(): Promise<void> {
  return apiRequest<void>('/orgs/leave/', { method: 'POST' })
}
