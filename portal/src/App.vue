<script setup>
/**
 * Componente raíz de la aplicación pública.
 * Coordina la estructura general (barra superior o modo kiosco a pantalla completa),
 * la pila de notificaciones globales, la pantalla de mantenimiento y la vista activa.
 */
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

import AppHeader from '@/components/layout/AppHeader.vue'
import KioskCornerMenu from '@/components/layout/KioskCornerMenu.vue'
import AppNotifications from '@/components/layout/AppNotifications.vue'
import HospitalCornerBadge from '@/components/layout/HospitalCornerBadge.vue'
import MaintenanceView from '@/views/MaintenanceView.vue'

const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

/**
 * Indica si la ruta actual debe renderizarse en Modo Kiosco (sin barra de navegación superior).
 */
const isKioskMode = computed(
  () => authStore.isAuthenticated && Boolean(route.meta?.kioskMode),
)

/**
 * Determina si corresponde mostrar la cabecera estándar y el menú de navegación por rol.
 */
const showStandardChrome = computed(
  () =>
    authStore.isAuthenticated &&
    !isKioskMode.value &&
    route.name !== 'login' &&
    route.name !== 'activate-account',
)
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell-kiosk': isKioskMode }">
    <AppHeader v-if="showStandardChrome" />
    <KioskCornerMenu v-if="isKioskMode" />
    <AppNotifications />

    <main class="main-content">
      <MaintenanceView v-if="uiStore.maintenanceActive" />
      <RouterView v-else />
    </main>

    <HospitalCornerBadge />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding-bottom: 3.5rem;
}

.app-shell-kiosk {
  background-color: var(--color-bg);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
