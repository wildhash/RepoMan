import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const fallbackApiTarget = 'http://localhost:8000'
const rawApiTarget = process.env.REPOMAN_DEV_PROXY_TARGET ?? fallbackApiTarget

let apiTarget = rawApiTarget.includes('://') ? rawApiTarget : `http://${rawApiTarget}`
let apiUrl

try {
  apiUrl = new URL(apiTarget)
} catch {
  apiTarget = fallbackApiTarget
  apiUrl = new URL(apiTarget)
}
const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
const wsTarget = `${wsProtocol}//${apiUrl.host}${apiUrl.pathname === '/' ? '' : apiUrl.pathname}`

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
