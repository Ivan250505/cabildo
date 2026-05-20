import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listStudySurveys, type SurveyEstado, type SurveyResponseSummary } from '../api/surveys'
import { getStudy } from '../api/studies'
import { toast } from '../lib/toast'

const ENCUESTAS_HABILITADAS = new Set([
  'ficha_precampo', 'acta_inicio', 'registro_asistencia', 'ficha_comision',
  'diario_campo', 'apuntes_reuniones',
])

const ICONOS: Record<string, string> = {
  ficha_precampo: '✏',
  autocenso: '📋',
  acta_inicio: '📝',
  registro_asistencia: '👥',
  ficha_comision: '📃',
  diario_campo: '📒',
  apuntes_reuniones: '🗒',
  arbol_riesgos: '⚠',
}

const ESTADO_LABEL: Record<SurveyEstado, string> = {
  no_iniciada: 'No iniciada',
  borrador: 'En borrador',
  en_revision: 'En revisión',
  completada: 'Completada',
}

const ESTADO_BADGE: Record<SurveyEstado, string> = {
  no_iniciada: 'badge-neutral',
  borrador: 'badge-warning',
  en_revision: 'badge-info',
  completada: 'badge-success',
}

export default function EncuestasPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: study } = useQuery({
    queryKey: ['study', id],
    queryFn: () => getStudy(id!),
    enabled: !!id,
  })

  const { data: surveys = [], isLoading } = useQuery({
    queryKey: ['study-surveys', id],
    queryFn: () => listStudySurveys(id!),
    enabled: !!id,
  })

  const fase1 = surveys.filter(s => s.fase === 'FASE1')
  const fase2 = surveys.filter(s => s.fase === 'FASE2')
  const completadas = surveys.filter(s => s.estado === 'completada').length

  function handleAbrir(code: string) {
    if (ENCUESTAS_HABILITADAS.has(code)) {
      navigate(`/estudios/${id}/encuestas/${code}`)
    } else {
      toast.info('Próximamente', `Esta encuesta estará disponible en un sprint posterior.`)
    }
  }

  if (isLoading) return <div className="loading-state">Cargando encuestas…</div>

  return (
    <>
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body">
          <div className="flex justify-between items-center">
            <div>
              <div className="page-title">Encuestas del estudio</div>
              <div className="page-sub">
                {study?.nombre_comunidad ?? 'Cargando…'}
                {' · '}
                <strong>{completadas}/{surveys.length}</strong> completadas
              </div>
            </div>
            <Link to={`/estudios/${id}`} className="btn btn-outline">
              ← Volver al estudio
            </Link>
          </div>
        </div>
      </div>

      <SurveyGroup titulo="📁 FASE 1 — Pre-campo" surveys={fase1} onAbrir={handleAbrir} />
      <SurveyGroup titulo="📁 FASE 2 — Campo" surveys={fase2} onAbrir={handleAbrir} />
    </>
  )
}

function SurveyGroup({
  titulo,
  surveys,
  onAbrir,
}: {
  titulo: string
  surveys: SurveyResponseSummary[]
  onAbrir: (code: string) => void
}) {
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-header">
        <span className="section-title" style={{ margin: 0 }}>{titulo}</span>
        <span className="text-sm text-muted">{surveys.length} formularios</span>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        {surveys.map(s => (
          <div
            key={s.survey_type_code}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <span style={{ fontSize: 22 }}>{ICONOS[s.survey_type_code] ?? '📄'}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{s.survey_type_nombre}</div>
              {s.updated_at && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  Última edición: {new Date(s.updated_at).toLocaleString('es-CO')}
                </div>
              )}
            </div>
            <span className={`badge ${ESTADO_BADGE[s.estado]}`} style={{ fontSize: 11 }}>
              {ESTADO_LABEL[s.estado]}
            </span>
            <button
              className="btn btn-outline btn-sm"
              onClick={() => onAbrir(s.survey_type_code)}
            >
              {s.estado === 'no_iniciada' ? 'Iniciar' : 'Continuar'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
