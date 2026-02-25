const API_BASE = '/api'
const WS_BASE = (window.location.protocol === 'https:' ? 'wss' : 'ws') + `://${window.location.host}`

export async function startTransform(repoUrl) {
  const res = await fetch(`${API_BASE}/repos/transform`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getJob(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getTranscript(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/transcript`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function createWebSocket(jobId) {
  return new WebSocket(`${WS_BASE}/ws/jobs/${jobId}`)
}
