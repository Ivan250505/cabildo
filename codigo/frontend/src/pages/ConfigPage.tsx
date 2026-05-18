import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getDriveStatus, getDriveAuthUrl, revokeDrive } from '../api/drive'
import { toast } from '../lib/toast'

const CONFIG_KEY = 'etnosia_config'

interface LocalConfig {
  bufferMetros: number
  escalaMapas: string
  formatoExportacion: string
}

function loadConfig(): LocalConfig {
  try {
    const raw = localStorage.getItem(CONFIG_KEY)
    if (raw) return { ...defaultConfig(), ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return defaultConfig()
}

function defaultConfig(): LocalConfig {
  return { bufferMetros: 50, escalaMapas: '1:10.000', formatoExportacion: 'PNG 300 dpi' }
}

export default function ConfigPage() {
  const queryClient = useQueryClient()
  const [config, setConfig] = useState<LocalConfig>(loadConfig)
  const [saved, setSaved] = useState(false)

  // Recargar si otra pestaña cambia localStorage
  useEffect(() => {
    const handler = () => setConfig(loadConfig())
    window.addEventListener('storage', handler)
    return () => window.removeEventListener('storage', handler)
  }, [])

  const { data: driveStatus, isLoading: driveLoading } = useQuery({
    queryKey: ['drive-status'],
    queryFn: getDriveStatus,
    retry: false,
  })

  const revokeMutation = useMutation({
    mutationFn: revokeDrive,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drive-status'] })
      toast.info('Google Drive desconectado', 'Puedes volver a conectarlo cuando quieras.')
    },
  })

  async function handleConnectDrive() {
    try {
      const { url } = await getDriveAuthUrl()
      window.location.href = url
    } catch {
      toast.error('Error de conexión', 'No se pudo obtener la URL de autorización de Google Drive.')
    }
  }

  function handleSaveConfig() {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="page-title">Configuración</div>
        <div className="page-sub">Parámetros globales de la plataforma</div>
      </div>

      <div className="two-col">
        <div>
          {/* SIG params */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Parámetros SIG globales</span>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Buffer por defecto (metros)</label>
                <input
                  className="form-input"
                  type="number"
                  min={10}
                  max={500}
                  value={config.bufferMetros}
                  onChange={e => setConfig(c => ({ ...c, bufferMetros: Number(e.target.value) }))}
                />
                <div className="form-hint">
                  Se usará como valor inicial al crear nuevos estudios. Buffer estándar Ministerio: 50 m.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Sistema de referencia de coordenadas</label>
                <input className="form-input" value="WGS84 — EPSG:4326" readOnly />
                <div className="form-hint">Fijo por normativa IGAC.</div>
              </div>

              <div className="form-group">
                <label className="form-label">Escala de mapas temáticos</label>
                <select
                  className="form-select"
                  value={config.escalaMapas}
                  onChange={e => setConfig(c => ({ ...c, escalaMapas: e.target.value }))}
                >
                  <option>1:5.000</option>
                  <option>1:10.000</option>
                  <option>1:25.000</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Formato exportación de mapas</label>
                <select
                  className="form-select"
                  value={config.formatoExportacion}
                  onChange={e => setConfig(c => ({ ...c, formatoExportacion: e.target.value }))}
                >
                  <option>PNG 300 dpi</option>
                  <option>SVG</option>
                  <option>PDF</option>
                </select>
              </div>
            </div>
            <div className="card-footer" style={{ textAlign: 'right' }}>
              {saved && (
                <span className="badge badge-success" style={{ marginRight: 10 }}>✓ Guardado</span>
              )}
              <button className="btn btn-primary btn-sm" onClick={handleSaveConfig}>
                Guardar cambios
              </button>
            </div>
          </div>

          {/* Google Drive */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Integración Google Drive</span>
            </div>
            <div className="card-body">
              {driveLoading ? (
                <div className="loading-state" style={{ padding: 12 }}>Verificando conexión…</div>
              ) : driveStatus?.connected ? (
                <>
                  <div className="alert alert-success" style={{ marginBottom: 12 }}>
                    ✓ Cuenta conectada · {driveStatus.google_email ?? 'Google Account'}
                  </div>
                  <p className="form-hint" style={{ marginBottom: 12 }}>
                    Esta cuenta se usa para sincronizar el corpus de todos los estudios.
                  </p>
                  {revokeMutation.isError && (
                    <div className="alert alert-danger" style={{ marginBottom: 8 }}>
                      Error al desconectar. Intenta de nuevo.
                    </div>
                  )}
                  <button
                    className="btn btn-outline btn-sm"
                    disabled={revokeMutation.isPending}
                    onClick={() => {
                      if (confirm('¿Desconectar la cuenta de Google? Deberás volver a autorizar para sincronizar Drive.')) {
                        revokeMutation.mutate()
                      }
                    }}
                  >
                    {revokeMutation.isPending ? 'Desconectando…' : 'Desconectar cuenta'}
                  </button>
                </>
              ) : (
                <>
                  <div className="alert alert-warning" style={{ marginBottom: 12 }}>
                    Sin cuenta de Google conectada. La sincronización de corpus no estará disponible.
                  </div>
                  <button className="btn btn-primary btn-sm" onClick={handleConnectDrive}>
                    Conectar con Google Drive
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Plantilla institucional */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0 }}>Plantilla institucional del informe</span>
          </div>
          <div className="card-body">
            <div className="alert alert-info" style={{ marginBottom: 12 }}>
              ℹ La plantilla Word institucional está integrada directamente en el generador de informes.
              La versión actual usa los colores y estructura aprobados por el Ministerio del Interior.
            </div>
            <div className="corpus-item ok" style={{ marginBottom: 8 }}>
              <div>
                <div className="corpus-label">Plantilla institucional integrada</div>
                <div className="corpus-count">
                  Colores: Rojo #B22222 · Azul #1A3A5C · Dorado #C8922A
                </div>
              </div>
              <span className="badge badge-success">Activa</span>
            </div>
            <div className="corpus-item ok" style={{ marginBottom: 8 }}>
              <div>
                <div className="corpus-label">Secciones generadas</div>
                <div className="corpus-count">
                  Portada · Marco legal · Info general · Historia · Caracterización etnológica · Análisis SIG · Conclusiones
                </div>
              </div>
              <span className="badge badge-success">✓</span>
            </div>
            <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
              La carga de plantillas personalizadas estará disponible en una versión futura.
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
