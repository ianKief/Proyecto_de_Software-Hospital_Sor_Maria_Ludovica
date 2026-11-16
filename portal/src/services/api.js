/**
 * Cliente HTTP centralizado para comunicarse con la API REST del backend.
 *
 * Responsabilidades:
 * - Tomar la URL base desde la variable de entorno VITE_API_BASE_URL.
 * - Adjuntar automáticamente el token JWT en el header Authorization (Bearer).
 * - Normalizar el manejo de errores HTTP (400, 401, 403, 404, 409, 500, 503 y fallos de red).
 */

const STORAGE_TOKEN_KEY = 'portal_auth_token'

// Callbacks registrables desde el store/router para evitar dependencias circulares
let unauthorizedHandler = null
let maintenanceHandler = null

/**
 * Registra las funciones que se ejecutarán automáticamente cuando la API responda
 * con 401 (sesión inválida/expirada) o 503 (sitio en modo mantenimiento).
 */
export function registerApiHandlers({ onUnauthorized, onMaintenance } = {}) {
  if (typeof onUnauthorized === 'function') {
    unauthorizedHandler = onUnauthorized
  }
  if (typeof onMaintenance === 'function') {
    maintenanceHandler = onMaintenance
  }
}

/**
 * Obtiene el token JWT almacenado localmente en el navegador, o null si no existe.
 */
export function getStoredToken() {
  return localStorage.getItem(STORAGE_TOKEN_KEY)
}

/**
 * Guarda o elimina el token JWT en el almacenamiento local del navegador.
 */
export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(STORAGE_TOKEN_KEY, token)
  } else {
    localStorage.removeItem(STORAGE_TOKEN_KEY)
  }
}

/**
 * Error enriquecido que representa una respuesta de error de la API o un fallo de conexión.
 */
export class ApiError extends Error {
  constructor({
    status = 0,
    code = 'unknown_error',
    message = 'Ocurrió un error inesperado.',
    details = [],
    fieldErrors = {},
    isConflict = false,
    isRetryable = false,
    isNetworkError = false,
  }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.fieldErrors = fieldErrors
    this.isConflict = isConflict
    this.isRetryable = isRetryable
    this.isNetworkError = isNetworkError
  }
}

/**
 * Unifica los errores por campo que devuelve el backend (ya sea en un objeto `fields`
 * o en una lista `details: [{ field, message }]`) para mostrarlos junto a cada input.
 */
function buildFieldErrorsMap(details, fieldsObj) {
  const map = {}
  if (fieldsObj && typeof fieldsObj === 'object' && !Array.isArray(fieldsObj)) {
    for (const [key, msg] of Object.entries(fieldsObj)) {
      if (key && msg) {
        map[key] = String(msg)
      }
    }
  }

  if (Array.isArray(details)) {
    for (const item of details) {
      if (item && item.field && item.message && !map[item.field]) {
        map[item.field] = item.message
      }
    }
  }
  return map
}

/**
 * Construye la URL final combinando VITE_API_BASE_URL con la ruta solicitada
 * y los parámetros de query opcionales.
 */
function buildUrl(endpoint, params) {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
  const cleanPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const fullPath = `${baseUrl}${cleanPath}`

  if (!params || Object.keys(params).length === 0) {
    return fullPath
  }

  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value))
    }
  }

  const queryString = searchParams.toString()
  return queryString ? `${fullPath}?${queryString}` : fullPath
}

/**
 * Ejecuta una petición HTTP hacia la API e interpreta los códigos de estado de manera uniforme.
 */
export async function apiRequest(endpoint, options = {}) {
  const {
    method = 'GET',
    body = undefined,
    params = undefined,
    headers = {},
    skipAuthRedirect = false,
  } = options

  const token = getStoredToken()
  const requestHeaders = {
    Accept: 'application/json',
    ...headers,
  }

  if (body !== undefined && !(body instanceof FormData)) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`
  }

  const url = buildUrl(endpoint, params)

  let response
  try {
    response = await fetch(url, {
      method,
      headers: requestHeaders,
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? body
            : JSON.stringify(body),
    })
  } catch {
    throw new ApiError({
      status: 0,
      code: 'network_error',
      message:
        'No se pudo establecer conexión con el servidor. Verificá tu conexión e intentá nuevamente.',
      isRetryable: true,
      isNetworkError: true,
    })
  }

  // Si la API volvió a responder con normalidad tras un mantenimiento previo, limpiamos el flag
  if (response.status !== 503 && maintenanceHandler) {
    maintenanceHandler(false, '')
  }

  // Parseo seguro del cuerpo (JSON si aplica)
  const contentType = response.headers.get('content-type') || ''
  let payload = null
  if (contentType.includes('application/json')) {
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
  } else if (response.status !== 204) {
    try {
      payload = await response.text()
    } catch {
      payload = null
    }
  }

  if (response.ok) {
    return payload
  }

  // Extracción uniforme del mensaje y detalle de error devuelto por nuestra API Flask
  const rawError = payload && typeof payload === 'object' ? payload.error : null
  const apiErrorObj =
    rawError && typeof rawError === 'object'
      ? rawError
      : payload && typeof payload === 'object'
        ? payload
        : null

  const backendMessage =
    typeof rawError === 'string'
      ? rawError
      : (apiErrorObj && (apiErrorObj.message || apiErrorObj.mensaje)) || ''
  const backendCode = (apiErrorObj && apiErrorObj.code) || 'http_error'
  const details = (apiErrorObj && Array.isArray(apiErrorObj.details) && apiErrorObj.details) || []
  const fieldsObj = (payload && typeof payload === 'object' && payload.fields) || null
  const fieldErrors = buildFieldErrorsMap(details, fieldsObj)

  switch (response.status) {
    case 400:
      throw new ApiError({
        status: 400,
        code: backendCode,
        message:
          backendMessage || 'Los datos ingresados contienen errores. Revisá los campos marcados.',
        details,
        fieldErrors,
      })

    case 401:
      // Si el 401 ocurre en una ruta protegida (no en el intento de login), cerramos sesión y redirigimos
      if (!skipAuthRedirect && unauthorizedHandler) {
        unauthorizedHandler()
      }
      throw new ApiError({
        status: 401,
        code: backendCode,
        message:
          backendMessage ||
          'Tu sesión expiró o las credenciales son inválidas. Iniciá sesión nuevamente.',
        details,
        fieldErrors,
      })

    case 403:
      throw new ApiError({
        status: 403,
        code: backendCode,
        message: backendMessage || 'No tenés permisos para realizar esta operación.',
        details,
        fieldErrors,
      })

    case 404:
      throw new ApiError({
        status: 404,
        code: backendCode,
        message: backendMessage || 'El recurso solicitado no existe o fue eliminado.',
        details,
      })

    case 409:
      throw new ApiError({
        status: 409,
        code: backendCode,
        message:
          backendMessage ||
          'La operación entró en conflicto con el estado actual de los datos. Se recargará la información.',
        details,
        fieldErrors,
        isConflict: true,
      })

    case 503: {
      const maintMsg =
        backendMessage ||
        'El sistema se encuentra temporalmente deshabilitado por tareas de mantenimiento.'
      if (maintenanceHandler) {
        maintenanceHandler(true, maintMsg)
      }
      throw new ApiError({
        status: 503,
        code: backendCode || 'service_unavailable',
        message: maintMsg,
      })
    }

    default:
      throw new ApiError({
        status: response.status,
        code: backendCode,
        message:
          backendMessage ||
          'Ocurrió un error interno en el servidor. Podés volver a intentar la operación.',
        isRetryable: response.status >= 500,
      })
  }
}

/**
 * Métodos abreviados para invocar peticiones GET, POST, PUT y DELETE contra la API.
 */
export const api = {
  get: (endpoint, params, options = {}) =>
    apiRequest(endpoint, { ...options, method: 'GET', params }),
  post: (endpoint, body, options = {}) =>
    apiRequest(endpoint, { ...options, method: 'POST', body }),
  put: (endpoint, body, options = {}) =>
    apiRequest(endpoint, { ...options, method: 'PUT', body }),
  delete: (endpoint, options = {}) =>
    apiRequest(endpoint, { ...options, method: 'DELETE' }),
}
