import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import IndigenousDivider from '../components/IndigenousDivider'
import { getStudy, getReports, generateReport, approveReport, downloadReportBlob, getExtractions } from '../api/studies'
import type { Extraction } from '../api/studies'
import type { Report } from '../types'

const TOC_ITEMS = [
  { id: 's1', label: '1. Portada institucional', ok: true, warn: false },
  { id: 's2', label: '2. Vista general comunidad', ok: true, warn: false },
  { id: 's3', label: '3. Contexto territorial', ok: true, warn: false },
  { id: 's4a', label: '4.1 Prácticas Culturales', ok: true, warn: false, sub: true },
  { id: 's4b', label: '4.2 Expresiones Simbólicas', ok: true, warn: false, sub: true },
  { id: 's4c', label: '4.3 Entornos Territoriales', ok: true, warn: false, sub: true },
  { id: 's4d', label: '4.4 Procesos Organizativos', ok: true, warn: false, sub: true },
  { id: 's5a', label: '5.1 Buffers de influencia', ok: true, warn: false, sub: true },
  { id: 's5b', label: '5.2 Matrices de distancia', ok: true, warn: false, sub: true },
  { id: 's5c', label: '5.3 Superposiciones territoriales', ok: true, warn: false, sub: true },
  { id: 's6a', label: '6.1 Discrepancias poblacionales', ok: false, warn: true, sub: true },
  { id: 's6b', label: '6.2 Cruce con DANE', ok: true, warn: false, sub: true },
  { id: 's6c', label: '6.3 Red de actores', ok: true, warn: false, sub: true },
  { id: 's6d', label: '6.4 Línea de tiempo', ok: true, warn: false, sub: true },
  { id: 's7', label: '7. Evidencia documental', ok: true, warn: false },
  { id: 's8', label: '8. Anexos cartográficos', ok: true, warn: false },
  { id: 's9', label: '9. Referencias', ok: true, warn: false },
]

const SECTION_HEADERS: Record<string, string> = {
  s4a: '4. Análisis SIG por capa',
  s5a: '5. Análisis espacial integrado',
  s6a: '6. Módulos de valor agregado',
}

// Agrupa las extracciones poblacionales por archivo fuente y arma las filas de la tabla
function buildPoblacionRows(extractions: Extraction[]) {
  const byFile: Record<string, Record<string, string>> = {}
  for (const e of extractions) {
    if (!['familias_count', 'personas_count', 'fecha_censo', 'fuente_censo'].includes(e.tipo_dato)) continue
    const file = e.fuente_archivo ?? 'Desconocido'
    if (!byFile[file]) byFile[file] = {}
    if (!byFile[file][e.tipo_dato]) byFile[file][e.tipo_dato] = e.valor ?? ''
  }
  return Object.entries(byFile).map(([file, vals]) => ({
    fuente: vals['fuente_censo'] ?? file.replace(/\.[^.]+$/, ''),
    familias: vals['familias_count'] ?? '—',
    personas: vals['personas_count'] ?? '—',
    fecha: vals['fecha_censo'] ?? '—',
  }))
}

function PoblacionTable({ extractions }: { extractions: Extraction[] }) {
  const rows = buildPoblacionRows(extractions)

  if (!rows.length) {
    return (
      <p className="doc-p" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
        Sin datos poblacionales extraídos. Ejecuta el proceso de extracción documental para poblar esta sección.
      </p>
    )
  }

  const valores = rows.map(r => parseInt(r.familias) || 0).filter(Boolean)
  const max = Math.max(...valores)
  const min = Math.min(...valores)
  const hayDiscrepancia = valores.length > 1 && max !== min

  return (
    <>
      <table className="doc-table">
        <thead>
          <tr><th>Fuente</th><th>Familias</th><th>Personas</th><th>Fecha</th><th>Estado</th></tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const fam = parseInt(row.familias) || 0
            const esDivergente = hayDiscrepancia && fam === max && i > 0
            return (
              <tr key={i} className={esDivergente ? 'discrepancy' : ''}>
                <td>{row.fuente}</td>
                <td>{esDivergente ? <span className="highlight-warn">{row.familias}</span> : row.familias}</td>
                <td>{esDivergente ? <span className="highlight-warn">{row.personas}</span> : row.personas}</td>
                <td>{row.fecha}</td>
                <td>{esDivergente ? '⚠ Diferencia' : '✓'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {hayDiscrepancia && (
        <p className="doc-p">
          Se identifican <strong>discrepancias en el número de familias</strong> entre las fuentes del corpus.
          Diferencia máxima: {max - min} familias.
        </p>
      )}
    </>
  )
}

function latestReport(reports: Report[]): Report | null {
  if (!reports.length) return null
  return reports.reduce((a, b) => (a.version > b.version ? a : b))
}

export default function RevisionPage() {
  const { id } = useParams<{ id: string }>()
  const [activeSection, setActiveSection] = useState('s1')
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: study, isLoading } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: reports = [], isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', id],
    queryFn: () => getReports(id!),
    enabled: !!id && !!study,
  })

  const { data: extractions = [] } = useQuery({
    queryKey: ['extractions', id],
    queryFn: () => getExtractions(id!),
    enabled: !!id && !!study,
  })

  const generateMutation = useMutation({
    mutationFn: () => generateReport(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', id] })
      queryClient.invalidateQueries({ queryKey: ['study', id] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: (reportId: string) => approveReport(id!, reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', id] })
      queryClient.invalidateQueries({ queryKey: ['study', id] })
    },
  })

  const handleDownload = async (report: Report) => {
    setDownloadError(null)
    try {
      const { blob, filename } = await downloadReportBlob(id!, report.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setDownloadError('No se pudo descargar el archivo. Intenta de nuevo.')
    }
  }

  if (isLoading || reportsLoading) return <div className="loading-state">Cargando estudio…</div>

  if (!id || !study) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📄</div>
        <p>Selecciona un estudio para revisar su informe.</p>
        <Link to="/estudios" className="btn btn-outline" style={{ marginTop: 16 }}>
          ← Ver estudios
        </Link>
      </div>
    )
  }

  const estadosConInforme = ['listo_revision', 'en_revision', 'aprobado', 'exportado']
  const tieneInforme = estadosConInforme.includes(study.estado)

  if (!tieneInforme) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⏳</div>
        <p><strong>{study.nombre_comunidad}</strong></p>
        <p className="text-sm text-muted" style={{ marginTop: 8 }}>
          El informe aún no está disponible para revisión.
          El estudio está en estado <strong>{study.estado}</strong>.
        </p>
        <p className="text-sm text-muted">
          Primero sincroniza el corpus desde Drive y luego genera el informe.
        </p>
        <Link to={`/estudios/${id}`} className="btn btn-outline" style={{ marginTop: 16 }}>
          ← Volver al estudio
        </Link>
      </div>
    )
  }

  const report = latestReport(reports)

  if (!report) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📝</div>
        <p><strong>{study.nombre_comunidad}</strong></p>
        <p className="text-sm text-muted" style={{ marginTop: 8 }}>
          El estudio está listo pero aún no se ha generado el informe Word.
        </p>
        {generateMutation.isError && (
          <div className="alert alert-danger" style={{ marginTop: 12 }}>
            Error al generar el informe. Intenta de nuevo.
          </div>
        )}
        <button
          className="btn btn-primary"
          style={{ marginTop: 16 }}
          disabled={generateMutation.isPending}
          onClick={() => generateMutation.mutate()}
        >
          {generateMutation.isPending ? 'Generando…' : 'Generar informe'}
        </button>
        <Link to={`/estudios/${id}`} className="btn btn-outline" style={{ marginTop: 8 }}>
          ← Volver al estudio
        </Link>
      </div>
    )
  }

  const today = new Date().toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })
  const docName = `Informe_${study.nombre_comunidad.replace(/\s+/g, '')}_v${report.version}.docx`
  const yaAprobado = report.estado === 'aprobado' || report.estado === 'exportado'

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="page-title">Revisión del informe</div>
          <div className="page-sub">
            {docName} · Generado {today} · v{report.version}
            {yaAprobado && <span className="badge badge-success" style={{ marginLeft: 8 }}>Aprobado</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Link to={`/estudios/${id}`} className="btn btn-outline">← Volver</Link>

          <button
            className="btn btn-outline"
            onClick={() => handleDownload(report)}
          >
            ⬇ Descargar .docx
          </button>

          {report.drive_url && (
            <a
              href={report.drive_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-outline"
            >
              📄 Ver PDF en Drive
            </a>
          )}

          {!yaAprobado && (
            <button
              className="btn btn-success btn-lg"
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate(report.id)}
            >
              {approveMutation.isPending ? 'Aprobando…' : '✓ Aprobar y exportar versión final'}
            </button>
          )}
        </div>
      </div>

      {downloadError && (
        <div className="alert alert-danger" style={{ marginBottom: 12 }}>{downloadError}</div>
      )}
      {approveMutation.isError && (
        <div className="alert alert-danger" style={{ marginBottom: 12 }}>
          Error al aprobar el informe. Intenta de nuevo.
        </div>
      )}
      {approveMutation.isSuccess && (
        <div className="alert alert-success" style={{ marginBottom: 12 }}>
          Informe aprobado correctamente.
        </div>
      )}

      <div className="col-left-sm">
        {/* TOC */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0, fontSize: 13 }}>Índice del informe</span>
          </div>
          <div className="card-body" style={{ padding: 12 }}>
            <div className="report-toc">
              {TOC_ITEMS.map((item) => {
                const showHeader = SECTION_HEADERS[item.id]
                return (
                  <div key={item.id}>
                    {showHeader && <div className="toc-section">{showHeader}</div>}
                    <div
                      className={`toc-item${item.sub ? ' toc-sub' : ''}${activeSection === item.id ? ' active' : ''}${item.warn ? ' warn' : ''}`}
                      onClick={() => setActiveSection(item.id)}
                    >
                      <span>{item.label}</span>
                      <span className={`badge ${item.warn ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: 10 }}>
                        {item.warn ? '⚠' : '✓'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="card-footer">
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
              16/17 secciones aprobadas · 1 requiere revisión
            </div>
          </div>
        </div>

        {/* Document preview */}
        <div>
          <div className="alert alert-warning" style={{ marginBottom: 12 }}>
            ⚠&nbsp;<div><strong>Sección 6.1 requiere revisión:</strong> Se detectó discrepancia entre fuentes poblacionales. Verifique y confirme la nota aclaratoria antes de aprobar.</div>
          </div>

          <div className="doc-preview">
            <div className="doc-h1">ESTUDIO ETNOLÓGICO<br />{study.nombre_comunidad.toUpperCase()}</div>
            <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>
              Ministerio del Interior · Dirección de Asuntos Indígenas · {today}
            </div>

            <IndigenousDivider patternId="doc-revision-div" variant="wayuu" />

            <div className="doc-h2">6.1 Validación de discrepancias entre fuentes poblacionales</div>
            <p className="doc-p">
              Con el fin de garantizar la consistencia de la información demográfica de {study.nombre_comunidad},
              el sistema realizó el cruce automático de las fuentes disponibles en el corpus:
            </p>

            <PoblacionTable extractions={extractions} />

            {(() => {
              const discrepancias = extractions.filter(e => e.tipo_dato === 'discrepancia_poblacion')
              if (!discrepancias.length) return null
              return (
                <div style={{ background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 'var(--radius)', padding: 12, fontSize: 12.5, color: '#92400e', margin: '12px 0' }}>
                  <strong>⚠ Discrepancias detectadas:</strong>
                  {discrepancias.map((d, i) => (
                    <div key={i} style={{ marginTop: 4 }}>{d.valor}</div>
                  ))}
                  <br />
                  <em>[El responsable técnico debe validar esta información antes de aprobar el informe]</em>
                </div>
              )
            })()}

            <div className="doc-h2">6.2 Cruce con datos abiertos del DANE</div>
            <p className="doc-p">
              Según el Censo Nacional de Población y Vivienda 2018 (DANE), el municipio de {study.municipio} — {study.departamento} registra
              una población registrada. El cabildo {study.nombre_comunidad} pertenece al pueblo {study.pueblo_indigena ?? 'indígena'} y
              se encuentra en proceso de reconocimiento formal ante la DAIRM del Ministerio del Interior.
            </p>
          </div>
        </div>
      </div>
    </>
  )
}
