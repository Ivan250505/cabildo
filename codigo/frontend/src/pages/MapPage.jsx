import { useQuery } from "@tanstack/react-query"
import { getResguardosGeoJSON, getMapLeyenda } from "../api/studies"
import ResguardosMap from "../components/map/ResguardosMap"
import Spinner from "../components/ui/Spinner"

export default function MapPage() {
  const { data: geojson, isLoading } = useQuery({
    queryKey: ["map-resguardos"],
    queryFn:  () => getResguardosGeoJSON(),
    refetchInterval: 60000,
  })
  const { data: leyenda } = useQuery({
    queryKey: ["map-leyenda"],
    queryFn:  getMapLeyenda,
  })

  return (
    <div className="flex h-full flex-col">
      {/* Encabezado */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
        <div>
          <h1 className="font-heading text-2xl font-bold text-navy">Mapa de Resguardos</h1>
          <p className="text-gray-500 text-sm">
            {geojson?.features?.length ?? 0} comunidades con coordenadas registradas
          </p>
        </div>
        {/* Leyenda de estados */}
        {leyenda && (
          <div className="flex flex-wrap gap-2">
            {leyenda.estados.slice(0,5).map(({ estado, color, label }) => (
              <span key={estado} className="flex items-center gap-1 text-xs text-gray-600">
                <span className="h-3 w-3 rounded-full inline-block" style={{ background: color }} />
                {label}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Mapa */}
      <div className="flex-1 p-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <Spinner size="lg" />
          </div>
        ) : (
          <ResguardosMap geojson={geojson} height="100%" />
        )}
      </div>
    </div>
  )
}
