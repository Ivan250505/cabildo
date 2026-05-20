import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getStudy, getLocations } from '../api/studies'
import type { StudyLocation } from '../api/studies'

// ── Configuración visual por tipo de ubicación ────────────────────────────────

const TIPO_CONFIG: Record<StudyLocation['tipo'], { color: string; label: string; icon: string; radius: number }> = {
  sede_cabildo:       { color: '#22c55e', label: 'Sede del cabildo',      icon: '🏛', radius: 14 },
  sitio_sagrado:      { color: '#f59e0b', label: 'Sitio sagrado',          icon: '✦',  radius: 11 },
  territorio_ancestral:{ color: '#b22222', label: 'Territorio ancestral',  icon: '◆',  radius: 13 },
  lugar_historico:    { color: '#3b82f6', label: 'Lugar histórico',        icon: '📜', radius: 10 },
  ruta_migratoria:    { color: '#8b5cf6', label: 'Ruta migratoria',        icon: '→',  radius: 9  },
  punto_geografico:   { color: '#64748b', label: 'Punto geográfico',       icon: '●',  radius: 8  },
}

const TIPO_ORDER: StudyLocation['tipo'][] = [
  'sede_cabildo', 'sitio_sagrado', 'territorio_ancestral',
  'lugar_historico', 'ruta_migratoria', 'punto_geografico',
]

// Centro por defecto: Caquetá, Colombia
const DEFAULT_CENTER: [number, number] = [1.1, -75.0]

function getMapCenter(locations: StudyLocation[]): [number, number] {
  if (!locations.length) return DEFAULT_CENTER
  const lats = locations.map(l => l.lat)
  const lngs = locations.map(l => l.lng)
  return [
    (Math.min(...lats) + Math.max(...lats)) / 2,
    (Math.min(...lngs) + Math.max(...lngs)) / 2,
  ]
}

function getMapZoom(locations: StudyLocation[]): number {
  if (locations.length <= 1) return 13
  const latSpan = Math.max(...locations.map(l => l.lat)) - Math.min(...locations.map(l => l.lat))
  const lngSpan = Math.max(...locations.map(l => l.lng)) - Math.min(...locations.map(l => l.lng))
  const span = Math.max(latSpan, lngSpan)
  if (span < 0.05) return 13
  if (span < 0.5) return 11
  if (span < 2) return 9
  if (span < 5) return 8
  return 6
}

function ConfidenceBadge({ confianza }: { confianza: number | null }) {
  if (!confianza) return null
  const pct = Math.round(confianza * 100)
  const color = pct >= 85 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <span style={{ fontSize: 10, fontWeight: 600, color, marginLeft: 4 }}>
      {pct}%
    </span>
  )
}

export default function MapaCalorPage() {
  const { id } = useParams<{ id: string }>()
  const [activeTipos, setActiveTipos] = useState<Set<string>>(new Set(TIPO_ORDER))

  const { data: study } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: locations = [], isLoading, isError } = useQuery({
    queryKey: ['locations', id],
    queryFn: () => getLocations(id!),
    enabled: !!id,
  })

  const toggleTipo = (tipo: string) => {
    setActiveTipos(prev => {
      const next = new Set(prev)
      if (next.has(tipo)) next.delete(tipo)
      else next.add(tipo)
      return next
    })
  }

  const visible = locations.filter(l => activeTipos.has(l.tipo))
  const center = getMapCenter(locations)
  const zoom = getMapZoom(locations)

  const byTipo = TIPO_ORDER.map(tipo => ({
    tipo,
    items: locations.filter(l => l.tipo === tipo),
    ...TIPO_CONFIG[tipo],
  })).filter(g => g.items.length > 0)

  return (
    <>
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="page-title">Georreferenciación</div>
          <div className="page-sub">
            {study?.nombre_comunidad} · {locations.length} punto{locations.length !== 1 ? 's' : ''} extraído{locations.length !== 1 ? 's' : ''} del corpus
          </div>
        </div>
        <div className="flex gap-2">
          <Link to={`/estudios/${id}`} className="btn btn-outline">← Volver</Link>
          <Link to={`/estudios/${id}/generar`} className="btn btn-outline">Generar informe</Link>
        </div>
      </div>

      {isLoading && (
        <div className="loading-state">Cargando ubicaciones…</div>
      )}

      {isError && (
        <div className="alert alert-danger">
          No se pudieron cargar las ubicaciones. Verifica que el corpus haya sido procesado.
        </div>
      )}

      {!isLoading && !isError && (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16, alignItems: 'start' }}>

          {/* Panel lateral */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

            {/* Leyenda y filtros */}
            <div className="card">
              <div className="card-header">
                <span className="section-title" style={{ margin: 0, fontSize: 13 }}>Capas</span>
              </div>
              <div className="card-body" style={{ padding: '8px 12px' }}>
                {TIPO_ORDER.map(tipo => {
                  const cfg = TIPO_CONFIG[tipo]
                  const count = locations.filter(l => l.tipo === tipo).length
                  if (!count) return null
                  const active = activeTipos.has(tipo)
                  return (
                    <div
                      key={tipo}
                      onClick={() => toggleTipo(tipo)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '6px 4px', cursor: 'pointer', borderRadius: 4,
                        opacity: active ? 1 : 0.4,
                        transition: 'opacity 0.15s',
                        userSelect: 'none',
                      }}
                    >
                      <span style={{
                        width: 12, height: 12, borderRadius: '50%',
                        background: cfg.color, flexShrink: 0,
                        boxShadow: active ? `0 0 0 2px ${cfg.color}40` : 'none',
                      }} />
                      <span style={{ fontSize: 12, flex: 1 }}>{cfg.label}</span>
                      <span className="badge" style={{ fontSize: 10, background: cfg.color + '22', color: cfg.color }}>
                        {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Lista de puntos */}
            {byTipo.map(({ tipo, items, color, label, icon }) => (
              <div key={tipo} className="card">
                <div className="card-header" style={{ paddingTop: 8, paddingBottom: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color }}>
                    {icon} {label}
                  </span>
                </div>
                <div className="card-body" style={{ padding: '6px 12px' }}>
                  {items.map(loc => (
                    <div key={loc.id} style={{ marginBottom: 8, fontSize: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <strong style={{ color: 'var(--text)' }}>{loc.nombre}</strong>
                        <ConfidenceBadge confianza={loc.confianza} />
                      </div>
                      <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                        {loc.lat.toFixed(5)}, {loc.lng.toFixed(5)}
                      </div>
                      {loc.descripcion && (
                        <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2, lineHeight: 1.4 }}>
                          {loc.descripcion.slice(0, 120)}{loc.descripcion.length > 120 ? '…' : ''}
                        </div>
                      )}
                      {loc.fuente_archivo && (
                        <div style={{ color: 'var(--text-muted)', fontSize: 10, marginTop: 2, fontStyle: 'italic' }}>
                          Fuente: {loc.fuente_archivo}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {locations.length === 0 && (
              <div className="card">
                <div className="card-body">
                  <div className="empty-state" style={{ padding: 24 }}>
                    <div className="empty-state-icon">📍</div>
                    <p style={{ fontSize: 13 }}>No hay coordenadas extraídas aún.</p>
                    <p className="text-sm text-muted">
                      Ejecuta la extracción documental para que la IA identifique coordenadas en el corpus.
                    </p>
                    <Link to={`/estudios/${id}/generar`} className="btn btn-primary" style={{ marginTop: 12, fontSize: 13 }}>
                      Ir a generar
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Mapa */}
          <div style={{ borderRadius: 'var(--radius)', overflow: 'hidden', border: '1px solid var(--border)', height: 600 }}>
            <MapContainer
              center={center}
              zoom={zoom}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; OpenStreetMap'
              />

              {visible.map(loc => {
                const cfg = TIPO_CONFIG[loc.tipo]
                return (
                  <CircleMarker
                    key={loc.id}
                    center={[loc.lat, loc.lng]}
                    radius={cfg.radius}
                    pathOptions={{
                      fillColor: cfg.color,
                      fillOpacity: 0.85,
                      color: '#fff',
                      weight: 2,
                    }}
                  >
                    <Popup>
                      <div style={{ minWidth: 200, fontSize: 13 }}>
                        <strong style={{ color: cfg.color }}>{cfg.icon} {loc.nombre}</strong>
                        <div style={{ color: '#666', fontSize: 11, marginTop: 2 }}>{cfg.label}</div>
                        <hr style={{ margin: '6px 0', border: 'none', borderTop: '1px solid #eee' }} />
                        <div style={{ fontSize: 12 }}>
                          <strong>Coordenadas:</strong>{' '}
                          {loc.lat.toFixed(6)}, {loc.lng.toFixed(6)}
                        </div>
                        {loc.descripcion && (
                          <div style={{ fontSize: 12, marginTop: 4, color: '#444' }}>
                            {loc.descripcion.slice(0, 200)}
                          </div>
                        )}
                        {loc.fuente_archivo && (
                          <div style={{ fontSize: 11, marginTop: 4, color: '#888', fontStyle: 'italic' }}>
                            Fuente: {loc.fuente_archivo}
                          </div>
                        )}
                        {loc.confianza && (
                          <div style={{ fontSize: 11, marginTop: 4, color: '#888' }}>
                            Confianza: {Math.round(loc.confianza * 100)}%
                          </div>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>
          </div>
        </div>
      )}

      {/* Info pie */}
      {locations.length > 0 && (
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
          Coordenadas extraídas automáticamente por IA del corpus documental ·
          Haz clic en un punto del mapa para ver el detalle ·
          Usa los filtros de capa para mostrar u ocultar tipos
        </div>
      )}
    </>
  )
}
