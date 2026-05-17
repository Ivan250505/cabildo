import client from './client'
import type { Study, StudyDetail, StudyListResponse } from '../types'

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
