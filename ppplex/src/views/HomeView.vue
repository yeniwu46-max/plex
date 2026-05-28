<script setup lang="ts">
import { useRouter } from 'vue-router'
import DefenseHeader from '../components/DefenseHeader.vue'
import DemoLink from '../components/DemoLink.vue'
import ScreenshotFrame from '../components/ScreenshotFrame.vue'
import { useManifest } from '../composables/useManifest'

const router = useRouter()
const { manifest } = useManifest()

function openPage(pageId: string) {
  router.push({ name: 'page', params: { pageId } })
}
</script>

<template>
  <DefenseHeader :title="manifest.meta.title" :subtitle="manifest.meta.tagline" />

  <div class="content-wrap">
    <section class="card hero-card">
      <p class="pitch">{{ manifest.meta.subtitle }}</p>
      <div class="hero-actions">
        <button type="button" class="btn" @click="openPage('script')">答辩脚本</button>
        <button type="button" class="btn" @click="openPage('features')">功能演示</button>
        <DemoLink path="/login" label="登录页演示" />
      </div>
    </section>

    <section class="card">
      <h2>答辩时长</h2>
      <div class="duration-grid">
        <button type="button" class="duration-card" @click="openPage('script')">
          <strong>5 分钟</strong>
          <span>速览三屏</span>
        </button>
        <button type="button" class="duration-card duration-card--active" @click="openPage('script')">
          <strong>10 分钟</strong>
          <span>推荐标准场</span>
        </button>
        <button type="button" class="duration-card" @click="openPage('script')">
          <strong>15 分钟</strong>
          <span>含架构与边界</span>
        </button>
      </div>
    </section>

    <section class="card">
      <h2>快速入口</h2>
      <div class="page-chips">
        <button
          v-for="page in manifest.pages"
          :key="page.id"
          type="button"
          class="chip"
          @click="openPage(page.id)"
        >
          {{ page.title }}
        </button>
      </div>
    </section>

    <section class="card">
      <h2>界面一览</h2>
      <div class="screenshot-grid">
        <div
          v-for="shot in manifest.screenshots"
          :key="shot.file"
          class="screenshot-thumb"
        >
          <ScreenshotFrame :file="shot.file" :alt="shot.label" />
          <span>{{ shot.label }}</span>
          <DemoLink :path="shot.route" label="演示" />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero-card .hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.duration-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

@media (max-width: 600px) {
  .duration-grid {
    grid-template-columns: 1fr;
  }
}

.duration-card {
  border: 1px solid var(--plex-border);
  border-radius: 10px;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.25);
  color: var(--plex-text);
  text-align: left;
}

.duration-card strong {
  display: block;
  font-size: 1.2rem;
  color: var(--plex-student);
}

.duration-card span {
  font-size: 0.85rem;
  color: var(--plex-muted);
}

.duration-card--active {
  border-color: var(--plex-student);
  box-shadow: 0 0 24px var(--plex-glow);
}

.page-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--plex-border);
  background: rgba(16, 185, 129, 0.08);
  color: var(--plex-student);
}

.screenshot-thumb .btn {
  margin: 0.4rem 0.6rem 0.6rem;
  font-size: 0.8rem;
}
</style>
