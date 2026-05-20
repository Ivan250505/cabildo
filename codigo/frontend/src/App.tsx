import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import EstudiosPage from './pages/EstudiosPage'
import DetallePage from './pages/DetallePage'
import GenerarPage from './pages/GenerarPage'
import RevisionPage from './pages/RevisionPage'
import UsuariosPage from './pages/UsuariosPage'
import ConfigPage from './pages/ConfigPage'
import DebugPage from './pages/DebugPage'
import MapaCalorPage from './pages/MapaCalorPage'
import ResumenIAPage from './pages/ResumenIAPage'
import EncuestasPage from './pages/EncuestasPage'
import FormularioPage from './pages/FormularioPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <AppLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="estudios" element={<EstudiosPage />} />
        <Route path="estudios/:id" element={<DetallePage />} />
        <Route path="estudios/:id/generar" element={<GenerarPage />} />
        <Route path="estudios/:id/revision" element={<RevisionPage />} />
        <Route path="estudios/:id/debug" element={<DebugPage />} />
        <Route path="estudios/:id/mapa" element={<MapaCalorPage />} />
        <Route path="estudios/:id/encuestas" element={<EncuestasPage />} />
        <Route path="estudios/:id/encuestas/:code" element={<FormularioPage />} />
        <Route path="resumen-ia" element={<ResumenIAPage />} />
        <Route path="usuarios" element={<UsuariosPage />} />
        <Route path="config" element={<ConfigPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
