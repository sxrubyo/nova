import { useState, useEffect, useContext } from 'react'
import { AuthContext } from '../pages/AuthContext'
import { SERVER_ORIGIN, API_BASE_PATH } from '../config/appConfig'

export const useStream = (agentName = null) => {
  const [events, setEvents] = useState([])
  const { apiKey } = useContext(AuthContext)

  useEffect(() => {
    const url = new URL(`${SERVER_ORIGIN}${API_BASE_PATH}/stream/events`)
    if (apiKey) {
      url.searchParams.append('x_api_key', apiKey)
    }
    if (agentName) url.searchParams.append('agent_name', agentName)

    const eventSource = new EventSource(url.toString(), { withCredentials: true })

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents((prev) => [data, ...prev].slice(0, 50))
      } catch (err) {
        console.error('SSE Parse Error:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('SSE Connection Error:', err)
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [apiKey, agentName])

  return events
}
