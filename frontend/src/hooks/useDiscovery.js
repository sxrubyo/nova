import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export function useDiscovery(autoLoad = true) {
  const [agents, setAgents] = useState([])
  const [isLoading, setIsLoading] = useState(autoLoad)
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState('')
  const [lastScanAt, setLastScanAt] = useState(null)
  const [durationMs, setDurationMs] = useState(null)

  const load = async (force = false, { throwOnError = false } = {}) => {
    const endpoint = force ? '/discovery/scan' : '/discovery/agents'
    const startedAt = Date.now()
    setError('')
    if (force) setIsScanning(true)
    if (!force) setIsLoading(true)
    try {
      const response = await api.get(endpoint)
      setAgents(response.agents || [])
      setLastScanAt(response.last_scan_at || null)
      setDurationMs(response.duration_ms || null)
      return response
    } catch (loadError) {
      setError(loadError.message || 'Unable to load discovery data')
      if (throwOnError) {
        throw loadError
      }
    } finally {
      if (force) {
        const remaining = 900 - (Date.now() - startedAt)
        if (remaining > 0) {
          await new Promise((resolve) => window.setTimeout(resolve, remaining))
        }
      }
      setIsLoading(false)
      setIsScanning(false)
    }
  }

  useEffect(() => {
    if (!autoLoad) return undefined
    load(false)
    const timer = window.setInterval(() => {
      load(false)
    }, 60000)
    return () => window.clearInterval(timer)
  }, [autoLoad])

  const scanNow = async () => {
    return load(true, { throwOnError: true })
  }

  const connectAgent = async (agentKey, config = {}) => {
    await api.post(`/discovery/agents/${agentKey}/connect`, { config })
    await load(false)
  }

  const disconnectAgent = async (agentKey) => {
    await api.delete(`/discovery/agents/${agentKey}/disconnect`)
    await load(false)
  }

  const getAgentStatus = async (agentKey) => {
    return api.get(`/discovery/agents/${agentKey}/status`)
  }

  const getAgentLogs = async (agentKey, limit = 100) => {
    return api.get(`/discovery/agents/${agentKey}/logs?limit=${limit}`)
  }

  return {
    agents,
    connectedAgents: agents.filter((agent) => agent.metadata?.connected),
    isLoading,
    isScanning,
    error,
    lastScanAt,
    durationMs,
    scanNow,
    connectAgent,
    disconnectAgent,
    getAgentStatus,
    getAgentLogs,
    refresh: load,
  }
}
