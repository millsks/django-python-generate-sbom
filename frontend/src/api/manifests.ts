// Manifest upload API calls.
import { apiUpload } from './client'

export interface ManifestMetadata {
  applicationId: string
  componentName: string
  repositoryUrl: string
  sourceBranch: string
}

export interface UploadResponse {
  upload_id: string
  detected_format: string
}

export function uploadManifest(file: File, meta: ManifestMetadata): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('application_id', meta.applicationId)
  form.append('component_name', meta.componentName)
  form.append('repository_url', meta.repositoryUrl)
  form.append('source_branch', meta.sourceBranch)
  return uploadManifestForm(form)
}

function uploadManifestForm(form: FormData): Promise<UploadResponse> {
  return apiUpload<UploadResponse>('/manifests/upload/', form)
}
