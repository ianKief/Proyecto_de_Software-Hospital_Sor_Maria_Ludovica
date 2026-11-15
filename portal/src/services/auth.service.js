import { api } from '@/services/api'

/**
 * Servicio de acceso a los endpoints de autenticación y perfil (/api/auth/*).
 */
export const authService = {
  /**
   * Inicia sesión con correo electrónico y contraseña.
   */
  loginWithCredentials(email, password) {
    return api.post(
      '/auth/login',
      { email, password },
      { skipAuthRedirect: true },
    )
  },

  /**
   * Inicia sesión enviando el ID token devuelto por Google Identity Services.
   */
  loginWithGoogleToken(idToken) {
    return api.post(
      '/auth/google',
      { id_token: idToken },
      { skipAuthRedirect: true },
    )
  },

  /**
   * Obtiene los datos actualizados del usuario autenticado (GET /api/auth/me).
   */
  getCurrentUser() {
    return api.get('/auth/me', undefined, { skipAuthRedirect: true })
  },

  /**
   * Actualiza los datos personales y/o contraseña del usuario autenticado (PUT /api/auth/me).
   */
  updateCurrentUserProfile(payload) {
    return api.put('/auth/me', payload)
  },

  /**
   * Cierra la sesión actual en el backend (POST /api/auth/logout).
   */
  logoutSession() {
    return api.post('/auth/logout', {}, { skipAuthRedirect: true })
  },
}
