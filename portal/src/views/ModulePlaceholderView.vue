<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section class="container-page" aria-labelledby="module-heading">
    <div class="card">
      <h1 id="module-heading">{{ route.meta.title || 'Panel Operativo' }}</h1>
      <p class="module-description">
        {{
          route.meta.description ||
          'Sección operativa del sistema de gestión del servicio de alimentación.'
        }}
      </p>
    </div>
  </section>
</template>

<style scoped>
h1 {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
  color: var(--color-brand-deep);
}

.module-description {
  margin: 0;
  color: var(--color-text-muted);
}
</style>
