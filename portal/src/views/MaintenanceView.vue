<script setup>
/**
 * Vista de sitio en mantenimiento (503).
 * Muestra el mensaje configurado por el Administrador y permite comprobar
 * si el mantenimiento ya finalizó sin perder la sesión activa.
 */
import { ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/services/api'

const uiStore = useUiStore()
const authStore = useAuthStore()
const checking = ref(false)

/**
 * Consulta GET /api/configuration para verificar si el modo mantenimiento fue desactivado.
 * Si el sitio volvió a estar operativo y hay un token guardado, sincroniza la sesión del usuario.
 */
async function reintentarConexion() {
  checking.value = true
  try {
    const config = await api.get('/configuration', undefined, { skipAuthRedirect: true })
    if (config && config.mantenimiento_activo) {
      uiStore.setMaintenance(true, config.mensaje_mantenimiento || '')
      return
    }

    uiStore.setMaintenance(false, '')
    if (authStore.token) {
      await authStore.fetchCurrentUser()
    }
  } catch (error) {
    if (error.status !== 503) {
      uiStore.setMaintenance(false, '')
    }
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <section class="container-page" aria-labelledby="maintenance-title" role="alert">
    <div class="card maintenance-card">
      <div class="status-badge" aria-hidden="true">Mantenimiento</div>
      <h1 id="maintenance-title">Sitio temporalmente en mantenimiento</h1>
      <p class="maintenance-message">
        {{ uiStore.maintenanceMessage }}
      </p>
      <div class="actions">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="checking"
          @click="reintentarConexion"
        >
          {{ checking ? 'Verificando estado...' : 'Reintentar acceso' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.maintenance-card {
  max-width: 560px;
  margin: 4rem auto;
  text-align: center;
}

.status-badge {
  display: inline-flex;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background-color: var(--color-warning-bg);
  color: var(--color-warning);
  font-weight: 700;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

h1 {
  margin: 0 0 0.75rem;
  font-size: 1.6rem;
}

.maintenance-message {
  color: var(--color-text-muted);
  margin: 0 0 1.5rem;
}

.actions {
  display: flex;
  justify-content: center;
}
</style>
