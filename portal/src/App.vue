<script setup>
import { ref, computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore, ROLES_OPERATIVOS } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import MaintenanceView from '@/views/MaintenanceView.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const mobileMenuOpen = ref(false)
const kioskMenuOpen = ref(false)

// Cerramos los menús desplegables al cambiar de ruta
watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
    kioskMenuOpen.value = false
  },
)

const isKioskMode = computed(
  () => authStore.isAuthenticated && Boolean(route.meta?.kioskMode),
)

const showStandardChrome = computed(
  () => authStore.isAuthenticated && !isKioskMode.value && route.name !== 'login',
)

const sectorNombre = computed(() => {
  const s = authStore.userSector
  if (!s) return ''
  return typeof s === 'object' ? s.nombre || '' : String(s)
})

/**
 * Opciones de navegación filtradas dinámicamente según el rol del usuario autenticado.
 */
const navItems = computed(() => {
  const role = authStore.userRole
  if (!role) return []

  const allItems = [
    {
      label: 'Pedidos de mi sector',
      to: '/pedidos',
      roles: [ROLES_OPERATIVOS.JEFE_SERVICIO],
    },
    {
      label: 'Autorizaciones',
      to: '/autorizaciones',
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION],
    },
    {
      label: 'Personal',
      to: '/personal',
      roles: [ROLES_OPERATIVOS.JEFE_SERVICIO, ROLES_OPERATIVOS.SERVICIO_ALIMENTACION],
    },
    {
      label: 'Cupos',
      to: '/cupos',
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION, ROLES_OPERATIVOS.JEFE_SERVICIO],
    },
    {
      label: 'Reportes',
      to: '/reportes',
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION, ROLES_OPERATIVOS.JEFE_SERVICIO],
    },
    {
      label: 'Modo Kiosco (Comedor)',
      to: '/comedor',
      roles: [ROLES_OPERATIVOS.SECTOR_COMEDOR],
    },
  ]

  return allItems.filter((item) => item.roles.includes(role))
})

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
  <div class="app-shell" :class="{ 'app-shell-kiosk': isKioskMode }">
    <!-- Barra superior y navegación estándar (oculta en modo kiosco y en /login) -->
    <header v-if="showStandardChrome" class="top-header">
      <div class="header-inner">
        <div class="brand-area">
          <RouterLink :to="authStore.homeRouteByRole" class="brand-link">
            <img
              src="/logo-hospital.png"
              alt="HIAEP Sor María Ludovica - La Plata"
              class="brand-logo-img"
            />
            <span class="brand-system-tag">Servicio de Alimentación</span>
          </RouterLink>
        </div>

        <!-- Botón hamburguesa para pantallas chicas (< 767px) -->
        <button
          type="button"
          class="btn btn-secondary mobile-menu-toggle"
          :aria-expanded="mobileMenuOpen ? 'true' : 'false'"
          aria-controls="main-navigation"
          aria-label="Abrir o cerrar menú de navegación"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <span aria-hidden="true">{{ mobileMenuOpen ? '✕' : '☰' }}</span>
          <span class="toggle-text">Menú</span>
        </button>

        <!-- Datos del usuario autenticado, rol, sector y acciones de cuenta -->
        <div class="user-summary" :class="{ 'mobile-open': mobileMenuOpen }">
          <div class="user-meta">
            <span class="user-fullname">{{ authStore.userFullName }}</span>
            <div class="user-badges">
              <span class="badge badge-role">{{ authStore.userRole }}</span>
              <span
                v-if="authStore.isJefeServicio && sectorNombre"
                class="badge badge-sector"
              >
                Sector: {{ sectorNombre }}
              </span>
            </div>
          </div>

          <div class="user-actions">
            <RouterLink
              to="/perfil"
              class="btn btn-secondary btn-sm"
              :class="{ 'nav-profile-active': route.path === '/perfil' }"
            >
              Mi perfil
            </RouterLink>
            <button
              type="button"
              class="btn btn-primary btn-sm"
              :disabled="authStore.loading"
              @click="handleLogout"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </div>

      <!-- Barra de navegación por rol -->
      <nav
        id="main-navigation"
        aria-label="Navegación principal"
        class="main-nav"
        :class="{ 'mobile-open': mobileMenuOpen }"
      >
        <ul class="nav-list">
          <li v-for="item in navItems" :key="item.to" class="nav-item">
            <RouterLink
              :to="item.to"
              class="nav-link"
              active-class="nav-link-active"
            >
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>
    </header>

    <!-- Acceso discreto en esquina para Modo Kiosco (Sector Comedor) -->
    <div v-if="isKioskMode" class="kiosk-corner-controls">
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

    <!-- Región global de notificaciones (información, éxito, advertencia, error) -->
    <div
      v-if="uiStore.notifications.length > 0"
      class="notifications-stack container-page"
      aria-live="polite"
    >
      <div
        v-for="item in uiStore.notifications"
        :key="item.id"
        class="alert"
        :class="{
          'alert-error': item.type === 'error',
          'alert-success': item.type === 'success',
          'alert-warning': item.type === 'warning',
          'alert-info': item.type === 'info',
        }"
        :role="item.type === 'error' ? 'alert' : 'status'"
      >
        <span>{{ item.message }}</span>
        <button
          type="button"
          class="alert-close-btn"
          aria-label="Cerrar mensaje"
          @click="uiStore.dismissNotification(item.id)"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Contenido principal (o pantalla de mantenimiento si la API respondió 503) -->
    <main class="main-content">
      <MaintenanceView v-if="uiStore.maintenanceActive" />
      <RouterView v-else />
    </main>

    <!-- Insignia institucional permanente en esquina entre todas las pantallas -->
    <aside class="persistent-corner-logo" aria-label="Identidad institucional del hospital">
      <img
        src="/logo-hospital.png"
        alt="Hospital Interzonal de Agudos Especializado en Pediatría Sor María Ludovica"
        class="corner-logo-img"
      />
    </aside>
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

.top-header {
  background-color: #ffffff;
  border-top: 4px solid var(--color-brand-deep);
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 30;
}

.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0.65rem 1rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.brand-link {
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
  text-decoration: none;
  color: var(--color-brand-navy);
}

.brand-logo-img {
  height: 48px;
  width: auto;
  object-fit: contain;
}

.brand-system-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.7rem;
  border-radius: var(--radius-sm);
  background-color: var(--color-brand-navy);
  color: #ffffff;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.mobile-menu-toggle {
  display: none;
}

.user-summary {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.2rem;
}

.user-fullname {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--color-brand-deep);
}

.user-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.65rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.badge-role {
  background-color: var(--color-brand-teal-soft);
  color: var(--color-brand-deep);
  border: 1px solid var(--color-brand-teal);
}

.badge-sector {
  background-color: var(--color-brand-navy);
  color: #ffffff;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-sm {
  min-height: 44px;
  padding: 0.45rem 0.9rem;
  font-size: 0.875rem;
}

.nav-profile-active {
  border-color: var(--color-brand-deep);
  color: #ffffff;
  background-color: var(--color-brand-navy);
}

/* Barra de navegación con fondo #223A59 y acento activo #63AEBF */
.main-nav {
  background-color: var(--color-brand-navy);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
}

.nav-list {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1rem;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  min-height: 48px;
  padding: 0.5rem 1.1rem;
  color: rgba(255, 255, 255, 0.88);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.925rem;
  border-bottom: 4px solid transparent;
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.nav-link:hover {
  color: #ffffff;
  background-color: rgba(99, 174, 191, 0.18);
}

.nav-link-active {
  color: #ffffff;
  border-bottom-color: var(--color-brand-teal);
  background-color: var(--color-brand-deep);
}

/* Controles discretos para el Modo Kiosco */
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

/* Notificaciones globales */
.notifications-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-bottom: 0;
}

.alert-close-btn {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  min-width: 36px;
  min-height: 36px;
  font-size: 1rem;
  font-weight: 700;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Logo institucional fijo en la esquina inferior derecha en todas las vistas */
.persistent-corner-logo {
  position: fixed;
  bottom: 0.75rem;
  right: 0.85rem;
  z-index: 25;
  background-color: rgba(255, 255, 255, 0.96);
  border: 1.5px solid var(--color-brand-teal);
  border-left: 4px solid var(--color-brand-navy);
  border-radius: var(--radius-md);
  padding: 0.3rem 0.65rem;
  box-shadow: var(--shadow-md);
  pointer-events: none;
  display: inline-flex;
  align-items: center;
}

.corner-logo-img {
  height: 34px;
  width: auto;
  object-fit: contain;
  display: block;
}

/* Responsive móvil (< 767px) */
@media (max-width: 767px) {
  .brand-system-tag {
    display: none;
  }

  .brand-logo-img {
    height: 40px;
  }

  .mobile-menu-toggle {
    display: inline-flex;
  }

  .user-summary,
  .main-nav {
    display: none;
    width: 100%;
  }

  .user-summary.mobile-open {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-border);
  }

  .user-meta {
    align-items: flex-start;
  }

  .user-actions {
    width: 100%;
    justify-content: stretch;
  }

  .user-actions > * {
    flex: 1;
  }

  .main-nav.mobile-open {
    display: block;
  }

  .nav-list {
    flex-direction: column;
    padding: 0.5rem 1rem;
  }

  .nav-link {
    width: 100%;
    border-bottom: none;
    border-left: 4px solid transparent;
    border-radius: var(--radius-sm);
  }

  .nav-link-active {
    border-left-color: var(--color-brand-teal);
    background-color: var(--color-brand-deep);
  }

  .corner-logo-img {
    height: 28px;
  }
}
</style>
