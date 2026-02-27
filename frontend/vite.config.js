import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'
const apiUrl = new URL(apiTarget)
const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
const wsTarget = `${wsProtocol}//${apiUrl.host}`

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': apiTarget,
      '/ws': { target: wsTarget, ws: true },
    },
  },
})
