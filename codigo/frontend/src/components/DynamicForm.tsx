import { useEffect, useMemo, useRef, useState } from 'react'
import type {
  AnswerInput, JournalEntryInput, PersonInput,
  SurveyAnswer, SurveyJournalEntry, SurveyPerson,
  SurveyQuestion, SurveyResponseDetail, SurveyTypeFull,
} from '../api/surveys'
import PersonsTable from './PersonsTable'
import JournalEntries from './JournalEntries'

type Props = {
  surveyType: SurveyTypeFull
  response: SurveyResponseDetail
  onSaveAnswers: (answers: AnswerInput[]) => Promise<void>
  onSavePersons: (questionCode: string, persons: PersonInput[]) => Promise<void>
  onSaveJournal: (questionCode: string, entries: JournalEntryInput[]) => Promise<void>
  saving: boolean
  lastSavedAt: Date | null
}

type FormState = Record<string, unknown>

function answerToValue(q: SurveyQuestion, a: SurveyAnswer | undefined): unknown {
  if (!a) {
    if (q.tipo_dato === 'multiselect') return []
    if (q.tipo_dato === 'boolean') return false
    return ''
  }
  switch (q.tipo_dato) {
    case 'number': return a.valor_numero ?? ''
    case 'date': return a.valor_fecha ? a.valor_fecha.slice(0, 10) : ''
    case 'boolean': return !!a.valor_bool
    case 'multiselect': return Array.isArray(a.valor_json) ? a.valor_json : []
    default: return a.valor_texto ?? ''
  }
}

function valueToAnswerInput(q: SurveyQuestion, value: unknown): AnswerInput {
  const base: AnswerInput = { question_code: q.code }
  switch (q.tipo_dato) {
    case 'number':
      base.valor_numero = value === '' || value == null ? null : Number(value)
      break
    case 'date':
      base.valor_fecha = value ? new Date(String(value)).toISOString() : null
      break
    case 'boolean':
      base.valor_bool = Boolean(value)
      break
    case 'multiselect':
      base.valor_json = Array.isArray(value) ? value : []
      break
    default:
      base.valor_texto = value == null ? null : String(value)
  }
  return base
}

export default function DynamicForm({
  surveyType, response, onSaveAnswers, onSavePersons, onSaveJournal, saving, lastSavedAt,
}: Props) {
  const disabled = response.estado === 'completada'

  // Estado del formulario indexado por question_code
  const initialState = useMemo<FormState>(() => {
    const ansByCode: Record<string, SurveyAnswer> = {}
    for (const a of response.answers) ansByCode[a.question_code] = a
    const state: FormState = {}
    for (const sec of surveyType.sections) {
      for (const q of sec.questions) {
        state[q.code] = answerToValue(q, ansByCode[q.code])
      }
    }
    return state
  }, [surveyType, response.answers])

  const [form, setForm] = useState<FormState>(initialState)
  const [dirty, setDirty] = useState<Set<string>>(new Set())

  // Re-sincronizar si response cambia desde afuera
  useEffect(() => { setForm(initialState) }, [initialState])

  // Autosave con debounce 1500ms
  const debounceRef = useRef<number | null>(null)
  useEffect(() => {
    if (dirty.size === 0) return
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(async () => {
      const items: AnswerInput[] = []
      for (const sec of surveyType.sections) {
        for (const q of sec.questions) {
          if (dirty.has(q.code)) items.push(valueToAnswerInput(q, form[q.code]))
        }
      }
      if (items.length > 0) {
        await onSaveAnswers(items)
        setDirty(new Set())
      }
    }, 1500)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [form, dirty])

  function handleChange(code: string, value: unknown) {
    setForm(prev => ({ ...prev, [code]: value }))
    setDirty(prev => new Set(prev).add(code))
  }

  // Personas agrupadas por question_code (para PersonsTable)
  const personsByQuestion = useMemo(() => {
    const map: Record<string, SurveyPerson[]> = {}
    for (const p of response.persons) {
      if (!map[p.question_code]) map[p.question_code] = []
      map[p.question_code].push(p)
    }
    return map
  }, [response.persons])

  // Journal entries agrupadas por question_code
  const journalByQuestion = useMemo(() => {
    const map: Record<string, SurveyJournalEntry[]> = {}
    for (const j of response.journal_entries ?? []) {
      if (!map[j.question_code]) map[j.question_code] = []
      map[j.question_code].push(j)
    }
    return map
  }, [response.journal_entries])

  const showToc = surveyType.sections.length >= 6

  return (
    <>
      <SaveIndicator saving={saving} dirty={dirty.size > 0} lastSavedAt={lastSavedAt} />

      <div style={{ display: 'grid', gridTemplateColumns: showToc ? '220px 1fr' : '1fr', gap: 18, alignItems: 'start' }}>
        {showToc && (
          <aside style={{ position: 'sticky', top: 56, alignSelf: 'start' }}>
            <div className="card" style={{ padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                Secciones
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {surveyType.sections.map(sec => (
                  <li key={sec.id}>
                    <a
                      href={`#sec-${sec.code}`}
                      onClick={(e) => {
                        e.preventDefault()
                        const el = document.getElementById(`sec-${sec.code}`)
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                      }}
                      style={{
                        display: 'block', padding: '4px 6px', fontSize: 12,
                        color: 'var(--text)', textDecoration: 'none',
                        borderLeft: '2px solid transparent', borderRadius: 4,
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-alt)' }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                    >
                      {sec.titulo}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        )}

        <div>
          {surveyType.sections.map(sec => (
            <div className="card" key={sec.id} id={`sec-${sec.code}`} style={{ marginBottom: 18, scrollMarginTop: 60 }}>
              <div className="card-header">
                <span className="section-title" style={{ margin: 0 }}>{sec.titulo}</span>
              </div>
              {sec.descripcion && (
                <div style={{ padding: '0 18px', fontSize: 12, color: 'var(--text-muted)', marginTop: -4 }}>
                  {sec.descripcion}
                </div>
              )}
              <div className="card-body">
                {sec.questions.map(q => (
                  <QuestionField
                    key={q.id}
                    question={q}
                    value={form[q.code]}
                    disabled={disabled}
                    onChange={(v) => handleChange(q.code, v)}
                    personsExisting={personsByQuestion[q.code] ?? []}
                    onPersonsChange={(persons) => onSavePersons(q.code, persons)}
                    journalExisting={journalByQuestion[q.code] ?? []}
                    onJournalChange={(entries) => onSaveJournal(q.code, entries)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}


function SaveIndicator({ saving, dirty, lastSavedAt }: { saving: boolean; dirty: boolean; lastSavedAt: Date | null }) {
  let text = '—'
  let color = 'var(--text-muted)'
  if (saving) { text = 'Guardando…'; color = 'var(--warning, #b8860b)' }
  else if (dirty) { text = 'Cambios sin guardar'; color = 'var(--warning, #b8860b)' }
  else if (lastSavedAt) { text = `✓ Guardado ${lastSavedAt.toLocaleTimeString('es-CO')}`; color = 'var(--success, #1f7a36)' }

  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 5,
      padding: '6px 12px', marginBottom: 14, fontSize: 12,
      background: 'var(--bg)', borderBottom: '1px solid var(--border-subtle)',
      color, textAlign: 'right',
    }}>
      {text}
    </div>
  )
}


function QuestionField({
  question, value, disabled, onChange,
  personsExisting, onPersonsChange,
  journalExisting, onJournalChange,
}: {
  question: SurveyQuestion
  value: unknown
  disabled: boolean
  onChange: (v: unknown) => void
  personsExisting: SurveyPerson[]
  onPersonsChange: (persons: PersonInput[]) => Promise<void>
  journalExisting: SurveyJournalEntry[]
  onJournalChange: (entries: JournalEntryInput[]) => Promise<void>
}) {
  const q = question
  const labelEl = (
    <label className="form-label" style={{ display: 'block', marginBottom: 4 }}>
      {q.label}
      {q.required && <span style={{ color: 'var(--danger, #b22)' }}> *</span>}
    </label>
  )
  const ayudaEl = q.ayuda && (
    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
      {q.ayuda}
    </div>
  )

  if (q.tipo_dato === 'textarea') {
    return (
      <div className="form-group">
        {labelEl}
        <textarea
          className="form-input"
          style={{ minHeight: 90, resize: 'vertical' }}
          disabled={disabled}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
        />
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'number') {
    return (
      <div className="form-group">
        {labelEl}
        <input className="form-input" type="number" disabled={disabled}
          value={(value as string | number | null) ?? ''}
          onChange={(e) => onChange(e.target.value)} />
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'date') {
    return (
      <div className="form-group">
        {labelEl}
        <input className="form-input" type="date" disabled={disabled}
          value={String(value ?? '').slice(0, 10)}
          onChange={(e) => onChange(e.target.value)} />
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'boolean') {
    return (
      <div className="form-group">
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: disabled ? 'default' : 'pointer' }}>
          <input type="checkbox" disabled={disabled}
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)} />
          <span>{q.label}{q.required && <span style={{ color: 'var(--danger, #b22)' }}> *</span>}</span>
        </label>
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'select') {
    const options = Array.isArray(q.opciones) ? (q.opciones as string[]) : []
    return (
      <div className="form-group">
        {labelEl}
        <select className="form-select" disabled={disabled}
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">— Selecciona —</option>
          {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'multiselect') {
    const options = Array.isArray(q.opciones) ? (q.opciones as string[]) : []
    const current = Array.isArray(value) ? (value as string[]) : []
    return (
      <div className="form-group">
        {labelEl}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
          {options.map(opt => {
            const checked = current.includes(opt)
            return (
              <label key={opt} style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: disabled ? 'default' : 'pointer' }}>
                <input type="checkbox" disabled={disabled} checked={checked}
                  onChange={(e) => {
                    const next = e.target.checked ? [...current, opt] : current.filter(o => o !== opt)
                    onChange(next)
                  }} />
                <span>{opt}</span>
              </label>
            )
          })}
        </div>
        {ayudaEl}
      </div>
    )
  }
  if (q.tipo_dato === 'journal_entries') {
    return (
      <div className="form-group">
        {labelEl}
        {ayudaEl}
        <div style={{ marginTop: 8 }}>
          <JournalEntries
            existing={journalExisting}
            disabled={disabled}
            onChange={onJournalChange}
          />
        </div>
      </div>
    )
  }
  if (q.tipo_dato === 'table_persons') {
    const fields = (q.validaciones && typeof q.validaciones === 'object'
      && Array.isArray((q.validaciones as { fields?: string[] }).fields))
      ? (q.validaciones as { fields: string[] }).fields as Array<
          'nombre' | 'documento' | 'genero' | 'edad' | 'cargo' | 'ocupacion' | 'escolaridad' | 'contacto' | 'pueblo'
        >
      : undefined
    return (
      <div className="form-group">
        {labelEl}
        {ayudaEl}
        <div style={{ marginTop: 8 }}>
          <PersonsTable
            existing={personsExisting}
            fields={fields}
            disabled={disabled}
            onChange={onPersonsChange}
          />
        </div>
      </div>
    )
  }

  // Default: text
  return (
    <div className="form-group">
      {labelEl}
      <input className="form-input" type="text" disabled={disabled}
        value={String(value ?? '')}
        onChange={(e) => onChange(e.target.value)} />
      {ayudaEl}
    </div>
  )
}
