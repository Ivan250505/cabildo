import { useQuery } from '@tanstack/react-query'
import { getCorpusDatos } from '../api/studies'

interface Props {
  studyId: string
  fileId: string
}

export default function DatosEstructurados({ studyId, fileId }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['corpus-datos', studyId, fileId],
    queryFn: () => getCorpusDatos(studyId, fileId),
    enabled: !!studyId && !!fileId,
  })

  if (isLoading) {
    return <div className="text-sm text-muted" style={{ padding: 8 }}>Cargando datos…</div>
  }
  if (isError || !data) {
    return <div className="text-sm" style={{ color: 'var(--danger)' }}>No se pudieron cargar los datos estructurados.</div>
  }

  if (!data.tiene_datos) {
    return (
      <div style={{ padding: 12, background: 'var(--bg-alt)', borderRadius: 6, fontSize: 12 }}>
        <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>
          📋 Datos estructurados aún no generados para este archivo.
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Se llenarán cuando se ejecute la extracción dirigida (próximo sprint).
          Rol detectado: <strong>{data.rol_en_corpus ?? 'sin clasificar'}</strong>
        </div>
        {data.template_si_vacio && (
          <details style={{ marginTop: 8 }}>
            <summary style={{ cursor: 'pointer', fontSize: 11, color: 'var(--text-muted)' }}>
              Ver campos que se extraerán
            </summary>
            <div style={{ marginTop: 6 }}>
              <JsonView data={data.template_si_vacio} placeholder />
            </div>
          </details>
        )}
      </div>
    )
  }

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 8, fontSize: 11, color: 'var(--text-muted)',
      }}>
        <span>Esquema: <strong>{data.esquema_version}</strong></span>
        {data.extraido_con_modelo && <span>Modelo: <code>{data.extraido_con_modelo}</code></span>}
      </div>
      <JsonView data={data.datos_estructurados as Record<string, unknown>} />
    </div>
  )
}

// ── Renderer recursivo ──────────────────────────────────────────────────────

function JsonView({ data, placeholder }: { data: Record<string, unknown>; placeholder?: boolean }) {
  const entries = Object.entries(data)
  if (entries.length === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Sin campos.</div>
  }

  // Separar primitivos de complejos para mostrarlos en tabla y luego en secciones
  const primitivos: [string, unknown][] = []
  const complejos: [string, unknown][] = []

  for (const [k, v] of entries) {
    if (k === 'extra' && isEmptyContainer(v)) continue
    if (isPrimitive(v)) primitivos.push([k, v])
    else complejos.push([k, v])
  }

  return (
    <div>
      {primitivos.length > 0 && (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <tbody>
            {primitivos.map(([k, v]) => (
              <tr key={k} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '5px 8px', color: 'var(--text-muted)', width: '40%', verticalAlign: 'top' }}>
                  {prettyKey(k)}
                </td>
                <td style={{
                  padding: '5px 8px', fontWeight: placeholder ? 400 : 600,
                  color: placeholder ? 'var(--text-muted)' : 'var(--text)',
                  fontStyle: placeholder ? 'italic' : 'normal',
                  wordBreak: 'break-word',
                }}>
                  {formatPrimitive(v, placeholder)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {complejos.map(([k, v]) => (
        <div key={k} style={{ marginTop: 12 }}>
          <div style={{
            fontSize: 11, fontWeight: 700, color: 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: '.4px', marginBottom: 4,
          }}>
            {prettyKey(k)}
          </div>
          {Array.isArray(v) ? <ArrayView items={v} /> : <ObjectView obj={v as Record<string, unknown>} placeholder={placeholder} />}
        </div>
      ))}
    </div>
  )
}

function ObjectView({ obj, placeholder }: { obj: Record<string, unknown>; placeholder?: boolean }) {
  if (!obj || Object.keys(obj).length === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', paddingLeft: 8 }}>—</div>
  }
  return <JsonView data={obj} placeholder={placeholder} />
}

function ArrayView({ items }: { items: unknown[] }) {
  if (items.length === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', paddingLeft: 8 }}>Sin entradas.</div>
  }
  // Lista de primitivos
  if (items.every(isPrimitive)) {
    return (
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
        {items.map((it, i) => <li key={i}>{formatPrimitive(it)}</li>)}
      </ul>
    )
  }
  // Lista de objetos → tabla
  const keys = Array.from(
    new Set(
      items
        .filter(it => it && typeof it === 'object' && !Array.isArray(it))
        .flatMap(it => Object.keys(it as Record<string, unknown>)),
    ),
  )
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: 'var(--bg-alt)' }}>
            {keys.map(k => (
              <th key={k} style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>
                {prettyKey(k)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              {keys.map(k => {
                const v = (it as Record<string, unknown>)?.[k]
                return (
                  <td key={k} style={{ padding: '5px 8px', verticalAlign: 'top', wordBreak: 'break-word' }}>
                    {isPrimitive(v) ? formatPrimitive(v) : JSON.stringify(v)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

function isPrimitive(v: unknown): boolean {
  return v === null || ['string', 'number', 'boolean'].includes(typeof v)
}

function isEmptyContainer(v: unknown): boolean {
  if (v == null) return true
  if (Array.isArray(v)) return v.length === 0
  if (typeof v === 'object') return Object.keys(v as object).length === 0
  return false
}

function prettyKey(k: string): string {
  return k
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatPrimitive(v: unknown, placeholder = false): string {
  if (v === null || v === undefined) return placeholder ? 'pendiente' : '—'
  if (typeof v === 'boolean') return v ? 'Sí' : 'No'
  return String(v)
}
