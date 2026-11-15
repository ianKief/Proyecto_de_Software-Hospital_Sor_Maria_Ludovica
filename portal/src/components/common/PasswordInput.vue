<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  id: {
    type: String,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
  name: {
    type: String,
    default: 'password',
  },
  autocomplete: {
    type: String,
    default: 'current-password',
  },
  placeholder: {
    type: String,
    default: '',
  },
  error: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  required: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const showPassword = ref(false)
const errorId = computed(() => `${props.id}-error`)

function onInput(event) {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <div class="form-group">
    <label :for="id" class="form-label">{{ label }}</label>
    <div class="password-input-wrapper">
      <input
        :id="id"
        :value="modelValue"
        :type="showPassword ? 'text' : 'password'"
        :name="name"
        :autocomplete="autocomplete"
        :placeholder="placeholder"
        class="form-input password-input"
        :aria-invalid="error ? 'true' : 'false'"
        :aria-describedby="error ? errorId : undefined"
        :disabled="disabled"
        :required="required"
        @input="onInput"
      />
      <button
        type="button"
        class="password-eye-btn"
        :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
        :aria-pressed="showPassword ? 'true' : 'false'"
        :disabled="disabled"
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
    <p v-if="error" :id="errorId" class="field-error" role="alert">
      {{ error }}
    </p>
  </div>
</template>

<style scoped>
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
</style>
