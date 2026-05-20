// Catálogo de roles del corpus para la UI.
// Fuente de verdad: DOCUMENTACION/CATALOGO_TIPOS_ARCHIVO.md
import type { CorpusRol } from '../types'

export interface RolInfo {
  code: CorpusRol
  nombre: string
  fase: 'FASE1' | 'FASE2' | 'cualquiera'
  prioridad: 'alta' | 'media' | 'baja'
  requeridoFase3: boolean
  icono: string
}

export const CATALOGO_ROLES: RolInfo[] = [
  // FASE 1 — alta prioridad
  { code: 'ficha_precampo',      nombre: 'Ficha de Pre-campo',        fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '📋' },
  { code: 'reglamento',          nombre: 'Reglamento Interno',        fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '📜' },
  { code: 'acta_eleccion',       nombre: 'Acta de Elección',          fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '📝' },
  { code: 'acta_posesion',       nombre: 'Acta de Posesión',          fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '📝' },
  { code: 'autocenso_depurado',  nombre: 'Autocenso Depurado',        fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '👥' },
  { code: 'autocenso',           nombre: 'Autocenso',                 fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '👥' },
  { code: 'resena_historica',    nombre: 'Reseña Histórica',          fase: 'FASE1', prioridad: 'alta',  requeridoFase3: true,  icono: '📚' },
  // FASE 1 — media/baja
  { code: 'solicitud_formal',    nombre: 'Solicitud Formal',          fase: 'FASE1', prioridad: 'media', requeridoFase3: false, icono: '✉' },
  { code: 'censo_comunidad',     nombre: 'Censo de la Comunidad',     fase: 'FASE1', prioridad: 'media', requeridoFase3: false, icono: '👥' },
  { code: 'rut_comunidad',       nombre: 'RUT de la Comunidad',       fase: 'FASE1', prioridad: 'media', requeridoFase3: false, icono: '🏷' },
  { code: 'mapa_territorial',    nombre: 'Mapa Territorial',          fase: 'FASE1', prioridad: 'media', requeridoFase3: false, icono: '🗺' },
  { code: 'base_datos_dane',     nombre: 'Base de Datos DANE',        fase: 'FASE1', prioridad: 'baja',  requeridoFase3: false, icono: '📊' },
  // FASE 2 — alta prioridad ("la moneda")
  { code: 'ficha_comision',      nombre: 'Ficha de Comisión',         fase: 'FASE2', prioridad: 'alta',  requeridoFase3: true,  icono: '📃' },
  { code: 'diario_campo',        nombre: 'Diario de Campo',           fase: 'FASE2', prioridad: 'alta',  requeridoFase3: true,  icono: '📒' },
  { code: 'acta_inicio',         nombre: 'Acta de Inicio',            fase: 'FASE2', prioridad: 'alta',  requeridoFase3: true,  icono: '📝' },
  { code: 'arbol_riesgo',        nombre: 'Árbol de Riesgos',          fase: 'FASE2', prioridad: 'alta',  requeridoFase3: true,  icono: '⚠' },
  { code: 'geopackage',          nombre: 'GeoPackage / Shapefile',    fase: 'FASE2', prioridad: 'alta',  requeridoFase3: true,  icono: '🗄' },
  { code: 'proyecto_qgis',       nombre: 'Proyecto QGIS',             fase: 'FASE2', prioridad: 'alta',  requeridoFase3: false, icono: '🗺' },
  // FASE 2 — media/baja
  { code: 'registro_asistencia', nombre: 'Registro de Asistencia',    fase: 'FASE2', prioridad: 'media', requeridoFase3: false, icono: '✍' },
  { code: 'cartografia_social',  nombre: 'Cartografía Social',        fase: 'FASE2', prioridad: 'media', requeridoFase3: false, icono: '🧭' },
  { code: 'apuntes_reuniones',   nombre: 'Apuntes de Reuniones',      fase: 'FASE2', prioridad: 'media', requeridoFase3: false, icono: '🗒' },
  { code: 'evidencia_foto',      nombre: 'Evidencia Fotográfica',     fase: 'FASE2', prioridad: 'baja',  requeridoFase3: false, icono: '📷' },
  // Soporte
  { code: 'cronograma',          nombre: 'Cronograma',                fase: 'cualquiera', prioridad: 'baja', requeridoFase3: false, icono: '📅' },
  { code: 'concepto_etnologico', nombre: 'Concepto Etnológico',       fase: 'cualquiera', prioridad: 'baja', requeridoFase3: false, icono: '🎓' },
  { code: 'borrador_acto_administrativo', nombre: 'Borrador Acto Adm.', fase: 'cualquiera', prioridad: 'baja', requeridoFase3: false, icono: '⚖' },
  { code: 'otro',                nombre: 'Otro / Sin clasificar',     fase: 'cualquiera', prioridad: 'baja', requeridoFase3: false, icono: '❓' },
]

export const ROL_LABEL: Record<CorpusRol, string> = Object.fromEntries(
  CATALOGO_ROLES.map(r => [r.code, r.nombre]),
) as Record<CorpusRol, string>

export const ROL_ICON: Record<CorpusRol, string> = Object.fromEntries(
  CATALOGO_ROLES.map(r => [r.code, r.icono]),
) as Record<CorpusRol, string>

export const FUENTE_LABEL: Record<string, string> = {
  manual: 'Manual',
  heuristica_extension: 'Por extensión',
  heuristica_carpeta: 'Por carpeta',
  heuristica_nombre: 'Por nombre',
  heuristica_nombre_debil: 'Por nombre (débil)',
  ia_inicio: 'IA',
  fallback_otro: 'Sin clasificar',
}
