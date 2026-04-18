import { useEffect } from 'react'
import { useAuthStore } from '@/stores/app-stores'

export function useAuth() {
  const initialize = useAuthStore((state) => state.initialize)
  const isLoading = useAuthStore((state) => state.isLoading)
  const store = useAuthStore()

  useEffect(() => {
    if (isLoading) {
      initialize()
    }
  }, [initialize, isLoading])

  return store
}
