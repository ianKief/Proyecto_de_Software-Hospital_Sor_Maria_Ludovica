<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { validateLoginForm } from '@/utils/validators'

import PasswordInput from '@/components/common/PasswordInput.vue'
import GoogleSignInButton from '@/components/common/GoogleSignInButton.vue'

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

async function handleGoogleCredential(idToken) {
  clearErrors()
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

function handleGoogleError(message) {
  clearErrors()
  generalError.value = message
}
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

        <PasswordInput
          id="login-password"
          v-model="form.password"
          label="Contraseña"
          name="password"
          autocomplete="current-password"
          placeholder="Ingresá tu contraseña"
          :error="fieldErrors.password"
          :disabled="isSubmitting"
          required
          @update:model-value="fieldErrors.password = ''"
        />

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

      <GoogleSignInButton
        :disabled="isSubmitting"
        @credential="handleGoogleCredential"
        @error="handleGoogleError"
      />

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

@media (min-width: 768px) {
  .login-wrapper {
    padding: 2rem;
  }

  .login-card {
    padding: 2.25rem 2.25rem;
  }
}
</style>
