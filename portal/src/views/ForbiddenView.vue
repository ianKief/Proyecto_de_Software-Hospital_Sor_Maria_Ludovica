<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function irAlInicio() {
  router.push(authStore.homeRouteByRole)
}
</script>

<template>
  <section class="container-page" aria-labelledby="forbidden-title">
    <div class="card forbidden-card">
      <div class="status-badge" aria-hidden="true">403</div>
      <h1 id="forbidden-title">Acceso denegado</h1>
      <p class="forbidden-text">
        Tu rol actual (<strong>{{ authStore.userRole || 'Sin rol' }}</strong>) no tiene permisos
        para acceder a esta sección del sistema.
      </p>
      <div class="actions">
        <button type="button" class="btn btn-primary" @click="irAlInicio">
          Ir a mi pantalla principal
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.forbidden-card {
  max-width: 540px;
  margin: 3rem auto;
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background-color: var(--color-danger-bg);
  color: var(--color-danger);
  font-weight: 700;
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

h1 {
  margin: 0 0 0.75rem;
  font-size: 1.6rem;
}

.forbidden-text {
  color: var(--color-text-muted);
  margin: 0 0 1.5rem;
}

.actions {
  display: flex;
  justify-content: center;
}
</style>
