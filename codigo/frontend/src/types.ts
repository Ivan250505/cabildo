export type StudyEstado =
  | 'borrador' | 'sincronizando' | 'corpus_ok' | 'procesando'
  | 'listo_revision' | 'en_revision' | 'aprobado' | 'exportado' | 'error'

export interface Study {
  id: string
  nombre_comunidad: string
  pueblo_indigena: string | null
  municipio: string
  departamento: string
  estado: StudyEstado
  responsable_id: string | null
  created_at: string
  updated_at: string
}

export interface StudyDetail extends Study {
  vereda: string | null
  nit_comunidad: string | null
  contrato_referencia: string | null
  notas_adicionales: string | null
  lat: number | null
  lng: number | null
  error_msg: string | null
  url_drive_fase1: string | null
  url_drive_fase2: string | null
  url_drive_fase3: string | null
  drive_folder_id: string | null
  buffer_metros: number
  created_by: string | null
}

export interface StudyListResponse {
  total: number
  page: number
  limit: number
  items: Study[]
}

export interface BackendUser {
  id: string
  nombre_completo: string
  email: string
  rol: 'admin' | 'tecnico' | 'campo' | 'supervisor'
  estado: 'activo' | 'suspendido'
  estudios_asignados: number
  ultimo_acceso: string | null
  created_at: string
}

export interface UserListResponse {
  total: number
  page: number
  limit: number
  items: BackendUser[]
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: BackendUser
}
