import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Plus, Search, Trash2 } from "lucide-react"
import { useForm } from "react-hook-form"
import { getStudies, createStudy, deleteStudy } from "../api/studies"
import Badge from "../components/ui/Badge"
import Spinner from "../components/ui/Spinner"

const DEPARTAMENTOS_CO = [
  "Amazonas","Antioquia","Arauca","Atlántico","Bolívar","Boyacá","Caldas",
  "Caquetá","Casanare","Cauca","Cesar","Chocó","Córdoba","Cundinamarca",
  "Guainía","Guaviare","Huila","La Guajira","Magdalena","Meta","Nariño",
  "Norte de Santander","Putumayo","Quindío","Risaralda","San Andrés",
  "Santander","Sucre","Tolima","Valle del Cauca","Vaupés","Vichada",
]

function CreateModal({ onClose, onCreate }) {
  const { register, handleSubmit, formState: { isSubmitting, errors } } = useForm()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-heading text-xl font-bold text-navy">Nuevo estudio</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>
        <form onSubmit={handleSubmit(onCreate)} className="px-6 py-4 space-y-4">
          <div>
            <label className="label">Nombre de la comunidad *</label>
            <input className="input" {...register("nombre_comunidad", { required: true })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Municipio *</label>
              <input className="input" {...register("municipio", { required: true })} />
            </div>
            <div>
              <label className="label">Departamento *</label>
              <select className="input" {...register("departamento", { required: true })}>
                <option value="">Seleccione…</option>
                {DEPARTAMENTOS_CO.map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Pueblo indígena</label>
              <input className="input" {...register("pueblo_indigena")} />
            </div>
            <div>
              <label className="label">Vereda</label>
              <input className="input" {...register("vereda")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">NIT comunidad</label>
              <input className="input" {...register("nit_comunidad")} />
            </div>
            <div>
              <label className="label">Contrato referencia</label>
              <input className="input" {...register("contrato_referencia")} />
            </div>
          </div>
          <div>
            <label className="label">URL Drive Fase 1</label>
            <input className="input" placeholder="https://drive.google.com/drive/folders/…" {...register("url_drive_fase1")} />
          </div>
          <div>
            <label className="label">URL Drive Fase 2</label>
            <input className="input" placeholder="https://drive.google.com/drive/folders/…" {...register("url_drive_fase2")} />
          </div>
          <div>
            <label className="label">URL Drive Fase 3</label>
            <input className="input" placeholder="https://drive.google.com/drive/folders/…" {...register("url_drive_fase3")} />
          </div>
          <div>
            <label className="label">Notas adicionales</label>
            <textarea className="input resize-none" rows={3} {...register("notas_adicionales")} />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-outline flex-1">Cancelar</button>
            <button type="submit" disabled={isSubmitting} className="btn-primary flex-1">
              {isSubmitting ? "Creando…" : "Crear estudio"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function StudiesPage() {
  const [search, setSearch] = useState("")
  const [showModal, setShowModal] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["studies", search],
    queryFn: () => getStudies({ limit: 50 }),
  })

  const createMut = useMutation({
    mutationFn: createStudy,
    onSuccess: () => { qc.invalidateQueries(["studies"]); setShowModal(false) },
  })

  const deleteMut = useMutation({
    mutationFn: deleteStudy,
    onSuccess: () => qc.invalidateQueries(["studies"]),
  })

  const studies = (data?.items ?? []).filter((s) =>
    !search || s.nombre_comunidad.toLowerCase().includes(search.toLowerCase()) ||
    s.municipio.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-3xl font-bold text-navy">Estudios</h1>
          <p className="text-gray-500 text-sm mt-1">{data?.total ?? 0} estudios registrados</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Nuevo estudio
        </button>
      </div>

      {/* Búsqueda */}
      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          className="input pl-9 max-w-sm"
          placeholder="Buscar por comunidad o municipio…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-navy text-white">
              <tr>
                {["Comunidad", "Pueblo", "Municipio", "Departamento", "Estado", "Acciones"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-semibold text-xs uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {studies.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-12 text-gray-400">No hay estudios.</td></tr>
              ) : studies.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800">
                    <Link to={`/studies/${s.id}`} className="hover:text-primary">{s.nombre_comunidad}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{s.pueblo_indigena || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{s.municipio}</td>
                  <td className="px-4 py-3 text-gray-600">{s.departamento}</td>
                  <td className="px-4 py-3"><Badge label={s.estado} /></td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => { if (confirm("¿Eliminar este estudio?")) deleteMut.mutate(s.id) }}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                      disabled={!["borrador","error"].includes(s.estado)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <CreateModal
          onClose={() => setShowModal(false)}
          onCreate={(data) => createMut.mutateAsync(data)}
        />
      )}
    </div>
  )
}
