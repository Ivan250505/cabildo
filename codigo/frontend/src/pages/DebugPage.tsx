import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getStudy, getCorpusFiles, getExtractionSummary } from '../api/studies'

const TIPO_LABELS: Record<string, string> = {
  // IA estructurada
  familias_count:         'Familias (IA)',
  personas_count:         'Personas (IA)',
  fecha_censo:            'Fecha censo (IA)',
  nombre_comunidad:       'Nombre comunidad (IA)',
  pueblo_indigena:        'Pueblo indígena (IA/regex)',
  municipio:              'Municipio (IA/regex)',
  departamento:           'Departamento (IA/regex)',
  vereda:                 'Vereda (IA)',
  resguardo:              'Resguardo (IA)',
  representante_legal:    'Representante (IA)',
  nit:                    'NIT (IA/regex)',
  actividad_cultural:     'Actividad cultural (IA)',
  territorio_descripcion: 'Territorio (IA)',
  fuente_censo:           'Fuente censo (IA)',
  contrato_referencia:    'Contrato (IA)',
  discrepancia_poblacion: 'Discrepancia pob. (IA)',
  // spaCy NER
  ner_per:                'Personas (spaCy)',
  ner_org:                'Organizaciones (spaCy)',
  ner_loc:                'Lugares (spaCy)',
  ner_gpe:                'Lugares políticos (spaCy)',
  ner_misc:               'Miscelánea (spaCy)',
  // Regex
  fecha:                  'Fechas (regex)',
  poblacion:              'Población (regex)',
}

const AI_TIPOS = new Set([
  'familias_count','personas_count','fecha_censo','nombre_comunidad','pueblo_indigena',
  'municipio','departamento','vereda','resguardo','representante_legal','nit',
  'actividad_cultural','territorio_descripcion','fuente_censo','contrato_referencia',
  'discrepancia_poblacion',
])

export default function DebugPage() {
  const { id } = useParams<{ id: string }>()
  const [study, setStudy]         = useState<any>(null)
  const [corpus, setCorpus]       = useState<any[]>([])
  const [summary, setSummary]     = useState<any>(null)
  const [tick, setTick]           = useState(0)
  const [lastRefresh, setLastRefresh] = useState('')
  const [error, setError]         = useState<string | null>(null)
  const intervalRef               = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    if (!id) return
    try {
      const [s, c, sum] = await Promise.all([
        getStudy(id),
        getCorpusFiles(id),
        getExtractionSummary(id).catch(() => null),
      ])
      setStudy(s)
      setCorpus(c)
      setSummary(sum)
      setLastRefresh(new Date().toLocaleTimeString('es-CO'))
      setError(null)
    } catch (e: any) {
      setError(e?.message ?? 'Error conectando al backend')
    }
  }

  useEffect(() => {
    refresh()
    intervalRef.current = setInterval(() => {
      setTick(t => t + 1)
    }, 3000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [id])

  useEffect(() => { if (tick > 0) refresh() }, [tick])

  const estadoColor: Record<string, string> = {
    borrador:       '#6b7280',
    sincronizando:  '#3b82f6',
    corpus_ok:      '#10b981',
    procesando:     '#f59e0b',
    listo_revision: '#8b5cf6',
    en_revision:    '#06b6d4',
    aprobado:       '#10b981',
    exportado:      '#1d4ed8',
    error:          '#dc2626',
  }

  const corpusByEstado = corpus.reduce((acc: Record<string, number>, f: any) => {
    acc[f.estado] = (acc[f.estado] ?? 0) + 1
    return acc
  }, {})

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px', fontFamily: 'inherit' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <Link to={`/estudios/${id}/generar`} style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: 13 }}>
          ← Volver a Generar
        </Link>
        <span style={{ background: '#f59e0b', color: '#fff', borderRadius: 4, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>
          DEPURACIÓN TEMPORAL
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          Actualización automática cada 3 s · última: <strong>{lastRefresh || '…'}</strong>
        </span>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #dc2626', borderRadius: 6, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
          ✗ {error} — ¿está corriendo el backend en localhost:8000?
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Estado del estudio */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0 }}>Estado del estudio</span>
          </div>
          <div className="card-body" style={{ fontSize: 13 }}>
            {study ? (
              <>
                <div style={{ marginBottom: 8 }}>
                  <strong>{study.nombre_comunidad}</strong>{' '}
                  <span style={{ color: 'var(--text-muted)' }}>ID: {study.id?.slice(0, 8)}…</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <span>Estado:</span>
                  <span style={{
                    background: estadoColor[study.estado] ?? '#6b7280',
                    color: '#fff', borderRadius: 4, padding: '2px 10px',
                    fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
                  }}>{study.estado}</span>
                </div>
                {study.error_msg && (
                  <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 4, padding: 8, fontSize: 12, color: '#991b1b', marginBottom: 8 }}>
                    <strong>Error:</strong> {study.error_msg}
                  </div>
                )}
                <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                  Actualizado: {study.updated_at ? new Date(study.updated_at).toLocaleString('es-CO') : '—'}
                </div>
              </>
            ) : <div style={{ color: 'var(--text-muted)' }}>Cargando…</div>}
          </div>
        </div>

        {/* Estado del corpus */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0 }}>Archivos del corpus ({corpus.length})</span>
          </div>
          <div className="card-body" style={{ fontSize: 13 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
              {Object.entries(corpusByEstado).map(([est, count]) => (
                <span key={est} style={{
                  background: est === 'procesado' ? '#10b981' : est === 'error' ? '#dc2626' : est === 'descargado' ? '#3b82f6' : '#6b7280',
                  color: '#fff', borderRadius: 4, padding: '3px 10px', fontSize: 12,
                }}>
                  {est}: {count as number}
                </span>
              ))}
            </div>
            <div style={{ maxHeight: 200, overflowY: 'auto', fontSize: 11 }}>
              {corpus.map((f: any) => (
                <div key={f.id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '3px 0', borderBottom: '1px solid var(--border)',
                }}>
                  <span style={{ color: 'var(--text-muted)', maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.nombre_archivo}
                  </span>
                  <span style={{
                    background: f.estado === 'procesado' ? '#10b981' : f.estado === 'error' ? '#dc2626' : f.estado === 'descargado' ? '#3b82f6' : '#9ca3af',
                    color: '#fff', borderRadius: 3, padding: '1px 6px', fontSize: 10,
                  }}>{f.estado}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Extracciones */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="section-title" style={{ margin: 0 }}>
            Extracciones guardadas en BD
            {summary && (
              <span style={{ marginLeft: 8, background: '#1a3a5c', color: '#fff', borderRadius: 4, padding: '2px 10px', fontSize: 12 }}>
                {summary.total_extracciones} total
              </span>
            )}
          </span>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {summary
              ? summary.total_extracciones === 0
                ? '⚠ Cero extracciones — la IA no ha procesado nada todavía o los archivos no son procesables'
                : `✓ ${summary.total_extracciones} registros encontrados`
              : 'Cargando…'}
          </div>
        </div>
        <div className="card-body">
          {summary && summary.total_extracciones === 0 && (
            <div style={{ background: '#fffbeb', border: '1px solid #f59e0b', borderRadius: 6, padding: 12, marginBottom: 12, fontSize: 13 }}>
              <strong>¿Por qué cero extracciones?</strong> Puede significar:
              <ul style={{ margin: '6px 0 0 18px', lineHeight: 1.8 }}>
                <li>El proceso de extracción aún no ha terminado (sigue corriendo en el backend)</li>
                <li>Los archivos PDF son escaneados sin capa de texto — pdfplumber no puede leerlos</li>
                <li>La clave de Gemini es inválida o fue revocada — las llamadas a IA fallan silenciosamente</li>
                <li>El proceso terminó sin archivos procesables (revisa el estado del estudio arriba)</li>
              </ul>
            </div>
          )}
          {summary && summary.total_extracciones > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {Object.entries(summary.por_tipo as Record<string, string[]>).map(([tipo, valores]) => {
                const aiGenerated = AI_TIPOS.has(tipo)
                return (
                  <div key={tipo} style={{
                    border: '1px solid var(--border)', borderRadius: 6, padding: 10,
                    borderLeft: `3px solid ${aiGenerated ? '#8b5cf6' : '#3b82f6'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, fontSize: 12 }}>
                        {TIPO_LABELS[tipo] ?? tipo}
                      </span>
                      <div style={{ display: 'flex', gap: 4 }}>
                        {aiGenerated
                          ? <span style={{ background: '#8b5cf6', color: '#fff', borderRadius: 3, padding: '1px 5px', fontSize: 9, fontWeight: 700 }}>IA</span>
                          : <span style={{ background: '#3b82f6', color: '#fff', borderRadius: 3, padding: '1px 5px', fontSize: 9, fontWeight: 700 }}>spaCy</span>
                        }
                        <span style={{ background: '#6b7280', color: '#fff', borderRadius: 3, padding: '1px 5px', fontSize: 9 }}>
                          {valores.length}
                        </span>
                      </div>
                    </div>
                    <div style={{ maxHeight: 80, overflowY: 'auto' }}>
                      {valores.slice(0, 5).map((v, i) => (
                        <div key={i} style={{ fontSize: 11, color: 'var(--text-muted)', borderBottom: '1px solid var(--border)', padding: '2px 0' }}>
                          {v.length > 60 ? v.slice(0, 60) + '…' : v}
                        </div>
                      ))}
                      {valores.length > 5 && (
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', paddingTop: 2 }}>
                          …y {valores.length - 5} más
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Diagnóstico rápido */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <span className="section-title" style={{ margin: 0 }}>Diagnóstico rápido</span>
        </div>
        <div className="card-body" style={{ fontSize: 13, lineHeight: 2 }}>
          <div>
            {corpus.filter((f: any) => ['pdf','docx','doc'].includes(f.tipo_archivo)).length > 0
              ? <span style={{ color: '#10b981' }}>✓</span>
              : <span style={{ color: '#dc2626' }}>✗</span>
            }{' '}
            Hay {corpus.filter((f: any) => ['pdf','docx','doc'].includes(f.tipo_archivo)).length} archivos PDF/DOCX en el corpus
          </div>
          <div>
            {corpus.filter((f: any) => f.estado === 'descargado' && ['pdf','docx','doc'].includes(f.tipo_archivo)).length > 0
              ? <span style={{ color: '#10b981' }}>✓</span>
              : <span style={{ color: '#dc2626' }}>✗</span>
            }{' '}
            {corpus.filter((f: any) => f.estado === 'descargado' && ['pdf','docx','doc'].includes(f.tipo_archivo)).length} PDF/DOCX marcados como descargados en BD
          </div>
          <div>
            {summary && summary.total_extracciones > 0
              ? <span style={{ color: '#10b981' }}>✓</span>
              : <span style={{ color: '#f59e0b' }}>⚠</span>
            }{' '}
            {summary?.total_extracciones ?? 0} extracciones guardadas en BD
          </div>
          <div>
            {summary && Object.keys(summary.por_tipo ?? {}).some(k => ['familias_count','personas_count','representante_legal'].includes(k))
              ? <span style={{ color: '#10b981' }}>✓ IA está extrayendo datos estructurados</span>
              : <span style={{ color: '#dc2626' }}>✗ IA no ha generado datos — clave inválida, revocada, o AI_PROVIDER=none</span>
            }
          </div>
          <div style={{ marginTop: 8, padding: 10, background: 'var(--bg-alt)', borderRadius: 6, fontSize: 12 }}>
            <strong>Revisar en los logs del backend</strong> (terminal donde corre uvicorn):
            busca líneas con <code>[IA]</code> — si hay errores de autenticación, la clave de Gemini es inválida.
          </div>
        </div>
      </div>
    </div>
  )
}
