import { useEffect } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

import useAuthStore from "./store/authStore"
import { FullPageSpinner } from "./components/ui/Spinner"
import Layout from "./components/layout/Layout"

import LoginPage       from "./pages/LoginPage"
import DashboardPage   from "./pages/DashboardPage"
import StudiesPage     from "./pages/StudiesPage"
import StudyDetailPage from "./pages/StudyDetailPage"
import MapPage         from "./pages/MapPage"
import UsersPage       from "./pages/UsersPage"

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function RequireAuth({ children }) {
  const { user, loading } = useAuthStore()
  if (loading) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }) {
  const { user } = useAuthStore()
  if (user?.rol !== "admin") return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { init } = useAuthStore()
  useEffect(() => { init() }, [init])

  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index           element={<DashboardPage />} />
            <Route path="studies"  element={<StudiesPage />} />
            <Route path="studies/:id" element={<StudyDetailPage />} />
            <Route path="map"      element={<MapPage />} />
            <Route
              path="users"
              element={
                <RequireAdmin>
                  <UsersPage />
                </RequireAdmin>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
