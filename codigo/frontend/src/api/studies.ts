import client from './client'
import type {
  Study, StudyDetail, StudyListResponse, Report,
  CorpusRol, CorpusClasificarResponse,
} from '../types'

export async function getStudies(params?: {
  estado?: string
  departamento?: string
  page?: number
  limit?: number
}): Promise<StudyListResponse> {
  const { data } = await client.get<StudyListResponse>('studies', { params })
  return data
}

export async function getStudy(id: string): Promise<StudyDetail> {
  const { data } = await client.get<StudyDetail>(`studies/${id}`)
  return data
}

export async function createStudy(payload: {
  nombre_comunidad: string
  pueblo_indigena?: string
  municipio: string
  departamento: string
  vereda?: string
  contrato_referencia?: string
  notas_adicionales?: string
  lat?: number
  lng?: number
  buffer_metros?: number
  modo_creacion?: 'drive_existente' | 'encuestas_nuevas'
}): Promise<StudyDetail> {
  const { data } = await client.post<StudyDetail>('studies', payload)
  return data
}

export async function updateStudy(id: string, payload: Partial<StudyDetail>): Promise<StudyDetail> {
  const { data } = await client.put<StudyDetail>(`studies/${id}`, payload)
  return data
}

export async function deleteStudy(id: string): Promise<void> {
  await client.delete(`studies/${id}`)
}

export async function getCorpusFiles(studyId: string) {
  const { data } = await client.get(`studies/${studyId}/corpus`)
  return data
}

// ── Clasificación de archivos (Sprint Drive A) ─────────────────────────────

export async function clasificarCorpus(
  studyId: string,
  params: { ignore_existing?: boolean; use_ai_fallback?: boolean } = {},
): Promise<CorpusClasificarResponse> {
  const { data } = await client.post<CorpusClasificarResponse>(
    `studies/${studyId}/corpus/clasificar`,
    {
      ignore_existing: params.ignore_existing ?? false,
      use_ai_fallback: params.use_ai_fallback ?? true,
    },
  )
  return data
}

export async function overrideCorpusRol(
  studyId: string,
  fileId: string,
  rol: CorpusRol,
  notas?: string,
) {
  const { data } = await client.patch(
    `studies/${studyId}/corpus/${fileId}/rol`,
    { rol, notas },
  )
  return data
}

// ── Datos estructurados por archivo (Sprint Drive B) ────────────────────────

export interface CorpusDatosResponse {
  file_id: string
  study_id: string
  nombre_archivo: string
  rol_en_corpus: string | null
  esquema_version: string | null
  extraido_con_modelo: string | null
  extraido_en: string | null
  hash_sha256: string | null
  tiene_datos: boolean
  datos_estructurados: Record<string, unknown> | null
  template_si_vacio: Record<string, unknown> | null
}

export async function getCorpusDatos(
  studyId: string, fileId: string,
): Promise<CorpusDatosResponse> {
  const { data } = await client.get<CorpusDatosResponse>(
    `studies/${studyId}/corpus/${fileId}/datos`,
  )
  return data
}

export async function putCorpusDatos(
  studyId: string, fileId: string, datos: Record<string, unknown>,
) {
  const { data } = await client.put(
    `studies/${studyId}/corpus/${fileId}/datos`,
    { datos },
  )
  return data
}

export async function transitionStudy(studyId: string, estado: Study['estado']): Promise<StudyDetail> {
  const { data } = await client.post<StudyDetail>(`studies/${studyId}/transition`, { estado })
  return data
}

export interface GisFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: { capa: string; capa_label: string; color: string; [key: string]: unknown }
}

export interface GisGeojson {
  type: 'FeatureCollection'
  features: GisFeature[]
  metadata: { total_puntos: number; capas: string[]; nombre_comunidad: string }
}

export interface Extraction {
  id: string
  tipo_dato: string
  valor: string | null
  fuente_archivo: string | null
  confianza: number | null
  extraido_en: string
}

export async function getExtractions(studyId: string): Promise<Extraction[]> {
  const { data } = await client.get<Extraction[]>(`studies/${studyId}/extractions`)
  return data
}

export interface ExtractionSummary {
  study_id: string
  total_extracciones: number
  por_tipo: Record<string, string[]>
}

export async function getExtractionSummary(studyId: string): Promise<ExtractionSummary> {
  const { data } = await client.get<ExtractionSummary>(`studies/${studyId}/documents/extractions/summary`)
  return data
}

export async function getGisGeojson(studyId: string): Promise<GisGeojson> {
  const { data } = await client.get<GisGeojson>(`studies/${studyId}/gis/geojson`)
  return data
}

export async function processCorpus(studyId: string, reprocess = false) {
  const { data } = await client.post(`studies/${studyId}/documents/process`, null, {
    params: { reprocess },
  })
  return data
}

// ── Pipeline v2 (Sprint Drive C) ────────────────────────────────────────────

export interface PipelineV2Summary {
  study_id: string
  total: number
  clasificados_inline: number
  procesados_ia: number
  saltados_sin_ia: number
  saltados_ya_procesados: number
  errores: string[]
  llamadas_ia_totales: number
  modelo_usado: string | null
  por_archivo: Array<{
    file_id: string
    nombre: string
    rol: string | null
    estado: string | null
    llamadas_ia: number
    modo: string | null
    error: string | null
  }>
}

export interface PipelineV2Status {
  estado: 'corriendo' | 'ok' | 'error' | 'sin_runs'
  summary: PipelineV2Summary | null
  error: string | null
}

export async function processCorpusV2(studyId: string, reprocess = false) {
  const { data } = await client.post(`studies/${studyId}/documents/process-v2`, null, {
    params: { reprocess },
  })
  return data as { status: string; study_id: string; pipeline: string }
}

export async function getProcessV2Status(studyId: string): Promise<PipelineV2Status> {
  const { data } = await client.get<PipelineV2Status>(`studies/${studyId}/documents/process-v2/status`)
  return data
}

// ── Consolidado del estudio (Sprint Drive E) ────────────────────────────────

export interface ConsolidatedData {
  metadata: {
    study_id: string
    nombre_comunidad: string
    pueblo_indigena: string | null
    municipio: string
    departamento: string
    generado_en: string
    archivos_consolidados: number
    archivos_con_datos: number
    archivos_sin_datos: number
    discrepancias_count: number
    overrides_aplicados?: number
  }
  fuentes: Array<{
    file_id: string
    nombre_archivo: string
    rol: string | null
    esquema_version: string | null
    fuente_extraccion: string | null
    tiene_datos: boolean
  }>
  identificacion: Record<string, any>
  poblacion: Record<string, any>
  historia: Record<string, any>
  identidad: Record<string, any>
  caracterizacion_intrarelacional: Record<string, any>
  caracterizacion_interrelacional: Record<string, any>
  prospectiva: Record<string, any>
  territorio_y_sig: Record<string, any>
}

export async function getDatosConsolidados(studyId: string): Promise<ConsolidatedData> {
  const { data } = await client.get<ConsolidatedData>(`studies/${studyId}/datos-consolidados`)
  return data
}

export async function setConsolidacionOverrides(
  studyId: string,
  overrides: Array<{ path: string; valor: unknown; nota?: string }>,
  merge = true,
) {
  const { data } = await client.put(`studies/${studyId}/consolidacion/overrides`, { overrides, merge })
  return data as { study_id: string; overrides: Record<string, unknown>; total: number }
}

export async function clearConsolidacionOverrides(studyId: string, path?: string) {
  await client.delete(`studies/${studyId}/consolidacion/overrides`, {
    params: path ? { path } : undefined,
  })
}

export async function runGisAnalysis(studyId: string) {
  const { data } = await client.post(`studies/${studyId}/gis/analyze`)
  return data
}

export async function getReports(studyId: string): Promise<Report[]> {
  const { data } = await client.get<Report[]>(`studies/${studyId}/reports`)
  return data
}

export async function generateReport(studyId: string): Promise<Report> {
  const { data } = await client.post<Report>(`studies/${studyId}/reports`)
  return data
}

export async function approveReport(studyId: string, reportId: string): Promise<Report> {
  const { data } = await client.post<Report>(`studies/${studyId}/reports/${reportId}/approve`)
  return data
}

export async function downloadReportBlob(studyId: string, reportId: string): Promise<{ blob: Blob; filename: string }> {
  const response = await client.get(`studies/${studyId}/reports/${reportId}/download`, {
    responseType: 'blob',
  })
  const disposition = response.headers['content-disposition'] ?? ''
  const match = disposition.match(/filename="([^"]+)"/)
  const filename = match ? match[1] : `informe_${studyId}.docx`
  return { blob: response.data as Blob, filename }
}

// ── Locations (coordenadas extraídas por IA) ──────────────────────────────────

export interface StudyLocation {
  id: string
  study_id: string
  nombre: string
  tipo: 'sede_cabildo' | 'sitio_sagrado' | 'territorio_ancestral' | 'lugar_historico' | 'ruta_migratoria' | 'punto_geografico'
  lat: number
  lng: number
  descripcion: string | null
  fuente_archivo: string | null
  confianza: number | null
  extraido_en: string
}

export async function getLocations(studyId: string): Promise<StudyLocation[]> {
  const { data } = await client.get<StudyLocation[]>(`studies/${studyId}/locations`)
  return data
}
