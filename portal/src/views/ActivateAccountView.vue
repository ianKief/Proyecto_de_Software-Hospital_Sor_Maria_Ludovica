<script setup>
/**
 * Vista pública de activación de cuenta para usuarios operativos nuevos.
 * Valida el token recibido por correo electrónico (GET /api/auth/activate),
 * muestra los datos de la cuenta y permite establecer la contraseña inicial
 * (POST /api/auth/activate), iniciando la sesión en el portal automáticamente.
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { authService } from '@/services/auth.service'
import { validateActivationForm } from '@/utils/validators'

import PasswordInput from '@/components/common/PasswordInput.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const verifyingToken = ref(true)
const tokenError = ref('')
const accountUser = ref(null)

const form = reactive({
  password: '',
  passwordConfirm: '',
})

const fieldErrors = reactive({
  password: '',
  password_confirm: '',
})

const generalError = ref('')
const isSubmitting = computed(() => authStore.loading)

const token = computed(() => {
  return typeof route.query.token === 'string' ? route.query.token.trim() : ''
})

/**
 * Limpia los mensajes de error por campo y la alerta general del formulario.
 */
function clearErrors() {
  fieldErrors.password = ''
  fieldErrors.password_confirm = ''
  generalError.value = ''
}

/**
 * Consulta GET /api/auth/activate al cargar la pantalla para comprobar que el
 * enlace recibido por correo sea válido y obtener los datos del usuario a activar.
 */
async function checkActivationToken() {
  verifyingToken.value = true
  tokenError.value = ''

  if (!token.value) {
    tokenError.value =
      'No se encontró el código de activación en el enlace. Verificá que hayas copiado la dirección completa del correo.'
    verifyingToken.value = false
    return
  }

  try {
    const data = await authService.verifyActivationToken(token.value)
    accountUser.value = data?.user || null
  } catch (error) {
    tokenError.value =
      error?.message ||
      'El enlace de activación es inválido o ha expirado (validez: 24 hs). Contactá al Administrador.'
  } finally {
    verifyingToken.value = false
  }
}

/**
 * Valida la contraseña elegida y envía la solicitud de activación a POST /api/auth/activate.
 * Al completarse, el usuario queda autenticado y es redirigido a la vista inicial de su rol.
 */
async function handleSubmit() {
  clearErrors()

  const { isValid, errors } = validateActivationForm(form)
  if (!isValid) {
    fieldErrors.password = errors.password || ''
    fieldErrors.password_confirm = errors.password_confirm || ''
    return
  }

  try {
    const user = await authStore.activateAccount({
      token: token.value,
      password: form.password,
      passwordConfirm: form.passwordConfirm,
    })

    uiStore.notify({
      type: 'success',
      message: `¡Tu cuenta fue activada con éxito! Bienvenido/a, ${user.nombre} ${user.apellido}.`,
    })
    router.push(authStore.homeRouteByRole)
  } catch (error) {
    if (error?.fieldErrors) {
      if (error.fieldErrors.password) fieldErrors.password = error.fieldErrors.password
      if (error.fieldErrors.password_confirm) {
        fieldErrors.password_confirm = error.fieldErrors.password_confirm
      }
    }
    generalError.value =
      error?.message || 'No se pudo activar la cuenta. Verificá los datos e intentá nuevamente.'
  }
}

onMounted(() => {
  checkActivationToken()
})
</script>

<template>
  <section class="activate-wrapper" aria-labelledby="activate-heading">
    <div class="card activate-card">
      <div class="logo-header">
        <img
          src="/logo-hospital.png"
          alt="HIAEP Sor María Ludovica - La Plata"
          class="activate-logo-img"
        />
      </div>

      <header class="activate-card-header">
        <h1 id="activate-heading">Activá tu cuenta</h1>
        <p class="activate-subtitle">
          Sistema de Gestión del Servicio de Alimentación
        </p>
      </header>

      <!-- Estado de carga mientras se verifica el token -->
      <div v-if="verifyingToken" class="status-box" role="status" aria-live="polite">
        Verificando enlace de activación...
      </div>

      <!-- Error cuando el token falta, es inválido o expiró -->
      <div v-else-if="tokenError" class="token-error-container">
        <div class="alert alert-error" role="alert" aria-live="assertive">
          <span>{{ tokenError }}</span>
        </div>
        <div class="token-error-actions">
          <RouterLink to="/login" class="btn btn-primary submit-btn">
            Ir al inicio de sesión
          </RouterLink>
        </div>
      </div>

      <!-- Formulario para definir la contraseña inicial -->
      <template v-else>
        <p v-if="accountUser" class="welcome-text">
          Hola <strong>{{ accountUser.nombre }} {{ accountUser.apellido }}</strong>
          <span v-if="accountUser.rol"> ({{ accountUser.rol }})</span>.
          Para completar la activación de tu cuenta, establecé tu contraseña de acceso.
        </p>

        <div
          v-if="generalError"
          class="alert alert-error activate-alert"
          role="alert"
          aria-live="assertive"
        >
          <span>{{ generalError }}</span>
        </div>

        <form class="activate-form" novalidate @submit.prevent="handleSubmit">
          <div v-if="accountUser" class="form-group">
            <label for="activate-email" class="form-label">Correo electrónico</label>
            <input
              id="activate-email"
              type="email"
              :value="accountUser.email"
              class="form-input input-readonly"
              disabled
            />
          </div>

          <PasswordInput
            id="activate-password"
            v-model="form.password"
            label="Nueva contraseña"
            name="password"
            autocomplete="new-password"
            placeholder="Mínimo 6 caracteres"
            :error="fieldErrors.password"
            :disabled="isSubmitting"
            required
            @update:model-value="fieldErrors.password = ''"
          />

          <PasswordInput
            id="activate-password-confirm"
            v-model="form.passwordConfirm"
            label="Confirmar nueva contraseña"
            name="password_confirm"
            autocomplete="new-password"
            placeholder="Repetí la contraseña"
            :error="fieldErrors.password_confirm"
            :disabled="isSubmitting"
            required
            @update:model-value="fieldErrors.password_confirm = ''"
          />

          <button
            type="submit"
            class="btn btn-primary submit-btn"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? 'Activando cuenta...' : 'Guardar contraseña y acceder' }}
          </button>
        </form>
      </template>

      <footer class="activate-card-footer">
        <RouterLink to="/login" class="back-link">
          Volver al inicio de sesión
        </RouterLink>
      </footer>
    </div>
  </section>
</template>

<style scoped>
.activate-wrapper {
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

.activate-card {
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

.activate-logo-img {
  height: 58px;
  width: auto;
  object-fit: contain;
}

.activate-card-header {
  text-align: center;
  margin-bottom: 1.25rem;
}

.activate-card-header h1 {
  margin: 0 0 0.3rem;
  font-size: 1.65rem;
  color: var(--color-brand-deep);
}

.activate-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.92rem;
}

.welcome-text {
  margin: 0 0 1.25rem;
  font-size: 0.92rem;
  color: var(--color-text);
  text-align: center;
  line-height: 1.5;
}

.status-box {
  text-align: center;
  padding: 1.5rem 1rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.token-error-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.activate-alert {
  margin-bottom: 1.25rem;
}

.input-readonly {
  background-color: #f1f5f9;
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.submit-btn {
  width: 100%;
  margin-top: 0.5rem;
  font-size: 1rem;
  text-decoration: none;
}

.activate-card-footer {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.back-link {
  color: var(--color-brand-navy);
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

@media (min-width: 768px) {
  .activate-wrapper {
    padding: 2rem;
  }

  .activate-card {
    padding: 2.25rem 2.25rem;
  }
}
</style>
