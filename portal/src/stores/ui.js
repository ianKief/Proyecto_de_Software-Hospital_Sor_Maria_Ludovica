import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Store global de interfaz para mostrar notificaciones (éxito, información,
 * advertencia o error) y controlar el estado de mantenimiento del sitio (503).
 */
export const useUiStore = defineStore('ui', () => {
  const notifications = ref([])
  const maintenanceActive = ref(false)
  const maintenanceMessage = ref(
    'El sistema se encuentra temporalmente en mantenimiento. Por favor, volvé a intentar más tarde.',
  )

  let nextId = 1

  /**
   * Agrega un mensaje flotante o banner global y lo descarta automáticamente
   * luego del tiempo indicado (salvo que timeout sea 0).
   */
  function notify({ type = 'info', message, timeout = 5000 }) {
    if (!message) return null
    const id = nextId++
    notifications.value.push({ id, type, message })

    if (timeout > 0) {
      setTimeout(() => {
        dismissNotification(id)
      }, timeout)
    }

    return id
  }

  /**
   * Elimina una notificación puntual de la pila según su identificador.
   */
  function dismissNotification(id) {
    notifications.value = notifications.value.filter((item) => item.id !== id)
  }

  /**
   * Limpia todas las notificaciones visibles en pantalla.
   */
  function clearNotifications() {
    notifications.value = []
  }

  /**
   * Activa o desactiva la vista global de sitio en mantenimiento cuando la API devuelve 503.
   */
  function setMaintenance(active, customMessage = '') {
    maintenanceActive.value = Boolean(active)
    if (customMessage) {
      maintenanceMessage.value = customMessage
    }
  }

  return {
    notifications,
    maintenanceActive,
    maintenanceMessage,
    notify,
    dismissNotification,
    clearNotifications,
    setMaintenance,
  }
})
