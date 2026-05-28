<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useManifest } from '../composables/useManifest'

const { manifest } = useManifest()
const route = useRoute()
const router = useRouter()

const activePage = computed(() => {
  if (route.name === 'home') return 'home'
  return (route.params.pageId as string) || 'home'
})

function go(pageId: string) {
  if (pageId === 'home') router.push({ name: 'home' })
  else router.push({ name: 'page', params: { pageId } })
}
</script>

<template>
  <aside class="defense-nav" aria-label="答辩导航">
    <div class="defense-nav__brand">
      <svg viewBox="0 0 48 48" width="28" height="28" aria-hidden="true">
        <path fill="currentColor" d="M24 3l5.1 15.9L45 24l-15.9 5.1L24 45l-5.1-15.9L3 24l15.9-5.1L24 3z" />
        <path fill="#031019" d="M24 13l2.2 8.8L35 24l-8.8 2.2L24 35l-2.2-8.8L13 24l8.8-2.2L24 13z" />
      </svg>
      <div>
        <strong>PPPLEX</strong>
        <small>A3 答辩导航</small>
      </div>
    </div>

    <nav class="defense-nav__links">
      <button
        type="button"
        class="defense-nav__link"
        :class="{ 'defense-nav__link--active': activePage === 'home' }"
        @click="go('home')"
      >
        首页
      </button>
      <button
        v-for="page in manifest.pages"
        :key="page.id"
        type="button"
        class="defense-nav__link"
        :class="{ 'defense-nav__link--active': activePage === page.id }"
        @click="go(page.id)"
      >
        {{ page.title }}
      </button>
    </nav>

    <p class="defense-nav__hint">
      完整文稿见
      <code>docs/defense/A3-PLEX-答辩项目说明.md</code>
    </p>
  </aside>
</template>

<style scoped>
.defense-nav {
  background: #061220;
  border-right: 1px solid var(--plex-border);
  padding: 1.25rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.defense-nav__brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--plex-student);
}

.defense-nav__brand strong {
  display: block;
  font-size: 1.1rem;
  letter-spacing: 0.06em;
}

.defense-nav__brand small {
  color: var(--plex-muted);
  font-size: 0.72rem;
}

.defense-nav__links {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.defense-nav__link {
  text-align: left;
  padding: 0.55rem 0.75rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--plex-muted);
  transition: background 0.15s, color 0.15s;
}

.defense-nav__link:hover,
.defense-nav__link--active {
  background: rgba(16, 185, 129, 0.12);
  color: var(--plex-student);
}

.defense-nav__hint {
  margin-top: auto;
  font-size: 0.72rem;
  color: var(--plex-muted);
  line-height: 1.4;
}

.defense-nav__hint code {
  font-size: 0.68rem;
  word-break: break-all;
}

@media (max-width: 900px) {
  .defense-nav {
    border-right: none;
    border-bottom: 1px solid var(--plex-border);
  }
}
</style>
