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
