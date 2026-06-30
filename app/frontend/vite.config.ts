import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, the browser hits the Vite server (5173) which proxies /api to the API.
// Inside Compose this target is the `api` service; locally it's localhost.
const apiProxy = process.env.VITE_API_PROXY || 'http://localhost:8080'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': { target: apiProxy, changeOrigin: true },
      '/healthz': { target: apiProxy, changeOrigin: true },
    },
  },
})
