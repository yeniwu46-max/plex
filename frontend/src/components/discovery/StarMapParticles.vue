<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
let frameId = 0
let particles: Array<{
  x: number
  y: number
  vx: number
  vy: number
  size: number
  alpha: number
  hue: number
}> = []

function initParticles(width: number, height: number) {
  const count = Math.min(120, Math.floor((width * height) / 12000))
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.14,
    vy: (Math.random() - 0.5) * 0.14,
    size: Math.random() * 1.8 + 0.4,
    alpha: Math.random() * 0.55 + 0.15,
    hue: Math.random() > 0.75 ? 280 : 175,
  }))
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const { width, height } = canvas
  ctx.clearRect(0, 0, width, height)

  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0) p.x = width
    if (p.x > width) p.x = 0
    if (p.y < 0) p.y = height
    if (p.y > height) p.y = 0

    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${p.hue}, 100%, 72%, ${p.alpha})`
    ctx.fill()
  }

  frameId = requestAnimationFrame(draw)
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas?.parentElement) return
  const rect = canvas.parentElement.getBoundingClientRect()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.max(1, Math.floor(rect.width * dpr))
  canvas.height = Math.max(1, Math.floor(rect.height * dpr))
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  initParticles(canvas.width, canvas.height)
}

onMounted(() => {
  resize()
  draw()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frameId)
  window.removeEventListener('resize', resize)
})
</script>

<template>
  <canvas ref="canvasRef" class="star-map-particles" aria-hidden="true" />
</template>

<style scoped>
.star-map-particles {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  opacity: 0.85;
}
</style>
