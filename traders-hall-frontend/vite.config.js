import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      // Anything starting /api is forwarded to the backend, so the frontend
      // only ever uses relative URLs. Two things fall out of that: no CORS in
      // development (the browser sees one origin), and the same code works in
      // production where a reverse proxy does the same job.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // WebSockets, once they exist. ws:true is required — without it the
      // upgrade handshake is proxied as a plain HTTP request and fails.
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})