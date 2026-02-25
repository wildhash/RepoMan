import { useState, useEffect, useRef, useCallback } from 'react'
import { createWebSocket } from '../api'

export function useWebSocket(jobId) {
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  const connect = useCallback(() => {
    if (!jobId) return
    const ws = createWebSocket(jobId)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setTimeout(connect, 3000) // auto-reconnect
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (e) => {
      const payload = JSON.parse(e.data)
      if (payload.event === 'ping') return
      setMessages((prev) => [...prev, payload])
      if (payload.event === 'pipeline_completed') {
        setStatus(payload.data?.status)
      }
    }
  }, [jobId])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { messages, status, connected }
}
