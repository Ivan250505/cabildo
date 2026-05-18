import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getStudy, getCorpusFiles, processCorpus, runGisAnalysis, generateReport, getReports } from '../api/studies'
import type { StudyDetail } from '../types'
import type { Report } from '../types'
import { toast } from '../lib/toast'

type GenStep = 'idle' | 'extracting' | 'gis' | 'writing' | 'done' | 'error'

const TIPO_ICON: Record<string, string> = {
  pdf: '📄', docx: '📝', xlsx: '📊', qgz: '🗺', gpkg: '🗄',
  shp: '📐', jpg: '🖼', heic: '🖼', mp4: '🎬', mp3: '🎙', otro: '📎',
}

export default function GenerarPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [step, setStep] = useState<GenStep>('idle')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [stepDetails, setStepDetails] = useState<Record<string, string>>({})
  const [elapsed, setElapsed] = useState(0)
  const genStartRef = useRef<number | null>(null)

  const { data: study, isLoading: studyLoading } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: corpus = [], isLoading: corpusLoading } = useQuery({
    queryKey: ['corpus', id],
    queryFn: () => getCorpusFiles(id!),
    enabled: !!id,
  })

  // Timer global desde que comienza la generación
  useEffect(() => {
    const isActive = step !== 'idle' && step !== 'done' && step !== 'error'
    if (!isActive) {
      genStartRef.current = null
      setElapsed(0)
      return
    }
    if (genStartRef.current === null) genStartRef.current = Date.now()
    const interval = setInterval(() => {
      if (genStartRef.current !== null) {
        setElapsed(Math.floor((Date.now() - genStartRef.current) / 1000))
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [step])

  if (studyLoading || corpusLoading) return <div className="loading-state">Cargando estudio…</div>

  if (!id || !study) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠</div>
        <p>Estudio no encontrado.</p>
        <Link to="/estudios" className="btn btn-outline" style={{ marginTop: 16 }}>← Volver</Link>
      </div>
    )
  }

  // Corpus stats
  const fase1 = corpus.filter((f: any) => f.fase === 'FASE1')
  const fase2 = corpus.filter((f: any) => f.fase === 'FASE2')
  const fase3 = corpus.filter((f: any) => f.fase === 'FASE3')
  const tieneCorpus = corpus.length > 0
  const tieneGpkg = corpus.some((f: any) => f.tipo_archivo === 'gpkg')
  const tieneQgz = corpus.some((f: any) => f.tipo_archivo === 'qgz')
  const tienePdf = corpus.some((f: any) => f.tipo_archivo === 'pdf')
  const tieneDocx = corpus.some((f: any) => f.tipo_archivo === 'docx')

  // Counts by tipo
  const porTipo: Record<string, number> = {}
  for (const f of corpus as any[]) {
    porTipo[f.tipo_archivo] = (porTipo[f.tipo_archivo] ?? 0) + 1
  }

  const canGenerate = tieneCorpus && step === 'idle' && !['procesando', 'sincronizando'].includes(study.estado)

  async function pollStudy(
    until: (s: StudyDetail) => boolean,
    timeout = 1_200_000,
  ): Promise<StudyDetail> {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 3000))
      const s = await getStudy(id!)
      if (s.estado === 'error') throw new Error(s.error_msg ?? 'Error procesando estudio')
      if (until(s)) return s
    }
    throw new Error('Tiempo de espera agotado (20 min). El proceso sigue corriendo en el servidor; recarga la página en unos minutos.')
  }

  async function pollReport(reportId: string, timeout = 1_200_000): Promise<Report> {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 3000))
      const reports = await getReports(id!)
      const r = reports.find(rep => rep.id === reportId)
      if (!r) continue
      if (r.estado === 'listo_revision' || r.estado === 'aprobado') return r
      if (r.estado === 'error') throw new Error(r.error_msg ?? 'Error generando informe')
    }
    throw new Error('Tiempo de espera agotado generando informe')
  }

  function formatElapsed(secs: number): string {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`
  }

  async function handleGenerate() {
    setStep('extracting')
    setErrorMsg(null)
    setStepDetails({})

    try {
      // Paso 1: Extracción documental (202 inmediato → polling hasta corpus_ok)
      await processCorpus(id!, false)
      const afterExtract = await pollStudy(
        s => !['procesando', 'sincronizando'].includes(s.estado),
      )
      setStepDetails(prev => ({
        ...prev,
        extracting: afterExtract.estado === 'corpus_ok'
          ? 'Corpus procesado correctamente'
          : `Estado: ${afterExtract.estado}`,
      }))

      // Paso 2: Análisis SIG (202 inmediato → polling hasta que salga de procesando)
      setStep('gis')
      if (tieneGpkg) {
        await runGisAnalysis(id!)
        const afterGis = await pollStudy(
          s => !['procesando'].includes(s.estado),
        )
        const omitido = afterGis.estado === 'corpus_ok'
        setStepDetails(prev => ({
          ...prev,
          gis: omitido ? 'Omitido (sin capas SIG disponibles)' : 'Análisis SIG completado',
        }))
      } else {
        setStepDetails(prev => ({ ...prev, gis: 'Omitido (sin archivos GPKG en corpus)' }))
      }

      // Paso 3: Generación del informe (202 inmediato → polling hasta listo_revision)
      setStep('writing')
      const pendingReport = await generateReport(id!)
      const finalReport = await pollReport(pendingReport.id)
      setStepDetails(prev => ({
        ...prev,
        writing: `Informe v${finalReport.version} generado`,
      }))

      setStep('done')
      toast.success('¡Informe generado!', 'Redirigiendo a la vista de revisión…')
      setTimeout(() => navigate(`/estudios/${id}/revision`), 1800)
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? err?.message ?? 'Error desconocido'
      setErrorMsg(msg)
      setStep('error')
      toast.error('Error en la generación', msg)
    }
  }

  const steps = [
    {
      key: 'extracting',
      label: 'Extracción documental',
      desc: 'Lee PDFs y DOCX del corpus · NLP + IA extraen datos estructurados',
      detail: stepDetails.extracting,
    },
    {
      key: 'gis',
      label: 'Análisis geoespacial',
      desc: 'Buffers 50 m · matrices de distancia · superposiciones territoriales',
      detail: stepDetails.gis,
    },
    {
      key: 'writing',
      label: 'Redacción con IA',
      desc: 'La IA escribe las secciones narrativas del estudio etnológico',
      detail: stepDetails.writing,
    },
  ]

  const stepOrder = ['extracting', 'gis', 'writing'] as const
  const currentIdx = stepOrder.indexOf(step as any)

  function stepStatus(key: string) {
    const idx = stepOrder.indexOf(key as any)
    if (step === 'done') return 'done'
    if (step === 'error' && idx === currentIdx) return 'error'
    if (idx < currentIdx) return 'done'
    if (idx === currentIdx) return 'active'
    return 'pending'
  }

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="page-title">Generar informe</div>
        <div className="page-sub">
          {study.nombre_comunidad}
          {study.pueblo_indigena && ` · Pueblo ${study.pueblo_indigena}`}
          {' · '}{study.municipio}, {study.departamento}
        </div>
      </div>

      <div className="two-col">
        {/* LEFT — Validación del corpus */}
        <div>
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>
                {tieneCorpus ? '✓ Corpus sincronizado' : '⚠ Sin corpus'}
              </span>
            </div>
            <div className="card-body">
              {!tieneCorpus ? (
                <div className="alert alert-warning">
                  No hay archivos sincronizados. Ve a la ficha del estudio y sincroniza el corpus desde Drive primero.
                </div>
              ) : (
                <>
                  {/* Conteo por fase */}
                  {[{ label: 'FASE 1 — Pre-campo', files: fase1 }, { label: 'FASE 2 — Campo', files: fase2 }, { label: 'FASE 3 — Post-campo', files: fase3 }].map(({ label, files }) => (
                    <div className={`corpus-item ${files.length > 0 ? 'ok' : 'warn'}`} key={label}>
                      <div>
                        <div className="corpus-label">📁 {label}</div>
                        <div className="corpus-count">{files.length} archivos</div>
                      </div>
                      <span className={`badge ${files.length > 0 ? 'badge-success' : 'badge-warning'}`}>
                        {files.length > 0 ? '✓' : '⚠ Vacío'}
                      </span>
                    </div>
                  ))}

                  <div className="divider" />

                  {/* Tipos detectados */}
                  <div className="corpus-label" style={{ marginBottom: 8 }}>Tipos detectados</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {Object.entries(porTipo).map(([tipo, count]) => (
                      <span key={tipo} className="badge badge-neutral" style={{ fontSize: 11 }}>
                        {TIPO_ICON[tipo] ?? '📎'} {tipo.toUpperCase()} ({count})
                      </span>
                    ))}
                  </div>

                  <div className="divider" />

                  {/* Capacidades disponibles */}
                  <div className={`corpus-item ${tienePdf || tieneDocx ? 'ok' : 'warn'}`}>
                    <div>
                      <div className="corpus-label">📄 Extracción documental</div>
                      <div className="corpus-count">PDF y DOCX procesables con NLP + IA</div>
                    </div>
                    <span className={`badge ${tienePdf || tieneDocx ? 'badge-success' : 'badge-warning'}`}>
                      {tienePdf || tieneDocx ? '✓' : '⚠'}
                    </span>
                  </div>
                  <div className={`corpus-item ${tieneGpkg || tieneQgz ? 'ok' : 'warn'}`}>
                    <div>
                      <div className="corpus-label">🗺 Análisis SIG</div>
                      <div className="corpus-count">
                        {tieneGpkg ? 'GeoPackage detectado' : tieneQgz ? 'Proyecto QGIS detectado' : 'Sin archivos geoespaciales — análisis SIG se omitirá'}
                      </div>
                    </div>
                    <span className={`badge ${tieneGpkg || tieneQgz ? 'badge-success' : 'badge-warning'}`}>
                      {tieneGpkg || tieneQgz ? '✓' : '⚠'}
                    </span>
                  </div>
                </>
              )}
            </div>
            {tieneCorpus && (
              <div className="card-footer">
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {corpus.length} archivos · Buffer SIG: {study.buffer_metros} m
                </span>
              </div>
            )}
          </div>

          {step === 'idle' && (
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Link to={`/estudios/${id}`} className="btn btn-outline" style={{ marginRight: 8 }}>
                ← Volver al estudio
              </Link>
              <button
                className="btn btn-primary btn-lg"
                disabled={!canGenerate}
                onClick={handleGenerate}
                title={!tieneCorpus ? 'Sincroniza el corpus desde Drive primero' : ''}
              >
                ⚡ Generar informe completo
              </button>
            </div>
          )}
        </div>

        {/* RIGHT — Progreso */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0 }}>
              {step === 'idle' ? 'Proceso de generación' : step === 'done' ? '✓ Informe generado' : step === 'error' ? '✗ Error en la generación' : '⚡ Generando informe…'}
            </span>
          </div>
          <div className="card-body">
            <div className="steps">
              {steps.map((s) => {
                const status = stepStatus(s.key)
                return (
                  <div className={`step ${status}`} key={s.key}>
                    <div className="step-icon">
                      {status === 'done' ? '✓' : status === 'active' ? '◷' : status === 'error' ? '✗' : steps.indexOf(s) + 1}
                    </div>
                    <div className="step-content">
                      <div className="step-name">{s.label}</div>
                      <div className="step-detail">
                        {s.detail ?? s.desc}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {step === 'error' && errorMsg && (
              <div className="alert alert-danger" style={{ marginTop: 16 }}>
                <strong>Error:</strong> {errorMsg}
                <br />
                <button className="btn btn-outline btn-sm" style={{ marginTop: 8 }} onClick={() => setStep('idle')}>
                  Reintentar
                </button>
              </div>
            )}

            {step === 'done' && (
              <div className="alert alert-success" style={{ marginTop: 16 }}>
                Informe generado. Redirigiendo a la revisión…
              </div>
            )}

            {step !== 'idle' && step !== 'error' && step !== 'done' && (
              <div style={{ marginTop: 16 }}>
                <div className="progress-bar-wrap" style={{ height: 6 }}>
                  <div
                    className="progress-bar"
                    style={{
                      width: step === 'extracting' ? '33%' : step === 'gis' ? '66%' : '90%',
                      transition: 'width 0.5s ease',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>⏱ {formatElapsed(elapsed)} transcurridos</span>
                  <span>El proceso puede tomar 5–20 min</span>
                </div>
              </div>
            )}

            {step === 'idle' && (
              <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>
                <p>El proceso corre los tres pasos en secuencia. El tiempo depende del tamaño del corpus y del proveedor de IA configurado.</p>
                {!tieneCorpus && (
                  <div className="alert alert-warning" style={{ marginTop: 8 }}>
                    Debes sincronizar el corpus desde Drive antes de generar el informe.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
