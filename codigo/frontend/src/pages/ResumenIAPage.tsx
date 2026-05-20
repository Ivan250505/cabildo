import { useState } from 'react'
import client from '../api/client'

type ResumenResponse = {
  archivo: string
  tamano_bytes: number
  texto_chars: number
  resumen: string
}

export default function ResumenIAPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ResumenResponse | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) {
      setError('Selecciona un archivo primero')
      return
    }
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await client.post<ResumenResponse>('quick/summarize', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(data)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || 'No se pudo generar el resumen')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <h2 className="section-title">Resumen IA de archivo</h2>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 20 }}>
        Sube un documento (PDF, DOCX, XLSX, TXT, CSV) y la IA generará un resumen breve de su contenido.
      </p>

      <form onSubmit={handleSubmit} className="card" style={{ padding: 20 }}>
        <div className="form-group">
          <label className="form-label">Archivo</label>
          <input
            type="file"
            className="form-input"
            accept=".pdf,.docx,.xlsx,.xls,.txt,.md,.csv"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null)
              setError('')
              setResult(null)
            }}
          />
          {file && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              {file.name} · {(file.size / 1024).toFixed(1)} KB
            </div>
          )}
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-lg"
          disabled={loading || !file}
        >
          {loading ? 'Analizando con IA...' : 'Generar resumen'}
        </button>
      </form>

      {error && (
        <div className="login-error" style={{ marginTop: 16 }}>
          {error}
        </div>
      )}

      {result && (
        <div className="card" style={{ padding: 20, marginTop: 20 }}>
          <h3 className="section-title" style={{ fontSize: 16 }}>Resumen</h3>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            {result.archivo} · {result.texto_chars.toLocaleString()} caracteres analizados
          </div>
          <p style={{ lineHeight: 1.6, fontSize: 15, whiteSpace: 'pre-wrap' }}>
            {result.resumen}
          </p>
        </div>
      )}
    </div>
  )
}
