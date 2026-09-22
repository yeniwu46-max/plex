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
            const moduleId = id.replaceAll('\\', '/')
            // 不把整个 Naive UI / ECharts 依赖树强制塞进首屏共享 chunk：
            // 这些组件只在教师/成长页使用，交给 Rollup 按路由拆分，避免首屏预算被离线页面依赖拖垮。
            if (id.includes('monaco-editor')) return 'monaco'
            if (id.includes('@antv/g6')) return 'g6'
            if (
              moduleId.includes('/node_modules/vue/')
              || moduleId.includes('/node_modules/pinia/')
              || moduleId.includes('/node_modules/vue-router/')
            ) return 'vue-vendor'
          },
        },
      },
    },
    server: {
      port: devPort,
      strictPort: true,
      // Allow temporary public tunnels (Cloudflare / Pinggy / localtunnel).
      allowedHosts: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
