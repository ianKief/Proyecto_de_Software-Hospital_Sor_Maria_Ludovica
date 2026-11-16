/**
 * Configuración de rutas y guards de navegación del portal público.
 *
 * Cada ruta define en su objeto `meta`:
 * - `requiresAuth`: indica si exige una sesión activa.
 * - `guestOnly`: indica si es exclusiva para usuarios no autenticados (como /login).
 * - `roles`: lista de roles operativos autorizados a visitar la ruta.
 * - `kioskMode`: activa el diseño a pantalla completa para las tablets del Sector Comedor.
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore, ROLES_OPERATIVOS } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { registerApiHandlers } from '@/services/api'

import LoginView from '@/views/LoginView.vue'
import ProfileView from '@/views/ProfileView.vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import MaintenanceView from '@/views/MaintenanceView.vue'
import ModulePlaceholderView from '@/views/ModulePlaceholderView.vue'

const TODOS_LOS_ROLES_OPERATIVOS = [
  ROLES_OPERATIVOS.JEFE_SERVICIO,
  ROLES_OPERATIVOS.SERVICIO_ALIMENTACION,
  ROLES_OPERATIVOS.SECTOR_COMEDOR,
]

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: {
      requiresAuth: false,
      guestOnly: true,
      title: 'Iniciar sesión',
    },
  },
  {
    path: '/',
    name: 'root',
    meta: {
      requiresAuth: true,
      roles: TODOS_LOS_ROLES_OPERATIVOS,
    },
    redirect: () => {
      const authStore = useAuthStore()
      return authStore.isAuthenticated ? authStore.homeRouteByRole : '/login'
    },
  },
  {
    path: '/pedidos',
    name: 'pedidos',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.JEFE_SERVICIO],
      title: 'Carga y Gestión de Pedidos',
      description: 'Registro y seguimiento de pedidos de comida del sector.',
      navLabel: 'Pedidos de mi sector',
    },
  },
  {
    path: '/personal',
    name: 'personal',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.JEFE_SERVICIO, ROLES_OPERATIVOS.SERVICIO_ALIMENTACION],
      title: 'Gestión de Personal',
      description: 'Administración de fichas del personal y consulta de residentes.',
      navLabel: 'Personal',
    },
  },
  {
    path: '/autorizaciones',
    name: 'autorizaciones',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION],
      title: 'Autorización de Pedidos',
      description: 'Revisión, autorización y rechazo de pedidos diarios y semanales.',
      navLabel: 'Autorizaciones',
    },
  },
  {
    path: '/cupos',
    name: 'cupos',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION, ROLES_OPERATIVOS.JEFE_SERVICIO],
      title: 'Cupos por Sector',
      description: 'Consulta y administración de cupos asignados por comida y sector.',
      navLabel: 'Cupos',
    },
  },
  {
    path: '/reportes',
    name: 'reportes',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION, ROLES_OPERATIVOS.JEFE_SERVICIO],
      title: 'Resúmenes y Reportes',
      description: 'Totales estadísticos de pedidos, autorizaciones y entregas.',
      navLabel: 'Reportes',
    },
  },
  {
    path: '/comedor',
    name: 'comedor',
    component: ModulePlaceholderView,
    meta: {
      requiresAuth: true,
      roles: [ROLES_OPERATIVOS.SECTOR_COMEDOR],
      kioskMode: true,
      title: 'Entrega de Comidas — Modo Kiosco',
      description: 'Búsqueda de comensales por DNI y registro de entregas del turno.',
      navLabel: 'Kiosco Comedor',
    },
  },
  {
    path: '/perfil',
    name: 'perfil',
    component: ProfileView,
    meta: {
      requiresAuth: true,
      roles: TODOS_LOS_ROLES_OPERATIVOS,
      title: 'Mi Perfil',
    },
  },
  {
    path: '/acceso-denegado',
    name: 'forbidden',
    component: ForbiddenView,
    meta: {
      requiresAuth: true,
      title: 'Acceso Denegado',
    },
  },
  {
    path: '/mantenimiento',
    name: 'maintenance',
    component: MaintenanceView,
    meta: {
      requiresAuth: false,
      title: 'Sitio en Mantenimiento',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/**
 * Guard global de navegación:
 * 1. Sincroniza la sesión almacenada al cargar la SPA por primera vez.
 * 2. Exige sesión activa en todas las rutas con `meta.requiresAuth`, guardando la ruta destino.
 * 3. Redirige a la pantalla inicial del rol cuando el usuario ya está autenticado e intenta ir a /login.
 * 4. Verifica que el rol del usuario esté incluido en `meta.roles`; si no, muestra /acceso-denegado.
 */
router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  const uiStore = useUiStore()

  // Vinculamos los handlers globales del cliente HTTP una vez que Pinia y el router están activos
  registerApiHandlers({
    onUnauthorized: () => {
      const currentPath = router.currentRoute.value?.fullPath || '/'
      authStore.clearSession()
      if (router.currentRoute.value?.name !== 'login') {
        router.push({
          name: 'login',
          query: currentPath && currentPath !== '/login' ? { redirect: currentPath } : undefined,
        })
      }
    },
    onMaintenance: (active, message) => {
      uiStore.setMaintenance(active, message)
    },
  })

  if (!authStore.initialized) {
    await authStore.initializeAuth()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : undefined,
    }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    const redirectTarget = typeof to.query.redirect === 'string' ? to.query.redirect : null
    if (redirectTarget && redirectTarget.startsWith('/')) {
      return redirectTarget
    }
    return authStore.homeRouteByRole
  }

  if (
    to.meta.requiresAuth &&
    Array.isArray(to.meta.roles) &&
    to.meta.roles.length > 0 &&
    !to.meta.roles.includes(authStore.userRole)
  ) {
    return { name: 'forbidden' }
  }

  return true
})

/**
 * Actualiza el título de la pestaña del navegador según la sección visitada.
 */
router.afterEach((to) => {
  const baseTitle = 'Portal de Alimentación — Hospital Sor María Ludovica'
  document.title = to.meta?.title ? `${to.meta.title} | ${baseTitle}` : baseTitle
})

export default router
