import client from './client'

export interface DriveStatus {
  connected: boolean
  google_email?: string | null
}

export interface SyncStarted {
  status: string
  study_id: string
}

export async function getDriveStatus(): Promise<DriveStatus> {
  const { data } = await client.get<DriveStatus>('drive/status')
  return data
}

export async function getDriveAuthUrl(): Promise<{ url: string; state: string }> {
  const { data } = await client.get<{ url: string; state: string }>('drive/auth-url')
  return data
}

export async function revokeDrive(): Promise<void> {
  await client.delete('drive/revoke')
}

export async function syncStudy(studyId: string): Promise<SyncStarted> {
  const { data } = await client.post<SyncStarted>(`drive/sync/${studyId}`)
  return data
}
