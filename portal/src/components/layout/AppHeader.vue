<script setup>
import { ref, computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore, ROLES_OPERATIVOS } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const mobileMenuOpen = ref(false)

// Cerramos el menú móvil al cambiar de pantalla
watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  },
)

const sectorNombre = computed(() => {
  const s = authStore.userSector
  if (!s) return ''
  return typeof s === 'object' ? s.nombre || '' : String(s)
})

/**
 * Opciones del menú principal filtradas según el rol del usuario autenticado.
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
  <header class="top-header">
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
</template>

<style scoped>
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
}
</style>
