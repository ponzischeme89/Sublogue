import { writable } from 'svelte/store'

const TOAST_LIMIT = 4

function createToastStore() {
  const { subscribe, update } = writable([])

  function removeToast(id) {
    update((items) => items.filter((item) => item.id !== id))
  }

  function addToast({ message, tone = 'info', duration = 5200 } = {}) {
    if (!message) return
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    const toast = { id, message, tone }

    update((items) => {
      const next = [toast, ...items]
      return next.slice(0, TOAST_LIMIT)
    })

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
  }

  return { subscribe, addToast, removeToast }
}

export const toasts = createToastStore()
export const addToast = toasts.addToast
export const removeToast = toasts.removeToast
