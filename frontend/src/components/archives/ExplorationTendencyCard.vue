<script setup lang="ts">
defineProps<{
  label: string
  description: string
}>()
</script>

<template>
  <section class="card tendency" aria-label="探索倾向">
    <h2 class="card__title">探索倾向</h2>
    <div class="tendency__viz" aria-hidden="true">
      <span class="tendency__ring tendency__ring--outer" />
      <span class="tendency__ring tendency__ring--inner" />
      <svg class="tendency__star" viewBox="0 0 48 48" width="40" height="40">
        <path
          fill="var(--plex-accent)"
          d="M24 4l5.2 14.8L44 24l-14.8 5.2L24 44l-5.2-14.8L4 24l14.8-5.2L24 4z"
        />
      </svg>
    </div>
    <p class="tendency__label">{{ label }}</p>
    <p class="tendency__desc">{{ description }}</p>
  </section>
</template>

<style scoped>
.card {
  border-radius: 1rem;
  border: 1px solid var(--plex-border);
  background: rgba(11, 22, 40, 0.72);
  backdrop-filter: blur(12px);
  padding: 1.1rem 1.25rem;
}

.card__title {
  margin: 0 0 0.85rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--plex-accent);
}

.tendency {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-height: 160px;
}

.tendency__viz {
  position: relative;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.65rem;
}

.tendency__ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(16, 240, 192, 0.25);
}

.tendency__ring--outer {
  inset: 0;
}

.tendency__ring--inner {
  inset: 18%;
  border-color: rgba(16, 240, 192, 0.15);
}

.tendency__star {
  filter: drop-shadow(0 0 12px rgba(16, 240, 192, 0.45));
}

.tendency__label {
  margin: 0 0 0.4rem;
  font-size: 0.95rem;
  font-weight: 700;
}

.tendency__desc {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--plex-muted);
  max-width: 16rem;
}
</style>
