import { useQuery } from "@tanstack/react-query"
import { FolderOpen, CheckCircle, AlertCircle, Clock } from "lucide-react"
import { Link } from "react-router-dom"
import { getStudies } from "../api/studies"
import Badge from "../components/ui/Badge"
import Spinner from "../components/ui/Spinner"
import useAuthStore from "../store/authStore"

const ESTADOS_ACTIVOS = ["sincronizando", "corpus_ok", "procesando", "listo_revision", "en_revision"]

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const { data, isLoading } = useQuery({
    queryKey: ["studies"],
    queryFn: () => getStudies({ limit: 100 }),
  })

  const studies = data?.items ?? []
  const total     = data?.total ?? 0
  const aprobados = studies.filter((s) => s.estado === "aprobado").length
  const enProceso = studies.filter((s) => ESTADOS_ACTIVOS.includes(s.estado)).length
  const errores   = studies.filter((s) => s.estado === "error").length

  return (
    <div className="p-8">
      {/* Encabezado */}
      <div className="mb-8">
        <h1 className="font-heading text-3xl font-bold text-navy">
          Bienvenido, {user?.nombre_completo?.split(" ")[0]}
        </h1>
        <p className="text-gray-500 mt-1">
          Panel de control — EtnoSIG · Simonky S.A.S.
        </p>
      </div>

      {/* Estadísticas */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={FolderOpen}  label="Total estudios"  value={total}     color="bg-navy" />
            <StatCard icon={CheckCircle} label="Aprobados"       value={aprobados} color="bg-success" />
            <StatCard icon={Clock}       label="En proceso"      value={enProceso} color="bg-warning" />
            <StatCard icon={AlertCircle} label="Con error"       value={errores}   color="bg-danger" />
          </div>

          {/* Estudios recientes */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading text-xl font-semibold text-navy">Estudios recientes</h2>
              <Link to="/studies" className="text-sm text-primary hover:underline">Ver todos</Link>
            </div>

            {studies.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-8">
                No hay estudios registrados aún.{" "}
                <Link to="/studies" className="text-primary hover:underline">Crear el primero</Link>
              </p>
            ) : (
              <div className="divide-y divide-gray-100">
                {studies.slice(0, 8).map((s) => (
                  <Link
                    key={s.id}
                    to={`/studies/${s.id}`}
                    className="flex items-center justify-between py-3 hover:bg-gray-50 -mx-2 px-2 rounded transition-colors"
                  >
                    <div>
                      <p className="font-medium text-gray-800 text-sm">{s.nombre_comunidad}</p>
                      <p className="text-xs text-gray-400">{s.municipio}, {s.departamento}</p>
                    </div>
                    <Badge label={s.estado} />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
