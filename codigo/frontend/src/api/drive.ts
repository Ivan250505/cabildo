import client from './client'

export interface DriveStatus {
  connected: boolean
  google_email?: string | null
}

export interface SyncStarted {
  status: string
  study_id: string
}

export interface DriveFileItem {
  id: string
  name: string
  mime_type: string
  size_bytes: number | null
  subfolder: string | null
  tipo: string
  is_procesable: boolean
}

export interface FolderFilesResponse {
  url: string
  total: number
  items: DriveFileItem[]
}

export interface ProcessFileRequest {
  drive_file_id: string
  file_name: string
  mime_type: string
  fase: string
}

export interface ProcessFileResult {
  drive_file_id: string
  nombre_archivo: string
  tipo: string
  tamanio_bytes: number | null
  resumen: string | null
  n_entidades: number
  estado: string
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

export async function listDriveFolder(url: string): Promise<FolderFilesResponse> {
  const { data } = await client.get<FolderFilesResponse>('drive/folder-files', { params: { url } })
  return data
}

export async function processDriveFile(studyId: string, body: ProcessFileRequest): Promise<ProcessFileResult> {
  const { data } = await client.post<ProcessFileResult>(`drive/process-file/${studyId}`, body)
  return data
}
