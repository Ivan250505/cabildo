import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getStudies, createStudy, deleteStudy } from '../api/studies'
import { ESTADO_LABEL, ESTADO_BADGE } from './estadoUtils'
import { DEPARTAMENTOS, getMunicipios } from '../data/colombia'
import type { Study, StudyEstado, StudyModo } from '../types'

// Sprints 0-5 (encuestas dinámicas): lógica completa en backend + frontend,
// pero los puntos de entrada visibles permanecen ocultos por decisión de producto.
// Reactivar cambiando a true.
const ENCUESTAS_VISIBLES = false

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
  const [showSelector, setShowSelector] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [modoCreacion, setModoCreacion] = useState<StudyModo>('drive_existente')
  const [form, setForm] = useState(BLANK_STUDY)
  const [studyToDelete, setStudyToDelete] = useState<Study | null>(null)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const crear = useMutation({
    mutationFn: createStudy,
    onSuccess: (nuevo) => {
      qc.invalidateQueries({ queryKey: ['studies'] })
      setShowModal(false)
      setForm(BLANK_STUDY)
      // Si fue modo "encuestas_nuevas", llevarlo directo a EncuestasPage
      if (modoCreacion === 'encuestas_nuevas' && nuevo?.id) {
        navigate(`/estudios/${nuevo.id}/encuestas`)
      }
    },
  })

  function abrirSelector() {
    if (ENCUESTAS_VISIBLES) {
      setShowSelector(true)
    } else {
      // Modo encuestas oculto: saltar selector y crear siempre como "drive_existente"
      setModoCreacion('drive_existente')
      setShowModal(true)
    }
  }

  function seleccionarModo(modo: StudyModo) {
    setModoCreacion(modo)
    setShowSelector(false)
    setShowModal(true)
  }

  const eliminar = useMutation({
    mutationFn: (id: string) => deleteStudy(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['studies'] })
      setStudyToDelete(null)
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
        <button className="btn btn-primary" onClick={abrirSelector}>
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
                        <button
                          className="btn btn-sm"
                          style={{ background: 'var(--danger)', color: '#fff', border: 'none' }}
                          onClick={() => setStudyToDelete(s as Study)}
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal confirmar eliminación */}
      {studyToDelete && (
        <div className="modal-backdrop" onClick={() => !eliminar.isPending && setStudyToDelete(null)}>
          <div className="modal" style={{ maxWidth: 420 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0, color: 'var(--danger)' }}>Eliminar estudio</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setStudyToDelete(null)} disabled={eliminar.isPending}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14, marginBottom: 8 }}>
                ¿Estás seguro de que deseas eliminar el estudio?
              </p>
              <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
                "{studyToDelete.nombre_comunidad}"
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                Esta acción es permanente y eliminará el corpus y todos los datos asociados.
              </p>
              {eliminar.isError && (
                <div className="alert alert-danger" style={{ marginTop: 12 }}>
                  No se pudo eliminar el estudio. Intenta de nuevo.
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setStudyToDelete(null)} disabled={eliminar.isPending}>
                Cancelar
              </button>
              <button
                className="btn"
                style={{ background: 'var(--danger)', color: '#fff', border: 'none' }}
                disabled={eliminar.isPending}
                onClick={() => eliminar.mutate(studyToDelete.id)}
              >
                {eliminar.isPending ? 'Eliminando…' : 'Sí, eliminar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal selector de origen */}
      {showSelector && (
        <div className="modal-backdrop" onClick={() => setShowSelector(false)}>
          <div className="modal" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>¿Cómo vas a crear este estudio?</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowSelector(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gap: 14 }}>
                <button
                  type="button"
                  className="card"
                  style={{
                    textAlign: 'left', padding: 18, border: '2px solid var(--border)',
                    cursor: 'pointer', background: 'transparent',
                  }}
                  onClick={() => seleccionarModo('drive_existente')}
                >
                  <div style={{ fontSize: 28, marginBottom: 4 }}>📂</div>
                  <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
                    Importar de Google Drive
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    El estudio ya existe — los archivos (actas, censos, ficha de pre-campo, etc.)
                    están en una carpeta de Drive. La IA los procesará automáticamente.
                  </div>
                </button>

                <button
                  type="button"
                  className="card"
                  style={{
                    textAlign: 'left', padding: 18, border: '2px solid var(--border)',
                    cursor: 'pointer', background: 'transparent',
                  }}
                  onClick={() => seleccionarModo('encuestas_nuevas')}
                >
                  <div style={{ fontSize: 28, marginBottom: 4 }}>✏</div>
                  <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
                    Empezar desde cero
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    El estudio aún no ha comenzado — voy a llenar los formularios desde la plataforma
                    (Ficha de Pre-campo, Acta de Inicio, Ficha de Comisión, etc.).
                  </div>
                </button>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowSelector(false)}>Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal nuevo estudio */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>Nuevo estudio etnológico</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Nombre de la comunidad *</label>
                <input
                  className="form-input"
                  placeholder="Ej. Cabildo Indígena Murui Muina"
                  value={form.nombre_comunidad}
                  onChange={(e) => setForm(f => ({ ...f, nombre_comunidad: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Pueblo indígena</label>
                <input
                  className="form-input"
                  placeholder="Ej. Murui-Muina (Uitoto)"
                  value={form.pueblo_indigena}
                  onChange={(e) => setForm(f => ({ ...f, pueblo_indigena: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Departamento *</label>
                <select
                  className="form-select"
                  value={form.departamento}
                  onChange={(e) => setForm(f => ({ ...f, departamento: e.target.value, municipio: '' }))}
                >
                  <option value="">— Selecciona un departamento —</option>
                  {DEPARTAMENTOS.map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Municipio *</label>
                <select
                  className="form-select"
                  value={form.municipio}
                  onChange={(e) => setForm(f => ({ ...f, municipio: e.target.value }))}
                  disabled={!form.departamento}
                >
                  <option value="">
                    {form.departamento ? '— Selecciona un municipio —' : '— Primero selecciona el departamento —'}
                  </option>
                  {getMunicipios(form.departamento).map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Contrato de referencia</label>
                <input
                  className="form-input"
                  placeholder="Ej. UC-CPS-MINTERIOR-023-2026"
                  value={form.contrato_referencia}
                  onChange={(e) => setForm(f => ({ ...f, contrato_referencia: e.target.value }))}
                />
              </div>
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
                  modo_creacion: modoCreacion,
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
