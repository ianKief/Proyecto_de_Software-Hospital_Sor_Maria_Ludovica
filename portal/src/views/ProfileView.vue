<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { validateProfileForm } from '@/utils/validators'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const loadingProfile = ref(false)
const generalError = ref('')

const form = reactive({
  nombre: '',
  apellido: '',
  email: '',
  dni: '',
  password: '',
  passwordConfirm: '',
})

const fieldErrors = reactive({
  nombre: '',
  apellido: '',
  email: '',
  dni: '',
  password: '',
  password_confirm: '',
})

const isSaving = computed(() => authStore.loading || loadingProfile.value)

const userInitials = computed(() => {
  const n = (authStore.user?.nombre || '')[0] || ''
  const a = (authStore.user?.apellido || '')[0] || ''
  return `${n}${a}`.toUpperCase() || 'U'
})

const sectorDisplay = computed(() => {
  const s = authStore.userSector
  if (!s) return 'No asignado / Aplica a todo el hospital'
  return typeof s === 'object' ? s.nombre || 'Sin nombre' : String(s)
})

function syncFormFromStore() {
  const u = authStore.user
  if (!u) return
  form.nombre = u.nombre || ''
  form.apellido = u.apellido || ''
  form.email = u.email || ''
  form.dni = u.dni || ''
  form.password = ''
  form.passwordConfirm = ''
}

function clearErrors() {
  generalError.value = ''
  for (const key of Object.keys(fieldErrors)) {
    fieldErrors[key] = ''
  }
}

async function refreshProfile() {
  loadingProfile.value = true
  clearErrors()
  try {
    await authStore.fetchCurrentUser()
    syncFormFromStore()
  } catch (error) {
    generalError.value =
      error?.message || 'No se pudieron obtener los datos actualizados de tu perfil.'
  } finally {
    loadingProfile.value = false
  }
}

async function handleSaveProfile() {
  clearErrors()

  const { isValid, errors } = validateProfileForm(form)
  if (!isValid) {
    for (const [key, msg] of Object.entries(errors)) {
      if (key in fieldErrors) {
        fieldErrors[key] = msg
      }
    }
    return
  }

  const payload = {
    nombre: form.nombre.trim(),
    apellido: form.apellido.trim(),
    email: form.email.trim(),
    dni: form.dni.trim(),
  }

  if (form.password) {
    payload.password = form.password
    payload.password_confirm = form.passwordConfirm
  }

  try {
    const response = await authStore.updateProfile(payload)
    syncFormFromStore()
    uiStore.notify({
      type: 'success',
      message: response?.message || 'Tus datos de perfil se actualizaron correctamente.',
    })
  } catch (error) {
    if (error?.fieldErrors) {
      for (const [key, msg] of Object.entries(error.fieldErrors)) {
        if (key in fieldErrors) {
          fieldErrors[key] = msg
        }
      }
    }
    generalError.value =
      error?.message || 'No se pudieron guardar los cambios. Revisá los campos ingresados.'
  }
}

function goBackHome() {
  router.push(authStore.homeRouteByRole)
}

onMounted(() => {
  syncFormFromStore()
  refreshProfile()
})
</script>

<template>
  <section class="container-page profile-page" aria-labelledby="profile-heading">
    <div class="profile-header-bar">
      <div>
        <span class="section-pill">Cuenta Operativa</span>
        <h1 id="profile-heading">Mi perfil</h1>
        <p class="section-subtitle">
          Consultá tu información institucional y actualizá tus datos personales o tu contraseña.
        </p>
      </div>
      <button type="button" class="btn btn-secondary" @click="goBackHome">
        ← Volver a mi panel
      </button>
    </div>

    <div class="profile-grid">
      <!-- Tarjeta de resumen institucional (solo lectura para rol y sector) -->
      <aside class="card summary-card" aria-label="Resumen de tu cuenta">
        <div class="avatar-circle" aria-hidden="true">{{ userInitials }}</div>
        <h2 class="summary-name">{{ authStore.userFullName }}</h2>
        <p class="summary-email">{{ authStore.user?.email }}</p>

        <dl class="summary-details">
          <div class="detail-row">
            <dt>Rol en el sistema</dt>
            <dd>
              <span class="role-tag">{{ authStore.userRole }}</span>
            </dd>
          </div>
          <div class="detail-row">
            <dt>DNI registrado</dt>
            <dd>{{ authStore.user?.dni || '—' }}</dd>
          </div>
          <div v-if="authStore.isJefeServicio || authStore.userSector" class="detail-row">
            <dt>Sector asignado</dt>
            <dd>{{ sectorDisplay }}</dd>
          </div>
          <div class="detail-row">
            <dt>Estado de la cuenta</dt>
            <dd>
              <span class="status-active">Activo</span>
            </dd>
          </div>
        </dl>

        <p class="summary-note">
          El rol y el sector asignado son administrados exclusivamente por el Administrador del
          sistema.
        </p>
      </aside>

      <!-- Formulario de edición de datos personales y contraseña -->
      <div class="card form-card">
        <h2 class="form-card-title">Editar información personal</h2>

        <div
          v-if="generalError"
          class="alert alert-error profile-alert"
          role="alert"
          aria-live="assertive"
        >
          <span>{{ generalError }}</span>
        </div>

        <form novalidate @submit.prevent="handleSaveProfile">
          <div class="fields-two-cols">
            <div class="form-group">
              <label for="profile-nombre" class="form-label">Nombre</label>
              <input
                id="profile-nombre"
                v-model="form.nombre"
                type="text"
                name="nombre"
                autocomplete="given-name"
                class="form-input"
                :aria-invalid="fieldErrors.nombre ? 'true' : 'false'"
                :aria-describedby="fieldErrors.nombre ? 'profile-nombre-error' : undefined"
                :disabled="isSaving"
                required
                @input="fieldErrors.nombre = ''"
              />
              <p
                v-if="fieldErrors.nombre"
                id="profile-nombre-error"
                class="field-error"
                role="alert"
              >
                {{ fieldErrors.nombre }}
              </p>
            </div>

            <div class="form-group">
              <label for="profile-apellido" class="form-label">Apellido</label>
              <input
                id="profile-apellido"
                v-model="form.apellido"
                type="text"
                name="apellido"
                autocomplete="family-name"
                class="form-input"
                :aria-invalid="fieldErrors.apellido ? 'true' : 'false'"
                :aria-describedby="fieldErrors.apellido ? 'profile-apellido-error' : undefined"
                :disabled="isSaving"
                required
                @input="fieldErrors.apellido = ''"
              />
              <p
                v-if="fieldErrors.apellido"
                id="profile-apellido-error"
                class="field-error"
                role="alert"
              >
                {{ fieldErrors.apellido }}
              </p>
            </div>
          </div>

          <div class="fields-two-cols">
            <div class="form-group">
              <label for="profile-email" class="form-label">Correo electrónico</label>
              <input
                id="profile-email"
                v-model="form.email"
                type="email"
                name="email"
                autocomplete="email"
                class="form-input"
                :aria-invalid="fieldErrors.email ? 'true' : 'false'"
                :aria-describedby="fieldErrors.email ? 'profile-email-error' : undefined"
                :disabled="isSaving"
                required
                @input="fieldErrors.email = ''"
              />
              <p v-if="fieldErrors.email" id="profile-email-error" class="field-error" role="alert">
                {{ fieldErrors.email }}
              </p>
            </div>

            <div class="form-group">
              <label for="profile-dni" class="form-label">DNI (solo números)</label>
              <input
                id="profile-dni"
                v-model="form.dni"
                type="text"
                inputmode="numeric"
                name="dni"
                placeholder="Ej: 30111222"
                class="form-input"
                :aria-invalid="fieldErrors.dni ? 'true' : 'false'"
                :aria-describedby="fieldErrors.dni ? 'profile-dni-error' : undefined"
                :disabled="isSaving"
                required
                @input="fieldErrors.dni = ''"
              />
              <p v-if="fieldErrors.dni" id="profile-dni-error" class="field-error" role="alert">
                {{ fieldErrors.dni }}
              </p>
            </div>
          </div>

          <hr class="section-divider" />

          <div class="password-section-header">
            <h3>Cambiar contraseña (opcional)</h3>
            <p>Dejá estos campos en blanco si deseás conservar tu contraseña actual.</p>
          </div>

          <div class="fields-two-cols">
            <div class="form-group">
              <label for="profile-password" class="form-label">Nueva contraseña</label>
              <input
                id="profile-password"
                v-model="form.password"
                type="password"
                name="password"
                autocomplete="new-password"
                placeholder="Mínimo 6 caracteres"
                class="form-input"
                :aria-invalid="fieldErrors.password ? 'true' : 'false'"
                :aria-describedby="fieldErrors.password ? 'profile-password-error' : undefined"
                :disabled="isSaving"
                @input="fieldErrors.password = ''"
              />
              <p
                v-if="fieldErrors.password"
                id="profile-password-error"
                class="field-error"
                role="alert"
              >
                {{ fieldErrors.password }}
              </p>
            </div>

            <div class="form-group">
              <label for="profile-password-confirm" class="form-label">
                Confirmar nueva contraseña
              </label>
              <input
                id="profile-password-confirm"
                v-model="form.passwordConfirm"
                type="password"
                name="password_confirm"
                autocomplete="new-password"
                placeholder="Repetí la nueva contraseña"
                class="form-input"
                :aria-invalid="fieldErrors.password_confirm ? 'true' : 'false'"
                :aria-describedby="
                  fieldErrors.password_confirm ? 'profile-password-confirm-error' : undefined
                "
                :disabled="isSaving"
                @input="fieldErrors.password_confirm = ''"
              />
              <p
                v-if="fieldErrors.password_confirm"
                id="profile-password-confirm-error"
                class="field-error"
                role="alert"
              >
                {{ fieldErrors.password_confirm }}
              </p>
            </div>
          </div>

          <div class="form-actions">
            <button
              type="button"
              class="btn btn-secondary"
              :disabled="isSaving"
              @click="syncFormFromStore"
            >
              Restaurar valores
            </button>
            <button type="submit" class="btn btn-primary" :disabled="isSaving">
              {{ isSaving ? 'Guardando cambios...' : 'Guardar cambios' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.profile-header-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.section-pill {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background-color: var(--color-brand-teal-soft);
  border: 1px solid var(--color-brand-teal);
  color: var(--color-brand-deep);
  font-size: 0.75rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}

.profile-header-bar h1 {
  margin: 0 0 0.25rem;
  font-size: 1.65rem;
  color: var(--color-brand-deep);
}

.section-subtitle {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.95rem;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
  align-items: start;
}

.summary-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.avatar-circle {
  width: 4.5rem;
  height: 4.5rem;
  border-radius: 999px;
  background: linear-gradient(145deg, var(--color-brand-navy) 0%, var(--color-brand-deep) 100%);
  border: 3px solid var(--color-brand-teal);
  color: #ffffff;
  font-size: 1.5rem;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.75rem;
}

.summary-name {
  margin: 0 0 0.2rem;
  font-size: 1.25rem;
  color: var(--color-brand-deep);
}

.summary-email {
  margin: 0 0 1.25rem;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.summary-details {
  width: 100%;
  margin: 0;
  padding: 1rem 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  text-align: left;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.detail-row dt {
  color: var(--color-text-muted);
  font-weight: 600;
}

.detail-row dd {
  margin: 0;
  font-weight: 700;
  color: var(--color-brand-navy);
}

.role-tag {
  display: inline-block;
  padding: 0.15rem 0.65rem;
  border-radius: 999px;
  background-color: var(--color-brand-teal-soft);
  border: 1px solid var(--color-brand-teal);
  color: var(--color-brand-deep);
  font-size: 0.8rem;
}

.status-active {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  background-color: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
  color: var(--color-success);
  font-size: 0.8rem;
}

.summary-note {
  margin: 1rem 0 0;
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.form-card-title {
  margin: 0 0 1.25rem;
  font-size: 1.25rem;
  color: var(--color-brand-deep);
}

.profile-alert {
  margin-bottom: 1.25rem;
}

.fields-two-cols {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0 1rem;
}

.section-divider {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 1rem 0 1.25rem;
}

.password-section-header {
  margin-bottom: 1rem;
}

.password-section-header h3 {
  margin: 0 0 0.2rem;
  font-size: 1.05rem;
  color: var(--color-brand-navy);
}

.password-section-header p {
  margin: 0;
  font-size: 0.86rem;
  color: var(--color-text-muted);
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

/* Tablet (768px - 1024px) */
@media (min-width: 768px) {
  .fields-two-cols {
    grid-template-columns: 1fr 1fr;
  }
}

/* Escritorio (> 1025px) */
@media (min-width: 1025px) {
  .profile-grid {
    grid-template-columns: 340px 1fr;
  }
}
</style>
