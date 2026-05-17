import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getStudies, createStudy } from '../api/studies'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import type { StudyEstado } from '../types'

const ESTADOS: { value: string; label: string }[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'borrador', label: 'Borrador' },
  { value: 'corpus_ok', label: 'Corpus listo' },
  { value: 'procesando', label: 'Procesando' },
  { value: 'listo_revision', label: 'Para revisión' },
  { value: 'en_revision', label: 'En revisión' },
  { value: 'aprobado', label: 'Aprobado' },
  { value: 'exportado', label: 'Exportado' },
  { value: 'error', label: 'Error' },
]

const BLANK_STUDY = { nombre_comunidad: '', pueblo_indigena: '', municipio: '', departamento: '', contrato_referencia: '' }

export default function EstudiosPage() {
  const [search, setSearch] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(BLANK_STUDY)
  const qc = useQueryClient()

  const crear = useMutation({
    mutationFn: createStudy,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['studies'] })
      setShowModal(false)
      setForm(BLANK_STUDY)
    },
  })

  const { data, isLoading, isError } = useQuery({
    queryKey: ['studies', estadoFilter],
    queryFn: () => getStudies({ estado: estadoFilter || undefined, limit: 100 }),
  })

  const studies = (data?.items ?? []).filter((s) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      s.nombre_comunidad.toLowerCase().includes(q) ||
      s.municipio.toLowerCase().includes(q) ||
      s.departamento.toLowerCase().includes(q) ||
      (s.pueblo_indigena ?? '').toLowerCase().includes(q)
    )
  })

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="page-title">Estudios etnológicos</div>
          <div className="page-sub">
            {isLoading ? 'Cargando…' : `${data?.total ?? 0} estudios registrados`}
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          ＋ Nuevo estudio
        </button>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16, padding: '12px 18px' }}>
        <div className="flex gap-2 items-center" style={{ flexWrap: 'wrap' }}>
          <input
            className="form-input"
            style={{ flex: '1 1 240px', marginBottom: 0 }}
            placeholder="Buscar por comunidad, municipio, pueblo indígena…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="form-select"
            style={{ flex: '0 1 200px', marginBottom: 0 }}
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
          >
            {ESTADOS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading && <div className="loading-state">Cargando estudios…</div>}
          {isError && <div className="loading-state" style={{ color: 'var(--danger)' }}>Error al cargar datos del servidor.</div>}
          {!isLoading && !isError && (
            <table>
              <thead>
                <tr>
                  <th>Comunidad</th>
                  <th>Pueblo indígena</th>
                  <th>Municipio</th>
                  <th>Estado</th>
                  <th>Actualización</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {studies.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty-state">
                      No se encontraron estudios{search ? ` para "${search}"` : ''}.
                    </td>
                  </tr>
                )}
                {studies.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: 600 }}>{s.nombre_comunidad}</td>
                    <td>{s.pueblo_indigena ?? '—'}</td>
                    <td>{s.municipio}, {s.departamento}</td>
                    <td>
                      <span className={`badge ${ESTADO_BADGE[s.estado as StudyEstado] ?? 'badge-neutral'}`}>
                        {ESTADO_LABEL[s.estado as StudyEstado] ?? s.estado}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(s.updated_at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <Link to={`/estudios/${s.id}`} className="btn btn-outline btn-sm">
                          Ver detalle
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal nuevo estudio */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>Nuevo estudio etnológico</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              {[
                { label: 'Nombre de la comunidad *', key: 'nombre_comunidad', placeholder: 'Ej. Cabildo Indígena Murui Muina' },
                { label: 'Pueblo indígena', key: 'pueblo_indigena', placeholder: 'Ej. Murui-Muina (Uitoto)' },
                { label: 'Municipio *', key: 'municipio', placeholder: 'Ej. Florencia' },
                { label: 'Departamento *', key: 'departamento', placeholder: 'Ej. Caquetá' },
                { label: 'Contrato de referencia', key: 'contrato_referencia', placeholder: 'Ej. UC-CPS-MINTERIOR-023-2026' },
              ].map(({ label, key, placeholder }) => (
                <div className="form-group" key={key}>
                  <label className="form-label">{label}</label>
                  <input
                    className="form-input"
                    placeholder={placeholder}
                    value={form[key as keyof typeof form]}
                    onChange={(e) => setForm(f => ({ ...f, [key]: e.target.value }))}
                  />
                </div>
              ))}
              {crear.isError && (
                <div className="login-error">Error al crear el estudio. Verifica los campos requeridos.</div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancelar</button>
              <button
                className="btn btn-primary"
                disabled={!form.nombre_comunidad || !form.municipio || !form.departamento || crear.isPending}
                onClick={() => crear.mutate({
                  nombre_comunidad: form.nombre_comunidad,
                  pueblo_indigena: form.pueblo_indigena || undefined,
                  municipio: form.municipio,
                  departamento: form.departamento,
                  contrato_referencia: form.contrato_referencia || undefined,
                })}
              >
                {crear.isPending ? 'Creando…' : 'Crear estudio'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
