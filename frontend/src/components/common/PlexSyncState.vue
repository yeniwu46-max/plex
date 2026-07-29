<script setup lang="ts">
withDefaults(
  defineProps<{
    label?: string
    hint?: string
    compact?: boolean
  }>(),
  {
    label: '正在同步…',
    hint: '',
    compact: false,
  },
)
</script>

<template>
  <div class="plex-sync" :class="{ 'plex-sync--compact': compact }" role="status" aria-live="polite">
    <div class="plex-sync__orb" aria-hidden="true">
      <span class="plex-sync__ring plex-sync__ring--a" />
      <span class="plex-sync__ring plex-sync__ring--b" />
      <span class="plex-sync__core" />
    </div>
    <div class="plex-sync__copy">
      <strong>{{ label }}</strong>
      <p v-if="hint">{{ hint }}</p>
      <div class="plex-sync__bar" aria-hidden="true">
        <span />
      </div>
    </div>
  </div>
</template>

<style scoped>
.plex-sync {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1rem var(--plex-page-gutter-x, 1.25rem);
  padding: 1.15rem 1.25rem;
  border: 1px solid rgba(37, 245, 238, 0.18);
  border-radius: 1rem;
  background:
    radial-gradient(circle at 12% 20%, rgba(37, 245, 238, 0.12), transparent 42%),
    linear-gradient(135deg, rgba(4, 18, 30, 0.92), rgba(3, 12, 22, 0.88));
  color: rgba(215, 230, 242, 0.88);
}

.plex-sync--compact {
  margin: 0.75rem 0;
  padding: 0.9rem 1rem;
}

.plex-sync__orb {
  position: relative;
  width: 2.75rem;
  height: 2.75rem;
  flex: 0 0 auto;
}

.plex-sync__ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid transparent;
}

.plex-sync__ring--a {
  border-top-color: #25f5ee;
  border-right-color: rgba(37, 245, 238, 0.35);
  animation: plex-spin 1.1s linear infinite;
}

.plex-sync__ring--b {
  inset: 0.35rem;
  border-bottom-color: #7dd3fc;
  border-left-color: rgba(125, 211, 252, 0.3);
  animation: plex-spin 1.6s linear infinite reverse;
}

.plex-sync__core {
  position: absolute;
  inset: 0.85rem;
  border-radius: 50%;
  background: radial-gradient(circle, #52fff1 0%, rgba(37, 245, 238, 0.2) 70%, transparent 100%);
  animation: plex-pulse 1.4s ease-in-out infinite;
}

.plex-sync__copy {
  min-width: 0;
  flex: 1;
}

.plex-sync__copy strong {
  display: block;
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #e8fbff;
}

.plex-sync__copy p {
  margin: 0.25rem 0 0;
  font-size: 0.82rem;
  color: rgba(170, 205, 220, 0.72);
}

.plex-sync__bar {
  margin-top: 0.65rem;
  height: 3px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(37, 245, 238, 0.12);
}

.plex-sync__bar span {
  display: block;
  width: 38%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, transparent, #25f5ee, #7dd3fc, transparent);
  animation: plex-shimmer 1.35s ease-in-out infinite;
}

@keyframes plex-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes plex-pulse {
  0%,
  100% {
    opacity: 0.55;
    transform: scale(0.92);
  }
  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

@keyframes plex-shimmer {
  0% {
    transform: translateX(-120%);
  }
  100% {
    transform: translateX(320%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .plex-sync__ring--a,
  .plex-sync__ring--b,
  .plex-sync__core,
  .plex-sync__bar span {
    animation: none;
  }
}
</style>
