import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const fallbackApiTarget = 'http://localhost:8000'
const rawApiTarget = process.env.REPOMAN_DEV_PROXY_TARGET ?? fallbackApiTarget

function resolveApiTarget(raw) {
  try {
    const candidate = raw.includes('://') ? raw : `http://${raw}`
    const url = new URL(candidate)
    return { apiTarget: candidate, apiUrl: url }
  } catch {
    console.warn(
      `Invalid REPOMAN_DEV_PROXY_TARGET="${raw}"; falling back to ${fallbackApiTarget}`,
    )
    const url = new URL(fallbackApiTarget)
    return { apiTarget: fallbackApiTarget, apiUrl: url }
  }
}

const { apiTarget, apiUrl } = resolveApiTarget(rawApiTarget)
const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
const wsTarget = `${wsProtocol}//${apiUrl.host}`

if (apiUrl.pathname !== '/' && process.env.REPOMAN_DEV_PROXY_TARGET) {
  console.warn(
    `REPOMAN_DEV_PROXY_TARGET path "${apiUrl.pathname}" is ignored for /ws proxying (using ${wsTarget})`,
  )
}

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
