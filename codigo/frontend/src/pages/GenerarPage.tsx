import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

type StepStatus = 'done' | 'active' | 'pending'

const STEPS: { name: string; detail: string }[] = [
  { name: 'Sincronización del corpus', detail: '62 archivos · 1.4 GB · 14 s' },
  { name: 'Lectura de capas SIG', detail: '4 capas · 127 puntos · ETNIA1_CABILDO_MURUI.qgz' },
  { name: 'Análisis geoespacial', detail: 'Buffers 50 m · 6 matrices de distancia · 6 superposiciones… 65%' },
  { name: 'Extracción documental', detail: 'PDFs, DOCX, XLSX — spaCy NER español' },
  { name: 'Módulos analíticos', detail: 'Discrepancias · DANE · Red de actores · Línea de tiempo' },
  { name: 'Ensamblado del informe', detail: 'Plantilla institucional Word · Mapas + tablas + textos' },
  { name: 'Exportación y registro', detail: 'Informe_MuruiMuina_v1.docx · Trazabilidad guardada' },
]

function getStepStatus(index: number, activeStep: number): StepStatus {
  if (index < activeStep) return 'done'
  if (index === activeStep) return 'active'
  return 'pending'
}

export default function GenerarPage() {
  const [generating, setGenerating] = useState(false)
  const [activeStep] = useState(2)
  const [buffer, setBuffer] = useState('50')
  const [layers, setLayers] = useState([true, true, true, true])
  const [modules, setModules] = useState([true, true, true, true])
  const navigate = useNavigate()

  function handleGenerate() {
    setGenerating(true)
  }

  function toggleLayer(i: number) {
    setLayers((prev) => prev.map((v, idx) => (idx === i ? !v : v)))
  }

  function toggleModule(i: number) {
    setModules((prev) => prev.map((v, idx) => (idx === i ? !v : v)))
  }

  const LAYER_NAMES = ['Prácticas Culturales (34 puntos)', 'Expresiones Simbólicas (28 puntos)', 'Entornos Territoriales (39 puntos)', 'Procesos Organizativos (26 puntos)']
  const MODULE_NAMES = ['Validación de discrepancias poblacionales', 'Cruce con datos abiertos DANE', 'Red de actores clave', 'Línea de tiempo de eventos organizativos']

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="page-title">Generar informe</div>
        <div className="page-sub">Cabildo Indígena Murui Muina · Configuración y validación del corpus</div>
      </div>

      <div className="two-col">
        {/* LEFT — Parámetros */}
        <div>
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>⚙ Parámetros de generación</span>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Estudio</label>
                <input className="form-input" value="Cabildo Indígena Murui Muina" readOnly />
              </div>

              <div className="form-group">
                <label className="form-label">Buffer de influencia (metros)</label>
                <input className="form-input" type="number" value={buffer} onChange={(e) => setBuffer(e.target.value)} />
                <div className="form-hint">Buffer estándar Ministerio del Interior: 50 m</div>
              </div>

              <div className="form-group">
                <label className="form-label">Capas SIG a procesar</label>
                <div className="checkbox-group">
                  {LAYER_NAMES.map((name, i) => (
                    <div className="checkbox-item" key={name}>
                      <input type="checkbox" id={`layer-${i}`} checked={layers[i]} onChange={() => toggleLayer(i)} />
                      <label htmlFor={`layer-${i}`}>{name}</label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="divider" />

              <div className="form-group">
                <label className="form-label">Módulos analíticos de valor agregado</label>
                <div className="checkbox-group">
                  {MODULE_NAMES.map((name, i) => (
                    <div className="checkbox-item" key={name}>
                      <input type="checkbox" id={`mod-${i}`} checked={modules[i]} onChange={() => toggleModule(i)} />
                      <label htmlFor={`mod-${i}`}>{name}</label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="divider" />

              <div className="form-group">
                <label className="form-label">Formato de salida</label>
                <select className="form-select">
                  <option>Word (.docx) — Estándar institucional</option>
                  <option>PDF (solo visualización)</option>
                </select>
              </div>
            </div>

            <div className="card-footer" style={{ textAlign: 'right' }}>
              <button className="btn btn-outline btn-sm" style={{ marginRight: 8 }}>Vista previa del corpus</button>
              <button className="btn btn-primary btn-lg" onClick={handleGenerate} disabled={generating}>
                ⚡ Generar informe completo
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT — Validación / Progreso */}
        <div>
          {!generating ? (
            <div className="card">
              <div className="card-header"><span className="section-title" style={{ margin: 0 }}>✓ Validación del corpus</span></div>
              <div className="card-body">
                {[
                  { label: '📁 FASE 1 — Pre-campo', count: '14 de 14 archivos encontrados', ok: true },
                  { label: '📁 FASE 2 — Campo', count: '46 de 46 archivos encontrados', ok: true },
                  { label: '📁 FASE 3 — Post-campo', count: '1 de 2 archivos (falta Acto administrativo firmado)', ok: false },
                  { label: '🗺 Proyecto QGIS', count: 'ETNIA1_CABILDO_MURUI.qgz detectado', ok: true },
                  { label: '🗄 GeoPackage', count: 'Archivo .gpkg detectado y legible', ok: true },
                  { label: '✦ Capas SIG', count: '4 capas · 127 puntos georreferenciados', ok: true },
                  { label: '📊 Autocenso', count: 'Autocenso_Murui Muina.xlsx · 98 personas, 27 familias', ok: true },
                  { label: '⚠ Discrepancia poblacional', count: 'Autocenso vs. Censo Ministerio: diferencia de 3 familias', ok: false },
                ].map((item) => (
                  <div className={`corpus-item ${item.ok ? 'ok' : 'warn'}`} key={item.label}>
                    <div>
                      <div className="corpus-label">{item.label}</div>
                      <div className="corpus-count">{item.count}</div>
                    </div>
                    <span className={`badge ${item.ok ? 'badge-success' : 'badge-warning'}`}>
                      {item.ok ? '✓ Completo' : '⚠ Revisar'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="card-header">
                <span className="section-title" style={{ margin: 0 }}>⚡ Generando informe...</span>
                <span className="text-sm text-muted">~8 min estimados</span>
              </div>
              <div className="card-body">
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: 'var(--text-muted)' }}>
                    <span>Progreso general</span><span>65%</span>
                  </div>
                  <div className="progress-bar-wrap" style={{ height: 8 }}>
                    <div className="progress-bar" style={{ width: '65%' }} />
                  </div>
                </div>

                <div className="steps">
                  {STEPS.map((step, i) => {
                    const status = getStepStatus(i, activeStep)
                    return (
                      <div className={`step ${status}`} key={step.name}>
                        <div className="step-icon">
                          {status === 'done' ? '✓' : status === 'active' ? '◷' : i + 1}
                        </div>
                        <div className="step-content">
                          <div className="step-name">{step.name}</div>
                          <div className="step-detail">{step.detail}</div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="divider" />
                <button
                  className="btn btn-success btn-full"
                  onClick={() => navigate('/estudios/1/revision')}
                >
                  ✓ Ver informe generado
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
