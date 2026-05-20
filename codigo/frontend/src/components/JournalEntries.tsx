import { useEffect, useState } from 'react'
import type { JournalEntryInput, SurveyJournalEntry } from '../api/surveys'

type Props = {
  existing: SurveyJournalEntry[]
  disabled?: boolean
  onChange: (entries: JournalEntryInput[]) => void
}

export default function JournalEntries({ existing, disabled, onChange }: Props) {
  const [entries, setEntries] = useState<JournalEntryInput[]>([])

  useEffect(() => {
    setEntries(existing.map((e, i) => ({
      orden: e.orden ?? i,
      fecha: e.fecha ? e.fecha.slice(0, 10) : null,
      titulo: e.titulo,
      contenido: e.contenido,
      tags: e.tags,
      extra: e.extra,
    })))
  }, [existing])

  function emit(next: JournalEntryInput[]) {
    setEntries(next)
    onChange(next)
  }

  function update(idx: number, field: keyof JournalEntryInput, value: unknown) {
    emit(entries.map((e, i) => (i === idx ? { ...e, [field]: value } : e)))
  }

  function updateTags(idx: number, raw: string) {
    const tags = raw.split(',').map(t => t.trim()).filter(Boolean)
    update(idx, 'tags', tags.length > 0 ? tags : null)
  }

  function add() {
    const today = new Date().toISOString().slice(0, 10)
    emit([...entries, { orden: entries.length, fecha: today, titulo: '', contenido: '', tags: null }])
  }

  function remove(idx: number) {
    emit(entries.filter((_, i) => i !== idx).map((e, i) => ({ ...e, orden: i })))
  }

  function move(idx: number, dir: -1 | 1) {
    const target = idx + dir
    if (target < 0 || target >= entries.length) return
    const next = [...entries]
    ;[next[idx], next[target]] = [next[target], next[idx]]
    emit(next.map((e, i) => ({ ...e, orden: i })))
  }

  return (
    <div>
      {entries.length === 0 && (
        <div style={{ padding: 16, textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic', border: '1px dashed var(--border)', borderRadius: 8, marginBottom: 8 }}>
          Sin entradas. Haz clic en "+ Nueva entrada" para empezar.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {entries.map((e, idx) => (
          <div key={idx} style={{
            border: '1px solid var(--border)', borderRadius: 8, padding: 12,
            background: 'var(--bg-alt)',
          }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
              <input
                className="form-input"
                type="date"
                style={{ width: 150, padding: '4px 8px', fontSize: 13 }}
                disabled={disabled}
                value={e.fecha ?? ''}
                onChange={(ev) => update(idx, 'fecha', ev.target.value || null)}
              />
              <input
                className="form-input"
                type="text"
                placeholder="Título de la entrada"
                style={{ flex: 1, padding: '4px 8px', fontSize: 13, fontWeight: 600 }}
                disabled={disabled}
                value={e.titulo ?? ''}
                onChange={(ev) => update(idx, 'titulo', ev.target.value)}
              />
              <div style={{ display: 'flex', gap: 2 }}>
                <button type="button" className="btn btn-ghost btn-sm" disabled={disabled || idx === 0}
                  onClick={() => move(idx, -1)} title="Mover arriba"
                  style={{ padding: '2px 6px' }}>▲</button>
                <button type="button" className="btn btn-ghost btn-sm" disabled={disabled || idx === entries.length - 1}
                  onClick={() => move(idx, 1)} title="Mover abajo"
                  style={{ padding: '2px 6px' }}>▼</button>
                <button type="button" className="btn btn-ghost btn-sm" disabled={disabled}
                  onClick={() => remove(idx)} title="Borrar"
                  style={{ padding: '2px 8px', color: 'var(--danger)' }}>✕</button>
              </div>
            </div>
            <textarea
              className="form-input"
              placeholder="Contenido de la entrada — observaciones, eventos, reflexiones, citas textuales…"
              style={{ width: '100%', minHeight: 80, padding: 8, fontSize: 13, resize: 'vertical' }}
              disabled={disabled}
              value={e.contenido ?? ''}
              onChange={(ev) => update(idx, 'contenido', ev.target.value)}
            />
            <input
              className="form-input"
              type="text"
              placeholder="Tags (separados por coma): ritual, territorio, mambeo"
              style={{ width: '100%', marginTop: 6, padding: '4px 8px', fontSize: 12 }}
              disabled={disabled}
              value={Array.isArray(e.tags) ? e.tags.join(', ') : ''}
              onChange={(ev) => updateTags(idx, ev.target.value)}
            />
          </div>
        ))}
      </div>

      <div style={{ marginTop: 10 }}>
        <button type="button" className="btn btn-outline btn-sm" disabled={disabled} onClick={add}>
          + Nueva entrada
        </button>
      </div>
    </div>
  )
}
