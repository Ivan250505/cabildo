import { NavLink } from "react-router-dom"
import {
  LayoutDashboard, FolderOpen, Users, Map,
  LogOut, ChevronRight,
} from "lucide-react"
import useAuthStore from "../../store/authStore"

const NAV = [
  { to: "/",        icon: LayoutDashboard, label: "Dashboard"  },
  { to: "/studies", icon: FolderOpen,      label: "Estudios"   },
  { to: "/map",     icon: Map,             label: "Mapa"        },
]
const ADMIN_NAV = [
  { to: "/users", icon: Users, label: "Usuarios" },
]

export default function Sidebar() {
  const { user, logout } = useAuthStore()

  return (
    <aside className="flex h-screen w-64 flex-col bg-navy text-white">
      {/* Logo */}
      <div className="flex flex-col items-center gap-1 border-b border-white/10 px-6 py-6">
        <span className="font-heading text-2xl font-bold text-white">EtnoSIG</span>
        <span className="text-xs text-gold">Simonky S.A.S.</span>
      </div>

      {/* Navegación */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-white/15 text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}

        {user?.rol === "admin" && (
          <>
            <div className="pt-4 pb-1 px-3 text-xs font-semibold uppercase tracking-wider text-white/40">
              Administración
            </div>
            {ADMIN_NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-white/15 text-white"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* Usuario */}
      <div className="border-t border-white/10 px-4 py-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gold text-navy font-bold text-sm">
            {user?.nombre_completo?.[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.nombre_completo}</p>
            <p className="text-xs text-white/50 capitalize">{user?.rol}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
        >
          <LogOut size={16} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
