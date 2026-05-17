import { useEffect } from "react"
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet"
import "leaflet/dist/leaflet.css"

function FitBounds({ features }) {
  const map = useMap()
  useEffect(() => {
    if (!features?.length) return
    const coords = features.map((f) => [
      f.geometry.coordinates[1],
      f.geometry.coordinates[0],
    ])
    map.fitBounds(coords, { padding: [40, 40], maxZoom: 12 })
  }, [features, map])
  return null
}

export default function ResguardosMap({ geojson, height = "100%" }) {
  const features = geojson?.features ?? []

  return (
    <MapContainer
      center={[4.5, -74.0]}
      zoom={6}
      style={{ height, width: "100%" }}
      className="rounded-lg"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {features.map((f, i) => {
        const [lng, lat] = f.geometry.coordinates
        const p = f.properties
        return (
          <CircleMarker
            key={i}
            center={[lat, lng]}
            radius={10}
            pathOptions={{
              color: "#fff",
              weight: 2,
              fillColor: p.color || "#B22222",
              fillOpacity: 0.85,
            }}
          >
            <Popup>
              <div className="text-sm space-y-1 min-w-[180px]">
                <p className="font-bold text-navy leading-tight">{p.nombre_comunidad}</p>
                {p.pueblo_indigena && <p className="text-gold font-medium">{p.pueblo_indigena}</p>}
                <p className="text-gray-600">{p.municipio}, {p.departamento}</p>
                <span
                  className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium"
                  style={{ background: p.color + "22", color: p.color }}
                >
                  {p.estado?.replace(/_/g, " ")}
                </span>
              </div>
            </Popup>
          </CircleMarker>
        )
      })}

      {features.length > 0 && <FitBounds features={features} />}
    </MapContainer>
  )
}
