<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()
</script>

<template>
  <section class="container-page" aria-labelledby="module-heading">
    <div class="card">
      <h1 id="module-heading">{{ route.meta.title || 'Panel Operativo' }}</h1>
      <p class="module-subtitle">
        Sesión iniciada como <strong>{{ authStore.userFullName }}</strong> ({{
          authStore.userRole
        }}).
      </p>
      <p v-if="authStore.userSector" class="module-sector">
        Sector asignado: <strong>{{ authStore.userSector.nombre || authStore.userSector }}</strong>
      </p>
      <p class="module-description">
        {{
          route.meta.description ||
          'Vista base del módulo lista para conectar con los componentes operativos.'
        }}
      </p>
    </div>
  </section>
</template>

<style scoped>
h1 {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
}

.module-subtitle,
.module-sector {
  margin: 0 0 0.5rem;
  color: var(--color-text);
}

.module-description {
  margin: 0.75rem 0 0;
  color: var(--color-text-muted);
}
</style>
