import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import IndigenousDivider from '../components/IndigenousDivider'
import { getStudy } from '../api/studies'

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

export default function RevisionPage() {
  const { id } = useParams<{ id: string }>()
  const [activeSection, setActiveSection] = useState('s1')

  const { data: study, isLoading } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  if (isLoading) return <div className="loading-state">Cargando estudio…</div>

  // Si no hay id de estudio, mostrar estado vacío
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

  // Verificar si el estudio tiene informe listo para revisión
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

  // Informe disponible — mostrar revisor
  const today = new Date().toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' })
  const docName = `Informe_${study.nombre_comunidad.replace(/\s+/g, '')}_v1.docx`

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="page-title">Revisión del informe</div>
          <div className="page-sub">
            {docName} · Generado {today} · 47 páginas
          </div>
        </div>
        <div className="flex gap-2">
          <Link to={`/estudios/${id}`} className="btn btn-outline">← Volver</Link>
          <button className="btn btn-outline">⬇ Descargar borrador .docx</button>
          <button className="btn btn-success btn-lg">✓ Aprobar y exportar versión final</button>
        </div>
      </div>

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
              el sistema realizó el cruce automático de las cuatro fuentes disponibles en el corpus:
            </p>

            <table className="doc-table">
              <thead>
                <tr><th>Fuente</th><th>Familias</th><th>Personas</th><th>Fecha</th><th>Estado</th></tr>
              </thead>
              <tbody>
                <tr><td>Censo del Ministerio del Interior</td><td>24</td><td>89</td><td>2024</td><td>✓ Oficial</td></tr>
                <tr className="discrepancy">
                  <td>Autocenso comunitario</td>
                  <td><span className="highlight-warn">27</span></td>
                  <td><span className="highlight-warn">98</span></td>
                  <td>2025</td>
                  <td>⚠ Diferencia</td>
                </tr>
                <tr><td>Derecho de petición (solicitud)</td><td>25</td><td>92</td><td>2025</td><td>✓</td></tr>
                <tr><td>Registros del cabildo (actas)</td><td>26</td><td>95</td><td>2025</td><td>✓</td></tr>
              </tbody>
            </table>

            <p className="doc-p">
              Se identifican <strong>discrepancias en el número de familias</strong> entre el Censo del Ministerio (24 familias / 89 personas)
              y el autocenso comunitario más reciente (27 familias / 98 personas), con una diferencia de 3 familias y 9 personas.
            </p>

            <div style={{ background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 'var(--radius)', padding: 12, fontSize: 12.5, color: '#92400e', margin: '12px 0' }}>
              <strong>⚠ Nota aclaratoria generada automáticamente:</strong> La diferencia puede explicarse por nacimientos
              posteriores al último corte censal del Ministerio (2024) y por el ingreso de 3 familias que se han autoreconocido
              como parte del colectivo en el período 2024-2025. Se recomienda al responsable técnico validar y complementar esta nota.
              <br /><br />
              <em>[El responsable técnico puede editar esta nota antes de aprobar el informe]</em>
            </div>

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
