import client from './client'
import type { Study, StudyDetail, StudyListResponse, Report } from '../types'

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

export async function transitionStudy(studyId: string, estado: Study['estado']): Promise<StudyDetail> {
  const { data } = await client.post<StudyDetail>(`studies/${studyId}/transition`, { estado })
  return data
}

export async function processCorpus(studyId: string, reprocess = false) {
  const { data } = await client.post(`studies/${studyId}/documents/process`, null, {
    params: { reprocess },
  })
  return data
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
