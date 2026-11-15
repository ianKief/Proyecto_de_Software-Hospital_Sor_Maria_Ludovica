<script setup>
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const kioskMenuOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    kioskMenuOpen.value = false
  },
)

async function handleLogout() {
  await authStore.logout()
  uiStore.notify({
    type: 'info',
    message: 'Sesión cerrada correctamente.',
  })
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="kiosk-corner-controls">
    <button
      type="button"
      class="btn btn-secondary kiosk-trigger-btn"
      :aria-expanded="kioskMenuOpen ? 'true' : 'false'"
      aria-controls="kiosk-corner-menu"
      aria-label="Opciones del operador del comedor"
      @click="kioskMenuOpen = !kioskMenuOpen"
    >
      ⚙ Operador: {{ authStore.userFullName }}
    </button>

    <div
      v-if="kioskMenuOpen"
      id="kiosk-corner-menu"
      class="card kiosk-dropdown"
      role="region"
      aria-label="Menú del turno de comedor"
    >
      <p class="kiosk-operator-info">
        <strong>{{ authStore.userFullName }}</strong>
        <span>{{ authStore.userRole }}</span>
      </p>
      <div class="kiosk-dropdown-actions">
        <RouterLink to="/perfil" class="btn btn-secondary">
          Mi perfil
        </RouterLink>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="authStore.loading"
          @click="handleLogout"
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kiosk-corner-controls {
  position: fixed;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 40;
}

.kiosk-trigger-btn {
  box-shadow: var(--shadow-md);
}

.kiosk-dropdown {
  margin-top: 0.5rem;
  min-width: 240px;
  padding: 1rem;
  box-shadow: var(--shadow-lg);
}

.kiosk-operator-info {
  margin: 0 0 0.75rem;
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
  color: var(--color-brand-navy);
}

.kiosk-operator-info span {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.kiosk-dropdown-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
