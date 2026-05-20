import { useQuery } from '@tanstack/react-query'
import { getDatosConsolidados, type ConsolidatedData } from '../api/studies'

interface Props { studyId: string }

const SECCIONES: Array<{ key: keyof ConsolidatedData; titulo: string; icon: string }> = [
  { key: 'identificacion',                  titulo: 'III. Identificación',                 icon: '🪪' },
  { key: 'poblacion',                       titulo: 'III. Población',                       icon: '👥' },
  { key: 'historia',                        titulo: 'IV. Historia',                         icon: '📚' },
  { key: 'identidad',                       titulo: 'V. Identidad',                          icon: '🌿' },
  { key: 'caracterizacion_intrarelacional', titulo: 'VI.1. Caracterización intrarelacional', icon: '🏛' },
  { key: 'caracterizacion_interrelacional', titulo: 'VI.2. Caracterización interrelacional', icon: '🤝' },
  { key: 'prospectiva',                     titulo: 'VII. Prospectiva',                      icon: '🔮' },
  { key: 'territorio_y_sig',                titulo: 'VIII. Territorio y SIG',                icon: '🗺' },
]


export default function DatosConsolidados({ studyId }: Props) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['datos-consolidados', studyId],
    queryFn: () => getDatosConsolidados(studyId),
    enabled: !!studyId,
  })

  if (isLoading) return <div className="loading-state">Construyendo consolidado…</div>
  if (isError || !data) {
    return (
      <div className="empty-state">
        <p>No se pudo cargar el consolidado.</p>
        <button className="btn btn-outline btn-sm" onClick={() => refetch()}>Reintentar</button>
      </div>
    )
  }

  const meta = data.metadata
  const sinDatos = meta.archivos_con_datos === 0

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-body">
          <div className="flex justify-between items-center">
            <div>
              <div className="section-title" style={{ margin: 0 }}>📊 Consolidado del estudio</div>
              <div className="text-sm text-muted" style={{ marginTop: 4 }}>
                {meta.nombre_comunidad} · generado {new Date(meta.generado_en).toLocaleString('es-CO')}
              </div>
            </div>
            <button className="btn btn-outline btn-sm" onClick={() => refetch()}>🔄 Recalcular</button>
          </div>
          <div className="divider" />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, textAlign: 'center' }}>
            <Metric label="ARCHIVOS" value={meta.archivos_consolidados} />
            <Metric label="CON DATOS" value={meta.archivos_con_datos} highlight={meta.archivos_con_datos > 0} />
            <Metric label="SIN DATOS" value={meta.archivos_sin_datos} dim />
            <Metric
              label="DISCREPANCIAS"
              value={meta.discrepancias_count}
              warning={meta.discrepancias_count > 0}
            />
          </div>
          {meta.overrides_aplicados ? (
            <div className="alert alert-info" style={{ marginTop: 12, fontSize: 12 }}>
              ℹ {meta.overrides_aplicados} override(s) manual(es) aplicado(s) sobre el consolidado.
            </div>
          ) : null}
        </div>
      </div>

      {sinDatos && (
        <div className="alert alert-warning" style={{ marginBottom: 12 }}>
          ⚠ El corpus aún no tiene archivos procesados con el pipeline v2.
          Ejecute <strong>🚀 Procesar (v2)</strong> desde la cabecera del estudio para
          generar los <code>datos_estructurados</code> por archivo.
        </div>
      )}

      {SECCIONES.map(({ key, titulo, icon }) => (
        <Seccion key={key} titulo={titulo} icon={icon} datos={data[key] as Record<string, unknown>} />
      ))}

      <FuentesCard fuentes={data.fuentes} />
    </div>
  )
}


function Metric({ label, value, highlight, warning, dim }: {
  label: string; value: number;
  highlight?: boolean; warning?: boolean; dim?: boolean
}) {
  const color = warning ? 'var(--danger)' : highlight ? 'var(--success)' : dim ? 'var(--text-muted)' : 'var(--primary)'
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', letterSpacing: '.4px', marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, fontWeight: 700, color }}>{value}</div>
    </div>
  )
}


function Seccion({ titulo, icon, datos }: { titulo: string; icon: string; datos: Record<string, unknown> }) {
  if (!datos || Object.keys(datos).length === 0) return null
  if (esVacio(datos)) return null

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="card-header">
        <span className="section-title" style={{ margin: 0 }}>{icon} {titulo}</span>
      </div>
      <div className="card-body" style={{ fontSize: 13 }}>
        <CamposGenericos datos={datos} />
      </div>
    </div>
  )
}


function CamposGenericos({ datos }: { datos: Record<string, unknown> }) {
  // Mostrar primitivos (incluyendo {valor, fuente}) en tabla; listas y dicts complejos como sub-secciones.
  const primitivos: Array<[string, unknown]> = []
  const complejos: Array<[string, unknown]> = []

  for (const [k, v] of Object.entries(datos)) {
    if (k === 'candidatos') continue  // auditoría interna, no se muestra
    if (esCampoConFuente(v)) { primitivos.push([k, v]); continue }
    if (esPrimitivo(v)) { primitivos.push([k, v]); continue }
    if (Array.isArray(v) && v.length === 0) continue
    if (v && typeof v === 'object' && Object.keys(v as object).length === 0) continue
    complejos.push([k, v])
  }

  return (
    <>
      {primitivos.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 10 }}>
          <tbody>
            {primitivos.map(([k, v]) => (
              <FilaCampo key={k} campo={k} valor={v} />
            ))}
          </tbody>
        </table>
      )}
      {complejos.map(([k, v]) => (
        <BloqueComplejo key={k} campo={k} valor={v} />
      ))}
    </>
  )
}


function FilaCampo({ campo, valor }: { campo: string; valor: unknown }) {
  const conFuente = esCampoConFuente(valor)
  const v = conFuente ? (valor as any).valor : valor
  const fuente = conFuente ? (valor as any).fuente : null
  const isOverride = conFuente && (valor as any).override === true
  return (
    <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
      <td style={{
        padding: '6px 8px', color: 'var(--text-muted)', width: '36%',
        verticalAlign: 'top',
      }}>{prettyKey(campo)}</td>
      <td style={{ padding: '6px 8px', verticalAlign: 'top' }}>
        <div style={{ fontWeight: 600 }}>{formatPrim(v)}</div>
        {fuente && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            {isOverride ? '✏ Manual' : `Fuente: ${fuente}`}
          </div>
        )}
      </td>
    </tr>
  )
}


function BloqueComplejo({ campo, valor }: { campo: string; valor: unknown }) {
  // Discrepancias se resaltan en amarillo
  const isDiscrepancias = campo === 'discrepancias'
  return (
    <div style={{
      marginTop: 12, padding: 10,
      background: isDiscrepancias ? '#fef3c7' : 'transparent',
      border: isDiscrepancias ? '1px solid #fcd34d' : 'none',
      borderRadius: 6,
    }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: isDiscrepancias ? '#92400e' : 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '.4px', marginBottom: 6,
      }}>
        {isDiscrepancias ? '⚠ ' : ''}{prettyKey(campo)}
      </div>
      {Array.isArray(valor)
        ? <TablaLista items={valor} />
        : <CamposGenericos datos={valor as Record<string, unknown>} />
      }
    </div>
  )
}


function TablaLista({ items }: { items: unknown[] }) {
  if (items.length === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Sin entradas.</div>
  }
  if (items.every(esPrimitivo)) {
    return (
      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12 }}>
        {items.map((it, i) => <li key={i}>{formatPrim(it)}</li>)}
      </ul>
    )
  }
  const keys = Array.from(new Set(
    items
      .filter(it => it && typeof it === 'object' && !Array.isArray(it))
      .flatMap(it => Object.keys(it as Record<string, unknown>).filter(k => !k.startsWith('_')))
  ))
  const itemsConFuente = items.filter(it => it && typeof it === 'object' && '_fuente' in (it as object))
  const showFuente = itemsConFuente.length > 0

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: 'var(--bg-alt)' }}>
            {keys.map(k => (
              <th key={k} style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>
                {prettyKey(k)}
              </th>
            ))}
            {showFuente && (
              <th style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>Fuente</th>
            )}
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => {
            const obj = (typeof it === 'object' && it !== null) ? it as Record<string, unknown> : { valor: it }
            return (
              <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {keys.map(k => (
                  <td key={k} style={{ padding: '5px 8px', verticalAlign: 'top', wordBreak: 'break-word' }}>
                    {formatPrim(obj[k])}
                  </td>
                ))}
                {showFuente && (
                  <td style={{ padding: '5px 8px', fontSize: 11, color: 'var(--text-muted)' }}>
                    {(obj as any)._fuente ?? '—'}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}


function FuentesCard({ fuentes }: { fuentes: ConsolidatedData['fuentes'] }) {
  if (!fuentes || fuentes.length === 0) return null
  const conDatos = fuentes.filter(f => f.tiene_datos)
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <div className="card-header">
        <span className="section-title" style={{ margin: 0 }}>📎 Fuentes citadas ({conDatos.length}/{fuentes.length})</span>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--bg-alt)' }}>
              <th style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>Archivo</th>
              <th style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>Rol</th>
              <th style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>Método</th>
              <th style={{ padding: '5px 8px', textAlign: 'left', fontSize: 11, color: 'var(--text-muted)' }}>Datos</th>
            </tr>
          </thead>
          <tbody>
            {fuentes.map(f => (
              <tr key={f.file_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td style={{ padding: '5px 8px', wordBreak: 'break-word' }}>{f.nombre_archivo}</td>
                <td style={{ padding: '5px 8px' }}>{f.rol ?? '—'}</td>
                <td style={{ padding: '5px 8px', fontSize: 11, color: 'var(--text-muted)' }}>{f.fuente_extraccion ?? '—'}</td>
                <td style={{ padding: '5px 8px' }}>
                  {f.tiene_datos
                    ? <span className="badge badge-success" style={{ fontSize: 10 }}>✓</span>
                    : <span className="badge badge-neutral" style={{ fontSize: 10 }}>—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}


// ── Helpers ────────────────────────────────────────────────────────────────

function esPrimitivo(v: unknown): boolean {
  return v === null || ['string', 'number', 'boolean'].includes(typeof v)
}
function esCampoConFuente(v: unknown): boolean {
  return typeof v === 'object' && v !== null && !Array.isArray(v) && 'valor' in (v as object) && 'fuente' in (v as object)
}
function esVacio(obj: Record<string, unknown>): boolean {
  return Object.values(obj).every(v => {
    if (v === null || v === undefined || v === '') return true
    if (Array.isArray(v)) return v.length === 0
    if (typeof v === 'object') return Object.keys(v as object).length === 0
    return false
  })
}
function prettyKey(k: string): string {
  return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
function formatPrim(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'boolean') return v ? 'Sí' : 'No'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
