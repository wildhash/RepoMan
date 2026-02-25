import { useState, useEffect, useRef, useCallback } from 'react'
import { createWebSocket } from '../api'

export function useWebSocket(jobId) {
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState(null)
  const [connected, setConnected] = useState(false)
  const [currentPhase, setCurrentPhase] = useState(null)
  const [completedPhases, setCompletedPhases] = useState([])
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const shouldReconnectRef = useRef(true)

  const connect = useCallback(() => {
    if (!jobId) return

    const existing = wsRef.current
    if (
      existing &&
      (existing.readyState === WebSocket.OPEN ||
        existing.readyState === WebSocket.CONNECTING)
    ) {
      return
    }

    const ws = createWebSocket(jobId)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)

      if (!shouldReconnectRef.current) return
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = setTimeout(connect, 3000) // auto-reconnect
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (e) => {
      let payload
      try {
        payload = JSON.parse(e.data)
      } catch {
        return
      }

      if (payload.event === 'ping') return
      setMessages((prev) => [...prev, payload])

      if (payload.event === 'pipeline_started') {
        setStatus(null)
        setCurrentPhase(null)
        setCompletedPhases([])
      }

      if (payload.event === 'phase_started') {
        setCurrentPhase(payload.data?.phase)
      }
      if (payload.event === 'phase_completed') {
        const p = payload.data?.phase
        if (p) {
          setCompletedPhases((prev) => (prev.includes(p) ? prev : [...prev, p]))
        }
      }

      if (payload.event === 'pipeline_completed') {
        setStatus(payload.data?.status)
      }
    }
  }, [jobId])

  useEffect(() => {
    setMessages([])
    setStatus(null)
    setCurrentPhase(null)
    setCompletedPhases([])

    shouldReconnectRef.current = true
    connect()
    return () => {
      shouldReconnectRef.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  return { messages, status, connected, currentPhase, completedPhases }
}
