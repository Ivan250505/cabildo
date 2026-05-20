import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '../lib/toast'
import Swal from 'sweetalert2'
import DynamicForm from '../components/DynamicForm'
import {
  completeSurveyResponse, downloadSurveyPdf, getStudySurveyResponse,
  getSurveyTypeFull, saveAnswers, saveJournalEntries, savePersons,
  startSurveyResponse,
  type AnswerInput, type JournalEntryInput, type PersonInput,
} from '../api/surveys'
import { getStudy } from '../api/studies'

export default function FormularioPage() {
  const { id, code } = useParams<{ id: string; code: string }>()
  const qc = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)

  const { data: study } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: surveyType, isLoading: loadingType } = useQuery({
    queryKey: ['survey-type-full', code],
    queryFn: () => getSurveyTypeFull(code!),
    enabled: !!code,
  })

  const { data: existingResponse, isLoading: loadingResp } = useQuery({
    queryKey: ['survey-response', id, code],
    queryFn: () => getStudySurveyResponse(id!, code!),
    enabled: !!id && !!code,
  })

  // Si no existe response aún, crearla automáticamente
  const ensureResponse = useMutation({
    mutationFn: () => startSurveyResponse(id!, code!),
    onSuccess: (resp) => {
      qc.setQueryData(['survey-response', id, code], resp)
    },
  })

  useEffect(() => {
    if (!loadingResp && existingResponse === null && id && code && !ensureResponse.isPending) {
      ensureResponse.mutate()
    }
  }, [existingResponse, loadingResp, id, code])

  const response = existingResponse ?? null

  const completar = useMutation({
    mutationFn: () => completeSurveyResponse(id!, code!),
    onSuccess: (resp) => {
      qc.setQueryData(['survey-response', id, code], resp)
      qc.invalidateQueries({ queryKey: ['study-surveys', id] })
      qc.invalidateQueries({ queryKey: ['corpus', id] })
      toast.success(
        '✓ Encuesta completada',
        'PDF generado. La IA está analizando el documento en segundo plano (≈30s).',
      )
    },
  })

  const descargar = useMutation({
    mutationFn: () => downloadSurveyPdf(id!, code!),
    onError: () => toast.error('Error', 'No se pudo descargar el PDF.'),
  })

  async function handleSaveAnswers(items: AnswerInput[]) {
    if (!id || !code) return
    setSaving(true)
    try {
      const resp = await saveAnswers(id, code, items)
      qc.setQueryData(['survey-response', id, code], resp)
      setLastSavedAt(new Date())
    } catch {
      toast.error('Error al guardar', 'No se pudieron guardar los cambios. Revisa tu conexión.')
    } finally {
      setSaving(false)
    }
  }

  async function handleSavePersons(questionCode: string, persons: PersonInput[]) {
    if (!id || !code) return
    setSaving(true)
    try {
      const resp = await savePersons(id, code, questionCode, persons)
      qc.setQueryData(['survey-response', id, code], resp)
      setLastSavedAt(new Date())
    } catch {
      toast.error('Error al guardar', 'No se pudo guardar la lista.')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveJournal(questionCode: string, entries: JournalEntryInput[]) {
    if (!id || !code) return
    setSaving(true)
    try {
      const resp = await saveJournalEntries(id, code, questionCode, entries)
      qc.setQueryData(['survey-response', id, code], resp)
      setLastSavedAt(new Date())
    } catch {
      toast.error('Error al guardar', 'No se pudo guardar el diario.')
    } finally {
      setSaving(false)
    }
  }

  async function handleComplete() {
    const result = await Swal.fire({
      title: '¿Marcar como completada?',
      html: '<div style="text-align:left">Al completar:<br/>' +
        '• Se genera el <strong>PDF</strong> de la encuesta<br/>' +
        '• Se incorpora al <strong>corpus</strong> del estudio<br/>' +
        '• La <strong>IA</strong> lo analiza automáticamente (resumen + entidades)</div>',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sí, completar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#1A3A5C',
      cancelButtonColor: '#6b7280',
    })
    if (result.isConfirmed) completar.mutate()
  }

  if (loadingType || loadingResp || !surveyType || !response) {
    return <div className="loading-state">Cargando formulario…</div>
  }

  const isCompleted = response.estado === 'completada'

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-body">
          <div className="flex justify-between items-center">
            <div>
              <div className="page-title">{surveyType.nombre}</div>
              <div className="page-sub">
                {study?.nombre_comunidad} · {surveyType.fase}
              </div>
            </div>
            <div className="flex gap-2">
              <Link to={`/estudios/${id}/encuestas`} className="btn btn-outline">
                ← Volver a encuestas
              </Link>
              <button
                className="btn btn-outline"
                disabled={descargar.isPending}
                onClick={() => descargar.mutate()}
                title={isCompleted ? 'Descargar PDF final' : 'Descargar PDF (borrador)'}
              >
                {descargar.isPending ? 'Generando…' : '📄 Ver PDF'}
              </button>
              {!isCompleted && (
                <button
                  className="btn btn-primary"
                  disabled={completar.isPending}
                  onClick={handleComplete}
                >
                  {completar.isPending ? 'Completando…' : '✓ Marcar completada'}
                </button>
              )}
              {isCompleted && (
                <span className="badge badge-success" style={{ fontSize: 13, padding: '6px 14px' }}>
                  ✓ Completada
                </span>
              )}
            </div>
          </div>
          {surveyType.descripcion && (
            <div style={{ marginTop: 10, fontSize: 13, color: 'var(--text-muted)' }}>
              {surveyType.descripcion}
            </div>
          )}
        </div>
      </div>

      <DynamicForm
        surveyType={surveyType}
        response={response}
        onSaveAnswers={handleSaveAnswers}
        onSavePersons={handleSavePersons}
        onSaveJournal={handleSaveJournal}
        saving={saving}
        lastSavedAt={lastSavedAt}
      />
    </>
  )
}
