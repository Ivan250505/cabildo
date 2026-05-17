import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import useAuthStore from "../store/authStore"

export default function LoginPage() {
  const { login } = useAuthStore()
  const navigate = useNavigate()
  const [error, setError] = useState("")
  const { register, handleSubmit, formState: { isSubmitting } } = useForm()

  const onSubmit = async ({ email, password }) => {
    setError("")
    try {
      await login(email, password)
      navigate("/")
    } catch (e) {
      setError(e.response?.data?.detail || "Credenciales incorrectas")
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Panel izquierdo — branding */}
      <div className="hidden lg:flex w-1/2 flex-col items-center justify-center bg-navy px-12">
        <h1 className="font-heading text-5xl font-bold text-white mb-4">EtnoSIG</h1>
        <p className="text-gold text-lg font-medium mb-8">Simonky S.A.S.</p>
        <p className="text-white/70 text-center text-sm leading-relaxed max-w-xs">
          Plataforma de automatización de estudios etnológicos para el reconocimiento
          de comunidades indígenas ante el Ministerio del Interior de Colombia.
        </p>
        <div className="mt-12 grid grid-cols-2 gap-4 text-center">
          {[
            ["Estudios", "Gestión completa"],
            ["Drive", "Sincronización"],
            ["IA + NLP", "Extracción"],
            ["SIG", "Análisis espacial"],
          ].map(([t, s]) => (
            <div key={t} className="bg-white/10 rounded-lg p-4">
              <p className="text-white font-bold">{t}</p>
              <p className="text-white/50 text-xs">{s}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Panel derecho — formulario */}
      <div className="flex flex-1 items-center justify-center bg-gray-50 px-8">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <h2 className="font-heading text-3xl font-bold text-navy">Iniciar sesión</h2>
            <p className="text-gray-500 text-sm mt-2">Acceda con sus credenciales institucionales</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="label">Correo electrónico</label>
              <input
                type="email"
                className="input"
                placeholder="usuario@simonky.com"
                {...register("email", { required: true })}
              />
            </div>
            <div>
              <label className="label">Contraseña</label>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                {...register("password", { required: true })}
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <button type="submit" disabled={isSubmitting} className="btn-primary w-full py-3">
              {isSubmitting ? "Ingresando..." : "Ingresar"}
            </button>
          </form>

          <p className="text-center text-xs text-gray-400 mt-8">
            Contrato UC-CPS-MINTERIOR-023-2026
          </p>
        </div>
      </div>
    </div>
  )
}
