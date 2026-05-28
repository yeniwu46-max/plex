<script setup lang="ts">
import { computed } from 'vue'
import DefenseHeader from '../components/DefenseHeader.vue'
import DefenseSection from '../components/DefenseSection.vue'
import ScreenshotFrame from '../components/ScreenshotFrame.vue'
import DemoLink from '../components/DemoLink.vue'
import { useManifest } from '../composables/useManifest'

const props = defineProps<{
  pageId: string
}>()

const { manifest, sectionById } = useManifest()

const page = computed(() => manifest.pages.find((p) => p.id === props.pageId))

const sections = computed(() => {
  if (!page.value) return []
  return page.value.sections
    .map((id) => sectionById(id))
    .filter((s): s is NonNullable<typeof s> => Boolean(s))
})

function extendedSteps(sectionId: string) {
  const section = sectionById(sectionId)
  if (!section?.extends) return undefined
  const base = sectionById(section.extends)
  if (!base?.steps) return section.steps
  return [...base.steps, ...(section.steps ?? [])]
}
</script>

<template>
  <template v-if="page">
    <DefenseHeader :title="page.title" :subtitle="manifest.meta.tagline" />

    <div class="content-wrap">
      <DefenseSection
        v-for="section in sections"
        :key="section.id"
        :section="section"
        :extended-steps="extendedSteps(section.id)"
      />

      <section v-if="pageId === 'features'" class="card">
        <h2>全部截图</h2>
        <div class="screenshot-grid">
          <div
            v-for="shot in manifest.screenshots"
            :key="shot.file"
            class="screenshot-thumb"
          >
            <ScreenshotFrame :file="shot.file" :alt="shot.label" />
            <span>{{ shot.label }}</span>
            <DemoLink :path="shot.route" />
          </div>
        </div>
      </section>
    </div>
  </template>

  <div v-else class="content-wrap">
    <p>页面不存在</p>
  </div>
</template>

<style scoped>
.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}
</style>
