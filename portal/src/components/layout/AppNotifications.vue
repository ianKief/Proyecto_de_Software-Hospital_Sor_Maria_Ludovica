<script setup>
/**
 * Región global de alertas y notificaciones flotantes (información, éxito, advertencia y error).
 * Se alimenta del estado reactivo de `useUiStore()`.
 */
import { useUiStore } from '@/stores/ui'

const uiStore = useUiStore()
</script>

<template>
  <div
    v-if="uiStore.notifications.length > 0"
    class="notifications-stack container-page"
    aria-live="polite"
  >
    <div
      v-for="item in uiStore.notifications"
      :key="item.id"
      class="alert"
      :class="{
        'alert-error': item.type === 'error',
        'alert-success': item.type === 'success',
        'alert-warning': item.type === 'warning',
        'alert-info': item.type === 'info',
      }"
      :role="item.type === 'error' ? 'alert' : 'status'"
    >
      <span>{{ item.message }}</span>
      <button
        type="button"
        class="alert-close-btn"
        aria-label="Cerrar mensaje"
        @click="uiStore.dismissNotification(item.id)"
      >
        ✕
      </button>
    </div>
  </div>
</template>

<style scoped>
.notifications-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-bottom: 0;
}

.alert-close-btn {
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  min-width: 36px;
  min-height: 36px;
  font-size: 1rem;
  font-weight: 700;
}
</style>
