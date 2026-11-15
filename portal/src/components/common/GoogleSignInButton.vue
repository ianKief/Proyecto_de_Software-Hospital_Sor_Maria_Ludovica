<script setup>
import { ref, onMounted } from 'vue'

defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['credential', 'error'])

const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim()
const googleButtonContainer = ref(null)
const googleSdkReady = ref(false)

function handleGoogleResponse(response) {
  const idToken = response?.credential
  if (!idToken) {
    emit('error', 'No se recibió la credencial de Google. Intentá nuevamente.')
    return
  }
  emit('credential', idToken)
}

function handleFallbackClick() {
  emit(
    'error',
    'Para usar el inicio de sesión con Google, configurá la variable VITE_GOOGLE_CLIENT_ID en portal/.env y GOOGLE_CLIENT_ID en admin/.env.',
  )
}

function initGoogleIdentityServices() {
  if (!googleClientId) return

  const renderButton = () => {
    if (!window.google?.accounts?.id || !googleButtonContainer.value) return
    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: handleGoogleResponse,
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
  <div class="google-auth-section">
    <div
      v-if="googleClientId"
      ref="googleButtonContainer"
      class="google-gsi-container"
    ></div>

    <button
      v-if="!googleClientId || !googleSdkReady"
      type="button"
      class="btn btn-secondary google-fallback-btn"
      :disabled="disabled"
      @click="handleFallbackClick"
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
</template>

<style scoped>
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
</style>
