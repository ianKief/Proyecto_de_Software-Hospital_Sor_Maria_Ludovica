<script setup>
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

const isKioskMode = computed(
  () => authStore.isAuthenticated && Boolean(route.meta?.kioskMode),
)

const showStandardChrome = computed(
  () => authStore.isAuthenticated && !isKioskMode.value && route.name !== 'login',
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
