import { useEffect, useRef, useState } from 'react'
import type { CorpusRol, CorpusClasificacionFuente } from '../types'
import { CATALOGO_ROLES, ROL_ICON, ROL_LABEL, FUENTE_LABEL } from '../data/catalogoRoles'

interface Props {
  rol: CorpusRol | null
  fuente: CorpusClasificacionFuente | null
  confianza: number | null
  onChange: (nuevoRol: CorpusRol) => Promise<void> | void
  disabled?: boolean
  compact?: boolean
}

// Colores por fuente — refleja la confianza visualmente
const FUENTE_COLOR: Record<string, { bg: string; fg: string; border: string }> = {
  manual:                  { bg: '#dcfce7', fg: '#166534', border: '#86efac' },
  heuristica_extension:    { bg: '#dbeafe', fg: '#1e40af', border: '#93c5fd' },
  heuristica_carpeta:      { bg: '#dbeafe', fg: '#1e40af', border: '#93c5fd' },
  heuristica_nombre:       { bg: '#e0f2fe', fg: '#075985', border: '#7dd3fc' },
  heuristica_nombre_debil: { bg: '#fef3c7', fg: '#92400e', border: '#fcd34d' },
  ia_inicio:               { bg: '#ede9fe', fg: '#5b21b6', border: '#c4b5fd' },
  fallback_otro:           { bg: '#fee2e2', fg: '#991b1b', border: '#fca5a5' },
}

export default function RolBadge({ rol, fuente, confianza, onChange, disabled, compact }: Props) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const color = FUENTE_COLOR[fuente ?? 'fallback_otro'] ?? FUENTE_COLOR.fallback_otro
  const label = rol ? ROL_LABEL[rol] : 'Sin clasificar'
  const icono = rol ? ROL_ICON[rol] : '❓'
  const fuenteLabel = fuente ? FUENTE_LABEL[fuente] ?? fuente : '—'
  const confianzaTxt = confianza != null ? ` · ${Math.round(confianza * 100)}%` : ''

  async function pick(nuevo: CorpusRol) {
    if (nuevo === rol) { setOpen(false); return }
    setBusy(true)
    try { await onChange(nuevo) } finally { setBusy(false); setOpen(false) }
  }

  // Agrupar por fase para el dropdown
  const fase1 = CATALOGO_ROLES.filter(r => r.fase === 'FASE1')
  const fase2 = CATALOGO_ROLES.filter(r => r.fase === 'FASE2')
  const otros = CATALOGO_ROLES.filter(r => r.fase === 'cualquiera')

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        disabled={disabled || busy}
        onClick={() => setOpen(o => !o)}
        title={`Fuente: ${fuenteLabel}${confianzaTxt}${disabled ? '' : ' · click para cambiar'}`}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: compact ? '2px 8px' : '4px 10px',
          fontSize: compact ? 11 : 12, fontWeight: 600,
          background: color.bg, color: color.fg, border: `1px solid ${color.border}`,
          borderRadius: 12, cursor: disabled ? 'default' : 'pointer',
          whiteSpace: 'nowrap', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis',
          opacity: busy ? 0.6 : 1,
        }}
      >
        <span>{icono}</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</span>
        {!disabled && <span style={{ opacity: 0.6, marginLeft: 2 }}>▾</span>}
      </button>

      {open && (
        <div
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 4,
            background: '#fff', border: '1px solid var(--border)', borderRadius: 8,
            boxShadow: '0 10px 30px rgba(0,0,0,.18)', zIndex: 50,
            minWidth: 280, maxHeight: 380, overflowY: 'auto',
          }}
        >
          <RolGrupo titulo="📁 FASE 1 — Pre-campo" items={fase1} actual={rol} onPick={pick} />
          <RolGrupo titulo="📁 FASE 2 — Campo"     items={fase2} actual={rol} onPick={pick} />
          <RolGrupo titulo="Otros"                  items={otros} actual={rol} onPick={pick} />
        </div>
      )}
    </div>
  )
}

function RolGrupo({
  titulo, items, actual, onPick,
}: {
  titulo: string
  items: typeof CATALOGO_ROLES
  actual: CorpusRol | null
  onPick: (r: CorpusRol) => void
}) {
  return (
    <div>
      <div style={{
        fontSize: 10, fontWeight: 700, color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '.5px',
        padding: '8px 12px 4px', background: 'var(--bg-alt)',
      }}>
        {titulo}
      </div>
      {items.map(r => (
        <button
          key={r.code}
          type="button"
          onClick={() => onPick(r.code)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%',
            padding: '6px 12px', fontSize: 12, textAlign: 'left',
            background: r.code === actual ? '#eff6ff' : 'transparent',
            color: r.code === actual ? '#1e40af' : 'inherit',
            border: 'none', cursor: 'pointer',
            fontWeight: r.code === actual ? 600 : 400,
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#f3f4f6' }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = r.code === actual ? '#eff6ff' : 'transparent' }}
        >
          <span>{r.icono}</span>
          <span style={{ flex: 1 }}>{r.nombre}</span>
          {r.prioridad === 'alta' && (
            <span style={{ fontSize: 9, color: '#92400e', background: '#fef3c7', padding: '1px 5px', borderRadius: 4 }}>
              alta
            </span>
          )}
          {r.requeridoFase3 && (
            <span style={{ fontSize: 9, color: '#166534', background: '#dcfce7', padding: '1px 5px', borderRadius: 4 }}>
              F3
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
