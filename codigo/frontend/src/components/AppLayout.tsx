import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

function getInitials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}

function getBreadcrumb(pathname: string): string[] {
  if (pathname.includes('/generar')) return ['Estudios', 'Generar informe']
  if (pathname.includes('/revision')) return ['Estudios', 'Revisar informe']
  if (pathname.match(/\/estudios\/\d+/)) return ['Estudios', 'Vista general']
  if (pathname === '/estudios') return ['Estudios']
  if (pathname === '/dashboard') return ['Dashboard']
  if (pathname === '/resumen-ia') return ['Resumen IA']
  if (pathname === '/usuarios') return ['Administración', 'Usuarios']
  if (pathname === '/config') return ['Administración', 'Configuración']
  return []
}

export default function AppLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [confirmLogout, setConfirmLogout] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const breadcrumbs = getBreadcrumb(pathname)
  const isStudyActive = pathname.startsWith('/estudios')

  return (
    <div className="app">
      {/* ── SIDEBAR ── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="brand">Etn<span>IA</span></div>
          <div className="tagline">Plataforma de análisis etnográfico</div>
        </div>
        <div className="sidebar-gold-bar" />

        <div className="nav-section">
          <div className="nav-label">Principal</div>
          <NavLink to="/dashboard" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span className="icon">⊞</span> Dashboard
          </NavLink>
          <NavLink to="/estudios" className={({ isActive }) => `nav-item${isActive || isStudyActive ? ' active' : ''}`}>
            <span className="icon">📂</span> Estudios
          </NavLink>
          <NavLink to="/resumen-ia" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span className="icon">🤖</span> Resumen IA
          </NavLink>
        </div>

        <div className="nav-section">
          <div className="nav-label">Administración</div>
          <NavLink to="/usuarios" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span className="icon">👥</span> Usuarios
          </NavLink>
          <NavLink to="/config" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span className="icon">⚙</span> Configuración
          </NavLink>
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="avatar">{user ? getInitials(user.name) : 'U'}</div>
            <div>
              <div style={{ color: 'var(--text)', fontSize: '12.5px', fontWeight: 600 }}>
                {user?.name ?? 'Usuario'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {user?.role ?? ''}
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <div className="main">
        {/* TOPBAR */}
        <div className="topbar">
          <div className="topbar-brand">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <circle cx="14" cy="14" r="13" fill="#fff" fillOpacity=".12" stroke="#C8922A" strokeWidth="1.5" />
              <text x="14" y="19" textAnchor="middle" fontSize="12" fill="#fff" fontFamily="serif">🏛</text>
            </svg>
            <span className="topbar-brand-name">EtnIA</span>
          </div>

          <div className="breadcrumb">
            <span>EtnIA</span>
            {breadcrumbs.map((part, i) => (
              <span key={i} style={{ display: 'contents' }}>
                <span className="sep">›</span>
                {i === breadcrumbs.length - 1
                  ? <span className="current">{part}</span>
                  : <span>{part}</span>
                }
              </span>
            ))}
          </div>

          <div className="topbar-actions">
            <button className="btn btn-outline btn-sm">🔔</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setConfirmLogout(true)}>⏻ Salir</button>
          </div>
        </div>

        {/* CONTENT */}
        <div className="content">
          <Outlet />
        </div>

        {/* FOOTER */}
        <footer className="app-footer">
          <strong>EtnIA</strong> · Ministerio del Interior · Dirección de Asuntos Indígenas · Colombia
          &nbsp;·&nbsp; Simonky S.A.S. — Plataforma administrada
        </footer>
      </div>

      {confirmLogout && (
        <div className="modal-backdrop" onClick={() => setConfirmLogout(false)}>
          <div className="modal" style={{ maxWidth: 380 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="section-title" style={{ margin: 0 }}>¿Desea cerrar sesión?</span>
            </div>
            <div className="modal-body" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Su sesión se cerrará y deberá iniciar sesión nuevamente para acceder a la plataforma.
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setConfirmLogout(false)}>
                Cancelar
              </button>
              <button className="btn btn-primary" onClick={handleLogout}>
                Sí, cerrar sesión
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
