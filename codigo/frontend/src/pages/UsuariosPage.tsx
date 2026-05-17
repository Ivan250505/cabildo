import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, createUser, updateUser, deactivateUser } from '../api/users'
import type { BackendUser } from '../types'

const ROL_LABEL: Record<BackendUser['rol'], string> = {
  admin: 'Administrador', tecnico: 'Responsable Técnico',
  campo: 'Equipo de campo', supervisor: 'Supervisor',
}
const ROL_BADGE: Record<BackendUser['rol'], string> = {
  admin: 'badge-warning', tecnico: 'badge-info',
  campo: 'badge-neutral', supervisor: 'badge-info',
}
const ROLES = ['tecnico', 'campo', 'supervisor', 'admin'] as const

function getInitials(name: string) {
  return name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()
}

export default function UsuariosPage() {
  const qc = useQueryClient()
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [showNuevo, setShowNuevo] = useState(false)
  const [editUser, setEditUser] = useState<BackendUser | null>(null)

  const [nuevoForm, setNuevoForm] = useState({ nombre_completo: '', email: '', password: '', rol: 'tecnico' as BackendUser['rol'] })
  const [editForm, setEditForm] = useState({ nombre_completo: '', rol: 'tecnico' as BackendUser['rol'], estado: 'activo' as BackendUser['estado'] })

  const { data, isLoading, isError } = useQuery({
    queryKey: ['users'],
    queryFn: () => getUsers({ limit: 100 }),
  })

  const crear = useMutation({
    mutationFn: createUser,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setShowNuevo(false); setNuevoForm({ nombre_completo: '', email: '', password: '', rol: 'tecnico' }) },
  })

  const editar = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateUser>[1] }) => updateUser(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setEditUser(null) },
  })

  const desactivar = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setConfirmId(null) },
  })

  const users = data?.items ?? []

  function openEdit(u: BackendUser) {
    setEditUser(u)
    setEditForm({ nombre_completo: u.nombre_completo, rol: u.rol, estado: u.estado })
  }

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="page-title">Gestión de usuarios</div>
          <div className="page-sub">{isLoading ? 'Cargando…' : `${data?.total ?? 0} usuarios registrados`}</div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNuevo(true)}>＋ Nuevo usuario</button>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading && <div className="loading-state">Cargando usuarios…</div>}
          {isError && <div className="loading-state" style={{ color: 'var(--danger)' }}>Error al cargar usuarios.</div>}
          {!isLoading && !isError && (
            <table>
              <thead>
                <tr>
                  <th>Usuario</th><th>Correo</th><th>Rol</th><th>Estado</th>
                  <th>Estudios</th><th>Último acceso</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 && <tr><td colSpan={7} className="empty-state">No hay usuarios.</td></tr>}
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="avatar" style={{ width: 32, height: 32, fontSize: 12 }}>{getInitials(u.nombre_completo)}</div>
                        <div style={{ fontWeight: 600 }}>{u.nombre_completo}</div>
                      </div>
                    </td>
                    <td>{u.email}</td>
                    <td><span className={`badge ${ROL_BADGE[u.rol]}`}>{ROL_LABEL[u.rol]}</span></td>
                    <td>
                      {u.estado === 'activo'
                        ? <span className="badge badge-success"><span className="badge-dot" />Activo</span>
                        : <span className="badge badge-neutral">Suspendido</span>}
                    </td>
                    <td style={{ textAlign: 'center' }}>{u.estudios_asignados}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {u.ultimo_acceso ? new Date(u.ultimo_acceso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button className="btn btn-outline btn-sm" onClick={() => openEdit(u)}>Editar</button>
                        {u.estado === 'activo' && u.rol !== 'admin' && (
                          confirmId === u.id ? (
                            <>
                              <button className="btn btn-sm" style={{ background: 'var(--danger)', color: '#fff' }}
                                onClick={() => desactivar.mutate(u.id)} disabled={desactivar.isPending}>
                                ¿Confirmar?
                              </button>
                              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmId(null)}>Cancelar</button>
                            </>
                          ) : (
                            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--danger)' }}
                              onClick={() => setConfirmId(u.id)}>
                              Desactivar
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal nuevo usuario */}
      {showNuevo && (
        <div className="modal-backdrop" onClick={() => setShowNuevo(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>Nuevo usuario</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowNuevo(false)}>✕</button>
            </div>
            <div className="modal-body">
              {[
                { label: 'Nombre completo *', key: 'nombre_completo', type: 'text', placeholder: 'María Fernanda López' },
                { label: 'Correo electrónico *', key: 'email', type: 'email', placeholder: 'usuario@entidad.gov.co' },
                { label: 'Contraseña inicial *', key: 'password', type: 'password', placeholder: '••••••••' },
              ].map(({ label, key, type, placeholder }) => (
                <div className="form-group" key={key}>
                  <label className="form-label">{label}</label>
                  <input className="form-input" type={type} placeholder={placeholder}
                    value={nuevoForm[key as keyof typeof nuevoForm]}
                    onChange={(e) => setNuevoForm(f => ({ ...f, [key]: e.target.value }))} />
                </div>
              ))}
              <div className="form-group">
                <label className="form-label">Rol *</label>
                <select className="form-select" value={nuevoForm.rol}
                  onChange={(e) => setNuevoForm(f => ({ ...f, rol: e.target.value as BackendUser['rol'] }))}>
                  {ROLES.map(r => <option key={r} value={r}>{ROL_LABEL[r]}</option>)}
                </select>
              </div>
              {crear.isError && <div className="login-error">Error al crear usuario.</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowNuevo(false)}>Cancelar</button>
              <button className="btn btn-primary"
                disabled={!nuevoForm.nombre_completo || !nuevoForm.email || !nuevoForm.password || crear.isPending}
                onClick={() => crear.mutate(nuevoForm)}>
                {crear.isPending ? 'Creando…' : 'Crear usuario'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal editar usuario */}
      {editUser && (
        <div className="modal-backdrop" onClick={() => setEditUser(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>Editar — {editUser.nombre_completo}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setEditUser(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Nombre completo</label>
                <input className="form-input" value={editForm.nombre_completo}
                  onChange={(e) => setEditForm(f => ({ ...f, nombre_completo: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Rol</label>
                <select className="form-select" value={editForm.rol}
                  onChange={(e) => setEditForm(f => ({ ...f, rol: e.target.value as BackendUser['rol'] }))}>
                  {ROLES.map(r => <option key={r} value={r}>{ROL_LABEL[r]}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Estado</label>
                <select className="form-select" value={editForm.estado}
                  onChange={(e) => setEditForm(f => ({ ...f, estado: e.target.value as BackendUser['estado'] }))}>
                  <option value="activo">Activo</option>
                  <option value="suspendido">Suspendido</option>
                </select>
              </div>
              {editar.isError && <div className="login-error">Error al actualizar usuario.</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setEditUser(null)}>Cancelar</button>
              <button className="btn btn-primary" disabled={editar.isPending}
                onClick={() => editar.mutate({ id: editUser.id, payload: editForm })}>
                {editar.isPending ? 'Guardando…' : 'Guardar cambios'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
