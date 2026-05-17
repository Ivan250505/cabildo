import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft, CloudDownload, Cpu, FileText,
  CheckCircle, Download, RefreshCw,
} from "lucide-react"
import {
  getStudy, syncStudy, processCorpus, analyzeGIS,
  generateReport, approveReport, getReports, downloadReportUrl,
} from "../api/studies"
import Badge from "../components/ui/Badge"
import Spinner from "../components/ui/Spinner"
import useAuthStore from "../store/authStore"

function ActionButton({ icon: Icon, label, onClick, disabled, variant = "primary" }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
        variant === "primary" ? "btn-primary" :
        variant === "secondary" ? "btn-secondary" : "btn-outline"
      }`}
    >
      <Icon size={15} />
      {label}
    </button>
  )
}

function StepCard({ step, title, done, children }) {
  return (
    <div className={`card border-l-4 ${done ? "border-success" : "border-gray-200"}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
          done ? "bg-success text-white" : "bg-gray-200 text-gray-600"
        }`}>{done ? "✓" : step}</span>
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      {children}
    </div>
  )
}

export default function StudyDetailPage() {
  const { id } = useParams()
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [msg, setMsg] = useState("")
  const [err, setErr] = useState("")

  const { data: study, isLoading } = useQuery({
    queryKey: ["study", id],
    queryFn: () => getStudy(id),
    refetchInterval: (s) =>
      ["sincronizando", "procesando"].includes(s?.estado) ? 5000 : false,
  })

  const { data: reports } = useQuery({
    queryKey: ["reports", id],
    queryFn: () => getReports(id),
    enabled: !!id,
  })

  const run = (fn, successMsg) =>
    useMutation({
      mutationFn: fn,
      onSuccess: (data) => {
        setMsg(successMsg(data))
        setErr("")
        qc.invalidateQueries(["study", id])
        qc.invalidateQueries(["reports", id])
      },
      onError: (e) => setErr(e.response?.data?.detail || "Error desconocido"),
    })

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const syncMut     = useMutation({ mutationFn: () => syncStudy(id),     onSuccess: (d) => { setMsg(`Sincronizado: ${d.total_downloaded} archivos descargados.`); setErr(""); qc.invalidateQueries(["study",id]) }, onError: (e) => setErr(e.response?.data?.detail || "Error") })
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const processMut  = useMutation({ mutationFn: () => processCorpus(id), onSuccess: (d) => { setMsg(`Procesado: ${d.entidades_extraidas} entidades extraídas.`); setErr(""); qc.invalidateQueries(["study",id]) }, onError: (e) => setErr(e.response?.data?.detail || "Error") })
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const gisMut      = useMutation({ mutationFn: () => analyzeGIS(id),    onSuccess: (d) => { setMsg(`Análisis SIG: ${d.resultados_guardados} resultados guardados.`); setErr(""); qc.invalidateQueries(["study",id]) }, onError: (e) => setErr(e.response?.data?.detail || "Error") })
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const reportMut   = useMutation({ mutationFn: () => generateReport(id),onSuccess: () => { setMsg("Informe generado correctamente."); setErr(""); qc.invalidateQueries(["reports",id]) }, onError: (e) => setErr(e.response?.data?.detail || "Error") })
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const approveMut  = useMutation({ mutationFn: (rid) => approveReport(id, rid), onSuccess: () => { setMsg("Informe aprobado."); setErr(""); qc.invalidateQueries(["reports",id]); qc.invalidateQueries(["study",id]) }, onError: (e) => setErr(e.response?.data?.detail || "Error") })

  if (isLoading) return <div className="flex justify-center py-24"><Spinner size="lg" /></div>
  if (!study) return <p className="p-8 text-gray-500">Estudio no encontrado.</p>

  const estado = study.estado
  const isTecnico = ["admin","tecnico"].includes(user?.rol)
  const isSupervisor = ["admin","tecnico","supervisor"].includes(user?.rol)
  const lastReport = reports?.at(-1)

  return (
    <div className="p-8 max-w-4xl">
      <Link to="/studies" className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy mb-6">
        <ArrowLeft size={15} /> Volver a estudios
      </Link>

      {/* Encabezado */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="font-heading text-3xl font-bold text-navy">{study.nombre_comunidad}</h1>
          {study.pueblo_indigena && (
            <p className="text-gold font-medium mt-1">Pueblo {study.pueblo_indigena}</p>
          )}
          <p className="text-gray-500 text-sm mt-1">{study.municipio}, {study.departamento}</p>
        </div>
        <Badge label={estado} />
      </div>

      {/* Información básica */}
      <div className="card mt-6 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
        {[
          ["NIT", study.nit_comunidad],
          ["Vereda", study.vereda],
          ["Contrato", study.contrato_referencia],
          ["Buffer SIG", `${study.buffer_metros} m`],
        ].map(([k, v]) => v && (
          <div key={k}>
            <p className="text-gray-400 text-xs font-medium uppercase">{k}</p>
            <p className="text-gray-800 font-medium">{v}</p>
          </div>
        ))}
      </div>

      {/* Alertas */}
      {msg && <div className="mt-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-4 py-3">{msg}</div>}
      {err && <div className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-4 py-3">{err}</div>}

      {/* Pipeline de pasos */}
      <div className="mt-6 space-y-4">
        {/* Paso 1 — Sincronizar Drive */}
        <StepCard step={1} title="Sincronizar corpus desde Google Drive"
          done={["corpus_ok","procesando","listo_revision","en_revision","aprobado","exportado"].includes(estado)}>
          <div className="flex flex-wrap gap-2">
            {study.url_drive_fase1 && <span className="text-xs bg-sky-50 text-sky-700 px-2 py-1 rounded">Fase 1 ✓</span>}
            {study.url_drive_fase2 && <span className="text-xs bg-sky-50 text-sky-700 px-2 py-1 rounded">Fase 2 ✓</span>}
            {study.url_drive_fase3 && <span className="text-xs bg-sky-50 text-sky-700 px-2 py-1 rounded">Fase 3 ✓</span>}
          </div>
          {isTecnico && (
            <ActionButton
              icon={syncMut.isPending ? RefreshCw : CloudDownload}
              label={syncMut.isPending ? "Sincronizando…" : "Sincronizar desde Drive"}
              onClick={() => syncMut.mutate()}
              disabled={syncMut.isPending || !["borrador","sincronizando","corpus_ok","error"].includes(estado)}
              variant="secondary"
            />
          )}
        </StepCard>

        {/* Paso 2 — Procesar documentos */}
        <StepCard step={2} title="Procesar documentos con IA (NLP)"
          done={["listo_revision","en_revision","aprobado","exportado"].includes(estado)}>
          <p className="text-xs text-gray-500 mb-3">Extrae entidades, fechas y datos de población del corpus descargado.</p>
          {isTecnico && (
            <ActionButton
              icon={processMut.isPending ? RefreshCw : Cpu}
              label={processMut.isPending ? "Procesando…" : "Procesar corpus"}
              onClick={() => processMut.mutate()}
              disabled={processMut.isPending || !["corpus_ok","error"].includes(estado)}
            />
          )}
        </StepCard>

        {/* Paso 3 — Análisis SIG */}
        <StepCard step={3} title="Análisis SIG (buffers, matrices, mapas)"
          done={["listo_revision","en_revision","aprobado","exportado"].includes(estado)}>
          <p className="text-xs text-gray-500 mb-3">
            Buffer {study.buffer_metros} m · 6 matrices de distancia · 6 solapamientos · mapas PNG.
          </p>
          {isTecnico && (
            <ActionButton
              icon={gisMut.isPending ? RefreshCw : Cpu}
              label={gisMut.isPending ? "Analizando…" : "Ejecutar análisis SIG"}
              onClick={() => gisMut.mutate()}
              disabled={gisMut.isPending || !["corpus_ok","procesando"].includes(estado)}
              variant="secondary"
            />
          )}
        </StepCard>

        {/* Paso 4 — Generar informe */}
        <StepCard step={4} title="Generar informe Word"
          done={!!lastReport && lastReport.estado !== "generando"}>
          <p className="text-xs text-gray-500 mb-3">Genera el documento .docx con portada, análisis SIG, caracterización etnológica y conclusiones.</p>
          <div className="flex flex-wrap gap-2">
            {isTecnico && (
              <ActionButton
                icon={reportMut.isPending ? RefreshCw : FileText}
                label={reportMut.isPending ? "Generando…" : "Generar informe"}
                onClick={() => reportMut.mutate()}
                disabled={reportMut.isPending || !["listo_revision","en_revision","corpus_ok"].includes(estado)}
              />
            )}
            {lastReport && (
              <a
                href={downloadReportUrl(id, lastReport.id)}
                target="_blank"
                rel="noreferrer"
                className="btn-outline flex items-center gap-2"
              >
                <Download size={15} /> Descargar v{lastReport.version}
              </a>
            )}
            {lastReport && isSupervisor && lastReport.estado === "listo_revision" && (
              <ActionButton
                icon={CheckCircle}
                label="Aprobar informe"
                onClick={() => approveMut.mutate(lastReport.id)}
                disabled={approveMut.isPending}
                variant="secondary"
              />
            )}
          </div>
          {lastReport && (
            <p className="text-xs text-gray-400 mt-2">
              Última versión: v{lastReport.version} — <Badge label={lastReport.estado} />
            </p>
          )}
        </StepCard>
      </div>

      {/* Notas */}
      {study.notas_adicionales && (
        <div className="card mt-6">
          <h3 className="font-semibold text-gray-700 mb-2 text-sm">Notas adicionales</h3>
          <p className="text-gray-600 text-sm">{study.notas_adicionales}</p>
        </div>
      )}
    </div>
  )
}
