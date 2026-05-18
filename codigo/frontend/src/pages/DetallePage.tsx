import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import IndigenousDivider from '../components/IndigenousDivider'
import { getStudy, getCorpusFiles, updateStudy, getGisGeojson } from '../api/studies'
import { getDriveStatus, getDriveAuthUrl, syncStudy } from '../api/drive'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import type { StudyEstado } from '../types'

const TABS = ['📁 FASE 1 — Pre-campo', '📁 FASE 2 — Campo', '📁 FASE 3 — Post-campo', '☁ Google Drive']

const TIPO_ICON: Record<string, string> = {
  pdf: '📄', docx: '📝', xlsx: '📊', qgz: '🗺', gpkg: '🗄',
  shp: '📐', jpg: '🖼', heic: '🖼', mp4: '🎬', mp3: '🎙',
}


export default function DetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(0)
  const [driveUrls, setDriveUrls] = useState({ fase1: '', fase2: '', fase3: '' })
  const [syncStarted, setSyncStarted] = useState(false)
  const [syncElapsed, setSyncElapsed] = useState(0)
  const [urlsSaved, setUrlsSaved] = useState(false)
  const prevEstadoRef = useRef<string | undefined>(undefined)
  const syncStartRef = useRef<number | null>(null)

  const { data: study, isLoading, isError } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const s = query.state.data
      return s?.estado === 'sincronizando' ? 3000 : false
    },
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

  const { data: geojson } = useQuery({
    queryKey: ['gis-geojson', id],
    queryFn: () => getGisGeojson(id!),
    enabled: !!id,
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
  }, [study?.id])

  // Cuando termina la sincronización, refrescar el corpus
  useEffect(() => {
    if (prevEstadoRef.current === 'sincronizando' && study?.estado !== 'sincronizando') {
      queryClient.invalidateQueries({ queryKey: ['corpus', id] })
    }
    prevEstadoRef.current = study?.estado
  }, [study?.estado])

  // Timer de tiempo transcurrido durante la sincronización
  useEffect(() => {
    const isSyncing = syncMutation.isPending || study?.estado === 'sincronizando'
    if (!isSyncing) {
      syncStartRef.current = null
      setSyncElapsed(0)
      return
    }
    if (syncStartRef.current === null) {
      syncStartRef.current = Date.now()
    }
    const interval = setInterval(() => {
      if (syncStartRef.current !== null) {
        setSyncElapsed(Math.floor((Date.now() - syncStartRef.current) / 1000))
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [syncMutation.isPending, study?.estado])

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
    onSuccess: () => {
      setSyncStarted(true)
      queryClient.invalidateQueries({ queryKey: ['study', id] })
    },
  })

  const isSyncing = syncMutation.isPending || study?.estado === 'sincronizando'

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
                            <span className={f.estado === 'descargado' || f.estado === 'procesado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'descargado' || f.estado === 'procesado' ? '✓' : '⏳'}
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
                            <span className={f.estado === 'descargado' || f.estado === 'procesado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'descargado' || f.estado === 'procesado' ? '✓' : '⏳'}
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
              <span className="section-title" style={{ margin: 0 }}>
                Mapa SIG — {study.municipio}, {study.departamento}
              </span>
              {geojson && geojson.metadata.total_puntos > 0 && (
                <span className="text-sm text-muted">{geojson.metadata.total_puntos} puntos · {geojson.metadata.capas.length} capas</span>
              )}
            </div>
            <div className="card-body">
              {geojson && geojson.features.length > 0 ? (() => {
                // Calcular centroide real de los puntos
                const lats = geojson.features.map(f => f.geometry.coordinates[1])
                const lngs = geojson.features.map(f => f.geometry.coordinates[0])
                const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length
                const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length
                const realCenter: [number, number] = [centerLat, centerLng]

                // Agrupar por capa para la leyenda
                const capas: Record<string, string> = {}
                geojson.features.forEach(f => { capas[f.properties.capa_label] = f.properties.color })

                return (
                  <>
                    <div className="map-container">
                      {/* @ts-ignore — react-leaflet props */}
                      <MapContainer center={realCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
                        {/* @ts-ignore */}
                        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
                        {geojson.features.map((feature, i) => {
                          const [lng, lat] = feature.geometry.coordinates
                          const pos: [number, number] = [lat, lng]
                          const props = feature.properties
                          const popupAttrs = Object.entries(props)
                            .filter(([k]) => !['capa', 'capa_label', 'color', 'study_id', 'comunidad'].includes(k))
                            .slice(0, 5)
                          return (
                            // @ts-ignore
                            <CircleMarker key={i} center={pos} radius={7}
                              pathOptions={{ color: props.color, fillColor: props.color, fillOpacity: 0.8, weight: 1.5 }}>
                              <Popup>
                                <strong>{props.capa_label}</strong>
                                {popupAttrs.map(([k, v]) => (
                                  <div key={k} style={{ fontSize: 11 }}>{k}: {String(v)}</div>
                                ))}
                                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>{lat.toFixed(6)}, {lng.toFixed(6)}</div>
                              </Popup>
                            </CircleMarker>
                          )
                        })}
                      </MapContainer>
                    </div>
                    <div className="map-legend">
                      {Object.entries(capas).map(([label, color]) => (
                        <div className="map-legend-item" key={label}>
                          <div className="map-legend-dot" style={{ background: color }} />
                          {label}
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
                      Sistema: WGS84 · Centro: {centerLat.toFixed(4)}, {centerLng.toFixed(4)}
                    </div>
                  </>
                )
              })() : (
                <>
                  <div className="map-container">
                    {/* @ts-ignore */}
                    <MapContainer center={mapCenter} zoom={12} style={{ height: '100%', width: '100%' }}>
                      {/* @ts-ignore */}
                      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' />
                    </MapContainer>
                  </div>
                  <div className="alert alert-info" style={{ marginTop: 8, fontSize: 12 }}>
                    Sin datos SIG disponibles. Sincroniza el corpus con archivos .gpkg y ejecuta el análisis SIG desde Generar informe.
                  </div>
                </>
              )}
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
                            <span className={f.estado === 'descargado' || f.estado === 'procesado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'descargado' || f.estado === 'procesado' ? '✓' : '⏳'}
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
                  disabled={isSyncing || (!driveUrls.fase1 && !driveUrls.fase2)}
                >
                  {isSyncing ? '⏳ Sincronizando…' : '🔄 Sincronizar corpus'}
                </button>
              </div>

              {urlsSaved && (
                <div className="alert alert-success" style={{ marginTop: 12 }}>✓ URLs guardadas correctamente.</div>
              )}
              {saveUrlsMutation.isError && (
                <div className="alert alert-error" style={{ marginTop: 12 }}>✗ Error al guardar las URLs.</div>
              )}
              {syncMutation.isError && (
                <div className="alert alert-error" style={{ marginTop: 12 }}>✗ Error al iniciar la sincronización. Verifica que las URLs sean correctas y que Drive esté conectado.</div>
              )}
              {isSyncing && study?.estado === 'sincronizando' && (
                <div className="alert alert-info" style={{ marginTop: 12, fontSize: 12 }}>
                  ℹ La sincronización corre en segundo plano. Puedes navegar a otras páginas y volver más tarde.
                </div>
              )}
            </div>
          </div>

          {/* Panel derecho: estado de sincronización */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Estado de sincronización</span>
            </div>
            <div className="card-body">
              {isSyncing ? (
                <div style={{ textAlign: 'center', padding: 32 }}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>⟳</div>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Descargando archivos de Google Drive…</div>
                  <div className="text-sm text-muted">
                    {corpus.length > 0 ? `${corpus.length} archivos registrados hasta ahora` : 'Conectando con Drive…'}
                  </div>
                  <div style={{ margin: '20px auto', maxWidth: 280 }}>
                    <div className="progress-bar-wrap" style={{ height: 8 }}>
                      <div className="progress-bar" style={{ width: '70%' }} />
                    </div>
                  </div>
                  <div className="text-sm text-muted">
                    ⏱ {Math.floor(syncElapsed / 60)}:{String(syncElapsed % 60).padStart(2, '0')} transcurridos
                  </div>
                  <div className="text-sm text-muted" style={{ marginTop: 4 }}>
                    Puede tomar varios minutos según el tamaño del corpus
                  </div>
                </div>
              ) : corpus.length > 0 ? (
                <>
                  {syncStarted && (
                    <div className="alert alert-success" style={{ marginBottom: 16 }}>
                      ✓ Sincronización completada exitosamente.
                    </div>
                  )}
                  <div className="flex gap-3" style={{ marginBottom: 16 }}>
                    {[
                      { label: 'Total', value: corpus.length, unit: 'archivos' },
                      { label: 'FASE 1', value: corpus.filter((f: any) => f.fase === 'FASE1').length, unit: 'docs' },
                      { label: 'FASE 2', value: corpus.filter((f: any) => f.fase === 'FASE2').length, unit: 'arch.' },
                      { label: 'FASE 3', value: corpus.filter((f: any) => f.fase === 'FASE3').length, unit: 'docs' },
                    ].map((m) => (
                      <div key={m.label} style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 20, fontWeight: 700, color: 'var(--primary)' }}>
                          {m.value}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.4px' }}>{m.label}</div>
                        <div className="text-sm text-muted">{m.unit}</div>
                      </div>
                    ))}
                  </div>
                  <div className="alert alert-info" style={{ fontSize: 12 }}>
                    ✓ El corpus está disponible en las pestañas de fase para revisión.
                  </div>
                  {study?.error_msg && (
                    <div className="alert alert-warning" style={{ marginTop: 8, fontSize: 12 }}>
                      ⚠ {study.error_msg}
                    </div>
                  )}
                </>
              ) : (
                <div className="empty-state" style={{ padding: 32 }}>
                  <div className="empty-state-icon">☁</div>
                  <p>Aún no se ha sincronizado este estudio.</p>
                  {study?.error_msg && (
                    <div className="alert alert-error" style={{ marginTop: 8, fontSize: 12 }}>✗ {study.error_msg}</div>
                  )}
                  <p className="text-sm text-muted">Ingresa las URLs de Drive y haz clic en "Sincronizar corpus".</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
