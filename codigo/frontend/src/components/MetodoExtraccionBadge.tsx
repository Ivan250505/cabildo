import Swal from 'sweetalert2'

interface Props {
  fuente: string | null
}

interface BadgeInfo {
  label: string
  icon: string
  color: { bg: string; fg: string; border: string }
  tooltip: string
  bloqueado?: boolean
}

const STYLES: Record<string, BadgeInfo> = {
  local: {
    label: 'Texto', icon: '📄',
    color: { bg: '#f3f4f6', fg: '#374151', border: '#d1d5db' },
    tooltip: 'Texto nativo extraído localmente (sin IA).',
  },
  tesseract: {
    label: 'OCR Tesseract', icon: '🔍',
    color: { bg: '#ede9fe', fg: '#5b21b6', border: '#c4b5fd' },
    tooltip: 'OCR local con Tesseract sobre todo el archivo.',
  },
  gemini_vision: {
    label: 'Vision (doc)', icon: '👁',
    color: { bg: '#fce7f3', fg: '#9d174d', border: '#f9a8d4' },
    tooltip: 'Gemini Vision sobre el documento completo (caro).',
  },
  ocr_tesseract_paginas: {
    label: 'OCR páginas', icon: '🔍',
    color: { bg: '#ede9fe', fg: '#5b21b6', border: '#c4b5fd' },
    tooltip: 'Tesseract aplicado solo a las páginas sin texto nativo.',
  },
  ocr_vision_paginas: {
    label: 'Vision páginas', icon: '👁',
    color: { bg: '#fce7f3', fg: '#9d174d', border: '#f9a8d4' },
    tooltip: 'Gemini Vision aplicado solo a las páginas sin texto nativo.',
  },
  mixto: {
    label: 'Mixto', icon: '🔀',
    color: { bg: '#fef3c7', fg: '#92400e', border: '#fcd34d' },
    tooltip: 'Algunas páginas con texto nativo, otras con OCR/Vision.',
  },
  excel_tabla: {
    label: 'Excel tabla', icon: '📊',
    color: { bg: '#dcfce7', fg: '#166534', border: '#86efac' },
    tooltip: 'Excel parseado como tabla estructurada — sin llamadas IA.',
  },
  excel_texto: {
    label: 'Excel texto', icon: '📊',
    color: { bg: '#fef3c7', fg: '#92400e', border: '#fcd34d' },
    tooltip: 'Excel aplanado a texto plano (encabezados no reconocidos).',
  },
  exif_gps: {
    label: 'EXIF GPS', icon: '📍',
    color: { bg: '#dcfce7', fg: '#166534', border: '#86efac' },
    tooltip: 'Coordenadas leídas del EXIF de la foto — sin IA.',
  },
  exif_gps_y_vision: {
    label: 'EXIF + Vision', icon: '📷',
    color: { bg: '#dcfce7', fg: '#166534', border: '#86efac' },
    tooltip: 'EXIF GPS + descripción Vision del contenido de la foto.',
  },
  vision_imagen_completa: {
    label: 'Vision foto', icon: '📷',
    color: { bg: '#fce7f3', fg: '#9d174d', border: '#f9a8d4' },
    tooltip: 'Vision sobre la foto (sin EXIF GPS disponible).',
  },
  mdb_no_convertible: {
    label: 'MDB bloqueado', icon: '⚠',
    color: { bg: '#fee2e2', fg: '#991b1b', border: '#fca5a5' },
    tooltip: 'Base de datos Access no convertible. Click para instrucciones.',
    bloqueado: true,
  },
  no_procesable: {
    label: 'No procesable', icon: '❌',
    color: { bg: '#fee2e2', fg: '#991b1b', border: '#fca5a5' },
    tooltip: 'Formato no soportado por el pipeline.',
  },
  failed: {
    label: 'Falló', icon: '❌',
    color: { bg: '#fee2e2', fg: '#991b1b', border: '#fca5a5' },
    tooltip: 'La extracción de texto falló para este archivo.',
  },
}


export default function MetodoExtraccionBadge({ fuente }: Props) {
  if (!fuente) return null
  // Ocultar el badge para 'local' (caso ideal y más común)
  if (fuente === 'local') return null

  const info = STYLES[fuente] ?? {
    label: fuente, icon: 'ℹ',
    color: { bg: '#f3f4f6', fg: '#374151', border: '#d1d5db' },
    tooltip: `Método: ${fuente}`,
  }

  function handleClick() {
    if (info.bloqueado && fuente === 'mdb_no_convertible') {
      Swal.fire({
        title: '⚠ Archivo .mdb / .accdb no convertible',
        html:
          '<div style="text-align:left">' +
          '<p>Las bases de datos Access (.mdb/.accdb) no se procesan automáticamente porque requieren binarios del sistema operativo no disponibles en el servidor.</p>' +
          '<p><strong>Para incluir este archivo en el estudio:</strong></p>' +
          '<ol style="padding-left:20px">' +
          '<li>Ábrelo en <em>Access</em> o <em>LibreOffice Base</em>.</li>' +
          '<li>Exporta cada tabla relevante como <strong>Excel (.xlsx)</strong> o <strong>CSV</strong>.</li>' +
          '<li>Sube los archivos exportados al corpus y reclasifica.</li>' +
          '</ol>' +
          '</div>',
        icon: 'info',
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#1A3A5C',
      })
    }
  }

  return (
    <button
      type="button"
      onClick={info.bloqueado ? handleClick : undefined}
      title={info.tooltip}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 3,
        padding: '2px 7px', fontSize: 10, fontWeight: 600,
        background: info.color.bg, color: info.color.fg,
        border: `1px solid ${info.color.border}`, borderRadius: 10,
        cursor: info.bloqueado ? 'pointer' : 'default',
        whiteSpace: 'nowrap',
      }}
    >
      <span>{info.icon}</span>
      <span>{info.label}</span>
    </button>
  )
}
