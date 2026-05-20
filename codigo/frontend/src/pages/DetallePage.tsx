import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import IndigenousDivider from '../components/IndigenousDivider'
import RolBadge from '../components/RolBadge'
import DatosEstructurados from '../components/DatosEstructurados'
import MetodoExtraccionBadge from '../components/MetodoExtraccionBadge'
import DatosConsolidados from '../components/DatosConsolidados'
import { CATALOGO_ROLES } from '../data/catalogoRoles'
import {
  getStudy, getCorpusFiles, updateStudy, getGisGeojson,
  clasificarCorpus, overrideCorpusRol,
  processCorpusV2, getProcessV2Status,
} from '../api/studies'
import { getDriveStatus, getDriveAuthUrl, listDriveFolder, downloadDriveFile } from '../api/drive'
import type { DriveFileItem, DownloadFileResult } from '../api/drive'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import { DEPARTAMENTO_COORDS } from '../data/colombia'
import type { StudyEstado, CorpusRol } from '../types'
import { toast } from '../lib/toast'
import Swal from 'sweetalert2'

const TABS = ['📁 FASE 1 — Pre-campo', '📁 FASE 2 — Campo', '☁ Google Drive', '📊 Consolidado']

// Sprints 0-5 (encuestas dinámicas): lógica intacta, accesos visibles ocultos.
// Reactivar cambiando a true.
const ENCUESTAS_VISIBLES = false

const TIPO_ICON: Record<string, string> = {
  pdf: '📄', docx: '📝', xlsx: '📊', qgz: '🗺', gpkg: '🗄',
  shp: '📐', jpg: '🖼', heic: '🖼', mp4: '🎬', mp3: '🎙',
}

function formatSize(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// Sprint Drive D — extensiones que se ocultan por defecto (no le sirven al usuario)
const EXTENSIONES_OCULTAS = new Set([
  '.svg', '.exe', '.dll', '.bin', '.iso', '.dmg', '.app',
  '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz',
  '.bak', '.tmp', '.lnk', '.db', '.sqlite',
  '.dat', '.log', '.ini', '.cfg', '.sys',
])

function getExt(name: string): string {
  const m = name.toLowerCase().match(/\.[^./\\]+$/)
  return m ? m[0] : ''
}

function esArchivoUtil(f: DriveFileItem): boolean {
  const ext = getExt(f.name)
  if (EXTENSIONES_OCULTAS.has(ext)) return false
  return true
}

function clasificarTipo(f: DriveFileItem): 'pdf' | 'word' | 'excel' | 'imagen' | 'otros' {
  const ext = getExt(f.name)
  if (ext === '.pdf') return 'pdf'
  if (['.doc', '.docx', '.odt', '.rtf'].includes(ext)) return 'word'
  if (['.xls', '.xlsx', '.csv', '.ods'].includes(ext)) return 'excel'
  if (['.jpg', '.jpeg', '.png', '.heic', '.webp', '.gif', '.bmp', '.tif', '.tiff'].includes(ext)) return 'imagen'
  return 'otros'
}

const TIPO_ICON_FILTRO: Record<string, string> = {
  todos: '📂', pdf: '📄', word: '📝', excel: '📊', imagen: '🖼', otros: '📎',
}

const TIPO_LABEL_FILTRO: Record<string, string> = {
  todos: 'Todos', pdf: 'PDF', word: 'Word', excel: 'Excel', imagen: 'Imágenes', otros: 'Otros',
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

  // Archivo seleccionado en corpus para ver resumen
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null)

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false)
  const [processProgress, setProcessProgress] = useState({ done: 0, total: 0, currentName: '', fase: 'descargando' as 'descargando' | 'analizando' })
  const [processResults, setProcessResults] = useState<DownloadFileResult[]>([])
  const [processErrors, setProcessErrors] = useState<{ name: string; error: string }[]>([])

  // Sprint Drive D — buscador y filtros
  const [searchQuery, setSearchQuery] = useState('')
  const [tipoFilter, setTipoFilter] = useState<'todos' | 'pdf' | 'word' | 'excel' | 'imagen' | 'otros'>('todos')

  // UX modal explorador
  const [modalAbierto, setModalAbierto] = useState(false)
  // Categoría manual asignada en el modal por archivo (file_id → rol)
  const [manualRoles, setManualRoles] = useState<Record<string, CorpusRol | ''>>({})

  const { data: study, isLoading } = useQuery({
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

  const selectedFileObj = corpus.find((f: any) => f.id === selectedCorpusId) as any

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
      toast.success('URLs guardadas', 'Las carpetas de Drive quedaron registradas correctamente.')
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? 'No se pudieron guardar las URLs.'
      toast.error('Error al guardar', msg)
    },
  })

  // ── Clasificación de archivos (Sprint Drive A) ─────────────────────────
  const clasificarMutation = useMutation({
    mutationFn: (ignoreExisting: boolean) =>
      clasificarCorpus(id!, { ignore_existing: ignoreExisting, use_ai_fallback: true }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['corpus', id] })
      toast.success(
        'Clasificación completa',
        `${res.clasificados} archivos clasificados · ${res.omitidos} omitidos · ${res.fallback_otro} sin reconocer.`,
      )
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? 'No se pudo clasificar el corpus.'
      toast.error('Error al clasificar', msg)
    },
  })

  const overrideRolMutation = useMutation({
    mutationFn: ({ fileId, rol }: { fileId: string; rol: CorpusRol }) =>
      overrideCorpusRol(id!, fileId, rol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['corpus', id] })
    },
    onError: () => toast.error('Error', 'No se pudo cambiar el tipo del archivo.'),
  })

  // ── Pipeline v2 (Sprint Drive C) ──────────────────────────────────────
  const [v2Running, setV2Running] = useState(false)

  const v2StatusQuery = useQuery({
    queryKey: ['process-v2-status', id],
    queryFn: () => getProcessV2Status(id!),
    enabled: !!id && v2Running,
    refetchInterval: v2Running ? 3000 : false,
  })

  useEffect(() => {
    const st = v2StatusQuery.data
    if (!st || !v2Running) return
    if (st.estado === 'ok' && st.summary) {
      setV2Running(false)
      queryClient.invalidateQueries({ queryKey: ['corpus', id] })
      queryClient.invalidateQueries({ queryKey: ['corpus-datos'] })
      const s = st.summary
      toast.success(
        '✓ Pipeline v2 completado',
        `${s.procesados_ia} procesados · ${s.saltados_ya_procesados} ya estaban · ${s.saltados_sin_ia} sin IA · ${s.errores.length} errores · ${s.llamadas_ia_totales} llamadas IA.`,
      )
    } else if (st.estado === 'error') {
      setV2Running(false)
      toast.error('Pipeline v2 falló', st.error ?? 'Error desconocido.')
    }
  }, [v2StatusQuery.data, v2Running, id, queryClient])

  async function handleReclasificarTodo() {
    const result = await Swal.fire({
      title: '¿Reclasificar todos los archivos?',
      html: '<div style="text-align:left">' +
        'Esto vuelve a correr el clasificador automático sobre todos los archivos del corpus.<br><br>' +
        '<strong>Los tipos asignados manualmente se respetan</strong> (no se sobreescriben).' +
        '</div>',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sí, reclasificar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#1A3A5C',
    })
    if (result.isConfirmed) clasificarMutation.mutate(true)
  }

  async function handleConnectDrive() {
    try {
      const { url } = await getDriveAuthUrl()
      window.location.href = url
    } catch {
      toast.error('Error de conexión', 'No se pudo obtener la URL de autorización de Google Drive.')
    }
  }

  async function handleListFolder(url: string, fase: 'FASE1' | 'FASE2' | 'FASE3') {
    if (!url) {
      toast.warning('URL requerida', 'Primero escribe y guarda la URL de la carpeta de Drive.')
      return
    }
    setIsListing(true)
    setListError(null)
    setFolderFiles([])
    setSelectedIds(new Set())
    setProcessResults([])
    setProcessErrors([])
    setManualRoles({})
    setSearchQuery('')
    setTipoFilter('todos')
    setBrowseFase(fase)
    try {
      const result = await listDriveFolder(url)
      const utiles = result.items.filter(esArchivoUtil)
      const omitidos = result.items.length - utiles.length
      setFolderFiles(utiles)
      const procesables = utiles.filter(f => f.is_procesable)
      setSelectedIds(new Set(procesables.map(f => f.id)))
      setModalAbierto(true)  // abrir modal con la lista
      const detalle = omitidos > 0 ? ` · ${omitidos} archivos no útiles ocultos.` : ''
      toast.success(
        `${utiles.length} archivos disponibles`,
        `${procesables.length} PDF/DOCX seleccionados automáticamente.${detalle}`,
      )
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? 'Error al listar la carpeta de Drive. Verifica la URL y la conexión.'
      setListError(msg)
      toast.error('Error al leer carpeta', msg)
    } finally {
      setIsListing(false)
    }
  }

  async function handleProcess() {
    let toProcess = folderFiles.filter(f => selectedIds.has(f.id))
    if (!toProcess.length || !browseFase) return

    // Detectar archivos ya procesados (en corpus con estado 'procesado')
    const procesadosEnCorpus = new Set(
      corpus
        .filter((c: any) => c.estado === 'procesado' && c.drive_file_id)
        .map((c: any) => c.drive_file_id as string)
    )
    const yaProcesados = toProcess.filter(f => procesadosEnCorpus.has(f.id))
    const nuevos = toProcess.filter(f => !procesadosEnCorpus.has(f.id))

    if (yaProcesados.length > 0) {
      const result = await Swal.fire({
        title: 'Archivos ya analizados',
        html: `<div style="text-align:left">
          <strong>${yaProcesados.length}</strong> de <strong>${toProcess.length}</strong> archivos seleccionados ya tienen análisis previo.<br><br>
          ¿Qué deseas hacer?
        </div>`,
        icon: 'question',
        showCancelButton: true,
        showDenyButton: nuevos.length > 0,
        confirmButtonText: '🔄 Reanalizar todos',
        denyButtonText: nuevos.length > 0 ? `✨ Solo los ${nuevos.length} nuevos` : '',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#B22222',
        denyButtonColor: '#1A3A5C',
        cancelButtonColor: '#6b7280',
      })
      if (result.isDismissed) return
      if (result.isDenied) toProcess = nuevos
    }

    if (!toProcess.length) {
      toast.info('Sin archivos para procesar', 'Todos los seleccionados ya estaban analizados.')
      return
    }

    setIsProcessing(true)
    setProcessProgress({ done: 0, total: toProcess.length, currentName: '', fase: 'descargando' })
    setProcessResults([])
    setProcessErrors([])

    // ── Fase 1: descarga al storage permanente ─────────────────────────
    const results: DownloadFileResult[] = []
    const errors: { name: string; error: string }[] = []

    for (const file of toProcess) {
      setProcessProgress(p => ({ ...p, currentName: file.name }))
      const rolManual = manualRoles[file.id] || undefined
      try {
        const result = await downloadDriveFile(id!, {
          drive_file_id: file.id,
          file_name: file.name,
          mime_type: file.mime_type,
          fase: browseFase,
          rol_manual: rolManual,
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
    queryClient.invalidateQueries({ queryKey: ['corpus', id] })
    queryClient.invalidateQueries({ queryKey: ['study', id] })

    // ── Fase 2: pipeline v2 (clasifica + extrae con IA) ────────────────
    if (results.length > 0) {
      setProcessProgress({ done: 0, total: results.length, currentName: 'Clasificando + extrayendo con IA…', fase: 'analizando' })
      try {
        await processCorpusV2(id!, false)
        setV2Running(true)  // el polling existente terminará de mostrar resultados
        toast.success(
          'Archivos descargados',
          `${results.length} archivo${results.length !== 1 ? 's' : ''} en el corpus. La IA está clasificando y extrayendo datos…`
        )
      } catch (err: any) {
        toast.warning(
          'Descarga completada, análisis pendiente',
          err?.response?.data?.detail ?? 'No se pudo iniciar el pipeline v2. Usa el botón 🚀 Procesar (v2) en la cabecera.',
        )
      }
    } else if (errors.length > 0) {
      toast.error('Fallo en la descarga', 'Ningún archivo se pudo bajar. Revisa los detalles abajo.')
    }

    setIsProcessing(false)
  }

  function toggleSelect(fileId: string, checked: boolean) {
    const next = new Set(selectedIds)
    if (checked) next.add(fileId)
    else next.delete(fileId)
    setSelectedIds(next)
  }

  if (isLoading) return <div className="loading-state">Cargando estudio…</div>
  // Solo mostrar "no encontrado" cuando ya terminó la carga inicial y no hay datos cacheados.
  // Evita el flash durante refetch (cuando isError es true momentáneamente pero study sigue presente).
  if (!study) return (
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
    : DEPARTAMENTO_COORDS[study.departamento] ?? [4.0, -73.0]

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
              {ENCUESTAS_VISIBLES && (
                <div style={{ marginTop: 8 }}>
                  {study.modo_creacion === 'encuestas_nuevas' ? (
                    <span className="badge badge-success" style={{ fontSize: 11 }}>
                      ✏ Origen: Encuestas en plataforma
                    </span>
                  ) : (
                    <span className="badge badge-info" style={{ fontSize: 11 }}>
                      📂 Origen: Google Drive
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <span className={`badge ${ESTADO_BADGE[study.estado as StudyEstado] ?? 'badge-neutral'}`} style={{ fontSize: 13, padding: '6px 14px' }}>
                <span className="badge-dot" />
                {ESTADO_LABEL[study.estado as StudyEstado] ?? study.estado}
              </span>
              {ENCUESTAS_VISIBLES && study.modo_creacion === 'encuestas_nuevas' && (
                <Link to={`/estudios/${study.id}/encuestas`} className="btn btn-outline">
                  ✏ Ir a encuestas
                </Link>
              )}
              <Link to={`/estudios/${study.id}/mapa`} className="btn btn-outline">
                📍 Georreferenciación
              </Link>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/estudios/${study.id}/generar`)}
              >
                ⚡ Generar informe
              </button>
            </div>
          </div>

          <div className="divider" />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, textAlign: 'center' }}>
            {[
              { label: 'CORPUS TOTAL', value: corpus.length, unit: 'archivos' },
              { label: 'FASE 1', value: fase1.length, unit: 'documentos' },
              { label: 'FASE 2', value: fase2.length, unit: 'archivos + SIG' },
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
      {activeTab === 0 && (() => {
        return (
          <div className="two-col">
            <div className="card">
              <div className="card-header">
                <span className="section-title" style={{ margin: 0 }}>Archivos — Pre-campo</span>
                <div className="flex gap-2 items-center">
                  <span className="text-sm text-muted">{fase1.length} archivos</span>
                  {fase1.length > 0 && (
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={handleReclasificarTodo}
                      disabled={clasificarMutation.isPending}
                      title="Reclasifica todos los archivos del corpus"
                    >
                      {clasificarMutation.isPending ? '⏳ Clasificando…' : '🏷 Reclasificar'}
                    </button>
                  )}
                </div>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                {fase1.length === 0
                  ? <div className="empty-state" style={{ padding: 24 }}>Sin archivos en Fase 1</div>
                  : (
                    <div className="file-list">
                      {fase1.map((f: any) => {
                        const isSelected = f.id === selectedCorpusId
                        return (
                          <div key={f.id}>
                            <div
                              className="file-item"
                              onClick={() => setSelectedCorpusId(isSelected ? null : f.id)}
                              style={{
                                cursor: 'pointer',
                                background: isSelected ? 'var(--bg-alt)' : 'transparent',
                                borderLeft: isSelected ? '3px solid var(--primary)' : '3px solid transparent',
                                padding: '8px 14px',
                              }}
                            >
                              <div className="file-left" style={{ flex: 1, minWidth: 0 }}>
                                <span>{TIPO_ICON[f.tipo_archivo] ?? '📄'} {f.nombre_archivo}</span>
                                {f.resumen && !isSelected && (
                                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {f.resumen.slice(0, 80)}…
                                  </div>
                                )}
                              </div>
                              <span onClick={e => e.stopPropagation()} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                <RolBadge
                                  rol={f.rol_en_corpus}
                                  fuente={f.clasificacion_fuente}
                                  confianza={f.clasificacion_confianza}
                                  compact
                                  onChange={(nuevo) => overrideRolMutation.mutateAsync({ fileId: f.id, rol: nuevo })}
                                />
                                <MetodoExtraccionBadge fuente={f.fuente_extraccion} />
                              </span>
                              <span className={f.estado === 'descargado' || f.estado === 'procesado' || f.estado === 'clasificado' ? 'file-check' : 'file-warn'}>
                                {f.estado === 'descargado' || f.estado === 'procesado' || f.estado === 'clasificado' ? '✓' : '⏳'}
                              </span>
                              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 4 }}>
                                {isSelected ? '▲' : '▼'}
                              </span>
                            </div>
                            {isSelected && (
                              <div style={{ padding: '10px 14px 14px', background: 'var(--bg-alt)', borderBottom: '1px solid var(--border)' }}>
                                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>
                                  Análisis IA — {f.nombre_archivo}
                                </div>
                                {f.resumen
                                  ? <p style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text)', margin: 0 }}>{f.resumen}</p>
                                  : <p style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>
                                      Este archivo aún no tiene resumen generado. Procésalo desde la pestaña Google Drive.
                                    </p>
                                }
                                {f.procesado_en && (
                                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8 }}>
                                    Procesado: {new Date(f.procesado_en).toLocaleString('es-CO')}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )
                }
              </div>
            </div>

            <div className="card" style={{ alignSelf: 'start' }}>
              <div className="card-header">
                <span className="section-title" style={{ margin: 0 }}>
                  {selectedFileObj ? `📄 ${selectedFileObj.nombre_archivo}` : 'Datos del estudio'}
                </span>
              </div>
              <div className="card-body">
                {selectedFileObj ? (
                  <>
                    {/* Resumen legacy: solo si existe (la mayoría de archivos nuevos no lo tienen) */}
                    {selectedFileObj.resumen && (
                      <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                          Resumen del contenido
                        </div>
                        <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text)', margin: 0, whiteSpace: 'pre-wrap' }}>
                          {selectedFileObj.resumen}
                        </p>
                      </div>
                    )}

                    {/* Datos estructurados — el contenido principal del archivo */}
                    <div style={{
                      fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
                      textTransform: 'uppercase', marginBottom: 8,
                    }}>
                      Datos extraídos
                    </div>
                    <DatosEstructurados studyId={id!} fileId={selectedFileObj.id} />

                    {selectedFileObj.procesado_en && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12, fontStyle: 'italic' }}>
                        Procesado: {new Date(selectedFileObj.procesado_en).toLocaleString('es-CO')}
                      </div>
                    )}

                    <button className="btn btn-outline btn-sm" style={{ marginTop: 12 }} onClick={() => setSelectedCorpusId(null)}>
                      ← Ver datos del estudio
                    </button>
                  </>
                ) : (
                  <>
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
                    {fase1.length > 0 && (
                      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        Haz clic en un archivo de la lista para ver su análisis.
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )
      })()}

      {/* FASE 2 — con mapa */}
      {activeTab === 1 && (
        <div className="two-col">
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Archivos — Campo</span>
              <div className="flex gap-2 items-center">
                <span className="text-sm text-muted">{fase2.length} archivos</span>
                {fase2.length > 0 && (
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={handleReclasificarTodo}
                    disabled={clasificarMutation.isPending}
                    title="Reclasifica todos los archivos del corpus"
                  >
                    {clasificarMutation.isPending ? '⏳ Clasificando…' : '🏷 Reclasificar'}
                  </button>
                )}
              </div>
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
                          <div className="file-item" key={f.id} style={{ gap: 8 }}>
                            <div className="file-left" style={{ flex: 1, minWidth: 0 }}>
                              {TIPO_ICON[f.tipo_archivo] ?? '📄'} {f.nombre_archivo}
                            </div>
                            <RolBadge
                              rol={f.rol_en_corpus}
                              fuente={f.clasificacion_fuente}
                              confianza={f.clasificacion_confianza}
                              compact
                              onChange={(nuevo) => overrideRolMutation.mutateAsync({ fileId: f.id, rol: nuevo })}
                            />
                            <MetodoExtraccionBadge fuente={f.fuente_extraccion} />
                            <span className={f.estado === 'descargado' || f.estado === 'procesado' || f.estado === 'clasificado' ? 'file-check' : 'file-warn'}>
                              {f.estado === 'descargado' || f.estado === 'procesado' || f.estado === 'clasificado' ? '✓' : '⏳'}
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
              {geojson?.metadata?.total_puntos > 0 && (
                <span className="text-sm text-muted">{geojson.metadata.total_puntos} puntos · {geojson.metadata.capas?.length ?? 0} capas</span>
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

      {/* DRIVE — nuevo flujo: listar → modal → descargar y analizar */}
      {activeTab === 2 && (
        <div>
          {/* Panel único: configuración de carpetas (la lista de archivos va en un modal) */}
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
                    {(() => {
                      const urlGuardada = (study?.[`url_drive_${key}` as keyof typeof study] as string | null) ?? null
                      const guardada = !!urlGuardada && urlGuardada.trim() === driveUrls[key].trim()
                      return (
                        <button
                          className="btn btn-outline btn-sm"
                          style={{ whiteSpace: 'nowrap' }}
                          disabled={!guardada || isListing || !driveStatus?.connected}
                          onClick={() => handleListFolder(driveUrls[key], fase)}
                          title={
                            !driveStatus?.connected
                              ? 'Primero conecta tu cuenta de Google'
                              : !driveUrls[key]
                                ? 'Pega la URL de la carpeta'
                                : !guardada
                                  ? 'Guarda primero la URL con 💾 Guardar URLs'
                                  : 'Abrir explorador de archivos en modal'
                          }
                        >
                          📂 Ver
                        </button>
                      )
                    })()}
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

        </div>
      )}

      {/* Modal explorador de archivos de Drive (UX nueva) */}
      {modalAbierto && (() => {
        const filteredFiles = folderFiles.filter(f => {
          if (tipoFilter !== 'todos' && clasificarTipo(f) !== tipoFilter) return false
          if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase()
            if (!f.name.toLowerCase().includes(q) && !(f.subfolder ?? '').toLowerCase().includes(q)) return false
          }
          return true
        })
        const cerrar = () => { if (!isProcessing) setModalAbierto(false) }
        return (
          <div className="modal-backdrop" onClick={cerrar}>
            <div
              className="modal"
              style={{ maxWidth: 1000, width: '92vw', maxHeight: '88vh', display: 'flex', flexDirection: 'column', padding: 0 }}
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="modal-header" style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
                <span className="section-title" style={{ margin: 0 }}>
                  📂 Explorador {browseFase ? `· ${browseFase}` : ''} · {filteredFiles.length}{filteredFiles.length !== folderFiles.length ? `/${folderFiles.length}` : ''} archivos
                </span>
                <button className="btn btn-ghost btn-sm" onClick={cerrar} disabled={isProcessing} title="Cerrar">✕</button>
              </div>

              {/* Buscador + filtros */}
              {!isListing && !listError && folderFiles.length > 0 && (
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-alt)' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="🔍 Buscar archivo por nombre o subcarpeta…"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    style={{ marginBottom: 8, fontSize: 13 }}
                  />
                  <div className="flex gap-1" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
                    {(['todos', 'pdf', 'word', 'excel', 'imagen', 'otros'] as const).map(t => {
                      const count = t === 'todos' ? folderFiles.length : folderFiles.filter(f => clasificarTipo(f) === t).length
                      const active = tipoFilter === t
                      return (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setTipoFilter(t)}
                          style={{
                            padding: '3px 10px', fontSize: 11, fontWeight: 600,
                            background: active ? 'var(--primary)' : '#fff',
                            color: active ? '#fff' : 'var(--text-muted)',
                            border: `1px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
                            borderRadius: 14, cursor: 'pointer',
                            opacity: count === 0 && !active ? 0.4 : 1,
                          }}
                        >
                          {TIPO_ICON_FILTRO[t]} {TIPO_LABEL_FILTRO[t]} ({count})
                        </button>
                      )
                    })}
                    <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                      <button className="btn btn-outline btn-sm" disabled={isProcessing}
                        onClick={() => setSelectedIds(new Set([...Array.from(selectedIds), ...filteredFiles.map(f => f.id)]))}
                      >
                        Todo visible
                      </button>
                      <button className="btn btn-outline btn-sm" disabled={isProcessing}
                        onClick={() => setSelectedIds(new Set())}
                      >
                        Ninguno
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Body: lista de archivos */}
              <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: 0 }}>
                {isListing ? (
                  <div style={{ textAlign: 'center', padding: 60 }}>
                    <div style={{ fontSize: 28, marginBottom: 10 }}>⏳</div>
                    <div>Listando archivos de Drive…</div>
                    <div className="text-sm text-muted" style={{ marginTop: 4 }}>Recorriendo subcarpetas</div>
                  </div>
                ) : listError ? (
                  <div style={{ padding: 20 }}>
                    <div className="alert alert-error">✗ {listError}</div>
                  </div>
                ) : folderFiles.length === 0 ? (
                  <div className="empty-state" style={{ padding: 60 }}>
                    <div className="empty-state-icon">📭</div>
                    <p>La carpeta está vacía o no tiene archivos accesibles.</p>
                  </div>
                ) : filteredFiles.length === 0 ? (
                  <div className="empty-state" style={{ padding: 40 }}>
                    <p>No hay archivos que coincidan con la búsqueda/filtro.</p>
                  </div>
                ) : (
                  filteredFiles.map(file => {
                    const processed = processResults.find(r => r.drive_file_id === file.id)
                    const failed = processErrors.find(e => e.name === file.name)
                    const yaEnCorpus = corpus.find((c: any) => c.drive_file_id === file.id && c.estado === 'procesado')
                    const corpusEntry = corpus.find((c: any) => c.drive_file_id === file.id) as any
                    const rolPersistido = corpusEntry?.rol_en_corpus as CorpusRol | undefined
                    const rolSeleccionado = manualRoles[file.id] ?? (rolPersistido ?? '')
                    return (
                      <div
                        key={file.id}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: 'auto auto 1fr auto auto auto',
                          alignItems: 'center', gap: 10,
                          padding: '8px 20px', borderBottom: '1px solid var(--border-subtle)',
                          background: processed || yaEnCorpus ? 'var(--bg-alt)' : failed ? '#fef2f2' : 'transparent',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.has(file.id)}
                          disabled={isProcessing}
                          onChange={e => toggleSelect(file.id, e.target.checked)}
                        />
                        <span style={{ fontSize: 16 }}>{TIPO_ICON[file.tipo] ?? '📎'}</span>
                        <div style={{ minWidth: 0 }}>
                          {file.subfolder && (
                            <span style={{ fontSize: 10, color: 'var(--text-muted)', marginRight: 4 }}>
                              {file.subfolder}/
                            </span>
                          )}
                          <span style={{ fontSize: 13 }}>{file.name}</span>
                          {processed?.rol_inferido && !rolSeleccionado && (
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
                              Sugerido por nombre: <strong>{processed.rol_inferido}</strong>
                            </div>
                          )}
                        </div>
                        <select
                          value={rolSeleccionado}
                          disabled={isProcessing}
                          onChange={e => setManualRoles(m => ({ ...m, [file.id]: e.target.value as CorpusRol | '' }))}
                          style={{
                            fontSize: 11, padding: '3px 6px',
                            border: '1px solid var(--border)', borderRadius: 6,
                            background: rolSeleccionado ? '#dcfce7' : '#fff',
                            maxWidth: 200,
                          }}
                          title="Categoría a asignar (opcional — si lo dejas en automático, el sistema lo clasifica solo)"
                        >
                          <option value="">Auto (lo decide el sistema)</option>
                          <optgroup label="FASE 1 — Pre-campo">
                            {CATALOGO_ROLES.filter(r => r.fase === 'FASE1').map(r => (
                              <option key={r.code} value={r.code}>{r.icono} {r.nombre}</option>
                            ))}
                          </optgroup>
                          <optgroup label="FASE 2 — Campo">
                            {CATALOGO_ROLES.filter(r => r.fase === 'FASE2').map(r => (
                              <option key={r.code} value={r.code}>{r.icono} {r.nombre}</option>
                            ))}
                          </optgroup>
                          <optgroup label="Otros">
                            {CATALOGO_ROLES.filter(r => r.fase === 'cualquiera').map(r => (
                              <option key={r.code} value={r.code}>{r.icono} {r.nombre}</option>
                            ))}
                          </optgroup>
                        </select>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {formatSize(file.size_bytes)}
                        </span>
                        <span style={{ minWidth: 80, textAlign: 'right' }}>
                          {processed && <span className="badge badge-success" style={{ fontSize: 10 }}>✓ Descargado</span>}
                          {!processed && yaEnCorpus && <span className="badge badge-success" style={{ fontSize: 10 }}>✓ En corpus</span>}
                          {failed && <span className="badge badge-error" style={{ fontSize: 10 }}>✗</span>}
                        </span>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Footer: progreso o acción */}
              <div className="modal-footer" style={{ padding: '14px 20px', borderTop: '1px solid var(--border)' }}>
                {isProcessing ? (
                  <div className="drive-progress-panel" style={{ width: '100%' }}>
                    <div className="drive-progress-title">
                      {processProgress.fase === 'descargando' ? '📥 Descargando archivos…' : '🤖 Clasificando y extrayendo con IA…'}
                    </div>
                    <div className="drive-progress-file">📄 {processProgress.currentName}</div>
                    <div className="drive-progress-bar-wrap">
                      <div className="drive-progress-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="drive-progress-stats">
                      <span><strong>{processProgress.done}</strong> de <strong>{processProgress.total}</strong></span>
                      <span><strong>{Math.round(pct)}%</strong> completado</span>
                    </div>
                  </div>
                ) : (() => {
                  const yaCorpusIds = new Set(
                    corpus.filter((c: any) => c.estado === 'procesado' && c.drive_file_id).map((c: any) => c.drive_file_id)
                  )
                  const seleccionados = folderFiles.filter(f => selectedIds.has(f.id))
                  const todosYaAnalizados = seleccionados.length > 0 && seleccionados.every(f => yaCorpusIds.has(f.id))
                  const conRolManual = seleccionados.filter(f => manualRoles[f.id]).length
                  const labelAccion = todosYaAnalizados ? '🔄 Reanalizar' : '📥 Descargar y analizar'
                  return (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
                      <button className="btn btn-ghost" onClick={cerrar}>Cancelar</button>
                      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span className="text-sm text-muted">
                          {selectedIds.size} seleccionado{selectedIds.size !== 1 ? 's' : ''}
                          {conRolManual > 0 && ` · ${conRolManual} con categoría manual`}
                        </span>
                        <button
                          className="btn btn-primary"
                          disabled={selectedIds.size === 0}
                          onClick={handleProcess}
                          title="Descarga los archivos seleccionados al estudio y dispara la clasificación + extracción IA"
                        >
                          {labelAccion} ({selectedIds.size})
                        </button>
                      </div>
                    </div>
                  )
                })()}
              </div>
            </div>
          </div>
        )
      })()}

      {/* CONSOLIDADO — Sprint Drive E */}
      {activeTab === 3 && (
        <DatosConsolidados studyId={id!} />
      )}
    </>
  )
}
