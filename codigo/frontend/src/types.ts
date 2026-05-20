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

// ── Corpus file (con clasificación, Sprint Drive A) ──────────────────────────

export type CorpusRol =
  | 'solicitud_formal' | 'reglamento' | 'acta_eleccion' | 'acta_posesion'
  | 'autocenso_depurado' | 'autocenso' | 'censo_comunidad' | 'ficha_precampo'
  | 'rut_comunidad' | 'resena_historica' | 'mapa_territorial' | 'base_datos_dane'
  | 'acta_inicio' | 'cronograma' | 'diario_campo' | 'ficha_comision'
  | 'apuntes_reuniones' | 'arbol_riesgo' | 'cartografia_social' | 'registro_asistencia'
  | 'proyecto_qgis' | 'geopackage' | 'evidencia_foto'
  | 'concepto_etnologico' | 'borrador_acto_administrativo' | 'otro'

export type CorpusClasificacionFuente =
  | 'manual' | 'heuristica_extension' | 'heuristica_carpeta'
  | 'heuristica_nombre' | 'heuristica_nombre_debil' | 'ia_inicio' | 'fallback_otro'

export interface CorpusFile {
  id: string
  study_id: string
  fase: 'FASE1' | 'FASE2' | 'FASE3'
  nombre_archivo: string
  drive_file_id: string
  tipo_archivo: string
  rol_en_corpus: CorpusRol | null
  clasificacion_fuente: CorpusClasificacionFuente | null
  clasificacion_confianza: number | null
  notas_clasificacion: string | null
  tamanio_bytes: number | null
  ruta_local: string | null
  estado: 'pendiente' | 'descargado' | 'clasificado' | 'procesado' | 'error'
  error_msg: string | null
  sync_at: string
  procesado_en: string | null
}

export interface CorpusClasificacionItem {
  file_id: string
  nombre: string
  rol: CorpusRol | null
  fuente: CorpusClasificacionFuente
  confianza: number
  omitido: boolean
  notas?: string | null
}

export interface CorpusClasificarResponse {
  study_id: string
  total_archivos: number
  clasificados: number
  omitidos: number
  fallback_otro: number
  por_fuente: Record<string, number>
  archivos: CorpusClasificacionItem[]
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: BackendUser
}

export type ReportEstado = 'generando' | 'listo_revision' | 'en_revision' | 'aprobado' | 'exportado' | 'error'

export interface Report {
  id: string
  study_id: string
  version: number
  estado: ReportEstado
  archivo_docx: string | null
  archivo_zip: string | null
  hash_docx: string | null
  drive_file_id: string | null
  drive_url: string | null
  generado_por: string | null
  aprobado_por: string | null
  parametros: Record<string, unknown> | null
  error_msg: string | null
  generado_en: string
  aprobado_en: string | null
  exportado_en: string | null
}
