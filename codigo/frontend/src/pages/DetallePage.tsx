import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, LayerGroup, Popup } from 'react-leaflet'
import IndigenousDivider from '../components/IndigenousDivider'
import { getStudy, getCorpusFiles, updateStudy } from '../api/studies'
import { getDriveStatus, getDriveAuthUrl, syncStudy, type StudySyncResponse } from '../api/drive'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import type { StudyEstado } from '../types'

const TABS = ['📁 FASE 1 — Pre-campo', '📁 FASE 2 — Campo', '📁 FASE 3 — Post-campo', '☁ Google Drive']

const TIPO_ICON: Record<string, string> = {
  pdf: '📄', docx: '📝', xlsx: '📊', qgz: '🗺', gpkg: '🗄',
  shp: '📐', jpg: '🖼', heic: '🖼', mp4: '🎬', mp3: '🎙',
}

/* Demo SIG points used until real GIS processing is done */
const DEMO_LAYERS = [
  { name: 'Prácticas Culturales', color: '#B22222', points: [[1.618,-75.611],[1.612,-75.607],[1.622,-75.614]] as [number,number][] },
  { name: 'Expresiones Simbólicas', color: '#16a34a', points: [[1.620,-75.603],[1.614,-75.600],[1.617,-75.608]] as [number,number][] },
  { name: 'Entornos Territoriales', color: '#C8922A', points: [[1.607,-75.610],[1.613,-75.602],[1.621,-75.619]] as [number,number][] },
  { name: 'Procesos Organizativos', color: '#1A3A5C', points: [[1.615,-75.613],[1.619,-75.601],[1.623,-75.610]] as [number,number][] },
]

export default function DetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(0)
  const [driveUrls, setDriveUrls] = useState({ fase1: '', fase2: '', fase3: '' })
  const [syncResult, setSyncResult] = useState<StudySyncResponse | null>(null)
  const [urlsSaved, setUrlsSaved] = useState(false)

  const { data: study, isLoading, isError } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: corpus = [] } = useQuery({
    queryKey: ['corpus', id],
    queryFn: () => getCorpusFiles(id!),
    enabled: !!id,
  })

  const { data: driveStatus } = useQuery({
    queryKey: ['drive-status'],
    queryFn: getDriveStatus,
    retry: false,
  })

  useEffect(() => {
    if (study) {
      setDriveUrls({
        fase1: study.url_drive_fase1 ?? '',
        fase2: study.url_drive_fase2 ?? '',
        fase3: study.url_drive_fase3 ?? '',
      })
    }
  }, [study])

  const saveUrlsMutation = useMutation({
    mutationFn: () => updateStudy(id!, {
      url_drive_fase1: driveUrls.fase1 || undefined,
      url_drive_fase2: driveUrls.fase2 || undefined,
      url_drive_fase3: driveUrls.fase3 || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['study', id] })
      setUrlsSaved(true)
      setTimeout(() => setUrlsSaved(false), 3000)
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => syncStudy(id!),
    onSuccess: (result) => {
      setSyncResult(result)
      queryClient.invalidateQueries({ queryKey: ['corpus', id] })
      queryClient.invalidateQueries({ queryKey: ['study', id] })
    },
  })

  async function handleConnectDrive() {
    try {
      const { url } = await getDriveAuthUrl()
      window.location.href = url
    } catch {
      alert('No se pudo obtener la URL de autorización de Google Drive.')
    }
  }

  if (isLoading) return <div className="loading-state">Cargando estudio…</div>
  if (isError || !study) return (
    <div className="empty-state">
      <div className="empty-state-icon">⚠</div>
      <p>Estudio no encontrado.</p>
      <Link to="/estudios" className="btn btn-outline" style={{ marginTop: 16 }}>← Volver a estudios</Link>
    </div>
  )

  const fase1 = corpus.filter((f: any) => f.fase === 'FASE1')
  const fase2 = corpus.filter((f: any) => f.fase === 'FASE2')
  const fase3 = corpus.filter((f: any) => f.fase === 'FASE3')

  const mapCenter: [number, number] = study.lat && study.lng
    ? [study.lat, study.lng]
    : [1.6144, -75.6062]

  return (
    <>
      {/* Header */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body">
          <div className="flex justify-between items-center">
            <div>
              <div className="page-title">{study.nombre_comunidad}</div>
              <div className="page-sub">
                {study.pueblo_indigena && <>{study.pueblo_indigena} · </>}
                {study.municipio}, {study.departamento}
                {study.contrato_referencia && <> · Contrato: {study.contrato_referencia}</>}
              </div>
            </div>
            <div className="flex gap-2">
              <span className={`badge ${ESTADO_BADGE[study.estado as StudyEstado] ?? 'badge-neutral'}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                <span className="badge-dot" />
                {ESTADO_LABEL[study.estado as StudyEstado] ?? study.estado}
              </span>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/estudios/${study.id}/generar`)}
              >
                ⚡ Generar informe
              </button>
            </div>
          </div>

          <div className="divider" />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, textAlign: 'center' }}>
            {[
              { label: 'CORPUS TOTAL', value: corpus.length, unit: 'archivos' },
              { label: 'FASE 1', value: fase1.length, unit: 'documentos' },
              { label: 'FASE 2', value: fase2.length, unit: 'archivos + SIG' },
              { label: 'FASE 3', value: fase3.length, unit: 'documentos' },
            ].map((m) => (
              <div key={m.label}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3, textTransform: 'uppercase', letterSpacing: '.4px' }}>{m.label}</div>
                <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 20, fontWeight: 700 }}>{m.value}</div>
                <div className="text-sm text-muted">{m.unit}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <IndigenousDivider patternId="detalle-nasa" variant="nasa" />

      {/* Tabs */}
      <div className="tabs">
        {TABS.map((t, i) => (
          <button key={i} className={`tab${activeTab === i ? ' active' : ''}`} onClick={() => setActiveTab(i)}>
            {t}
          </button>
        ))}
      </div>

      {/* FASE 1 */}
      {activeTab === 0 && (
        <div className="two-col">
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Archivos — Pre-campo</span>
              <span className="text-sm text-muted">{fase1.length} archivos</span>
            </div>
            <div className="card-body">
              {fase1.length === 0
                ? <div className="empty-state" style={{ padding: 24 }}>Sin archivos en Fase 1</div>
                : (
                  <div className="file-tree">
                    <div className="file-folder">
                      <div className="file-folder-name">📂 FASE 1</div>
                      <div className="file-list">
                        {fase1.map((f: any) => (
                          <div className="file-item" key={f.id}>
                            <div className="file-left">
                              {TIPO_ICON[f.tipo_archivo] ?? '📄'} {f.nombre_archivo}
                            </div>
                            <span className={f.estado === 'sincronizado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'sincronizado' ? '✓' : '⏳'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              }
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="section-title" style={{ margin: 0 }}>Datos del estudio</span></div>
            <div className="card-body">
              <table style={{ width: '100%', fontSize: 13 }}>
                <tbody>
                  {[
                    ['Nombre oficial', study.nombre_comunidad],
                    ['Pueblo indígena', study.pueblo_indigena ?? '—'],
                    ['Municipio', study.municipio],
                    ['Departamento', study.departamento],
                    ['Vereda', study.vereda ?? '—'],
                    ['NIT / ID', study.nit_comunidad ?? '—'],
                    ['Buffer SIG', `${study.buffer_metros} m`],
                    ['Contrato', study.contrato_referencia ?? '—'],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ color: 'var(--text-muted)', padding: '5px 0', width: '45%' }}>{k}</td>
                      <td style={{ fontWeight: 600 }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {study.notas_adicionales && (
                <div className="alert alert-info" style={{ marginTop: 12 }}>
                  ℹ&nbsp;{study.notas_adicionales}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* FASE 2 — con mapa */}
      {activeTab === 1 && (
        <div className="two-col">
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Archivos — Campo</span>
              <span className="text-sm text-muted">{fase2.length} archivos</span>
            </div>
            <div className="card-body">
              {fase2.length === 0
                ? <div className="empty-state" style={{ padding: 24 }}>Sin archivos en Fase 2</div>
                : (
                  <div className="file-tree">
                    <div className="file-folder">
                      <div className="file-folder-name">📂 FASE 2</div>
                      <div className="file-list">
                        {fase2.map((f: any) => (
                          <div className="file-item" key={f.id}>
                            <div className="file-left">{TIPO_ICON[f.tipo_archivo] ?? '📄'} {f.nombre_archivo}</div>
                            <span className={f.estado === 'sincronizado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'sincronizado' ? '✓' : '⏳'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              }
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Mapa SIG — {study.municipio}, {study.departamento}</span>
            </div>
            <div className="card-body">
              <div className="map-container">
                <MapContainer center={mapCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; OpenStreetMap'
                  />
                  {DEMO_LAYERS.map((layer) => (
                    <LayerGroup key={layer.name}>
                      {layer.points.map((pos, i) => (
                        <CircleMarker key={i} center={pos} radius={7}
                          pathOptions={{ color: layer.color, fillColor: layer.color, fillOpacity: 0.75, weight: 1.5 }}>
                          <Popup><strong>{layer.name}</strong><br />Punto {i + 1}</Popup>
                        </CircleMarker>
                      ))}
                    </LayerGroup>
                  ))}
                </MapContainer>
              </div>
              <div className="map-legend">
                {DEMO_LAYERS.map((l) => (
                  <div className="map-legend-item" key={l.name}>
                    <div className="map-legend-dot" style={{ background: l.color }} />
                    {l.name}
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                Datos de demostración · Sistema: WGS84 · {mapCenter[0].toFixed(4)}, {mapCenter[1].toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FASE 3 */}
      {activeTab === 2 && (
        <div className="two-col">
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Archivos — Post-campo</span>
              <span className="text-sm text-muted">{fase3.length} archivos</span>
            </div>
            <div className="card-body">
              {fase3.length === 0
                ? <div className="empty-state" style={{ padding: 24 }}>Sin archivos en Fase 3</div>
                : (
                  <div className="file-tree">
                    <div className="file-folder">
                      <div className="file-folder-name">📂 FASE 3</div>
                      <div className="file-list">
                        {fase3.map((f: any) => (
                          <div className="file-item" key={f.id}>
                            <div className="file-left">{TIPO_ICON[f.tipo_archivo] ?? '📄'} {f.nombre_archivo}</div>
                            <span className={f.estado === 'sincronizado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'sincronizado' ? '✓' : '⏳'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              }
            </div>
          </div>
          <div>
            <div className="alert alert-info">
              ℹ&nbsp;La Fase 3 contiene el concepto etnológico y el borrador del acto administrativo una vez finalizado el trabajo de campo.
            </div>
          </div>
        </div>
      )}

      {/* DRIVE */}
      {activeTab === 3 && (
        <div className="two-col">
          {/* Panel izquierdo: configurar URLs */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>☁ Carpetas de Google Drive</span>
              {driveStatus?.connected
                ? <span className="badge badge-success" style={{ fontSize: 11 }}>● Conectado{driveStatus.google_email ? ` · ${driveStatus.google_email}` : ''}</span>
                : <span className="badge badge-neutral" style={{ fontSize: 11 }}>○ Sin cuenta Google</span>
              }
            </div>
            <div className="card-body">
              {!driveStatus?.connected && (
                <div className="alert alert-warning" style={{ marginBottom: 16 }}>
                  ⚠&nbsp;Debes conectar tu cuenta de Google antes de sincronizar.
                  <button
                    className="btn btn-outline btn-sm"
                    style={{ marginLeft: 12 }}
                    onClick={handleConnectDrive}
                  >
                    Conectar Google Drive
                  </button>
                </div>
              )}

              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                Pega la URL de cada carpeta de Drive correspondiente a cada fase del estudio.
                La URL debe tener el formato <code>https://drive.google.com/drive/folders/…</code>
              </div>

              {[
                { label: 'Carpeta FASE 1 — Pre-campo', key: 'fase1' as const, placeholder: 'https://drive.google.com/drive/folders/1ABC...' },
                { label: 'Carpeta FASE 2 — Campo', key: 'fase2' as const, placeholder: 'https://drive.google.com/drive/folders/2DEF...' },
                { label: 'Carpeta FASE 3 — Post-campo', key: 'fase3' as const, placeholder: 'https://drive.google.com/drive/folders/3GHI... (opcional)' },
              ].map(({ label, key, placeholder }) => (
                <div className="form-group" key={key}>
                  <label className="form-label">{label}</label>
                  <input
                    className="form-input"
                    type="url"
                    placeholder={placeholder}
                    value={driveUrls[key]}
                    onChange={(e) => setDriveUrls((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                </div>
              ))}

              <div className="flex gap-2" style={{ marginTop: 8 }}>
                <button
                  className="btn btn-outline"
                  onClick={() => saveUrlsMutation.mutate()}
                  disabled={saveUrlsMutation.isPending}
                >
                  {saveUrlsMutation.isPending ? 'Guardando…' : '💾 Guardar URLs'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => syncMutation.mutate()}
                  disabled={syncMutation.isPending || (!driveUrls.fase1 && !driveUrls.fase2)}
                >
                  {syncMutation.isPending ? '⏳ Sincronizando…' : '🔄 Sincronizar corpus'}
                </button>
              </div>

              {urlsSaved && (
                <div className="alert alert-success" style={{ marginTop: 12 }}>✓ URLs guardadas correctamente.</div>
              )}
              {saveUrlsMutation.isError && (
                <div className="alert alert-error" style={{ marginTop: 12 }}>✗ Error al guardar las URLs.</div>
              )}
              {syncMutation.isError && (
                <div className="alert alert-error" style={{ marginTop: 12 }}>✗ Error al sincronizar. Verifica que las URLs sean correctas y que Drive esté conectado.</div>
              )}
            </div>
          </div>

          {/* Panel derecho: resultado de sincronización */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Resultado de sincronización</span>
            </div>
            <div className="card-body">
              {!syncResult && !syncMutation.isPending && (
                <div className="empty-state" style={{ padding: 32 }}>
                  <div className="empty-state-icon">☁</div>
                  <p>Aún no se ha sincronizado este estudio.</p>
                  <p className="text-sm text-muted">Ingresa las URLs de Drive y haz clic en "Sincronizar corpus".</p>
                </div>
              )}

              {syncMutation.isPending && (
                <div style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
                  <div>Descargando archivos desde Google Drive…</div>
                  <div className="text-sm text-muted" style={{ marginTop: 6 }}>Esto puede tomar algunos segundos.</div>
                </div>
              )}

              {syncResult && (
                <>
                  <div className="flex gap-3" style={{ marginBottom: 16 }}>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                      <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, fontWeight: 700, color: 'var(--primary)' }}>
                        {syncResult.total_downloaded}
                      </div>
                      <div className="text-sm text-muted">Descargados</div>
                    </div>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                      <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, fontWeight: 700 }}>
                        {syncResult.fases.reduce((s, f) => s + f.files_skipped, 0)}
                      </div>
                      <div className="text-sm text-muted">Sin cambios</div>
                    </div>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                      <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, fontWeight: 700, color: syncResult.total_errors > 0 ? '#dc2626' : 'var(--text-muted)' }}>
                        {syncResult.total_errors}
                      </div>
                      <div className="text-sm text-muted">Errores</div>
                    </div>
                  </div>

                  {syncResult.fases.map((fase) => (
                    <div key={fase.fase} style={{ marginBottom: 10 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                        <span>📂 {fase.fase}</span>
                        <span className="text-muted">{fase.files_found} encontrados · {fase.files_downloaded} nuevos · {fase.files_skipped} sin cambios</span>
                      </div>
                      {fase.errors.length > 0 && fase.errors.map((err, i) => (
                        <div key={i} className="alert alert-error" style={{ fontSize: 11, padding: '4px 8px', marginTop: 2 }}>✗ {err}</div>
                      ))}
                    </div>
                  ))}

                  {syncResult.total_errors === 0 && (
                    <div className="alert alert-success" style={{ marginTop: 8 }}>
                      ✓ Sincronización completada. Los archivos ya están disponibles en las pestañas de fase.
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
