export default function ConfigPage() {
  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <div className="page-title">Configuración</div>
        <div className="page-sub">Parámetros globales y plantilla del informe</div>
      </div>

      <div className="two-col">
        <div>
          {/* SIG params */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Parámetros SIG globales</span>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Buffer por defecto (metros)</label>
                <input className="form-input" type="number" defaultValue="50" />
              </div>
              <div className="form-group">
                <label className="form-label">Sistema de referencia de coordenadas</label>
                <input className="form-input" defaultValue="WGS84 — EPSG:4326" readOnly />
              </div>
              <div className="form-group">
                <label className="form-label">Escala de mapas temáticos</label>
                <select className="form-select" defaultValue="1:10.000">
                  <option>1:5.000</option>
                  <option>1:10.000</option>
                  <option>1:25.000</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Formato exportación de mapas</label>
                <select className="form-select">
                  <option>PNG 300 dpi</option>
                  <option>SVG</option>
                  <option>PDF</option>
                </select>
              </div>
              <button className="btn btn-primary btn-sm">Guardar cambios</button>
            </div>
          </div>

          {/* Google Drive */}
          <div className="card">
            <div className="card-header">
              <span className="section-title" style={{ margin: 0 }}>Integración Google Drive</span>
            </div>
            <div className="card-body">
              <div className="alert alert-success" style={{ marginBottom: 12 }}>
                ✓ Cuenta de servicio conectada · drive-api@simonky.iam
              </div>
              <div className="form-group">
                <label className="form-label">Carpeta raíz del corpus</label>
                <input className="form-input" defaultValue="CABILDO INDIGENA MUINA" readOnly />
              </div>
              <button className="btn btn-outline btn-sm">Reconfigurar conexión</button>
            </div>
          </div>
        </div>

        {/* Plantilla */}
        <div className="card">
          <div className="card-header">
            <span className="section-title" style={{ margin: 0 }}>Plantilla institucional del informe</span>
          </div>
          <div className="card-body">
            <div className="alert alert-info" style={{ marginBottom: 12 }}>
              ℹ La plantilla define la estructura, tipografía y secciones del documento Word generado.
            </div>
            <div className="corpus-item ok" style={{ marginBottom: 8 }}>
              <div>
                <div className="corpus-label">plantilla_informe_v2.docx</div>
                <div className="corpus-count">Actualizada: May 01, 2026</div>
              </div>
              <span className="badge badge-success">Activa</span>
            </div>
            <div className="flex gap-2 mt-4">
              <button className="btn btn-outline btn-sm">⬇ Descargar plantilla</button>
              <button className="btn btn-primary btn-sm">⬆ Subir nueva versión</button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
