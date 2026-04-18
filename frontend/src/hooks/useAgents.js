import { useEffect } from 'react'
import { useAgentsStore } from '@/stores/app-stores'

export function useAgents() {
  const fetchAgents = useAgentsStore((state) => state.fetchAgents)
  const store = useAgentsStore()

  useEffect(() => {
    fetchAgents()
  }, [fetchAgents])

  return store
}
