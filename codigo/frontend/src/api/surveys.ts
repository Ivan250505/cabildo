import client from './client'

export type SurveyType = {
  id: string
  code: string
  nombre: string
  descripcion: string | null
  fase: 'FASE1' | 'FASE2'
  orden: number
  version: number
  activo: boolean
}

export type SurveyEstado = 'no_iniciada' | 'borrador' | 'en_revision' | 'completada'

export type SurveyResponseSummary = {
  survey_type_code: string
  survey_type_nombre: string
  fase: 'FASE1' | 'FASE2'
  orden: number
  estado: SurveyEstado
  response_id: string | null
  updated_at: string | null
  completed_at: string | null
}

export type SurveyTipoDato =
  | 'text' | 'textarea' | 'number' | 'date' | 'boolean'
  | 'select' | 'multiselect'
  | 'table_persons' | 'evidence_list' | 'journal_entries'
  | 'file'

export type SurveyQuestion = {
  id: string
  code: string
  label: string
  tipo_dato: SurveyTipoDato
  opciones: string[] | Record<string, unknown> | null
  required: boolean
  orden: number
  ayuda: string | null
  validaciones: Record<string, unknown> | null
}

export type SurveySection = {
  id: string
  code: string
  titulo: string
  descripcion: string | null
  orden: number
  questions: SurveyQuestion[]
}

export type SurveyTypeFull = SurveyType & {
  sections: SurveySection[]
}

export type SurveyAnswer = {
  question_code: string
  question_id: string
  valor_texto: string | null
  valor_numero: number | null
  valor_fecha: string | null
  valor_bool: boolean | null
  valor_json: unknown | null
}

export type SurveyPerson = {
  id: string
  question_code: string
  orden: number
  nombre: string
  documento: string | null
  genero: string | null
  edad: number | null
  cargo: string | null
  ocupacion: string | null
  escolaridad: string | null
  contacto: string | null
  pueblo: string | null
  extra: Record<string, unknown> | null
}

export type SurveyEvidence = {
  id: string
  question_code: string
  categoria: string
  orden: number
  titulo: string
  descripcion: string | null
}

export type SurveyJournalEntry = {
  id: string
  question_code: string
  orden: number
  fecha: string | null
  titulo: string
  contenido: string | null
  tags: string[] | null
  extra: Record<string, unknown> | null
}

export type SurveyResponseDetail = {
  id: string
  study_id: string
  survey_type_code: string
  survey_type_nombre: string
  fase: 'FASE1' | 'FASE2'
  estado: SurveyEstado
  version: number
  created_at: string
  updated_at: string
  completed_at: string | null
  pdf_url: string | null
  answers: SurveyAnswer[]
  persons: SurveyPerson[]
  evidences: SurveyEvidence[]
  journal_entries: SurveyJournalEntry[]
}

export type AnswerInput = {
  question_code: string
  valor_texto?: string | null
  valor_numero?: number | null
  valor_fecha?: string | null
  valor_bool?: boolean | null
  valor_json?: unknown | null
}

export type PersonInput = {
  orden?: number
  nombre: string
  documento?: string | null
  genero?: string | null
  edad?: number | null
  cargo?: string | null
  ocupacion?: string | null
  escolaridad?: string | null
  contacto?: string | null
  pueblo?: string | null
  extra?: Record<string, unknown> | null
}

export type JournalEntryInput = {
  orden?: number
  fecha?: string | null
  titulo?: string
  contenido?: string | null
  tags?: string[] | null
  extra?: Record<string, unknown> | null
}


export async function listSurveyTypes(): Promise<SurveyType[]> {
  const { data } = await client.get<SurveyType[]>('surveys/types')
  return data
}

export async function listStudySurveys(studyId: string): Promise<SurveyResponseSummary[]> {
  const { data } = await client.get<SurveyResponseSummary[]>(`studies/${studyId}/surveys`)
  return data
}

export async function getSurveyTypeFull(code: string): Promise<SurveyTypeFull> {
  const { data } = await client.get<SurveyTypeFull>(`surveys/types/${code}`)
  return data
}

export async function getStudySurveyResponse(
  studyId: string, code: string,
): Promise<SurveyResponseDetail | null> {
  const { data } = await client.get<SurveyResponseDetail | null>(`studies/${studyId}/surveys/${code}`)
  return data
}

export async function startSurveyResponse(
  studyId: string, code: string,
): Promise<SurveyResponseDetail> {
  const { data } = await client.post<SurveyResponseDetail>(`studies/${studyId}/surveys/${code}`)
  return data
}

export async function saveAnswers(
  studyId: string, code: string, answers: AnswerInput[],
): Promise<SurveyResponseDetail> {
  const { data } = await client.put<SurveyResponseDetail>(
    `studies/${studyId}/surveys/${code}/answers`,
    { answers },
  )
  return data
}

export async function savePersons(
  studyId: string, code: string, questionCode: string, persons: PersonInput[],
): Promise<SurveyResponseDetail> {
  const { data } = await client.put<SurveyResponseDetail>(
    `studies/${studyId}/surveys/${code}/persons`,
    { question_code: questionCode, persons },
  )
  return data
}

export async function saveJournalEntries(
  studyId: string, code: string, questionCode: string, entries: JournalEntryInput[],
): Promise<SurveyResponseDetail> {
  const { data } = await client.put<SurveyResponseDetail>(
    `studies/${studyId}/surveys/${code}/journal`,
    { question_code: questionCode, entries },
  )
  return data
}

export async function completeSurveyResponse(
  studyId: string, code: string,
): Promise<SurveyResponseDetail> {
  const { data } = await client.post<SurveyResponseDetail>(
    `studies/${studyId}/surveys/${code}/complete`,
  )
  return data
}

/** Descarga el PDF de la encuesta (con token de auth via interceptor). */
export async function downloadSurveyPdf(studyId: string, code: string): Promise<void> {
  const res = await client.get(`studies/${studyId}/surveys/${code}/pdf`, {
    responseType: 'blob',
  })
  const blob = new Blob([res.data], { type: 'application/pdf' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.target = '_blank'
  // Intentar nombre desde Content-Disposition
  const cd = res.headers['content-disposition'] as string | undefined
  const match = cd && /filename="?([^";]+)"?/i.exec(cd)
  a.download = match ? match[1] : `encuesta_${code}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}
