const COLORS = {
  borrador:       "bg-gray-100 text-gray-700",
  sincronizando:  "bg-blue-100 text-blue-700",
  corpus_ok:      "bg-sky-100 text-sky-700",
  procesando:     "bg-orange-100 text-orange-700",
  listo_revision: "bg-lime-100 text-lime-700",
  en_revision:    "bg-green-100 text-green-700",
  aprobado:       "bg-navy/10 text-navy",
  exportado:      "bg-primary/10 text-primary",
  error:          "bg-red-100 text-red-700",
  activo:         "bg-green-100 text-green-700",
  suspendido:     "bg-gray-100 text-gray-500",
  admin:          "bg-primary/10 text-primary font-bold",
  tecnico:        "bg-navy/10 text-navy",
  supervisor:     "bg-gold/10 text-gold-600",
  campo:          "bg-lime-100 text-lime-700",
}

export default function Badge({ label }) {
  const cls = COLORS[label] ?? "bg-gray-100 text-gray-600"
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label?.replace(/_/g, " ")}
    </span>
  )
}
