import { useEffect, useRef, useState } from 'react'
import { SERVER_ORIGIN } from '@/config/appConfig'

function getWebSocketUrl() {
  const origin = SERVER_ORIGIN || window.location.origin
  if (origin.startsWith('https://')) return `${origin.replace('https://', 'wss://')}/ws/events`
  if (origin.startsWith('http://')) return `${origin.replace('http://', 'ws://')}/ws/events`
  return `ws://${window.location.host}/ws/events`
}

export function useNovaEvents() {
  const [events, setEvents] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const reconnectRef = useRef(null)

  useEffect(() => {
    let socket = null
    let cancelled = false

    const connect = () => {
      socket = new WebSocket(getWebSocketUrl())

      socket.onopen = () => {
        if (cancelled) return
        setIsConnected(true)
      }

      socket.onmessage = (message) => {
        if (cancelled) return
        try {
          const parsed = JSON.parse(message.data)
          setLastEvent(parsed)
          setEvents((current) => [parsed, ...current].slice(0, 100))
        } catch {
          // Ignore malformed event payloads.
        }
      }

      socket.onclose = () => {
        if (cancelled) return
        setIsConnected(false)
        reconnectRef.current = window.setTimeout(connect, 1500)
      }

      socket.onerror = () => {
        socket?.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      setIsConnected(false)
      window.clearTimeout(reconnectRef.current)
      socket?.close()
    }
  }, [])

  return { events, isConnected, lastEvent }
}
