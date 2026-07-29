import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_PROXY || 'http://127.0.0.1:5100'
  const devPort = Number(env.VITE_DEV_PORT || 5180)

  return {
    plugins: [vue()],
    build: {
      manifest: true,
      // G6 is a route-level dynamic dependency. A dedicated gzip budget below
      // provides a more meaningful gate than Vite's raw-size-only warning.
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes('naive-ui') || id.includes('@vicons')) return 'ui'
            if (id.includes('echarts') || id.includes('zrender')) return 'charts'
            if (id.includes('monaco-editor')) return 'monaco'
            if (id.includes('@antv/g6')) return 'g6'
            if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) return 'vue-vendor'
          },
        },
      },
    },
    server: {
      port: devPort,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
