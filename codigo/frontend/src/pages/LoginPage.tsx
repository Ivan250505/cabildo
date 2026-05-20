import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Swal from 'sweetalert2'
import { useAuthStore } from '../stores/authStore'
import { login } from '../api/auth'
import IndigenousDivider from '../components/IndigenousDivider'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { setAuth } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(email, password)
      setAuth(res.access_token, {
        id: res.user.id,
        name: res.user.nombre_completo,
        email: res.user.email,
        role: res.user.rol,
      })

      // Modal de bienvenida
      const nombre = res.user.nombre_completo || res.user.email
      const rol = res.user.rol
      await Swal.fire({
        title: `¡Bienvenido, ${nombre}!`,
        html:
          `<div style="font-size:14px;color:#374151">` +
          `Sesión iniciada como <strong>${rol}</strong>.<br><br>` +
          `<span style="font-size:12px;color:#6b7280">Plataforma EtnIA · Ministerio del Interior</span>` +
          `</div>`,
        icon: 'success',
        confirmButtonText: 'Continuar',
        confirmButtonColor: '#1A3A5C',
        timer: 4000,
        timerProgressBar: true,
      })

      navigate('/dashboard')
    } catch {
      setError('Correo o contraseña incorrectos. Verifique sus credenciales.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-logo">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ marginBottom: 8 }} aria-hidden="true">
            <circle cx="24" cy="24" r="22" fill="#1A3A5C" stroke="#C8922A" strokeWidth="2" />
            <text x="24" y="30" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#fff" fontFamily="serif">🏛</text>
          </svg>
          <div className="brand">Etn<span>IA</span></div>
          <div className="tagline">Plataforma de Análisis Etnográfico · Colombia</div>
        </div>

        <IndigenousDivider patternId="login-wayuu" variant="wayuu" />

        <div className="login-title">Iniciar sesión</div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Correo electrónico</label>
            <input
              className="form-input"
              type="email"
              placeholder="usuario@entidad.gov.co"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Contraseña</label>
            <input
              className="form-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-full btn-lg"
            style={{ marginTop: 8 }}
            disabled={loading}
          >
            {loading ? 'Verificando...' : 'Ingresar →'}
          </button>
        </form>

        <div className="login-footer">
          Acceso restringido al personal autorizado<br />
          <span className="gov-ref">Ministerio del Interior · Protocolo Etnológico</span><br />
          <span>Simonky S.A.S. — Plataforma administrada</span>
        </div>
      </div>
    </div>
  )
}
