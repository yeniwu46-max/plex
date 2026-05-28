import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@defense': fileURLToPath(new URL('../docs/defense', import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 5174,
    strictPort: false,
    open: true,
  },
  preview: {
    host: true,
    port: 5174,
    strictPort: false,
  },
})
