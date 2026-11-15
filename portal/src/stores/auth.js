import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getStoredToken, setStoredToken, ApiError } from '@/services/api'
import { authService } from '@/services/auth.service'

const STORAGE_USER_KEY = 'portal_auth_user'

export const ROLES_OPERATIVOS = Object.freeze({
  JEFE_SERVICIO: 'Jefe de Servicio',
  SERVICIO_ALIMENTACION: 'Servicio de Alimentación',
  SECTOR_COMEDOR: 'Sector Comedor',
})

const LISTA_ROLES_PERMITIDOS = Object.values(ROLES_OPERATIVOS)

/**
 * Mapa que asocia cada rol operativo con su ruta inicial dentro del portal público.
 */
export const RUTA_INICIAL_POR_ROL = Object.freeze({
  [ROLES_OPERATIVOS.JEFE_SERVICIO]: '/pedidos',
  [ROLES_OPERATIVOS.SERVICIO_ALIMENTACION]: '/autorizaciones',
  [ROLES_OPERATIVOS.SECTOR_COMEDOR]: '/comedor',
})

function loadStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveStoredUser(user) {
  if (user) {
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(STORAGE_USER_KEY)
  }
}

/**
 * Store de autenticación y sesión del usuario en el portal público.
 *
 * Decisión de almacenamiento del token:
 * Se persiste el JWT en `localStorage` (junto con el estado reactivo en Pinia) para que
 * la sesión soporte recargas de página o cierres accidentales de pestaña en las tablets
 * del Sector Comedor durante todo un turno operativo.
 * Comparativa de alternativas:
 * - Memoria (solo Pinia): más aislada frente a XSS, pero pierde la sesión ante cualquier F5.
 * - sessionStorage: sobrevive a F5 en la misma pestaña, pero se pierde si en la tablet se cierra
 *   o reabre el navegador durante el turno.
 * - Cookie HttpOnly: requiere configuración de credenciales cross-site (SameSite/CSRF) cuando
 *   frontend y API corren en orígenes distintos.
 * Para mitigar los riesgos de `localStorage`, el token tiene expiración acotada al turno en el
 * backend, nunca se expone en URLs ni por consola, y se elimina inmediatamente ante un 401 o logout.
 */
export const useAuthStore = defineStore('auth', () => {
  const token = ref(getStoredToken())
  const user = ref(loadStoredUser())
  const loading = ref(false)
  const initialized = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const userRole = computed(() => user.value?.rol || null)
  const userFullName = computed(() => {
    if (!user.value) return ''
    return `${user.value.nombre || ''} ${user.value.apellido || ''}`.trim()
  })
  const userSector = computed(() => user.value?.sector || null)

  const isJefeServicio = computed(
    () => userRole.value === ROLES_OPERATIVOS.JEFE_SERVICIO,
  )
  const isServicioAlimentacion = computed(
    () => userRole.value === ROLES_OPERATIVOS.SERVICIO_ALIMENTACION,
  )
  const isSectorComedor = computed(
    () => userRole.value === ROLES_OPERATIVOS.SECTOR_COMEDOR,
  )

  const homeRouteByRole = computed(() => {
    return RUTA_INICIAL_POR_ROL[userRole.value] || '/login'
  })

  function setSession(newToken, newUser) {
    token.value = newToken
    user.value = newUser
    setStoredToken(newToken)
    saveStoredUser(newUser)
  }

  function clearSession() {
    token.value = null
    user.value = null
    setStoredToken(null)
    saveStoredUser(null)
  }

  /**
   * Consulta GET /api/auth/me usando el token actual para sincronizar los datos
   * del usuario autenticado y verificar que posea un rol operativo válido.
   */
  async function fetchCurrentUser() {
    const response = await authService.getCurrentUser()
    const profile = response?.user || response

    if (!profile || !LISTA_ROLES_PERMITIDOS.includes(profile.rol)) {
      clearSession()
      throw new ApiError({
        status: 403,
        code: 'forbidden',
        message:
          'Esta cuenta no tiene un rol habilitado para ingresar a la aplicación pública.',
      })
    }

    user.value = profile
    saveStoredUser(profile)
    return profile
  }

  /**
   * Se ejecuta al iniciar la aplicación para validar si hay un token guardado
   * y refrescar los datos del usuario desde GET /api/auth/me.
   */
  async function initializeAuth() {
    if (initialized.value) return
    if (!token.value) {
      clearSession()
      initialized.value = true
      return
    }

    try {
      await fetchCurrentUser()
    } catch {
      clearSession()
    } finally {
      initialized.value = true
    }
  }

  /**
   * Inicia sesión con email y contraseña contra POST /api/auth/login
   * y luego obtiene los datos actualizados desde GET /api/auth/me.
   */
  async function login(email, password) {
    loading.value = true
    try {
      const data = await authService.loginWithCredentials(email, password)
      setSession(data.token, data.user || null)
      const currentUser = await fetchCurrentUser()
      initialized.value = true
      return currentUser
    } catch (error) {
      clearSession()
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * Inicia sesión enviando el ID token de Google Identity Services a POST /api/auth/google
   * y luego sincroniza el perfil del usuario con GET /api/auth/me.
   */
  async function loginWithGoogle(idToken) {
    loading.value = true
    try {
      const data = await authService.loginWithGoogleToken(idToken)
      setSession(data.token, data.user || null)
      const currentUser = await fetchCurrentUser()
      initialized.value = true
      return currentUser
    } catch (error) {
      clearSession()
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * Actualiza los datos personales o la contraseña del usuario autenticado mediante PUT /api/auth/me.
   */
  async function updateProfile(payload) {
    loading.value = true
    try {
      const data = await authService.updateCurrentUserProfile(payload)
      if (data?.user) {
        user.value = data.user
        saveStoredUser(data.user)
      }
      return data
    } finally {
      loading.value = false
    }
  }

  /**
   * Cierra la sesión invocando POST /api/auth/logout y limpiando el almacenamiento local.
   */
  async function logout() {
    loading.value = true
    try {
      if (token.value) {
        await authService.logoutSession()
      }
    } catch {
      // Incluso si el token ya había expirado en el servidor, limpiamos la sesión local
    } finally {
      clearSession()
      loading.value = false
    }
  }

  return {
    token,
    user,
    loading,
    initialized,
    isAuthenticated,
    userRole,
    userFullName,
    userSector,
    isJefeServicio,
    isServicioAlimentacion,
    isSectorComedor,
    homeRouteByRole,
    setSession,
    clearSession,
    fetchCurrentUser,
    initializeAuth,
    login,
    loginWithGoogle,
    updateProfile,
    logout,
  }
})
