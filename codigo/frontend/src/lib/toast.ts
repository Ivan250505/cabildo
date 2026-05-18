import Swal from 'sweetalert2'

const base = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 3500,
  timerProgressBar: true,
  customClass: { popup: 'swal-toast' },
  didOpen: (toast) => {
    toast.addEventListener('mouseenter', Swal.stopTimer)
    toast.addEventListener('mouseleave', Swal.resumeTimer)
  },
})

export const toast = {
  success: (title: string, text?: string) =>
    base.fire({ icon: 'success', title, text }),

  error: (title: string, text?: string) =>
    base.fire({ icon: 'error', title, text, timer: 5000 }),

  warning: (title: string, text?: string) =>
    base.fire({ icon: 'warning', title, text, timer: 4500 }),

  info: (title: string, text?: string) =>
    base.fire({ icon: 'info', title, text }),

  confirm: (title: string, text: string, confirmText = 'Sí, continuar') =>
    Swal.fire({
      title,
      text,
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#B22222',
      cancelButtonColor: '#6b7280',
      confirmButtonText: confirmText,
      cancelButtonText: 'Cancelar',
    }),
}
