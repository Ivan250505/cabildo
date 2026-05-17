import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, RotateCcw, UserX } from "lucide-react"
import { useForm } from "react-hook-form"
import { getUsers, createUser, deleteUser, resetPassword } from "../api/users"
import Badge from "../components/ui/Badge"
import Spinner from "../components/ui/Spinner"

function CreateUserModal({ onClose, onCreate }) {
  const { register, handleSubmit, formState: { isSubmitting } } = useForm()
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h3 className="font-heading text-xl font-bold text-navy">Nuevo usuario</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>
        <form onSubmit={handleSubmit(onCreate)} className="px-6 py-4 space-y-4">
          <div>
            <label className="label">Nombre completo *</label>
            <input className="input" {...register("nombre_completo", { required: true })} />
          </div>
          <div>
            <label className="label">Correo electrónico *</label>
            <input type="email" className="input" {...register("email", { required: true })} />
          </div>
          <div>
            <label className="label">Contraseña temporal *</label>
            <input type="password" className="input" {...register("password", { required: true, minLength: 8 })} />
          </div>
          <div>
            <label className="label">Rol *</label>
            <select className="input" {...register("rol", { required: true })}>
              <option value="tecnico">Técnico</option>
              <option value="campo">Campo</option>
              <option value="supervisor">Supervisor</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-outline flex-1">Cancelar</button>
            <button type="submit" disabled={isSubmitting} className="btn-primary flex-1">
              {isSubmitting ? "Creando…" : "Crear usuario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function UsersPage() {
  const [showModal, setShowModal] = useState(false)
  const [resetMsg, setResetMsg] = useState("")
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn:  () => getUsers({ limit: 100 }),
  })

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => { qc.invalidateQueries(["users"]); setShowModal(false) },
  })

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries(["users"]),
  })

  const resetMut = useMutation({
    mutationFn: resetPassword,
    onSuccess: (d) => setResetMsg(d.message),
  })

  const users = data?.items ?? []

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-3xl font-bold text-navy">Usuarios</h1>
          <p className="text-gray-500 text-sm mt-1">{data?.total ?? 0} usuarios registrados</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Nuevo usuario
        </button>
      </div>

      {resetMsg && (
        <div className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-4 py-3">
          {resetMsg}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-navy text-white">
              <tr>
                {["Nombre","Email","Rol","Estado","Último acceso","Acciones"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">{u.nombre_completo}</td>
                  <td className="px-4 py-3 text-gray-500">{u.email}</td>
                  <td className="px-4 py-3"><Badge label={u.rol} /></td>
                  <td className="px-4 py-3"><Badge label={u.estado} /></td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {u.ultimo_acceso ? new Date(u.ultimo_acceso).toLocaleDateString("es-CO") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => { if (confirm("¿Resetear contraseña?")) resetMut.mutate(u.id) }}
                        className="text-gray-400 hover:text-navy transition-colors"
                        title="Resetear contraseña"
                      >
                        <RotateCcw size={14} />
                      </button>
                      <button
                        onClick={() => { if (confirm("¿Suspender usuario?")) deleteMut.mutate(u.id) }}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Suspender"
                      >
                        <UserX size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <CreateUserModal
          onClose={() => setShowModal(false)}
          onCreate={(data) => createMut.mutateAsync(data)}
        />
      )}
    </div>
  )
}
