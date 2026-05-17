import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getStudies } from '../api/studies'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['studies', 'all'],
    queryFn: () => getStudies({ limit: 100 }),
  })

  const studies = data?.items ?? []

  const stats = [
    {
      label: 'Estudios activos',
      icon: '📂',
      value: studies.filter(s => !['aprobado', 'exportado', 'error'].includes(s.estado)).length,
      sub: 'En cualquier fase',
    },
    {
      label: 'Total registrados',
      icon: '📄',
      value: data?.total ?? 0,
      sub: 'Acumulado histórico',
    },
    {
      label: 'Pendientes revisión',
      icon: '⏳',
      value: studies.filter(s => ['listo_revision', 'en_revision'].includes(s.estado)).length,
      sub: 'Requieren aprobación',
      color: 'var(--warning)',
    },
    {
      label: 'Aprobados / Exportados',
      icon: '✅',
      value: studies.filter(s => ['aprobado', 'exportado'].includes(s.estado)).length,
      sub: 'Finalizados',
      color: 'var(--success)',
    },
  ]

  const recent = [...studies]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 5)

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="page-title">Dashboard</div>
        <div className="page-sub">Resumen del estado de los estudios etnológicos</div>
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        {stats.map((s) => (
          <div className="card stat-card" key={s.label}>
            <div className="stat-icon">{s.icon}</div>
            <div className="stat-value" style={s.color ? { color: s.color } : {}}>
              {isLoading ? '—' : s.value}
            </div>
            <div className="stat-label">{s.label}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Recent studies */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <span className="section-title" style={{ margin: 0 }}>Estudios recientes</span>
          <Link to="/estudios" className="btn btn-outline btn-sm">Ver todos →</Link>
        </div>
        <div className="table-wrap">
          {isLoading && <div className="loading-state">Cargando estudios…</div>}
          {isError && <div className="loading-state" style={{ color: 'var(--danger)' }}>Error al cargar datos.</div>}
          {!isLoading && !isError && (
            <table>
              <thead>
                <tr>
                  <th>Comunidad</th>
                  <th>Municipio</th>
                  <th>Estado</th>
                  <th>Última actualización</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recent.length === 0 && (
                  <tr><td colSpan={5} className="empty-state">No hay estudios registrados aún.</td></tr>
                )}
                {recent.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 600 }}>{s.nombre_comunidad}</td>
                    <td>{s.municipio}, {s.departamento}</td>
                    <td>
                      <span className={`badge ${ESTADO_BADGE[s.estado] ?? 'badge-neutral'}`}>
                        {ESTADO_LABEL[s.estado] ?? s.estado}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(s.updated_at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td>
                      <Link to={`/estudios/${s.id}`} className="btn btn-outline btn-sm">Ver</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  )
}
