// Org and membership API calls.
import { apiRequest } from './client'
import type { OrgSummary } from './auth'

export interface OrgListItem extends OrgSummary {
  active: boolean
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
