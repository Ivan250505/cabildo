import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import IndigenousDivider from '../components/IndigenousDivider'
import { getStudy, getCorpusFiles, updateStudy, getGisGeojson } from '../api/studies'
import { getDriveStatus, getDriveAuthUrl, listDriveFolder, processDriveFile } from '../api/drive'
import type { DriveFileItem, ProcessFileResult } from '../api/drive'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import type { StudyEstado } from '../types'

const TABS = ['📁 FASE 1 — Pre-campo', '📁 FASE 2 — Campo', '📁 FASE 3 — Post-campo', '☁ Google Drive']

const TIPO_ICON: Record<string, string> = {
  pdf: '📄', docx: '📝', xlsx: '📊', qgz: '🗺', gpkg: '🗄',
  shp: '📐', jpg: '🖼', heic: '🖼', mp4: '🎬', mp3: '🎙',
}

function formatSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(0)
  const [driveUrls, setDriveUrls] = useState({ fase1: '', fase2: '', fase3: '' })
  const [urlsSaved, setUrlsSaved] = useState(false)

  // File browser state
  const [browseFase, setBrowseFase] = useState<'FASE1' | 'FASE2' | 'FASE3' | null>(null)
  const [folderFiles, setFolderFiles] = useState<DriveFileItem[]>([])
  const [isListing, setIsListing] = useState(false)
  const [listError, setListError] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false)
  const [processProgress, setProcessProgress] = useState({ done: 0, total: 0, currentName: '' })
  const [processResults, setProcessResults] = useState<ProcessFileResult[]>([])
  const [processErrors, setProcessErrors] = useState<{ name: string; error: string }[]>([])

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

  async function handleConnectDrive() {
    try {
      const { url } = await getDriveAuthUrl()
      window.location.href = url
    } catch {
      alert('No se pudo obtener la URL de autorización de Google Drive.')
    }
  }

  async function handleListFolder(url: string, fase: 'FASE1' | 'FASE2' | 'FASE3') {
    if (!url) return
    setIsListing(true)
    setListError(null)
    setFolderFiles([])
    setSelectedIds(new Set())
    setProcessResults([])
    setProcessErrors([])
    setBrowseFase(fase)
    try {
      const result = await listDriveFolder(url)
      setFolderFiles(result.items)
      // Auto-select procesables (PDF/DOCX)
      setSelectedIds(new Set(result.items.filter(f => f.is_procesable).map(f => f.id)))
    } catch (err: any) {
      setListError(err?.response?.data?.detail ?? 'Error al listar la carpeta de Drive. Verifica la URL y la conexión.')
    } finally {
      setIsListing(false)
    }
  }

  async function handleProcess() {
    const toProcess = folderFiles.filter(f => selectedIds.has(f.id))
    if (!toProcess.length || !browseFase) return
    setIsProcessing(true)
    setProcessProgress({ done: 0, total: toProcess.length, currentName: '' })
    setProcessResults([])
    setProcessErrors([])

    const results: ProcessFileResult[] = []
    const errors: { name: string; error: string }[] = []

    for (const file of toProcess) {
      setProcessProgress(p => ({ ...p, currentName: file.name }))
      try {
        const result = await processDriveFile(id!, {
          drive_file_id: file.id,
          file_name: file.name,
          mime_type: file.mime_type,
          fase: browseFase,
        })
        results.push(result)
      } catch (err: any) {
        errors.push({
          name: file.name,
          error: err?.response?.data?.detail ?? err?.message ?? 'Error desconocido',
        })
      }
      setProcessProgress(p => ({ ...p, done: p.done + 1 }))
    }

    setProcessResults(results)
    setProcessErrors(errors)
    setIsProcessing(false)
    queryClient.invalidateQueries({ queryKey: ['corpus', id] })
    queryClient.invalidateQueries({ queryKey: ['study', id] })
  }

  function toggleSelect(fileId: string, checked: boolean) {
    const next = new Set(selectedIds)
    if (checked) next.add(fileId)
    else next.delete(fileId)
    setSelectedIds(next)
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

  const pct = processProgress.total > 0 ? (processProgress.done / processProgress.total) * 100 : 0

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
              {geojson && geojson.features && geojson.features.length > 0 ? (() => {
                const lats = geojson.features.map(f => f.geometry.coordinates[1])
                const lngs = geojson.features.map(f => f.geometry.coordinates[0])
                const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length
                const centerLng = lngs.reduce((a, b) => a + b, 0) / lngs.length
                const realCenter: [number, number] = [centerLat, centerLng]
                const capas: Record<string, string> = {}
                geojson.features.forEach(f => { capas[f.properties.capa_label] = f.properties.color })
                return (
                  <>
                    <div className="map-container">
                      {/* @ts-ignore */}
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
                    Sin datos SIG. Procesa archivos .gpkg desde el tab Drive y ejecuta el análisis SIG desde Generar informe.
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

      {/* DRIVE — nuevo flujo: listar → seleccionar → procesar uno a uno */}
      {activeTab === 3 && (
        <div className="two-col">
          {/* Panel izquierdo: configuración de carpetas */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>☁ Carpetas de Google Drive</span>
              {driveStatus?.connected
                ? <span className="badge badge-success" style={{ fontSize: 11 }}>● {driveStatus.google_email ?? 'Conectado'}</span>
                : <span className="badge badge-neutral" style={{ fontSize: 11 }}>○ Sin cuenta Google</span>
              }
            </div>
            <div className="card-body">
              {!driveStatus?.connected && (
                <div className="alert alert-warning" style={{ marginBottom: 16 }}>
                  ⚠&nbsp;Conecta tu cuenta de Google para poder listar y procesar archivos.
                  <button className="btn btn-outline btn-sm" style={{ marginLeft: 12 }} onClick={handleConnectDrive}>
                    Conectar Google Drive
                  </button>
                </div>
              )}

              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                Pega la URL de cada carpeta de Drive. Luego haz clic en <strong>📂 Ver</strong> para
                listar los archivos y seleccionar cuáles procesar.
              </div>

              {[
                { label: 'FASE 1 — Pre-campo', key: 'fase1' as const, fase: 'FASE1' as const, placeholder: 'https://drive.google.com/drive/folders/…' },
                { label: 'FASE 2 — Campo', key: 'fase2' as const, fase: 'FASE2' as const, placeholder: 'https://drive.google.com/drive/folders/…' },
                { label: 'FASE 3 — Post-campo', key: 'fase3' as const, fase: 'FASE3' as const, placeholder: 'https://drive.google.com/drive/folders/… (opcional)' },
              ].map(({ label, key, fase, placeholder }) => (
                <div className="form-group" key={key}>
                  <label className="form-label">{label}</label>
                  <div className="flex gap-2">
                    <input
                      className="form-input"
                      type="url"
                      placeholder={placeholder}
                      value={driveUrls[key]}
                      onChange={(e) => setDriveUrls(prev => ({ ...prev, [key]: e.target.value }))}
                      style={{ flex: 1 }}
                    />
                    <button
                      className="btn btn-outline btn-sm"
                      style={{ whiteSpace: 'nowrap' }}
                      disabled={!driveUrls[key] || isListing || !driveStatus?.connected}
                      onClick={() => handleListFolder(driveUrls[key], fase)}
                    >
                      📂 Ver
                    </button>
                  </div>
                </div>
              ))}

              <div className="flex gap-2" style={{ marginTop: 12 }}>
                <button
                  className="btn btn-outline"
                  onClick={() => saveUrlsMutation.mutate()}
                  disabled={saveUrlsMutation.isPending}
                >
                  {saveUrlsMutation.isPending ? 'Guardando…' : '💾 Guardar URLs'}
                </button>
              </div>

              {urlsSaved && <div className="alert alert-success" style={{ marginTop: 10 }}>✓ URLs guardadas.</div>}
              {saveUrlsMutation.isError && <div className="alert alert-error" style={{ marginTop: 10 }}>✗ Error al guardar las URLs.</div>}

              {corpus.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                    Corpus actual
                  </div>
                  <div className="flex gap-3">
                    {[
                      { label: 'Total', v: corpus.length },
                      { label: 'F1', v: fase1.length },
                      { label: 'F2', v: fase2.length },
                      { label: 'F3', v: fase3.length },
                    ].map(m => (
                      <div key={m.label} style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, fontWeight: 700, color: 'var(--primary)' }}>{m.v}</div>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{m.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Panel derecho: explorador de archivos */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>
                {browseFase ? `📂 ${browseFase} · ${folderFiles.length} archivos` : 'Explorador de archivos'}
              </span>
              {browseFase && folderFiles.length > 0 && !isProcessing && (
                <div className="flex gap-2">
                  <button className="btn btn-outline btn-sm" onClick={() => setSelectedIds(new Set(folderFiles.map(f => f.id)))}>
                    Todo
                  </button>
                  <button className="btn btn-outline btn-sm" onClick={() => setSelectedIds(new Set(folderFiles.filter(f => f.is_procesable).map(f => f.id)))}>
                    PDF/DOCX
                  </button>
                  <button className="btn btn-outline btn-sm" onClick={() => setSelectedIds(new Set())}>
                    Ninguno
                  </button>
                </div>
              )}
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {isListing ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <div style={{ fontSize: 28, marginBottom: 10 }}>⏳</div>
                  <div>Listando archivos de Drive…</div>
                  <div className="text-sm text-muted" style={{ marginTop: 4 }}>Recorriendo subcarpetas</div>
                </div>
              ) : listError ? (
                <div style={{ padding: 16 }}>
                  <div className="alert alert-error">✗ {listError}</div>
                </div>
              ) : !browseFase ? (
                <div className="empty-state" style={{ padding: 40 }}>
                  <div className="empty-state-icon">📂</div>
                  <p>Haz clic en <strong>📂 Ver</strong> junto a una fase para listar sus archivos.</p>
                </div>
              ) : folderFiles.length === 0 ? (
                <div className="empty-state" style={{ padding: 40 }}>
                  <div className="empty-state-icon">📭</div>
                  <p>La carpeta está vacía o no tiene archivos accesibles.</p>
                </div>
              ) : (
                <>
                  {/* Lista de archivos */}
                  <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                    {folderFiles.map(file => {
                      const processed = processResults.find(r => r.drive_file_id === file.id)
                      const failed = processErrors.find(e => e.name === file.name)
                      return (
                        <div
                          key={file.id}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '6px 14px', borderBottom: '1px solid var(--border-subtle)',
                            background: processed ? 'var(--bg-alt)' : failed ? '#fef2f2' : 'transparent',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={selectedIds.has(file.id)}
                            disabled={isProcessing}
                            onChange={e => toggleSelect(file.id, e.target.checked)}
                          />
                          <span style={{ fontSize: 14 }}>{TIPO_ICON[file.tipo] ?? '📎'}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            {file.subfolder && (
                              <span style={{ fontSize: 10, color: 'var(--text-muted)', marginRight: 4 }}>
                                {file.subfolder}/
                              </span>
                            )}
                            <span style={{ fontSize: 12 }}>{file.name}</span>
                            {processed?.resumen && (
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {processed.resumen}
                              </div>
                            )}
                          </div>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                            {formatSize(file.size_bytes)}
                          </span>
                          {processed && <span className="badge badge-success" style={{ fontSize: 10 }}>✓</span>}
                          {failed && <span className="badge badge-error" style={{ fontSize: 10 }}>✗</span>}
                          {file.is_procesable && !processed && !failed && (
                            <span className="badge badge-neutral" style={{ fontSize: 10 }}>PDF/DOCX</span>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  {/* Barra de procesamiento */}
                  <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border)' }}>
                    {isProcessing ? (
                      <>
                        <div style={{ fontSize: 12, marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
                          <span>⚡ {processProgress.done}/{processProgress.total} — <em>{processProgress.currentName}</em></span>
                          <span className="text-muted">{Math.round(pct)}%</span>
                        </div>
                        <div className="progress-bar-wrap" style={{ height: 6 }}>
                          <div className="progress-bar" style={{ width: `${pct}%`, transition: 'width 0.3s ease' }} />
                        </div>
                      </>
                    ) : (
                      <div className="flex gap-2" style={{ alignItems: 'center' }}>
                        <button
                          className="btn btn-primary"
                          disabled={selectedIds.size === 0}
                          onClick={handleProcess}
                        >
                          ⚡ Procesar {selectedIds.size} archivo{selectedIds.size !== 1 ? 's' : ''} seleccionado{selectedIds.size !== 1 ? 's' : ''}
                        </button>
                        <span className="text-sm text-muted">
                          {selectedIds.size} de {folderFiles.length} seleccionados
                        </span>
                      </div>
                    )}

                    {!isProcessing && processResults.length > 0 && (
                      <div className="alert alert-success" style={{ marginTop: 10, fontSize: 12 }}>
                        ✓ {processResults.length} archivo{processResults.length !== 1 ? 's' : ''} procesado{processResults.length !== 1 ? 's' : ''}.
                        {processErrors.length > 0 && ` ${processErrors.length} con error.`}
                      </div>
                    )}
                    {!isProcessing && processErrors.length > 0 && processResults.length === 0 && (
                      <div className="alert alert-error" style={{ marginTop: 10, fontSize: 12 }}>
                        ✗ Todos los archivos fallaron. Verifica la conexión con Drive.
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
