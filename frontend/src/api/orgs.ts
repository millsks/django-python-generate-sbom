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

export function addMember(email: string): Promise<Member> {
  return apiRequest<Member>('/orgs/members/', {
    method: 'POST',
    body: { email },
  })
}

// Create a brand-new user account and add them to the active org (Story 2.10),
// distinct from addMember (which only adds an already-registered user).
export function createMemberUser(email: string, tempPassword: string): Promise<Member> {
  return apiRequest<Member>('/orgs/members/create-user/', {
    method: 'POST',
    body: { email, temp_password: tempPassword },
  })
}

export function removeMember(userId: number): Promise<void> {
  return apiRequest<void>(`/orgs/members/${userId}/`, { method: 'DELETE' })
}

// Promote a member to admin of the active org (Story 2.16). Adds an admin — demotes
// no one; an org may have multiple admins. Replaces the old transfer-admin.
export function promoteAdmin(userId: number): Promise<void> {
  return apiRequest<void>('/orgs/promote-admin/', { method: 'POST', body: { user_id: userId } })
}

export function leaveOrg(): Promise<void> {
  return apiRequest<void>('/orgs/leave/', { method: 'POST' })
}

// --- Global-admin (platform) management (Story 13.1) — all global-admin-only. ---
export interface GlobalAdmin {
  user_id: number
  email: string
}

export function listGlobalAdmins(): Promise<{ global_admins: GlobalAdmin[] }> {
  return apiRequest<{ global_admins: GlobalAdmin[] }>('/admin/global-admins/')
}

// Grant global admin to a registered user by email (added to the ADMIN org + admin of every org).
export function grantGlobalAdmin(email: string): Promise<GlobalAdmin> {
  return apiRequest<GlobalAdmin>('/admin/global-admins/', { method: 'POST', body: { email } })
}

// Revoke global admin: removes them from the ADMIN org and demotes to member in every org.
export function revokeGlobalAdmin(userId: number): Promise<void> {
  return apiRequest<void>(`/admin/global-admins/${userId}/`, { method: 'DELETE' })
}
