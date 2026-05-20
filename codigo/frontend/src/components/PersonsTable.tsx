import { useEffect, useState } from 'react'
import type { PersonInput, SurveyPerson } from '../api/surveys'

type FieldKey = keyof Omit<PersonInput, 'orden' | 'extra'>

const FIELD_LABELS: Record<FieldKey, string> = {
  nombre: 'Nombre',
  documento: 'Documento',
  genero: 'Género',
  edad: 'Edad',
  cargo: 'Cargo',
  ocupacion: 'Ocupación',
  escolaridad: 'Escolaridad',
  contacto: 'Contacto',
  pueblo: 'Pueblo / Estado',
}

type Props = {
  existing: SurveyPerson[]
  fields?: FieldKey[]
  disabled?: boolean
  onChange: (persons: PersonInput[]) => void
}

const DEFAULT_FIELDS: FieldKey[] = ['nombre', 'documento', 'cargo', 'contacto']

export default function PersonsTable({ existing, fields, disabled, onChange }: Props) {
  const cols = fields && fields.length > 0 ? fields : DEFAULT_FIELDS
  const [rows, setRows] = useState<PersonInput[]>([])

  // Sincronizar con datos del backend cuando cambian
  useEffect(() => {
    setRows(existing.map((p, i) => ({
      orden: p.orden ?? i,
      nombre: p.nombre,
      documento: p.documento,
      genero: p.genero,
      edad: p.edad,
      cargo: p.cargo,
      ocupacion: p.ocupacion,
      escolaridad: p.escolaridad,
      contacto: p.contacto,
      pueblo: p.pueblo,
      extra: p.extra,
    })))
  }, [existing])

  function update(idx: number, field: FieldKey, value: string) {
    const next = rows.map((r, i) => {
      if (i !== idx) return r
      if (field === 'edad') {
        const num = value === '' ? null : Number(value)
        return { ...r, edad: Number.isFinite(num) ? num : null }
      }
      return { ...r, [field]: value || null }
    })
    setRows(next)
    onChange(next)
  }

  function addRow() {
    const next = [...rows, { orden: rows.length, nombre: '' }]
    setRows(next)
    onChange(next)
  }

  function removeRow(idx: number) {
    const next = rows.filter((_, i) => i !== idx).map((r, i) => ({ ...r, orden: i }))
    setRows(next)
    onChange(next)
  }

  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
        <thead style={{ background: 'var(--bg-alt)' }}>
          <tr>
            <th style={{ padding: '8px 10px', textAlign: 'left', width: 32 }}>#</th>
            {cols.map(c => (
              <th key={c} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, fontSize: 12 }}>
                {FIELD_LABELS[c]}
              </th>
            ))}
            <th style={{ width: 40 }}></th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={cols.length + 2} style={{ padding: 18, textAlign: 'center', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Sin registros. Haz clic en "+ Agregar fila" para empezar.
              </td>
            </tr>
          )}
          {rows.map((row, idx) => (
            <tr key={idx} style={{ borderTop: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '6px 10px', color: 'var(--text-muted)' }}>{idx + 1}</td>
              {cols.map(c => (
                <td key={c} style={{ padding: 4 }}>
                  <input
                    className="form-input"
                    style={{ padding: '4px 8px', fontSize: 13 }}
                    type={c === 'edad' ? 'number' : 'text'}
                    value={(row[c] as string | number | null | undefined) ?? ''}
                    disabled={disabled}
                    onChange={e => update(idx, c, e.target.value)}
                    placeholder={FIELD_LABELS[c]}
                  />
                </td>
              ))}
              <td style={{ padding: 4, textAlign: 'center' }}>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={disabled}
                  onClick={() => removeRow(idx)}
                  title="Borrar fila"
                  style={{ padding: '2px 8px', color: 'var(--danger)' }}
                >
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ padding: 10, background: 'var(--bg-alt)', borderTop: '1px solid var(--border-subtle)' }}>
        <button
          type="button"
          className="btn btn-outline btn-sm"
          disabled={disabled}
          onClick={addRow}
        >
          + Agregar fila
        </button>
      </div>
    </div>
  )
}
