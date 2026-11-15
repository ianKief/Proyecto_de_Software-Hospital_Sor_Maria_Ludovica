/**
 * Funciones de validación del lado del cliente para los formularios de autenticación y perfil.
 * Complementan (sin reemplazar) las validaciones que ejecuta el backend.
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const NOMBRE_APELLIDO_REGEX = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s'-]+$/
const DNI_REGEX = /^\d{7,10}$/

/**
 * Valida los campos del formulario de login con email y contraseña.
 */
export function validateLoginForm({ email = '', password = '' }) {
  const errors = {}
  const cleanEmail = String(email).trim()

  if (!cleanEmail) {
    errors.email = 'El correo electrónico es obligatorio.'
  } else if (!EMAIL_REGEX.test(cleanEmail)) {
    errors.email = 'Ingresá un correo electrónico con formato válido.'
  }

  if (!password || !String(password).trim()) {
    errors.password = 'La contraseña es obligatoria.'
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

/**
 * Valida los campos del formulario de edición de perfil del usuario operativo.
 */
export function validateProfileForm({
  nombre = '',
  apellido = '',
  email = '',
  dni = '',
  password = '',
  passwordConfirm = '',
}) {
  const errors = {}
  const cleanNombre = String(nombre).trim()
  const cleanApellido = String(apellido).trim()
  const cleanEmail = String(email).trim()
  const cleanDni = String(dni).trim()

  if (!cleanNombre) {
    errors.nombre = 'El nombre es obligatorio.'
  } else if (cleanNombre.length > 100) {
    errors.nombre = 'El nombre no puede superar los 100 caracteres.'
  } else if (!NOMBRE_APELLIDO_REGEX.test(cleanNombre)) {
    errors.nombre = 'El nombre solo puede contener letras y espacios.'
  }

  if (!cleanApellido) {
    errors.apellido = 'El apellido es obligatorio.'
  } else if (cleanApellido.length > 100) {
    errors.apellido = 'El apellido no puede superar los 100 caracteres.'
  } else if (!NOMBRE_APELLIDO_REGEX.test(cleanApellido)) {
    errors.apellido = 'El apellido solo puede contener letras y espacios.'
  }

  if (!cleanEmail) {
    errors.email = 'El correo electrónico es obligatorio.'
  } else if (cleanEmail.length > 120) {
    errors.email = 'El correo electrónico no puede superar los 120 caracteres.'
  } else if (!EMAIL_REGEX.test(cleanEmail)) {
    errors.email = 'Ingresá un correo electrónico con formato válido.'
  }

  if (!cleanDni) {
    errors.dni = 'El DNI es obligatorio.'
  } else if (!DNI_REGEX.test(cleanDni)) {
    errors.dni = 'El DNI debe contener únicamente números (entre 7 y 10 dígitos).'
  }

  if (password && String(password).length > 0) {
    if (String(password).length < 6) {
      errors.password = 'La nueva contraseña debe tener al menos 6 caracteres.'
    }
    if (password !== passwordConfirm) {
      errors.password_confirm = 'Las contraseñas ingresadas no coinciden.'
    }
  } else if (passwordConfirm && String(passwordConfirm).length > 0) {
    errors.password_confirm = 'Ingresá también la nueva contraseña para poder confirmarla.'
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}

