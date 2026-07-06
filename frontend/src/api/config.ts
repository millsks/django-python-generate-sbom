// Public runtime config fetched from GET /api/v1/config/ (Story 11.20). Lets the SPA
// read deploy-time feature flags — e.g. whether the interactive API docs are enabled —
// before and without authentication, so header affordances that must show in both auth
// states are driven by the same backend setting that gates the endpoint itself.
import { apiRequest } from './client'

export interface AppConfig {
  api_docs_enabled: boolean
}

export function getAppConfig(): Promise<AppConfig> {
  return apiRequest<AppConfig>('/config/')
}
