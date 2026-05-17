import type { StudyEstado } from '../types'

export const ESTADO_LABEL: Record<StudyEstado, string> = {
  borrador: 'Borrador',
  sincronizando: 'Sincronizando',
  corpus_ok: 'Corpus listo',
  procesando: 'Procesando',
  listo_revision: 'Para revisión',
  en_revision: 'En revisión',
  aprobado: 'Aprobado',
  exportado: 'Exportado',
  error: 'Error',
}

export const ESTADO_BADGE: Record<StudyEstado, string> = {
  borrador: 'badge-neutral',
  sincronizando: 'badge-info',
  corpus_ok: 'badge-info',
  procesando: 'badge-info',
  listo_revision: 'badge-warning',
  en_revision: 'badge-warning',
  aprobado: 'badge-success',
  exportado: 'badge-success',
  error: 'badge-danger',
}
