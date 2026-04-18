import { useEffect } from 'react'
import { useGatewayStore } from '@/stores/app-stores'

export function useGateway() {
  const fetchGatewayStatus = useGatewayStore((state) => state.fetchGatewayStatus)
  const store = useGatewayStore()

  useEffect(() => {
    fetchGatewayStatus()
  }, [fetchGatewayStatus])

  return store
}
