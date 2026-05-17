import client from './client'

export interface DriveStatus {
  connected: boolean
  google_email?: string | null
}

export interface SyncPhaseResult {
  study_id: string
  fase: string
  files_found: number
  files_downloaded: number
  files_skipped: number
  errors: string[]
}

export interface StudySyncResponse {
  study_id: string
  fases: SyncPhaseResult[]
  total_downloaded: number
  total_errors: number
}

export async function getDriveStatus(): Promise<DriveStatus> {
  const { data } = await client.get<DriveStatus>('drive/status')
  return data
}

export async function getDriveAuthUrl(): Promise<{ url: string; state: string }> {
  const { data } = await client.get<{ url: string; state: string }>('drive/auth-url')
  return data
}

export async function syncStudy(studyId: string): Promise<StudySyncResponse> {
  const { data } = await client.post<StudySyncResponse>(`drive/sync/${studyId}`)
  return data
}
