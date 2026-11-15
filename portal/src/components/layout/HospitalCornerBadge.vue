<template>
  <aside class="persistent-corner-logo" aria-label="Identidad institucional del hospital">
    <img
      src="/logo-hospital.png"
      alt="Hospital Interzonal de Agudos Especializado en Pediatría Sor María Ludovica"
      class="corner-logo-img"
    />
  </aside>
</template>

<style scoped>
.persistent-corner-logo {
  position: fixed;
  bottom: 0.75rem;
  right: 0.85rem;
  z-index: 25;
  background-color: rgba(255, 255, 255, 0.96);
  border: 1.5px solid var(--color-brand-teal);
  border-left: 4px solid var(--color-brand-navy);
  border-radius: var(--radius-md);
  padding: 0.3rem 0.65rem;
  box-shadow: var(--shadow-md);
  pointer-events: none;
  display: inline-flex;
  align-items: center;
}

.corner-logo-img {
  height: 34px;
  width: auto;
  object-fit: contain;
  display: block;
}

@media (max-width: 767px) {
  .corner-logo-img {
    height: 28px;
  }
}
</style>
