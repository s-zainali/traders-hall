import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [tailwindcss(), vueDevTools(), vue()],
    server: {
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env.VITE_WS_BASE_URL || 'ws://localhost:8000',
          ws: true,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: '../traders-hall-backend/dist',
      emptyOutDir: true,
    },
  }
})