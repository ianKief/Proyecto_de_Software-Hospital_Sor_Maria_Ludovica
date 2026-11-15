<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { validateLoginForm } from '@/utils/validators'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const form = reactive({
  email: '',
  password: '',
})

const fieldErrors = reactive({
  email: '',
  password: '',
})

const generalError = ref('')
const isRetryableError = ref(false)
const showPassword = ref(false)

const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim()
const googleButtonContainer = ref(null)
const googleSdkReady = ref(false)

const isSubmitting = computed(() => authStore.loading)

function clearErrors() {
  fieldErrors.email = ''
  fieldErrors.password = ''
  generalError.value = ''
  isRetryableError.value = false
}

function applyApiError(error) {
  if (error?.fieldErrors) {
    if (error.fieldErrors.email) fieldErrors.email = error.fieldErrors.email
    if (error.fieldErrors.password) fieldErrors.password = error.fieldErrors.password
  }

  generalError.value =
    error?.message || 'No se pudo iniciar sesión. Verificá tus datos e intentá nuevamente.'
  isRetryableError.value = Boolean(error?.isRetryable)
}

/**
 * Redirige al usuario autenticado a la ruta que intentaba visitar originalmente
 * o, en su defecto, a la pantalla principal de su rol operativo.
 */
function redirectAfterLogin() {
  const redirectParam = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (redirectParam && redirectParam.startsWith('/') && redirectParam !== '/login') {
    router.push(redirectParam)
    return
  }
  router.push(authStore.homeRouteByRole)
}

async function handleSubmit() {
  clearErrors()

  const { isValid, errors } = validateLoginForm(form)
  if (!isValid) {
    fieldErrors.email = errors.email || ''
    fieldErrors.password = errors.password || ''
    return
  }

  try {
    const user = await authStore.login(form.email.trim(), form.password)
    uiStore.notify({
      type: 'success',
      message: `Bienvenido/a, ${user.nombre} ${user.apellido}.`,
    })
    redirectAfterLogin()
  } catch (error) {
    applyApiError(error)
  }
}

/**
 * Recibe el ID token emitido por Google Identity Services y lo envía a POST /api/auth/google.
 */
async function handleGoogleCredentialResponse(response) {
  clearErrors()

  const idToken = response?.credential
  if (!idToken) {
    generalError.value = 'No se recibió la credencial de Google. Intentá nuevamente.'
    return
  }

  try {
    const user = await authStore.loginWithGoogle(idToken)
    uiStore.notify({
      type: 'success',
      message: `Bienvenido/a, ${user.nombre} ${user.apellido}.`,
    })
    redirectAfterLogin()
  } catch (error) {
    applyApiError(error)
  }
}

function handleUnconfiguredGoogleClick() {
  clearErrors()
  generalError.value =
    'Para usar el inicio de sesión con Google, configurá la variable VITE_GOOGLE_CLIENT_ID en portal/.env y GOOGLE_CLIENT_ID en admin/.env.'
}

/**
 * Carga dinámicamente el script oficial de Google Identity Services e inicializa el botón.
 */
function initGoogleIdentityServices() {
  if (!googleClientId) return

  const renderButton = () => {
    if (!window.google?.accounts?.id || !googleButtonContainer.value) return
    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: handleGoogleCredentialResponse,
    })
    window.google.accounts.id.renderButton(googleButtonContainer.value, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'rectangular',
      logo_alignment: 'left',
      width: 360,
      locale: 'es',
    })
    googleSdkReady.value = true
  }

  if (window.google?.accounts?.id) {
    renderButton()
    return
  }

  const existingScript = document.getElementById('google-gsi-script')
  if (existingScript) {
    existingScript.addEventListener('load', renderButton)
    return
  }

  const script = document.createElement('script')
  script.id = 'google-gsi-script'
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  script.defer = true
  script.onload = renderButton
  document.head.appendChild(script)
}

onMounted(() => {
  initGoogleIdentityServices()
})
</script>

<template>
  <section class="login-wrapper" aria-labelledby="login-heading">
    <div class="card login-card">
      <div class="logo-header">
        <img
          src="/logo-hospital.png"
          alt="HIAEP Sor María Ludovica - La Plata"
          class="login-logo-img"
        />
      </div>

      <header class="login-card-header">
        <h1 id="login-heading">Iniciar sesión</h1>
        <p class="login-subtitle">
          Sistema de Gestión del Servicio de Alimentación
        </p>
      </header>

      <!-- Alerta de error general (401, 403, 500 o error de red) -->
      <div
        v-if="generalError"
        class="alert alert-error login-alert"
        role="alert"
        aria-live="assertive"
      >
        <div class="alert-body">
          <span>{{ generalError }}</span>
          <button
            v-if="isRetryableError"
            type="button"
            class="btn btn-secondary btn-retry"
            :disabled="isSubmitting"
            @click="handleSubmit"
          >
            Reintentar
          </button>
        </div>
      </div>

      <form class="login-form" novalidate @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="login-email" class="form-label">Correo electrónico</label>
          <input
            id="login-email"
            v-model="form.email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="ejemplo@hospital.com"
            class="form-input"
            :aria-invalid="fieldErrors.email ? 'true' : 'false'"
            :aria-describedby="fieldErrors.email ? 'login-email-error' : undefined"
            :disabled="isSubmitting"
            required
            @input="fieldErrors.email = ''"
          />
          <p v-if="fieldErrors.email" id="login-email-error" class="field-error" role="alert">
            {{ fieldErrors.email }}
          </p>
        </div>

        <div class="form-group">
          <label for="login-password" class="form-label">Contraseña</label>
          <div class="password-input-wrapper">
            <input
              id="login-password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              name="password"
              autocomplete="current-password"
              placeholder="Ingresá tu contraseña"
              class="form-input password-input"
              :aria-invalid="fieldErrors.password ? 'true' : 'false'"
              :aria-describedby="fieldErrors.password ? 'login-password-error' : undefined"
              :disabled="isSubmitting"
              required
              @input="fieldErrors.password = ''"
            />
            <button
              type="button"
              class="password-eye-btn"
              :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              :aria-pressed="showPassword ? 'true' : 'false'"
              :disabled="isSubmitting"
              @click="showPassword = !showPassword"
            >
              <!-- Ícono de ojo tachado cuando la contraseña está visible -->
              <svg
                v-if="showPassword"
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path
                  d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"
                />
                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
              <!-- Ícono de ojo abierto cuando la contraseña está oculta -->
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </button>
          </div>
          <p
            v-if="fieldErrors.password"
            id="login-password-error"
            class="field-error"
            role="alert"
          >
            {{ fieldErrors.password }}
          </p>
        </div>

        <button
          type="submit"
          class="btn btn-primary submit-btn"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Verificando credenciales...' : 'Ingresar' }}
        </button>
      </form>

      <div class="divider" role="separator" aria-label="O ingresá con tu cuenta de Google">
        <span>o ingresá con tu cuenta de Google</span>
      </div>

      <!-- Contenedor del botón de Google Identity Services -->
      <div class="google-auth-section">
        <div
          v-if="googleClientId"
          ref="googleButtonContainer"
          class="google-gsi-container"
        ></div>

        <!-- Botón visible cuando todavía no se definió VITE_GOOGLE_CLIENT_ID en .env o mientras carga el SDK -->
        <button
          v-if="!googleClientId || !googleSdkReady"
          type="button"
          class="btn btn-secondary google-fallback-btn"
          :disabled="isSubmitting"
          @click="handleUnconfiguredGoogleClick"
        >
          <svg
            class="google-icon"
            viewBox="0 0 24 24"
            width="20"
            height="20"
            aria-hidden="true"
          >
            <path
              fill="#4285F4"
              d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z"
            />
            <path
              fill="#FBBC05"
              d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.14-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z"
            />
            <path
              fill="#EA4335"
              d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z"
            />
          </svg>
          <span>Iniciar sesión con Google</span>
        </button>
      </div>

      <footer class="login-card-footer">
        <p>
          Si no tenés cuenta activa o necesitás recuperar el acceso, solicitalo al
          <strong>Administrador</strong> del sistema.
        </p>
      </footer>
    </div>
  </section>
</template>

<style scoped>
.login-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: linear-gradient(
    135deg,
    #f4f9fb 0%,
    #eaf5f8 55%,
    rgba(99, 174, 191, 0.25) 100%
  );
}

.login-card {
  width: 100%;
  max-width: 460px;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.logo-header {
  display: flex;
  justify-content: center;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.login-logo-img {
  height: 58px;
  width: auto;
  object-fit: contain;
}

.login-card-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.login-card-header h1 {
  margin: 0 0 0.3rem;
  font-size: 1.65rem;
  color: var(--color-brand-deep);
}

.login-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.92rem;
}

.login-alert {
  margin-bottom: 1.25rem;
}

.alert-body {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  width: 100%;
}

.btn-retry {
  align-self: flex-start;
  min-height: 40px;
  padding: 0.35rem 0.85rem;
}

.password-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input {
  width: 100%;
  padding-right: 3rem;
}

.password-eye-btn {
  position: absolute;
  right: 0.25rem;
  top: 50%;
  transform: translateY(-50%);
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-brand-navy);
  cursor: pointer;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}

.password-eye-btn:hover:not(:disabled) {
  color: var(--color-brand-deep);
  background-color: var(--color-brand-teal-soft);
}

.password-eye-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-btn {
  width: 100%;
  margin-top: 0.5rem;
  font-size: 1rem;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 1.25rem 0;
  color: var(--color-text-muted);
  font-size: 0.85rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid var(--color-border);
}

.divider span {
  padding: 0 0.75rem;
}

.google-auth-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.google-gsi-container {
  display: flex;
  justify-content: center;
  width: 100%;
  min-height: 48px;
}

.google-fallback-btn {
  width: 100%;
  font-weight: 600;
}

.google-icon {
  flex-shrink: 0;
}

.login-card-footer {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.83rem;
  color: var(--color-text-muted);
  text-align: center;
}

.login-card-footer p {
  margin: 0;
}

/* Tablet y Escritorio (>= 768px) */
@media (min-width: 768px) {
  .login-wrapper {
    padding: 2rem;
  }

  .login-card {
    padding: 2.25rem 2.25rem;
  }
}
</style>
